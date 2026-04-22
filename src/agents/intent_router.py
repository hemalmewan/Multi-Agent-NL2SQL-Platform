"""
intent_router.py
================
Intent classification agent for the medicore hospital analytics system.

This module contains ``RouterIntent``, a thin agent wrapper that asks an LLM
to classify an incoming user query as either ``"SQL"`` (database query) or
``"GENERAL"`` (conversational / informational).  The classification result
drives downstream routing: SQL-labelled queries are forwarded to the Text-to-SQL
pipeline, while GENERAL queries are ignored from the system.

Classification labels
---------------------
- ``"SQL"``     — The query involves retrieving, filtering, aggregating, or
  analysing data from one of the hospital database tables (patients, doctors,
  admissions, billing, etc.).
- ``"GENERAL"`` — The query is conversational, informational, or unrelated to
  hospital data.

Prompt
------
The system prompt is imported from
``src.agents.prompts._ROUTER_INTENT_PROMPT`` as ``_ROUTER_INTENT``.  It
instructs the LLM to output a strict JSON object of the form::

    {"label": "SQL" | "GENERAL"}

Dependencies
------------
- Any ``LLMProvider``-compatible object (``OpenRouterProvider``,
  ``OpenAIProvider``, ``DummyProvider``) injected at construction time.
- ``loguru`` — structured logging.
"""

##===========================
## Import Required Libraries
##===========================
from typing import Dict,Any,Optional
from loguru import logger
import time
import json

##===================================
## Import User Define Python Modules
##===================================
from src.agents.prompts._ROUTER_INTENT_PROMPT import _ROUTER_INTENT


class RouterIntent:
    """Intent classification agent that routes user queries to the correct pipeline.

    Wraps any ``LLMProvider``-compatible object and uses the ``_ROUTER_INTENT``
    system prompt to classify a free-text user query as ``"SQL"`` or
    ``"GENERAL"``.

    Attributes
    ----------
    llm_call : LLMProvider
        The LLM provider instance used to generate the classification.
        Must expose a ``generate(user_prompt, system_prompt)`` method that
        returns a dict conforming to the standard LLM response schema
        (see ``llm_providers.py``).

    Example
    -------
    >>> from src.infrastructure.llm.llm_providers import _global_llm_provider
    >>> router = RouterIntent(llm=_global_llm_provider())
    >>> result = router.router("How many patients were admitted last month?")
    >>> print(result["intent"])   # "SQL"
    """

    def __init__(self, llm):
        """Initialise the RouterIntent agent.

        Parameters
        ----------
        llm : LLMProvider
            An instantiated LLM provider (e.g. ``OpenRouterProvider``,
            ``OpenAIProvider``, or ``DummyProvider``).  The object must
            implement ``generate(user_prompt, system_prompt) -> dict``.
        """
        self.llm_call = llm

    def router(self, user_query: str) -> Dict[str, Any]:
        """Classify a user query as ``"SQL"`` or ``"GENERAL"``.

        Builds a minimal user prompt from ``user_query``, calls the LLM with
        the ``_ROUTER_INTENT`` system prompt, and extracts the ``label`` field
        from the JSON response.

        Parameters
        ----------
        user_query : str
            The raw natural-language query entered by the user.  Must be a
            non-empty string.

        Returns
        -------
        Dict[str, Any]
            A dictionary with the following keys:

            - ``"intent"`` (*str*) — Classification label: ``"SQL"`` or
              ``"GENERAL"``.  Empty string if the LLM returns an unexpected
              format.
            - ``"latency_ms"`` (*int | None*) — Wall-clock latency of the LLM
              call in milliseconds, forwarded from the provider response.
            - ``"total_tokens"`` (*int | None*) — Total tokens consumed by the
              classification call.
            - ``"token_cost"`` (*float | None*) — Estimated USD cost of the
              classification call.

        Raises
        ------
        ValueError
            If ``user_query`` is not a string or is blank / whitespace-only.
        TypeError
            If the LLM provider returns a non-dict response (indicates a
            provider implementation issue).
        RuntimeError
            Wraps any unexpected exception raised during the LLM call,
            preserving the original cause via exception chaining.

        Notes
        -----
        The intent value is extracted with ``response.get("response.label")``.
        This relies on the LLM embedding the label at the literal key
        ``"response.label"`` inside the response dict, which differs from the
        standard ``"response"`` key returned by the provider.  If the LLM
        returns ``{"label": "SQL"}`` inside the ``"response"`` string, this
        extraction will silently yield an empty string.
        """
        if not isinstance(user_query, str) or not user_query.strip():
            logger.error("Invalid user_query provided", value=user_query)
            raise ValueError("user query must be a non-empty string")

        prompt = f"User Query:{user_query}"

        try:
            response = self.llm_call.generate(
                user_prompt=prompt,
                system_prompt=_ROUTER_INTENT,
            )

            if not isinstance(response, dict):
                logger.error("Invalid response from LLM", response_type=type(response).__name__)
                raise TypeError("LLM response must be a dictionary")


            intent =response.get("response")
            intent = json.loads(intent)

            return {
                "intent": intent.get("label"),
                "latency_ms": response.get("latency_ms",0),
                "total_tokens": response.get("total_tokens",0),
                "token_cost": response.get("token_cost",0),
            }

        except Exception as e:
            logger.exception(
                "Router intent generation failed",
                query=user_query,
                error=str(e)
            )
            raise RuntimeError("Failed to process router intent") from e








    
