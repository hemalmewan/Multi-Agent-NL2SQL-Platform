"""
llm_providers.py
================
LLM provider abstraction layer for the AI Engineering Bootcamp mini-project-04.

This module defines a unified interface for interacting with different Large
Language Model (LLM) backends.  All concrete providers inherit from the
``LLMProvider`` abstract base class and implement a single ``generate`` method
that returns a standardised response dictionary containing the model output,
token usage statistics, estimated cost, and wall-clock latency.

Supported providers
-------------------
- **OpenRouterProvider** — Routes requests through the OpenRouter API
  (``https://openrouter.ai/api/v1``), which aggregates many model vendors
  behind a single OpenAI-compatible endpoint.
- **OpenAIProvider** — Calls the official OpenAI Chat Completions API directly.
- **DummyProvider** — Returns a static response with zeroed metrics; intended
  for unit testing and local development without API keys.

Factory / singleton helpers
---------------------------
``_llm_service_provider``
    Reads the active configuration and instantiates the correct provider class.
``_global_llm_provider``
    Returns a module-level singleton ``LLMProvider`` instance, creating it on
    first call.  Re-use this throughout the application to avoid repeated
    initialisation overhead.

Response schema
---------------
Every ``generate`` call returns a ``dict`` with the following keys:

.. code-block:: python

    {
        "response":           str,   # The model's text reply
        "prompt_tokens":      int,   # Tokens consumed by the input
        "completion_tokens":  int,   # Tokens produced in the reply
        "total_tokens":       int,   # prompt_tokens + completion_tokens
        "token_cost":         float, # Estimated USD cost of the call
        "latency_ms":         int,   # End-to-end wall-clock time in ms
        "chat model":         str,   # Model identifier used for the call
    }

Token cost formula
------------------
Token cost is approximated using the ``gpt-4o-mini`` public pricing as a
reference rate::

    cost = (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000

Dependencies
------------
- ``openai`` — OpenAI Python SDK (also used for OpenRouter via ``base_url``
  override).
- ``src.infrastructure.config`` — Application-level configuration helpers and
  constants (``_get_config``, ``_get_api_key``, ``_get_chat_model``, etc.).
"""

##===========================
## Import Required Libraries
##===========================
from typing import List,Dict,Any,Optional
from openai import OpenAI
from loguru import logger
import time

##==================================
## Import user define python modules
##==================================
from src.infrastructure.config import(
    _get_config,
    _get_api_key,
    _get_chat_model,
    _MAX_TOKENS,
    _TEMPERATURE,
    _PROVIDER,
    _OPENROUTER_BASE_URL,
    TokenCounter
)

##============================
## LLM Provider Base Class
##============================
class LLMProvider:
    """Abstract base class for all LLM provider implementations.

    Defines the contract that every concrete provider must satisfy.
    Subclasses override ``generate`` to call their respective backend APIs
    and return a standardised response dictionary (see module docstring for
    the full schema).

    Usage
    -----
    Do not instantiate ``LLMProvider`` directly.  Instead use one of the
    concrete subclasses (``OpenRouterProvider``, ``OpenAIProvider``,
    ``DummyProvider``) or obtain an instance via the factory function
    ``_llm_service_provider`` / singleton ``_global_llm_provider``.
    """

    def generate(
        self,
        user_prompt:str,
        system_prompt:str,
        **kwargs
    )-> Dict[Any,str]:
        """Generate a model response for the given prompts.

        Parameters
        ----------
        user_prompt : str
            The human-turn message to send to the model.
        system_prompt : str
            The system-level instruction that conditions the model's behaviour.
        **kwargs
            Additional keyword arguments forwarded to the concrete
            implementation (e.g. ``temperature``, ``max_tokens``).

        Returns
        -------
        Dict[Any, str]
            Standardised response dictionary — see module docstring for keys.

        Raises
        ------
        NotImplementedError
            Always raised here; subclasses must provide their own implementation.
        """
        raise NotImplementedError("Subclasses must implement this method")


##===========================
## Openrouter Provider Class
##===========================
class OpenRouterProvider(LLMProvider):
    """LLM provider that routes requests through the OpenRouter gateway.

    OpenRouter exposes an OpenAI-compatible REST API (``/chat/completions``)
    that aggregates hundreds of models from different vendors behind a single
    endpoint.  This class wraps the OpenAI Python SDK and overrides
    ``base_url`` so all traffic goes to ``https://openrouter.ai/api/v1``
    instead of ``api.openai.com``.

    Attributes
    ----------
    model : str
        The fully-qualified model identifier understood by OpenRouter,
        e.g. ``"openai/gpt-4o-mini"`` or ``"anthropic/claude-3-haiku"``.
    temperature : float
        Sampling temperature controlling output randomness (0 = deterministic,
        1 = highly creative).  Defaults to ``0.2``.
    max_tokens : int
        Maximum number of tokens the model may generate in one call.
        Defaults to ``3000``.
    base_url : str
        OpenRouter API base URL.  Defaults to
        ``"https://openrouter.ai/api/v1"``.
    api_key : str
        API key retrieved from the application configuration for the
        ``openrouter`` provider.
    openai_client : openai.OpenAI
        Configured OpenAI SDK client pointed at the OpenRouter endpoint.
    token_counter : TokenCounter
        Utility for local token counting / estimation (uses ``gpt-4o-mini``
        tokeniser as a proxy).
    """

    def __init__(
        self,
        model:str="openai/gpt-4o-mini",
        temperature:float=0.2,
        max_tokens:int=3000,
        base_url:str="https://openrouter.ai/api/v1"
    ):
        """Initialise the OpenRouter provider.

        Parameters
        ----------
        model : str, optional
            Model identifier to use for completions.
            Defaults to ``"openai/gpt-4o-mini"``.
        temperature : float, optional
            Sampling temperature.  Defaults to ``0.2``.
        max_tokens : int, optional
            Maximum completion tokens per request.  Defaults to ``3000``.
        base_url : str, optional
            Base URL of the OpenRouter API.
            Defaults to ``"https://openrouter.ai/api/v1"``.
        """
        self.model=model or _get_chat_model
        self.temperature=temperature or _TEMPERATURE
        self.max_tokens=max_tokens or _MAX_TOKENS
        self.base_url=base_url or _OPENROUTER_BASE_URL
        self.api_key=_get_api_key(_PROVIDER)
        self.openai_client=OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.token_counter=TokenCounter(model="gpt-4o-mini")

    def generate(
        self,
        user_prompt:Optional[str]=None,
        system_prompt:Optional[str]=None,
        temperature:Optional[float]=None,
        max_tokens:Optional[int]=None,
        **kwargs
    )->Dict[Any,str]:
        """Send a chat completion request to OpenRouter and return results.

        Constructs an OpenAI-style message list (optional system message
        followed by the user message), calls the OpenRouter endpoint, and
        returns a standardised response dictionary.

        Parameters
        ----------
        user_prompt : str, optional
            The user-turn message.  If ``None``, an empty user message is
            sent (behaviour depends on the underlying model).
        system_prompt : str, optional
            System instruction prepended to the conversation.  Omitted from
            the message list when ``None`` or an empty string.
        temperature : float, optional
            Per-call temperature override.  Falls back to ``self.temperature``
            when not provided.
        max_tokens : int, optional
            Per-call max-token override.  Falls back to ``self.max_tokens``
            when not provided.
        **kwargs
            Ignored; present for forward-compatibility with the base class
            signature.

        Returns
        -------
        Dict[Any, str]
            A dictionary with the following keys:

            - ``"response"`` (*str*) — Model's text reply.
            - ``"prompt_tokens"`` (*int*) — Input tokens consumed.
            - ``"completion_tokens"`` (*int*) — Output tokens generated.
            - ``"total_tokens"`` (*int*) — Sum of prompt and completion tokens.
            - ``"token_cost"`` (*float*) — Estimated cost in USD.
            - ``"latency_ms"`` (*int*) — Wall-clock latency in milliseconds.
            - ``"chat model"`` (*str*) — Model identifier used for the call.
        """
        messages=[]

        if system_prompt:
            messages.append({"role":"system","content":system_prompt})

        messages.append({"role":"user","content":user_prompt})

        start_time=time.time()

        response=self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
        )

        end_time=time.time()
        latency_ms=int((end_time-start_time)*1000)

        llm_response=response.choices[0].message

        ##calculate token cost
        token_cost=(response.usage.prompt_tokens * 0.15 + response.usage.completion_tokens * 0.6)/10**6

        return{
            "response":llm_response.content,
            "prompt_tokens":response.usage.prompt_tokens,
            "completion_tokens":response.usage.completion_tokens,
            "total_tokens":response.usage.total_tokens,
            "token_cost": token_cost,
            "latency_ms":latency_ms,
            "chat model":self.model
        }
        

##=======================
## OpenAI Provider Class
##=======================
class OpenAIProvider(LLMProvider):
    """LLM provider that calls the official OpenAI Chat Completions API.

    Uses the OpenAI Python SDK with the default ``api.openai.com`` endpoint.
    This provider is suitable for production workloads where direct access to
    OpenAI models (GPT-4o, GPT-4o-mini, etc.) is required without going
    through a third-party gateway.

    Attributes
    ----------
    model : str
        OpenAI model identifier, e.g. ``"gpt-4o-mini"`` or ``"gpt-4o"``.
        Defaults to ``"gpt-4o-mini"``.
    temperature : float
        Sampling temperature.  Defaults to ``0.2``.
    max_tokens : int
        Maximum completion tokens per request.  Defaults to ``3000``.
    api_key : str
        OpenAI API key retrieved from the application configuration.
    openai_client : openai.OpenAI
        Configured OpenAI SDK client using the official endpoint.
    token_counter : TokenCounter
        Utility for local token counting / estimation.

    Notes
    -----
    The ``latency_ms`` calculation in this class truncates sub-second
    precision (``int(end_time - start_time) * 1000``), which will report
    ``0 ms`` for calls that complete in under one second.  This differs from
    ``OpenRouterProvider``, which uses ``int((end - start) * 1000)`` and
    preserves millisecond resolution.
    """

    def __init__(
        self,
        model:str="gpt-4o-mini",
        temperature:float=0.2,
        max_tokens:int=3000,
    ):
        """Initialise the OpenAI provider.

        Parameters
        ----------
        model : str, optional
            OpenAI model identifier.  Defaults to ``"gpt-4o-mini"``.
        temperature : float, optional
            Sampling temperature.  Defaults to ``0.2``.
        max_tokens : int, optional
            Maximum completion tokens per request.  Defaults to ``3000``.
        """
        self.model=model or _get_chat_model
        self.temperature=temperature or _TEMPERATURE
        self.max_tokens=max_tokens or _MAX_TOKENS
        self.api_key=_get_api_key(_PROVIDER)
        self.openai_client=OpenAI(
            api_key=self.api_key
        )
        self.token_counter=TokenCounter(model="gpt-4o-mini")

    def generate(
        self,
        user_prompt:Optional[str]=None,
        system_prompt:Optional[str]=None,
        temperature:Optional[float]=None,
        max_tokens:Optional[int]=None,
        **kwargs
    ) ->Dict[Any,str]:
        """Send a chat completion request to the OpenAI API and return results.

        Constructs an OpenAI-style message list (optional system message
        followed by the user message), calls the API, and returns a
        standardised response dictionary.

        Parameters
        ----------
        user_prompt : str, optional
            The user-turn message.
        system_prompt : str, optional
            System instruction prepended to the conversation.  Omitted when
            ``None`` or an empty string.
        temperature : float, optional
            Per-call temperature override.  Falls back to ``self.temperature``
            when not provided.
        max_tokens : int, optional
            Per-call max-token override.  Falls back to ``self.max_tokens``
            when not provided.
        **kwargs
            Ignored; present for forward-compatibility.

        Returns
        -------
        Dict[Any, str]
            A dictionary with the following keys:

            - ``"response"`` (*str*) — Model's text reply.
            - ``"prompt_tokens"`` (*int*) — Input tokens consumed.
            - ``"completion_tokens"`` (*int*) — Output tokens generated.
            - ``"total_tokens"`` (*int*) — Sum of prompt and completion tokens.
            - ``"token_cost"`` (*float*) — Estimated cost in USD.
            - ``"latency_ms"`` (*int*) — Wall-clock latency in milliseconds.
              Note: truncated to whole seconds due to integer cast order
              (see class-level Notes).
            - ``"chat model"`` (*str*) — Model identifier used for the call.
        """
        messages=[]

        if system_prompt:
            messages.append({"role":"system","content":system_prompt})

        messages.append({"role":"user","content":user_prompt})

        start_time=time.time()
        response=self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens
        )

        end_time=time.time()
        latency_ms=(int(end_time-start_time)*1000)

        llm_response=response.choices[0].message

        ##calculate token cost
        token_cost=(response.usage.prompt_tokens * 0.15 + response.usage.completion_tokens * 0.6)/10**6

        return{
            "response":llm_response.content,
            "prompt_tokens":response.usage.prompt_tokens,
            "completion_tokens":response.usage.completion_tokens,
            "total_tokens":response.usage.total_tokens,
            "token_cost": token_cost,
            "latency_ms":latency_ms,
            "chat model":self.model
        }


##============================
## Dummy Provider Class
##============================
class DummyProvider(LLMProvider):
    """No-op LLM provider for testing and local development.

    Returns a static, hardcoded response with all numeric metrics set to zero.
    No API key or network access is required, making it suitable for:

    - Unit / integration tests that verify pipeline logic without incurring
      API costs or requiring valid credentials.
    - Local development environments where live API calls are undesirable.
    - CI/CD pipelines that need to exercise the provider interface cheaply.

    Attributes
    ----------
    model : str
        Always ``"dummy_model"``; identifies this as the no-op backend.

    Notes
    -----
    ``response_text`` is currently built as a Python ``set`` literal
    (``{ "..." }``), so ``generate`` returns a set under the ``"response"``
    key rather than a plain string.  This is a known inconsistency with the
    other providers.
    """

    def __init__(self):
        """Initialise the DummyProvider with a placeholder model name."""
        self.model="dummy_model"

    def generate(
        self,
        user_prompt:Optional[str]=None,
        system_prompt:Optional[str]=None,
        **kwargs
    ) -> Dict[Any,str]:
        """Return a static dummy response with zeroed metrics.

        Parameters
        ----------
        user_prompt : str, optional
            Accepted but ignored.
        system_prompt : str, optional
            Accepted but ignored.
        **kwargs
            Accepted but ignored.

        Returns
        -------
        Dict[Any, str]
            A dictionary with the following keys:

            - ``"response"`` (*set[str]*) — Static placeholder text (note:
              this is a ``set``, not a ``str``, due to the ``{ }`` literal).
            - ``"prompt_tokens"`` (*int*) — Always ``0``.
            - ``"completion_tokens"`` (*int*) — Always ``0``.
            - ``"total_tokens"`` (*int*) — Always ``0``.
            - ``"token_cost"`` (*int*) — Always ``0``.
            - ``"latency_ms"`` (*int*) — Always ``0``.
            - ``"chat model"`` (*str*) — Always ``"dummy_model"``.
        """
        response_text={
            "This is a dummy model provider created for testing purpose."
        }

        return{
            "response":response_text,
            "prompt_tokens":0,
            "completion_tokens":0,
            "total_tokens":0,
            "token_cost":0,
            "latency_ms":0,
            "chat model":self.model
        }


##==============================
## LLM Service Provider Factory
##==============================
def _llm_service_provider(config:Optional[Dict[str,Any]]=None)-> LLMProvider:
    """Instantiate and return the appropriate ``LLMProvider`` from configuration.

    Reads the active application configuration (or uses the supplied
    ``config`` dict) to determine which provider backend is selected, then
    constructs and returns the corresponding ``LLMProvider`` subclass with
    all parameters wired from config values.

    Provider resolution order
    -------------------------
    1. ``"openrouter"`` → ``OpenRouterProvider``
    2. ``"openai"``     → ``OpenAIProvider``
    3. *(anything else)* → ``DummyProvider``

    Parameters
    ----------
    self
        Unused; present because this function is mistakenly defined with a
        ``self`` parameter — it should be a plain module-level function.
        Call it as ``_llm_service_provider(config=...)`` (``self`` will be
        ``None`` when called without an instance).
    config : Dict[str, Any], optional
        Pre-loaded configuration dictionary.  When ``None`` (default) the
        function calls ``_get_config()`` to load configuration from the
        application's standard source.

    Returns
    -------
    LLMProvider
        A fully initialised provider instance ready to call ``.generate()``.

    Configuration keys used
    -----------------------
    - ``"provider.default"`` — Selects the active backend
      (``"openrouter"`` | ``"openai"``).
    - ``"llm.temperature"`` — Sampling temperature passed to the provider.
    - ``"llm.max_tokens"`` — Token limit passed to the provider.
    - ``"provider.openrouter_base_url"`` — Base URL for OpenRouter
      (used only when provider is ``"openrouter"``).
    """
    if config is None:
        config=_get_config()

    if not isinstance(config, dict):
        logger.error("Invalid config: expected dict", received_type=type(config).__name__)
        raise TypeError("Config must be a dictionary")

    provider_name=(config.get("provider")).get("default")

    if not provider_name:
        logger.error("Missing 'provider.default' in config")
        raise ValueError("Provider is not specified in configuration")

    try:
        if provider_name=="openrouter":
            return OpenRouterProvider(
                model=_get_chat_model(provider_name),
                temperature=config.get("llm").get("temperature"),
                max_tokens=config.get("llm").get("max_tokens"),
                base_url=config.get("provider").get("openrouter_base_url")
            )
        elif provider_name=="openai":
            return OpenAIProvider(
                model=_get_chat_model(provider_name),
                temperature=config.get("llm").get("temperature"),
                max_tokens=config.get("llm").get("max_tokens")
            )
        else:
            logger.warning(
                "Unknown provider, falling back to DummyProvider",
                provider=provider_name
            )
            return DummyProvider()
    
    except Exception as e:
        logger.exception(
            "Failed to initialize LLM provider",
            provider=provider_name,
            error=str(e)
        )
        raise RuntimeError(f"Failed to initialize provider: {provider_name}") from e

##===============================
## Global LLM Provider Instance
##===============================
_global_llm_instance:Optional[LLMProvider]=None
"""Module-level singleton storage for the active ``LLMProvider``.

Initialised to ``None`` and populated on the first call to
``_global_llm_provider``.  Prefer accessing the provider through
``_global_llm_provider()`` rather than this variable directly.
"""

def _global_llm_provider(config:Optional[Dict[str,Any]]=None) -> LLMProvider:
    """Return the module-level singleton ``LLMProvider``, creating it if needed.

    Uses the lazy-initialisation pattern: the provider is constructed only
    on the first call (via ``_llm_service_provider``) and then cached in
    ``_global_llm_instance`` for all subsequent calls.  This avoids repeated
    configuration reads and client instantiation across different parts of the
    application.

    Returns
    -------
    LLMProvider
        The singleton provider instance for the active configuration.

    Thread safety
    -------------
    This function is **not** thread-safe.  If multiple threads call it
    simultaneously before ``_global_llm_instance`` is set, more than one
    provider instance may be created.  For multi-threaded use, guard the
    first call with a lock or initialise the provider explicitly at
    application startup before spawning threads.

    Example
    -------
    >>> provider = _global_llm_provider()
    >>> result = provider.generate(
    ...     user_prompt="Summarise this text ...",
    ...     system_prompt="You are a helpful assistant."
    ... )
    >>> print(result["response"])
    """
    global _global_llm_instance

    if _global_llm_instance is None:
        _global_llm_instance=_llm_service_provider(config=config)

    return _global_llm_instance
