"""
sql_generator.py
================
SQL generation agent for the NL2SQL pipeline.

This module contains ``SQLGenerator``, a schema-aware agent that translates
natural language queries into executable PostgreSQL statements using an LLM.

Pipeline overview
-----------------
1. Validate the incoming ``user_query`` and ``schema``.
2. Identify relevant database tables by matching schema keywords against
   the query text (:meth:`~SQLGenerator._get_relevent_tables`).
3. Resolve foreign-key join conditions between the selected tables
   (:meth:`~SQLGenerator._get_relevent_relationships`).
4. Format the filtered schema context into ``_SQL_GENERATOR_PROMPT`` and
   send it to the LLM.
5. Strip Markdown code fences from the response and return the clean SQL
   together with token-usage and latency metadata.

Dependencies
------------
- ``src.infrastructure.config._get_schema``
    Loads the database schema from ``config/schema.yaml`` when no schema is
    supplied by the caller.
- ``src.agents.prompts._SQL_GENERATOR_PROMPT._SQL_GENERATOR_PROMPT``
    Prompt template with ``{relevant_tables}``, ``{relevant_relationships}``,
    and ``{user_prompt}`` placeholders.
- Any ``LLMProvider``-compatible object injected at construction time
    (``OpenRouterProvider``, ``OpenAIProvider``, or ``DummyProvider``).
- ``loguru`` — structured logging throughout the pipeline.

Example
-------
::

    from src.infrastructure.llm.llm_providers import _global_llm_provider
    from src.agents.sql_generator import SQLGenerator

    agent = SQLGenerator(llm=_global_llm_provider())
    result = agent.generate_sql("List the top 5 doctors by number of admissions", schema=None)
    print(result["SQL query"])
"""

##============================
## Import Required Libraries
##============================
from typing import Dict,Any,Optional,List
from loguru import logger
import time

##===================================
## Import User Define Python Modules
##===================================
from src.infrastructure.config import _get_schema
from src.agents.prompts._SQL_GENERATOR_PROMPT import _SQL_GENERATOR_PROMPT

##===================================
## SQL Generator Agent
##===================================
class SQLGenerator:
    """
    An agent that converts natural language queries into SQL statements using an LLM.

    This class uses a schema-aware prompting strategy to identify relevant database
    tables and relationships from a provided schema, then constructs a targeted prompt
    for the LLM to generate a syntactically correct SQL query.

    Attributes:
        llm_call: An LLM client instance with a `generate(prompt: str) -> dict` method.
                  The response dict is expected to contain keys: 'response', 'latency_ms',
                  'token_cost', and 'total_tokens'.

    Example:
        >>> from src.infrastructure.llm_client import LLMClient
        >>> llm = LLMClient()
        >>> agent = SQLGenerator(llm)
        >>> result = agent.generate_sql("Show all orders placed in 2024", schema=None)
        >>> print(result["SQL query"])
        SELECT * FROM orders WHERE YEAR(order_date) = 2024;
    """

    def __init__(self,llm):
        """
        Initialise the SQLGenerator with an LLM client.

        Args:
            llm: An LLM client object exposing a `generate(prompt: str) -> dict`
                 method used to produce SQL from formatted prompts.
        """
        self.llm_call=llm

    def generate_sql(
        self,
        user_query:str,
        schema:Optional[Dict[str,Any]]
    )->Dict[str,Any]:
        """
        Translate a natural language query into a SQL statement.

        The method performs the following steps:
        1. Validates the input query and schema.
        2. Falls back to the configured default schema if none is provided.
        3. Identifies tables in the schema whose keywords match the query.
        4. Resolves relevant foreign-key relationships between those tables.
        5. Builds a prompt from the filtered schema context and sends it to the LLM.
        6. Strips Markdown code fences from the LLM response and returns the clean SQL.

        Args:
            user_query (str): A non-empty natural language question or instruction
                              describing the data to retrieve (e.g. "List all active users").
            schema (Optional[Dict[str, Any]]): A dictionary describing the database schema,
                containing at minimum:
                    - ``"tables"`` (dict): Mapping of table names to their metadata,
                      where each entry may include a ``"keywords"`` list used for
                      relevance matching.
                    - ``"relationships"`` (list): List of relationship dicts, each with
                      ``"from"`` and ``"to"`` keys in ``"table.column"`` format.
                If ``None``, the default schema is loaded via :func:`_get_schema`.

        Returns:
            Dict[str, Any]: A dictionary with the following keys:
                - ``"SQL query"`` (str): The generated SQL statement, stripped of
                  Markdown code fences.
                - ``"latency_ms"`` (float | int): Time taken by the LLM to respond,
                  in milliseconds.
                - ``"token_cost"`` (float | int): Estimated cost in tokens or currency
                  units for the LLM call.
                - ``"total_tokens"`` (int): Total number of tokens consumed by the
                  request and response.

        Raises:
            ValueError: If ``user_query`` is not a non-empty string.
            TypeError: If ``schema`` is not a dictionary, or if the LLM response is
                       not a dictionary.
            RuntimeError: If SQL generation fails for any other reason; wraps the
                          underlying exception.

        Example:
            >>> result = agent.generate_sql("How many customers signed up last month?", schema=None)
            >>> result["SQL query"]
            "SELECT COUNT(*) FROM customers WHERE signup_date >= DATE_TRUNC('month', NOW() - INTERVAL '1 month');"
        """

        if not isinstance(user_query, str) or not user_query.strip():
            logger.error("Invalid user_query", value=user_query)
            raise ValueError("user query must be a non-empty string")

        try:

            if schema is None:
                schema=_get_schema()
            
            if not isinstance(schema, dict):
                logger.error("Invalid schema format", schema_type=type(schema).__name__)
                raise TypeError("Schema must be a dictionary")

            relevant_tables=self._get_relevent_tables(schema,user_query)
            relevant_relationships=self._get_relevent_relationships(schema,relevant_tables)

            prompt=_SQL_GENERATOR_PROMPT.format(
                relevant_tables=", ".join(relevant_relationships["tables"]),
                relevant_relationships="\n".join(relevant_relationships["relationships"]),
                user_prompt=user_query
            )

            response=self.llm_call.generate(prompt)

            if not isinstance(response, dict):
                logger.error("Invalid LLM response", response_type=type(response).__name__)
                raise TypeError("LLM response must be a dictionary")

            sql_query=response.get("response"," ").strip()
            sql_query=sql_query.replace("```sql"," ").replace("```"," ").strip()

            return {
                "SQL query":sql_query,
                "latency_ms":response.get("latency_ms",0),
                "token_cost":response.get("token_cost",0),
                "total_tokens":response.get("total_tokens",0)
            }
        
        except Exception as e:
            logger.exception(
                "SQL generation failed",
                query=user_query,
                error=str(e)
            )
            raise RuntimeError("Failed to generate SQL query") from e
    
    def _get_relevent_tables(
        self,
        schema:Dict[str,Any],
        user_query:str
    )-> List[str]:
        """
        Identify database tables whose keywords appear in the user query.

        Iterates over every table defined in the schema and checks whether any of
        its associated keywords are present (case-insensitively) in the user query.
        Tables with at least one matching keyword are included in the result.

        Args:
            schema (Dict[str, Any]): The full database schema dictionary. Must contain
                a ``"tables"`` key mapping table names to their metadata dicts.
                Each metadata dict may include a ``"keywords"`` list of strings used
                for relevance matching.
            user_query (str): The natural language query string to match against
                table keywords.

        Returns:
            List[str]: A list of table names whose keywords were found in the query.
                       The list may be empty if no keywords matched.

        Raises:
            ValueError: If the schema does not contain a valid ``"tables"`` dictionary.
            Exception: Re-raises any unexpected error after logging it.

        Example:
            >>> schema = {
            ...     "tables": {
            ...         "orders": {"keywords": ["order", "purchase"]},
            ...         "customers": {"keywords": ["customer", "client"]},
            ...     },
            ...     "relationships": []
            ... }
            >>> agent._get_relevent_tables(schema, "show all orders")
            ['orders']
        """

        try:
            if "tables" not in schema or not isinstance(schema["tables"], dict):
                logger.error("Schema missing 'tables' or invalid format")
                raise ValueError("Invalid schema: missing 'tables'")
            
            query=user_query.lower()
            selected_tables=set()

            for table_name,data in schema["tables"].items():

                if not isinstance(data, dict):
                    continue
                for keyword in data.get("keywords",[]):
                    if isinstance(keyword, str) and keyword in query:
                        selected_tables.add(table_name)
            
            return list(selected_tables)
        
        except Exception as e:
            logger.exception("Failed to extract relevant tables", error=str(e))
            raise

    def _get_relevent_relationships(
        self,
        schema:Dict[str,Any],
        selected_tables:List[str]
    )-> Dict[str,List[str]]:
        """
        Resolve foreign-key relationships between a set of selected tables.

        Scans the ``"relationships"`` list in the schema and retains only those
        join conditions where *both* the source and target tables are already in
        the selected set. Each qualifying relationship is expressed as a string
        ``"table_a.col = table_b.col"`` suitable for use in a SQL ``JOIN … ON``
        clause. The method also ensures both table names are present in the
        returned tables list (they should be, but the set union makes this
        explicit).

        Args:
            schema (Dict[str, Any]): The full database schema dictionary. Must contain
                a ``"relationships"`` key with a list of relationship dicts. Each dict
                should have:
                    - ``"from"`` (str): Source column in ``"table.column"`` format.
                    - ``"to"`` (str): Target column in ``"table.column"`` format.
            selected_tables (List[str]): Table names previously identified as relevant
                to the user query (typically the output of :meth:`_get_relevent_tables`).

        Returns:
            Dict[str, List[str]]: A dictionary with two keys:
                - ``"tables"`` (List[str]): Deduplicated list of table names involved
                  in at least one relevant relationship, merged with the input
                  ``selected_tables``.
                - ``"relationships"`` (List[str]): List of join condition strings in
                  the form ``"table_a.col = table_b.col"``.

        Raises:
            Exception: Re-raises any unexpected error (e.g. missing ``"relationships"``
                       key) after logging it.

        Example:
            >>> schema = {
            ...     "tables": {...},
            ...     "relationships": [
            ...         {"from": "orders.customer_id", "to": "customers.id"},
            ...         {"from": "products.category_id", "to": "categories.id"},
            ...     ]
            ... }
            >>> agent._get_relevent_relationships(schema, ["orders", "customers"])
            {
                "tables": ["orders", "customers"],
                "relationships": ["orders.customer_id = customers.id"]
            }
        """

        try:

            selected_relationships=set()
            selected_tables_set=set(selected_tables)

            for rel in schema["relationships"]:
                if not isinstance(rel, dict):
                    continue

                from_field = rel.get("from")
                to_field = rel.get("to")

                if not from_field or not to_field:
                    continue

                from_table=from_field.split(".")[0]
                to_table=to_field.split(".")[0]

                if from_table in selected_tables_set and to_table in selected_tables_set:
                    selected_tables_set.add(from_table)
                    selected_tables_set.add(to_table)
                    selected_relationships.add(f"{from_field} = {to_field}")
            
            return {
                "relationships":list(selected_relationships),
                "tables":list(selected_tables_set)
            }
        
        except Exception as e:
            logger.exception("Failed to extract relationships", error=str(e))
            raise


            


        





        

        


