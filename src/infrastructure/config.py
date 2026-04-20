"""
config.py
=========
Central configuration module for the AI Engineering Bootcamp mini-project-04.

Responsibilities
----------------
- Resolves the project root and config directory at import time.
- Loads environment variables from the project-level ``.env`` file via
  ``python-dotenv``.
- Parses ``config/params.yaml`` and ``config/models.yaml`` into in-memory
  dictionaries that are consumed by the rest of the application.
- Exposes typed accessors and module-level constants for provider, LLM, and
  observability settings so callers never have to read raw YAML themselves.
- Provides :func:`validate` to assert that the active provider's API key is
  present in the environment before any network calls are made.
- Provides :func:`dump` to print a human-readable, non-secret summary of the
  resolved configuration (useful for debugging).
- Provides :class:`TokenCounter`, a thin wrapper around *tiktoken* that counts
  tokens for plain text strings and chat-message lists.

Module-level constants (private, accessed by public helpers)
------------------------------------------------------------
_PROJECT_ROOT       : pathlib.Path  – repository root (three levels above this file)
_CONFIG_DIR         : pathlib.Path  – ``<root>/config/``
_CONFIG             : dict          – parsed ``params.yaml``
_MODELS             : dict          – parsed ``models.yaml``
_PROVIDER           : str           – active LLM provider  (default: "openrouter")
_TIER               : str           – model quality tier    (default: "general")
_OPENROUTER_BASE_URL: str           – OpenRouter API base URL
_TEMPERATURE        : float         – sampling temperature  (default: 0.2)
_MAX_TOKENS         : int           – max tokens to generate (default: 3000)
_STREAMING          : bool          – whether to stream responses (default: False)
_CHAT_MODEL         : str | None    – resolved chat model ID for the active provider/tier
_OBSERVABILITY      : bool          – whether Langfuse observability is enabled (default: True)

Dependencies
------------
- ``dotenv``     : environment variable loading
- ``yaml``       : YAML parsing
- ``tiktoken``   : token counting (OpenAI BPE tokeniser)
- ``loguru``     : structured logging
- ``pathlib``    : filesystem path handling
"""

##===========================
## Import Required Libraries
##===========================
from dotenv import load_dotenv
import os
from typing import Dict,List,Any,Optional
import yaml
import tiktoken
from pathlib import Path
from loguru import logger

##==============================
## get project root directory
##==============================
_PROJECT_ROOT=Path(__file__).parent.parent.parent

##====================
## config directory
##====================
_CONFIG_DIR=_PROJECT_ROOT/"config"

##===========================
## load enviroment variables
##===========================
load_dotenv(dotenv_path=_PROJECT_ROOT/".env")

##=========================
## load yaml config files
##=========================
def _load_yaml(filename: str) -> Dict[str, Any]:
    """Load and parse a YAML configuration file from the config directory.

    Resolves *filename* relative to ``_CONFIG_DIR`` (``<project_root>/config/``),
    reads the file with UTF-8 encoding, and returns its contents as a plain
    Python dictionary.

    Parameters
    ----------
    filename : str
        Name of the YAML file to load (e.g. ``"params.yaml"``).  Only the
        bare filename is required — the config directory is prepended
        automatically.

    Returns
    -------
    Dict[str, Any]
        Parsed YAML contents.  Returns an empty dict ``{}`` if:

        * the file does not exist,
        * the file is empty or contains only ``null``,
        * the top-level YAML value is not a mapping (dict),
        * a YAML syntax error is encountered, or
        * any other I/O or unexpected error occurs.

    Side Effects
    ------------
    Logs a ``WARNING`` if the file is missing and an ``ERROR`` (or
    ``EXCEPTION`` for unexpected errors) for all other failure modes via
    *loguru*.

    Examples
    --------
    >>> cfg = _load_yaml("params.yaml")
    >>> cfg.get("provider", {})
    {'default': 'openrouter', 'tier': 'general', ...}
    """
    path = _CONFIG_DIR / filename

    if not path.exists():
        logger.warning(f"Config file not found: {path}")
        return {}

    try:
        with open(path, 'r', encoding="utf-8") as f:
            data = yaml.safe_load(f)

            if data is None:
                return {}

            if not isinstance(data, dict):
                logger.error(f"YAML content is not a dict in file: {path}")
                return {}

            return data

    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error in {path}: {e}")
    except OSError as e:
        logger.error(f"File read error for {path}: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error loading YAML file {path}: {e}")

    return {}

##==============================
## get nested values from dict
##==============================
def _get_nestead(data: Dict[str, Any], *keys, default=None):
    """Safely retrieve a value from an arbitrarily deep nested dictionary.

    Traverses *data* by following each key in *keys* in order.  If any
    intermediate value is not a ``dict``, or if a key is absent at any level,
    the function returns *default* immediately rather than raising a
    ``KeyError`` or ``TypeError``.

    Parameters
    ----------
    data : Dict[str, Any]
        The top-level dictionary to traverse.
    *keys : str
        An ordered sequence of keys that form the path to the desired value.
        For example, ``("provider", "default")`` retrieves
        ``data["provider"]["default"]``.
    default : Any, optional
        Value returned when the path does not exist or resolves to ``None``.
        Defaults to ``None``.

    Returns
    -------
    Any
        The value found at the specified path, or *default* if the path is
        unreachable or the resolved value is ``None``.

    Examples
    --------
    >>> cfg = {"llm": {"temperature": 0.7, "max_tokens": 2048}}
    >>> _get_nestead(cfg, "llm", "temperature")
    0.7
    >>> _get_nestead(cfg, "llm", "missing_key", default=0.2)
    0.2
    >>> _get_nestead(cfg, "nonexistent", "nested")
    None
    """
    for key in keys:
        if isinstance(data,dict):
            data=data.get(key,default)
        
        else:
            return default
        
    return data if data is not None else default
    


##====================================
## Load params and models yaml files
##====================================
_CONFIG=_load_yaml(filename="params.yaml")
_MODELS=_load_yaml(filename="models.yaml")
_SCHEMA=_load_yaml(filename="schema.yaml")

##==========================
## Provider Configuration
##==========================
_PROVIDER=_get_nestead(_CONFIG,"provider","default",default="openrouter")
_TIER=_get_nestead(_CONFIG,"provider","tier",default="general")
_OPENROUTER_BASE_URL=_get_nestead(_CONFIG,"provider","openrouter_base_url",default="https://openrouter.ai/api/v1")

##========================
## LLM Configurations
##========================
_TEMPERATURE=_get_nestead(_CONFIG,"llm","temperature",default=0.2)
_MAX_TOKENS=_get_nestead(_CONFIG,"llm","max_tokens",default=3000)
_STREAMING=_get_nestead(_CONFIG,"llm","streaming",default=False)

##===================
## Get Chat Model
##===================
def _get_chat_model(provider: Optional[str] = None, tier: Optional[str] = None) -> str:
    """Resolve the chat model identifier for a given provider and tier.

    Looks up ``_MODELS[provider]["chat"][tier]`` (via :func:`_get_nestead`) and
    returns the corresponding model ID string.  Falls back to the module-level
    defaults ``_PROVIDER`` and ``_TIER`` when the arguments are omitted.

    Parameters
    ----------
    provider : str, optional
        LLM provider key as it appears in ``models.yaml``
        (e.g. ``"openrouter"``, ``"openai"``).  Defaults to ``_PROVIDER``.
    tier : str, optional
        Model quality tier as it appears under the provider's ``chat`` section
        (e.g. ``"general"``, ``"advanced"``).  Defaults to ``_TIER``.

    Returns
    -------
    str or None
        The model ID string (e.g. ``"openai/gpt-4o-mini"``), or ``None`` if
        no matching entry is found in ``models.yaml``.  When ``None`` is
        returned, an error is logged via *loguru*.

    Examples
    --------
    >>> _get_chat_model()                          # uses module defaults
    'openai/gpt-4o-mini'
    >>> _get_chat_model("openai", "advanced")
    'gpt-4o'
    """
    provider=provider or _PROVIDER
    tier=tier or _TIER

    model_id=_get_nestead(_MODELS,provider,"chat",tier)

    if not model_id:
        logger.error(f"Model not found for provider: {provider} and tier: {tier}")
        return None
    
    return model_id

##==================
## Call Chat Model
##==================
_CHAT_MODEL=_get_chat_model()

##=========================
## Langfuse Configurations
##=========================
_OBSERVABILITY=_get_nestead(_CONFIG,"observability",default=True)


##========================
## API KEY Configuration
##========================
def _get_api_key(provider: Optional[str] = None) -> Optional[str]:
    """Retrieve the API key for the specified LLM provider from the environment.

    Normalises the provider name to lower-case, maps it to the corresponding
    environment variable name (e.g. ``openrouter`` → ``OPENROUTER_API_KEY``),
    and returns the value found in the process environment.

    For unrecognised providers, the environment variable name is inferred as
    ``<PROVIDER_NAME_UPPER>_API_KEY``.

    Parameters
    ----------
    provider : str, optional
        Case-insensitive provider identifier
        (``"openrouter"``, ``"openai"``, ``"anthropic"``, ``"google"``,
        ``"groq"``).  Defaults to the module-level ``_PROVIDER`` constant.

    Returns
    -------
    str or None
        The raw API key string if found, otherwise ``None``.  ``None`` is also
        returned if *provider* resolves to an empty string.

    Side Effects
    ------------
    * Logs an ``ERROR`` when no provider can be determined.
    * Logs a ``WARNING`` when the environment variable is absent or empty.
    * Logs an ``EXCEPTION`` for any unexpected error.

    Examples
    --------
    >>> import os; os.environ["OPENROUTER_API_KEY"] = "sk-test"
    >>> _get_api_key("openrouter")
    'sk-test'
    >>> _get_api_key("unknown_provider")  # falls back to UNKNOWN_PROVIDER_API_KEY
    None
    """
    try:
        provider_name = (provider or _PROVIDER or "").lower().strip()

        if not provider_name:
            logger.error("Provider is not specified")
            return None

        api_providers = {
            "openrouter": "OPENROUTER_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "groq": "GROQ_API_KEY",
        }

        env_var = api_providers.get(
            provider_name,
            f"{provider_name.upper()}_API_KEY"
        )

        api_key = os.getenv(env_var)

        if not api_key:
            logger.warning(
                "API key not found in environment",
                provider=provider_name,
                env_var=env_var
            )
            return None

        return api_key

    except Exception as e:
        logger.exception(
            "Unexpected error while retrieving API key",
            provider=provider,
            error=str(e)
        )
        return None


def validate() -> None:
    """Assert that the active provider is configured and its API key is present.

    This function is intended to be called once at application startup (e.g.
    in ``main.py`` or a dependency-injection container) to provide an early,
    clear error message when a required secret is missing — rather than letting
    the application fail with an obscure HTTP 401 during its first API call.

    Validation steps
    ----------------
    1. Confirm that ``_PROVIDER`` resolves to a non-empty string.
    2. Call :func:`_get_api_key` for the active provider.
    3. If no key is found, raise ``ValueError`` with a descriptive message
       that names the expected environment variable.

    Raises
    ------
    ValueError
        If the provider is not configured, or if the required API key
        environment variable is absent or empty.  The message includes the
        exact environment variable name so the developer knows what to add to
        ``.env``.
    RuntimeError
        If an unexpected (non-validation) error occurs during the check.

    Side Effects
    ------------
    Logs an ``INFO`` message on success and an ``ERROR`` message when the API
    key is missing.

    Examples
    --------
    >>> validate()                  # passes silently when everything is set
    >>> validate()                  # raises ValueError when key is absent
    ValueError: ❌ Missing required secret key: OPENROUTER_API_KEY
    Please add it to your .env file.
    """
    try:
        provider_name = (_PROVIDER or "").lower().strip()

        if not provider_name:
            raise ValueError("Provider is not configured")

        api_key = _get_api_key(provider_name)

        if not api_key:
            key_name = (
                "OPENROUTER_API_KEY"
                if provider_name == "openrouter"
                else f"{provider_name.upper()}_API_KEY"
            )

            logger.error(
                "Missing required API key",
                provider=provider_name,
                expected_env=key_name
            )

            raise ValueError(
                f"❌ Missing required secret key: {key_name}\n"
                f"Please add it to your .env file."
            )

        logger.info("All required environment variables are set", provider=provider_name)

    except ValueError:
        # re-raise intentional validation errors
        raise

    except Exception as e:
        logger.exception("Unexpected error during validation", error=str(e))
        raise RuntimeError("Validation failed due to an unexpected error") from e

##======================
## Show Configurations
##======================
def dump() -> None:
    """Print a human-readable summary of the current (non-secret) configuration.

    Outputs provider settings — including the resolved chat model — to
    ``stdout``.  API keys and other secrets are intentionally excluded.

    Intended for development / debugging; call it from a REPL or at the top
    of a notebook to verify that the correct YAML values were loaded and that
    the model selection resolved as expected.

    Returns
    -------
    None

    Side Effects
    ------------
    Writes directly to ``stdout`` via ``print``.

    Example output
    --------------
    ::

        ============================================================
        CONFIGURATION (NON-SECRETS ONLY)
        ============================================================

        🌐 Provider:
           Provider: openrouter
           Model Tier: general
           Openrouter Base URL: https://openrouter.ai/api/v1
           Chat Model: openai/gpt-4o-mini
    """
    print("\n" + "=" * 60)
    print("CONFIGURATION (NON-SECRETS ONLY)")
    print("=" * 60)
    
    print("\n🌐 Provider:")
    print(f"   Provider: {_PROVIDER}")
    print(f"   Model Tier: {_TIER}")
    print(f"   Openrouter Base URL: {_OPENROUTER_BASE_URL}")
    print(f"   Chat Model: {_CHAT_MODEL}")

##======================
## Get config file
##======================
def _get_config() -> Dict[str, Any]:
    """Return the parsed contents of ``params.yaml``.

    Returns
    -------
    Dict[str, Any]
        The full configuration dictionary loaded from
        ``<project_root>/config/params.yaml``.  Returns ``{}`` if the file
        was not found or could not be parsed.
    """
    return _CONFIG

##======================
## Get model file
##======================
def _get_all_models() -> Dict[str, Any]:
    """Return the parsed contents of ``models.yaml``.

    Returns
    -------
    Dict[str, Any]
        The full model registry dictionary loaded from
        ``<project_root>/config/models.yaml``.  The top-level keys are
        provider names; each maps to a dict of task types (e.g. ``"chat"``)
        which in turn map tier names to model ID strings.  Returns ``{}``
        if the file was not found or could not be parsed.
    """
    return _MODELS

##======================
## Get schema file
##======================
def _get_schema() -> Dict[str, Any]:
    """Return the parsed contents of ``schema.yaml``.

    Returns
    -------
    Dict[str, Any]
        The full schema dictionary loaded from
        ``<project_root>/config/schema.yaml``.  Returns ``{}`` if the file
        was not found or could not be parsed.
    """
    return _SCHEMA


##============================
## Token Count Configurations
##============================
class TokenCounter:
    """Token-counting utility backed by the *tiktoken* BPE tokeniser.

    Wraps *tiktoken* to provide token counts for both plain text strings and
    structured chat-message lists.  The correct encoding is selected
    automatically based on the model name supplied at construction time.

    Supported model families
    ------------------------
    - ``gpt-4o*`` (any variant)  → ``o200k_base`` encoding via
      ``tiktoken.encoding_for_model("gpt-4o")``
    - ``gpt-3.5*``               → ``cl100k_base`` encoding via
      ``tiktoken.encoding_for_model("gpt-3.5-turbo")``
    - All other models           → ``cl100k_base`` encoding (safe default for
      most modern OpenAI-compatible models)

    If *tiktoken* raises an exception during encoder initialisation (e.g. for
    an unrecognised model name), the class falls back to ``cl100k_base`` and
    prints a warning to ``stdout``.

    Attributes
    ----------
    encoding : tiktoken.Encoding
        The active *tiktoken* encoding object used for all token operations.

    Examples
    --------
    >>> counter = TokenCounter("gpt-4o-mini")
    >>> counter.count_tokens("Hello, world!")
    4
    >>> msgs = [{"role": "user", "content": "What is 2 + 2?"}]
    >>> counter.count_token_in_messages(msgs)
    12
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        """Initialise the TokenCounter for the specified model.

        Parameters
        ----------
        model : str, optional
            Model name used to select the appropriate *tiktoken* encoding.
            The check is case-insensitive.  Defaults to ``"gpt-4o-mini"``.
        """
        try:
            if "gpt-4o" in model.lower():
                self.encoding=tiktoken.encoding_for_model("gpt-4o")

            elif "gpt-3.5" in model.lower():
                self.encoding=tiktoken.encoding_for_model("gpt-3.5-turbo")

            else:
                self.encoding=tiktoken.encoding_for_model("cl100k_base")
        
        except Exception as e:
            print(f"Error loading tokenizer for '{model}': {e}. Falling back to cl100k_base")
            self.encoding=tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a plain text string.

        Parameters
        ----------
        text : str
            The text to tokenise.  Empty strings return ``0``.

        Returns
        -------
        int
            Number of tokens produced by encoding *text* with the active
            *tiktoken* encoding.

        Examples
        --------
        >>> TokenCounter().count_tokens("Hello!")
        3
        """
        return len(self.encoding.encode(text))
    
    def count_token_in_messages(self, messages: List[Dict[str, Any]]) -> int:
        """Count the total number of tokens across a list of chat messages.

        Iterates over *messages*, extracts the ``"role"`` and ``"content"``
        fields from each entry, and sums their individual token counts.  An
        overhead of **2 tokens** is added at the end to approximate the
        per-conversation framing added by the OpenAI chat-completion format.

        Each message can be either:

        * a plain ``dict`` with ``"role"`` and ``"content"`` keys, or
        * an object (e.g. a Pydantic model or dataclass) that exposes
          ``role`` and ``content`` attributes.

        Parameters
        ----------
        messages : List[Dict[str, Any]]
            Sequence of chat messages.  Missing ``"role"`` or ``"content"``
            values are treated as empty strings (contributing 0 tokens).

        Returns
        -------
        int
            Total token count, including the 2-token conversation overhead.

        Examples
        --------
        >>> counter = TokenCounter()
        >>> msgs = [
        ...     {"role": "system",    "content": "You are a helpful assistant."},
        ...     {"role": "user",      "content": "What is the capital of France?"},
        ... ]
        >>> counter.count_token_in_messages(msgs)
        22
        """
        token_count=0
        for message in messages:
            if isinstance(message,dict):
                role=message.get("role","")
                content=message.get("content","")
            else:
                role=getattr(message,"role","")
                content=getattr(message,"content","")
            
            token_count+=self.count_tokens(role)
            token_count+=self.count_tokens(content)

        token_count += 2
        return token_count
                

    
            

