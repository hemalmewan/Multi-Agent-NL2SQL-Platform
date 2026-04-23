"""
guardrails.py
=============
SQL query safety layer for the AI Engineering Bootcamp mini-project-04 pipeline.

This module defines :class:`SQLGuardRails`, which enforces a three-stage
validation pipeline on every SQL query before it reaches the database:

1. **Prohibited keyword detection** — immediately blocks any query that
   contains destructive DDL/DML keywords (DROP, DELETE, UPDATE, INSERT,
   ALTER, CREATE, TRUNCATE, GRANT, REVOKE).
2. **SELECT-only enforcement** — rejects any statement that is not a
   read-only SELECT query, ensuring the database is never mutated through
   this interface.
3. **LLM-assisted syntax validation** — delegates syntax checking to a
   configured LLM client, accepting only queries that the model confirms
   are syntactically correct.

Typical usage
-------------
>>> from src.infrastructure.guardrails.guardrails import SQLGuardRails
>>> guardrails = SQLGuardRails(llm=my_llm_client)
>>> if guardrails.is_validate(sql_query):
...     results = db.execute(sql_query)

Dependencies
------------
- ``loguru`` — structured logging throughout the pipeline.
- ``src.agents.prompts._QUERY_SYNTAX_CHECK_PROMPT`` — system prompt used
  when asking the LLM to verify SQL syntax.
"""

##===========================
## Import Required Libraries
##===========================
from typing import Dict, Any, Optional, Tuple
import os
from loguru import logger

##==================================
## Import User Define Python Modules
##==================================
from src.agents.prompts._QUERY_SYNTAX_CHECK_PROMPT import _QUERY_SYNTAX_CHECK_PROMPT


# ============================
## SQL Query Guardrails
## ============================
class SQLGuardRails:
    """
    A guardrails layer for validating SQL queries before database execution.

    This class enforces a multi-step safety pipeline on any SQL query:
      1. Rejects queries containing prohibited DML/DDL keywords (e.g. DROP, DELETE).
      2. Ensures the query starts with SELECT (read-only enforcement).
      3. Validates SQL syntax correctness via an LLM call.

    Only queries that pass all three checks are considered safe for execution.

    Parameters
    ----------
    llm : object
        An LLM client instance that exposes a ``generate(user_prompt, system_prompt)``
        method. Used for the syntax-validation step.

    Attributes
    ----------
    prohibited_quries : list[str]
        Uppercase SQL keywords whose presence in a query causes immediate rejection.
    llm_call : object
        The injected LLM client used for syntax checking.

    Examples
    --------
    >>> guardrails = SQLGuardRails(llm=my_llm_client)
    >>> guardrails.is_validate("SELECT * FROM users WHERE id = 1")
    True
    >>> guardrails.is_validate("DROP TABLE users")
    False
    """

    def __init__(self, llm):
        """
        Initialise SQLGuardRails with an LLM client.

        Parameters
        ----------
        llm : object
            An LLM client instance with a ``generate(user_prompt, system_prompt)``
            method. The client is used exclusively for SQL syntax validation.
        """
        self.prohibited_quries=[
            "DROP","DELETE","UPDATE","INSERT","ALTER",
            "CREATE","TRUNCATE","GRANT",
            "REVOKE"
        ]

        self.llm_call=llm

    ## ============================
    ##  Block dangerous SQL queries
    ## ============================
    def _is_prohibited(
        self,
        sql_query:str
        ) -> bool:
        """
        Detect whether a SQL query contains any prohibited keyword.

        Scans the uppercased query string for keywords that indicate
        destructive or mutating operations (DDL/DML). If any match is
        found the query is considered prohibited and a warning is logged.

        Parameters
        ----------
        sql_query : str
            The raw SQL query string to inspect.

        Returns
        -------
        bool
            ``True`` if one or more prohibited keywords are present,
            ``False`` if the query is free of prohibited keywords.

        Notes
        -----
        The check is case-insensitive because the query is uppercased
        before comparison. Leading/trailing whitespace is stripped first.
        """

        for keyword in self.prohibited_quries:
            if keyword in sql_query.strip().upper():
                logger.warning(f"Prohibited SQL query detected: {keyword}")
                return True

        return False

    ##===========================
    ## Allow Only SELECT queries
    ##===========================
    def _is_select(
        self,
        sql_query:str
        ) -> bool:
        """
        Verify that the SQL query is a read-only SELECT statement.

        The system only permits SELECT queries to reach the database.
        Any other statement type (e.g. EXEC, WITH used as a CTE root,
        CALL, etc.) is rejected at this stage.

        Parameters
        ----------
        sql_query : str
            The raw SQL query string to inspect.

        Returns
        -------
        bool
            ``True`` if the query starts with the ``SELECT`` keyword
            (case-insensitive), ``False`` otherwise.

        Notes
        -----
        The comparison strips leading whitespace and uppercases the query
        before checking the prefix, so formatting differences do not
        affect the result.
        """

        if sql_query.strip().upper().startswith("SELECT"):
            logger.info("SQL query is safe. Proceeding to syntax checking")
            return True

        logger.warning("SQL query is not a SELECT query. Rejecting query from system")
        return False


    ##==========================
    ## Check SQL Syntax Erros
    ##==========================
    def _is_query_syntax_valid(
        self,
        sql_query:str
        ) -> bool:
        """
        Validate SQL syntax by delegating to the configured LLM.

        Sends the query to the LLM together with a system prompt
        (``_QUERY_SYNTAX_CHECK_PROMPT``) that instructs the model to
        respond with exactly ``"TRUE"`` for syntactically valid SQL or
        ``"FALSE"`` otherwise.

        Parameters
        ----------
        sql_query : str
            The SQL query whose syntax should be validated.

        Returns
        -------
        bool
            ``True`` if the LLM responds with ``"TRUE"`` (case-insensitive
            after stripping whitespace), ``False`` for any other response.

        Notes
        -----
        The LLM response is uppercased and stripped before comparison, so
        minor formatting variations (e.g. newlines) do not cause false
        negatives. The raw response is logged at DEBUG level for
        traceability.
        """

        prompt=f"SQL QUERY:{sql_query}"

        response = self.llm_call.generate(
            user_prompt=prompt,
            system_prompt=_QUERY_SYNTAX_CHECK_PROMPT
        )

        response_text = response.get("response", "").strip().upper()

        logger.debug("LLM syntax response", response=response_text)

        return response_text == "TRUE"

    ##===============================
    ## Guardrails Check Orchestrator
    ##================================
    def is_validate(self, sql_query: str) -> bool:
        """
        Orchestrate the full guardrails pipeline for a SQL query.

        Runs the query through three sequential checks:

        1. **Input sanity** — rejects ``None``, empty strings, or non-string
           values immediately.
        2. **Prohibited keyword check** (``_is_prohibited``) — rejects any
           query containing destructive DDL/DML keywords.
        3. **SELECT-only enforcement** (``_is_select``) — rejects queries that
           are not read-only SELECT statements.
        4. **Syntax validation** (``_is_query_syntax_valid``) — uses an LLM to
           confirm the query is syntactically correct before allowing execution.

        Parameters
        ----------
        sql_query : str
            The SQL query string to validate.

        Returns
        -------
        bool
            ``True`` if the query passes every guardrail and is safe to
            forward to the database, ``False`` if it fails any check.

        Examples
        --------
        >>> guardrails = SQLGuardRails(llm=my_llm_client)
        >>> guardrails.is_validate("SELECT id, name FROM employees LIMIT 10")
        True
        >>> guardrails.is_validate("DELETE FROM employees WHERE id = 5")
        False
        >>> guardrails.is_validate("")
        False
        """
        logger.info("Starting SQL Guardrails",query=sql_query)

        if not sql_query or not isinstance(sql_query, str):
            logger.error("Invalid SQL query input")
            return False

        if self._is_prohibited(sql_query):
            logger.warning("SQL query is not safe. Rejecting the query from system")
            return False
        
        elif self._is_select(sql_query):
            if self._is_query_syntax_valid(sql_query):
                logger.info("SQL query syntax varified.Processing for database execution")
                return True
            else:
                logger.warning("SQL query syntax mismaching. Rejecting query from the system")
                return False
        
        logger.info("SQL query passed all guardrails")
        return True


        






        
        

        

        

    

    

        
 
        

    