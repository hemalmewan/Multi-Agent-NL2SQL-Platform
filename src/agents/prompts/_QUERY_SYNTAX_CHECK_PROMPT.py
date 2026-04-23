"""
_QUERY_SYNTAX_CHECK_PROMPT.py
==============================
System prompt used by :class:`SQLGuardRails` to validate SQL syntax via an LLM.

This module exposes a single string constant, ``_QUERY_SYNTAX_CHECK_PROMPT``,
which is passed as the ``system_prompt`` argument when calling the LLM inside
``SQLGuardRails._is_query_syntax_valid``.

The prompt instructs the model to act as a strict SQL validator and return
only ``"TRUE"`` (valid syntax) or ``"FALSE"`` (invalid syntax), with no
additional explanation.  The calling code uppercases and strips the response
before comparing it to ``"TRUE"``.

Constants
---------
_QUERY_SYNTAX_CHECK_PROMPT : str
    LLM system prompt for SQL syntax checking. Contains a placeholder
    ``{sql_query}`` that is substituted with the actual query at runtime
    by the caller before sending the request.

Usage
-----
This constant is imported and used exclusively by
``src.infrastructure.guardrails.guardrails.SQLGuardRails``:

>>> from src.agents.prompts._QUERY_SYNTAX_CHECK_PROMPT import _QUERY_SYNTAX_CHECK_PROMPT
>>> response = llm.generate(
...     user_prompt=f"SQL QUERY:{sql_query}",
...     system_prompt=_QUERY_SYNTAX_CHECK_PROMPT,
... )
"""

_QUERY_SYNTAX_CHECK_PROMPT="""
 Your are strict SQL query validator.

 Your task is to determine if the SQL query is valid or not.

 RETURN:
  - TRUE -> If the SQL query is valid.
  - FALSE -> If the SQL query is invalid.
 
 Do NOT explain the reason. Just return TRUE or FALSE.

 SQL Query :
 {sql_query}
"""