"""
Observability Layer
===================
Thin wrapper around `Langfuse <https://langfuse.com>`_ that provides
distributed tracing and LLM-call monitoring for the AI Engineering
Bootcamp mini-project-04 pipeline.

Architecture
------------
The module is intentionally kept as a single, import-side-effect-free
layer so that every other module can import from it without worrying
about whether Langfuse is installed or configured:

- If the ``LANGFUSE_SECRET_KEY`` / ``LANGFUSE_PUBLIC_KEY`` environment
  variables are absent, or if observability is disabled via config, all
  public helpers become silent no-ops.
- The Langfuse client is created **lazily** on first use and cached for
  the lifetime of the process.

Public surface (intended for use by other modules)
---------------------------------------------------
``_observe``
    Decorator factory — wraps a function as a Langfuse *span* or
    *generation*.  Falls back to a no-op decorator when tracing is off.

``_update_current_trace``
    Attaches user / session / tag metadata to the active trace.

``_update_current_observation``
    Updates the active span or generation with input, output, model, and
    token-usage information.

``_flush``
    Blocks until all buffered Langfuse events have been delivered.
    Call this before process exit to avoid dropping telemetry.

Configuration
-------------
Observability can be toggled at two levels:

1. **Environment variable** — set ``LANGFUSE_SECRET_KEY`` and
   ``LANGFUSE_PUBLIC_KEY`` (and optionally ``LANGFUSE_BASE_URL``).
2. **Config file** — set ``observerbility: false`` in the project
   config (``config.yaml`` or equivalent) to disable at runtime.
"""

##===========================
## Import Required Libraries
##===========================
import os
from typing import Optional,Dict,Any
from loguru import logger
from langfuse import Langfuse
from dotenv import load_dotenv
from  pathlib import Path

##==============================
## User Define Python Modules
##==============================
from src.infrastructure.config import(
    _get_config,
    _get_nestead,
    _OBSERVABILITY
)

##=============================
## Load Enviromental Variables
##=============================
_PROJECT_ROOT=Path(__file__).parent.parent

_ENV_PATH=_PROJECT_ROOT/".env"

if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)

_ENABLED:Optional[bool]=None

##=====================================
## Check Observability Configuration
##=====================================
def _is_enabled() -> bool:
    """Return ``True`` if observability / Langfuse tracing is enabled.

    The result is computed once and cached in the module-level ``_ENABLED``
    flag so that config and environment lookups only happen on the first
    call.

    Resolution order
    ----------------
    1. Return the cached ``_ENABLED`` value if already resolved.
    2. Evaluate the ``_OBSERVABILITY`` constant (set at import time from
       the project config via ``config._get_nestead``).
    3. Fall back to ``True`` (enabled) if config cannot be read.

    Returns
    -------
    bool
        ``True``  — tracing is active.
        ``False`` — tracing is disabled; all helpers are no-ops.
    """
    global _ENABLED
    if _ENABLED is not None:
        return _ENABLED
    
    try:
        _ENABLED=bool(_OBSERVABILITY or _get_nestead(_get_config(),"observerbility",default=True))
    
    except Exception:
        _ENABLED=True
    
    return _ENABLED

##=============================
## Configure Langfuse Client
##=============================
_langfuse_client=None
_initialised=False

def _get_langfuse_client():
    """Return the singleton Langfuse client, initialising it on first call.

    The client is created at most once per process.  Subsequent calls
    return the cached instance (or ``None`` when tracing is disabled /
    keys are missing).

    Initialisation requirements
    ---------------------------
    The following environment variables must be set (typically via
    ``.env`` in the project root):

    - ``LANGFUSE_SECRET_KEY`` — Langfuse secret key.
    - ``LANGFUSE_PUBLIC_KEY`` — Langfuse public key.
    - ``LANGFUSE_BASE_URL``   — (optional) defaults to
      ``https://cloud.langfuse.com``.

    Returns
    -------
    Langfuse | None
        Authenticated Langfuse client, or ``None`` when tracing is
        disabled or credentials are unavailable.
    """
    global _langfuse_client,_initialised

    if _initialised:
        return _langfuse_client
    
    _initialised=True

    if not _is_enabled():
        logger.info("Observerbility disabled via config - Langfuse not initialised.")
        return None
    
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    base_url = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

    if not secret_key or not public_key:
        logger.warning(
            "LangFuse keys not set (SECRET_KEY / PUBLIC_KEY). Please set these environment variables in .env file."
            "Tracing is disabled."
        )
        return None
    
    try:
        _langfuse_client=Langfuse(
            secret_key=secret_key,
            public_key=public_key,
            base_url=base_url
        )

        logger.info("LangFuse client initialised (host={})",base_url)
        return _langfuse_client

    except Exception as e:
        logger.error("LangFuse client initialization failed: {}",e)
        return None

##==========================
## Observe Decorator
##==========================
try:
    from langfuse import observe as _lf_observe
    from langfuse import get_client as _get_lf_client
except ImportError:
    _lf_observe = None
    _get_lf_client = None
    logger.debug("langfuse package not installed — @observe is a no-op.")


def _observe(
    *,
    name: Optional[str] = None,
    as_type: Optional[str] = None,
):
    """Return a Langfuse ``@observe`` decorator (or a no-op when tracing is off).

    This factory wraps ``langfuse.observe`` so callers never need to guard
    against Langfuse being absent or disabled.

    Parameters
    ----------
    name : str, optional
        Display name for the span / generation shown in the Langfuse UI.
        Defaults to the decorated function's ``__name__`` when omitted.
    as_type : str, optional
        Langfuse observation type.  Pass ``"generation"`` to record the
        span as an LLM generation (enables model / token-usage tracking).
        Omit for a plain span.

    Returns
    -------
    Callable
        A decorator that, when applied to a function, wraps it in a
        Langfuse observation context.  Returns an identity decorator when
        tracing is disabled or ``langfuse`` is not installed.

    Examples
    --------
    >>> @_observe(name="sql_generation", as_type="generation")
    ... def generate_sql(prompt: str) -> str:
    ...     ...
    """
    def _noop_decorator(fn):
        return fn

    if not _is_enabled() or _lf_observe is None:
        return _noop_decorator

    # Build kwargs for the real decorator
    kwargs = {}
    if name is not None:
        kwargs["name"] = name
    if as_type is not None:
        kwargs["as_type"] = as_type

    return _lf_observe(**kwargs)


##===============================
## Observe User Level Entry
##===============================
def _update_current_trace(
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    tags: Optional[list] = None,
) -> None:
    """Attach metadata to the currently active Langfuse trace.

    Must be called from within a function that is already decorated with
    ``@_observe``.  Only the keyword arguments that are explicitly passed
    (i.e. not ``None``) are forwarded to Langfuse, so callers can update
    individual fields without overwriting the others.

    Failures are swallowed and logged at ``DEBUG`` level so that tracing
    issues never interrupt the application's normal flow.

    Parameters
    ----------
    user_id : str, optional
        Identifier for the end-user making the request.  Useful for
        per-user analytics in the Langfuse dashboard.
    session_id : str, optional
        Groups multiple traces that belong to the same logical session
        (e.g. a multi-turn conversation).
    metadata : dict, optional
        Arbitrary key-value pairs attached to the trace.  Values must be
        JSON-serialisable.
    tags : list, optional
        Free-form string labels (e.g. ``["production", "sql-agent"]``)
        that can be used to filter traces in the Langfuse UI.

    Returns
    -------
    None
    """
    if _get_lf_client is None or not _is_enabled():
        return
    try:
        client = _get_lf_client()
        kwargs = {}
        if user_id is not None:
            kwargs["user_id"] = user_id
        if session_id is not None:
            kwargs["session_id"] = session_id
        if metadata is not None:
            kwargs["metadata"] = metadata
        if tags is not None:
            kwargs["tags"] = tags
        client.update_current_trace(**kwargs)
    except Exception as exc:
        logger.debug("update_current_trace failed (non-critical): {}", exc)

##================================
## Update Observation
##================================
def _update_current_observation(
    *,
    input: Optional[str] = None,
    output: Optional[str] = None,
    metadata: Optional[dict] = None,
    usage: Optional[dict] = None,
    model: Optional[str] = None,
) -> None:
    """Update the currently active Langfuse span or generation.

    Automatically selects the correct Langfuse update call:

    - If ``model`` or ``usage`` is provided, the active observation is
      treated as a **generation** and ``update_current_generation`` is
      called (enabling token-cost tracking in Langfuse).
    - Otherwise ``update_current_span`` is called for a plain span.

    Must be called from inside a function decorated with ``@_observe``.
    Only non-``None`` arguments are forwarded.  Failures are swallowed
    and logged at ``DEBUG`` level.

    Parameters
    ----------
    input : str, optional
        The prompt or input text sent to the model / function.
    output : str, optional
        The raw response or result produced by the model / function.
    metadata : dict, optional
        Arbitrary JSON-serialisable key-value pairs to attach to the
        observation (e.g. retrieval context, configuration snapshots).
    usage : dict, optional
        Token-usage breakdown.  Expected keys (all optional):

        - ``"input"``  — number of prompt tokens.
        - ``"output"`` — number of completion tokens.
        - ``"total"``  — total tokens (prompt + completion).

        When supplied, the observation is recorded as a generation so
        that Langfuse can compute cost estimates.
    model : str, optional
        Model identifier (e.g. ``"claude-sonnet-4-6"``).  When supplied,
        the observation is recorded as a generation.

    Returns
    -------
    None
    """
    if _get_lf_client is None or not _is_enabled():
        return
    try:
        client = _get_lf_client()

        # If model or usage provided → generation update
        if usage is not None or model is not None:
            gen_kwargs = {}
            if input is not None:
                gen_kwargs["input"] = input
            if output is not None:
                gen_kwargs["output"] = output
            if metadata is not None:
                gen_kwargs["metadata"] = metadata
            if model is not None:
                gen_kwargs["model"] = model
            if usage is not None:
                gen_kwargs["usage_details"] = usage
            try:
                client.update_current_generation(**gen_kwargs)
                return
            except Exception:
                pass

        # Otherwise → span update
        span_kwargs = {}
        if input is not None:
            span_kwargs["input"] = input
        if output is not None:
            span_kwargs["output"] = output
        if metadata is not None:
            span_kwargs["metadata"] = metadata
        
        if span_kwargs:
            client.update_current_span(**span_kwargs)
    except Exception as exc:
        logger.debug("update_current_observation failed (non-critical): {}", exc)

##============================
## Flush
##============================
def _flush() -> None:
    """Flush all buffered Langfuse events to the remote server.

    Langfuse batches telemetry events in memory for efficiency.  Call
    this function before the process exits (e.g. at the end of a
    script or request handler) to ensure no events are silently dropped.

    If tracing is disabled or the client is not initialised, this
    function returns immediately without side-effects.  Flush errors are
    swallowed and logged at ``DEBUG`` level.

    Returns
    -------
    None
    """
    if _get_lf_client is not None and _is_enabled():
        try:
            client = _get_lf_client()
            client.flush()
            logger.debug("LangFuse flushed.")
        except Exception as exc:
            logger.debug("LangFuse flush failed: {}", exc)