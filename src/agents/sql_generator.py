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
3. Build a filtered schema context — tables with their columns and any
   foreign-key relationships between the selected tables
   (:meth:`~SQLGenerator._build_schema_context`).
4. Format the filtered schema context into ``_SQL_GENERATOR_PROMPT`` and
   send it to the LLM.
5. Strip Markdown code fences from the response and return the clean SQL
   together with the original query, token-usage, and latency metadata.

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
from src.agents.prompts._QUERY_AMBIGUITY_CHECK import _QUERY_AMBIGUITY_CHECK_PROMPT

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
        schema:Optional[Dict[str,Any]]=None
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
                - ``"User Query"`` (str): The original natural language query passed
                  by the caller, echoed back for traceability.
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
            schema_context=self._build_schema_context(schema,relevant_tables)

            if not schema_context["relationships"] and not schema_context["tables"]:

                logger.warning(
                    "No tables found for the given query",
                    user_query=user_query
                )
                return {
                    "sql_query":"",
                    "message":"Unable to identify relevant data for your request. Please refine your query.",
                    "status":"failed",
                    "user_query":user_query,
                    "latency_ms":0,
                    "token_cost":0,
                    "total_tokens":0
                }
            
            if not schema_context["relationships"] and  len(schema_context["tables"])>1:

                logger.warning(
                        "Multiple tables found but no relationships",
                        query=user_query,
                        tables=relevant_tables
                    )

                return {
                    "sql_query":"",
                    "message":"The requested data spans multiple entities, but no valid relationships were found between them.",
                    "status":"failed",
                    "relevant_tables":relevant_tables,
                    "user_query":user_query,
                    "latency_ms":0,
                    "token_cost":0,
                    "total_tokens":0
                }

            prompt=_SQL_GENERATOR_PROMPT.format(
                relevant_tables=schema_context["tables"],
                relevant_relationships=schema_context["relationships"],
                user_prompt=user_query
            )

            response=self.llm_call.generate(prompt)

            if not isinstance(response, dict):
                logger.error("Invalid LLM response", response_type=type(response).__name__)
                raise TypeError("LLM response must be a dictionary")

            sql_query=response.get("response"," ").strip()
            sql_query=sql_query.replace("```sql"," ").replace("```"," ").strip()

            return {
                "sql_query":sql_query,
                "user_query":user_query,
                "relevant_tables":relevant_tables,
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
    
    def _build_schema_context(
        self,
        schema: Dict[str, Any],
        selected_tables: List[str]
    ) -> Dict[str, Any]:
        """
        Build a filtered schema context from the selected tables and their relationships.

        Starting from ``selected_tables``, the method scans every relationship in the
        schema and collects join conditions where both the source and target table are
        in the selected set.  It then assembles a column listing for each included
        table, producing a compact context dict that can be embedded directly into the
        LLM prompt.

        Args:
            schema (Dict[str, Any]): The full database schema dictionary. Expected keys:
                - ``"tables"`` (dict): Maps table names to their metadata, where each
                  entry may include a ``"column_names"`` list of column name strings.
                - ``"relationships"`` (list): List of relationship dicts, each with
                  ``"from"`` and ``"to"`` keys in ``"table.column"`` format.
            selected_tables (List[str]): Table names pre-selected by
                :meth:`_get_relevent_tables` whose columns should appear in the context.

        Returns:
            Dict[str, Any]: A dictionary with two keys:
                - ``"tables"`` (list[dict]): Each entry has the form
                  ``{"table": <name>, "columns": [<col>, ...]}``, one per selected table
                  that exists in the schema.
                - ``"relationships"`` (list[str]): Join conditions between selected
                  tables, formatted as ``"<from_col> = <to_col>"``.

        Example:
            >>> schema = {
            ...     "tables": {
            ...         "orders": {"column_names": ["id", "customer_id", "total"]},
            ...         "customers": {"column_names": ["id", "name"]},
            ...     },
            ...     "relationships": [
            ...         {"from": "orders.customer_id", "to": "customers.id"}
            ...     ]
            ... }
            >>> agent._build_schema_context(schema, ["orders", "customers"])
            {
                "tables": [
                    {"table": "orders", "columns": ["id", "customer_id", "total"]},
                    {"table": "customers", "columns": ["id", "name"]}
                ],
                "relationships": ["customer_id = id"]
            }
        """

        expanded_tables = set(selected_tables)
        relationships = set()    

        for rel in schema.get("relationships", []):
            from_field = rel.get("from")
            to_field = rel.get("to")

            if not from_field and not to_field:
                continue

            from_table = from_field.split(".")[0]
            to_table = to_field.split(".")[0]

            if (from_table in expanded_tables) and (to_table in expanded_tables):
                expanded_tables.add(from_table)
                expanded_tables.add(to_table)
                relationships.add(f"{from_field.split('.')[1]} = {to_field.split('.')[1]}")
        
        tables_context = []

        for table in expanded_tables:
            if table not in schema.get("tables", {}):
                continue
            table_data = schema.get("tables", {}).get(table, {})
            columns = table_data.get("column_names", [])

            tables_context.append({
                "table": table,
                "columns": columns
            })

        return {
            "tables": tables_context,
            "relationships": list(relationships)
        }
    
    def _check_ambiguity(self, user_query: str) -> Dict[str,Any]:
        """
        Determine whether a natural language query is clear and unambiguous.

        Sends the query to the LLM using the ambiguity-check system prompt
        (``_QUERY_AMBIGUITY_CHECK_PROMPT``) and interprets the response as a
        boolean signal:

        - ``"FALSE"`` — the query is clear and can proceed to SQL generation.
        - ``"TRUE"``  — the query is ambiguous or invalid and should be rejected.

        Any unexpected response or exception is treated as clear (returns
        ``False``) to fail safely.

        Args:
            user_query (str): The natural language query to evaluate.

        Returns:
            bool: ``False`` if the query is deemed clear and unambiguous by the
                  LLM; ``True`` otherwise (ambiguous, invalid, or on error).

        Example:
            >>> _check_ambiguity("List all patients admitted in January 2024")
            False
            >>> _check_ambiguity("show me the thing")
            True
        """
        logger.info("Starting ambiguity check", query=user_query)

        prompt = f"User Query: {user_query}"

        try:
            response = self.llm_call.generate(
                user_prompt=prompt,
                system_prompt=_QUERY_AMBIGUITY_CHECK_PROMPT
            )

            if not isinstance(response, dict):
                logger.error(
                    "Invalid LLM response format",
                    response_type=type(response).__name__
                )
                return False

            response_text = response.get("response", "").strip().upper()

            logger.debug(
                "Ambiguity raw response",
                query=user_query,
                response=response_text,
                latency_ms=response.get("latency_ms", 0),
                token_cost=response.get("token_cost", 0),
                total_tokens=response.get("total_tokens", 0)
            )

            if response_text == "FALSE":
                logger.info("Query classified as CLEAR", query=user_query)
                return {
                    "status":False,
                    "total_tokens":response.get("total_tokens",0),
                    "token_cost":response.get("token_cost",0),
                    "latency_ms":response.get("latency_ms",0)
                }

            elif response_text == "TRUE":
                logger.warning("Query classified as AMBIGUOUS/INVALID", query=user_query)
                return {
                    "status":True,
                    "total_tokens":response.get("total_tokens",0),
                    "token_cost":response.get("token_cost",0),
                    "latency_ms":response.get("latency_ms",0)
                }

            else:
                logger.error(
                    "Unexpected ambiguity response",
                    query=user_query,
                    response=response_text
                )
                return {
                    "status":False,
                    "total_tokens":response.get("total_tokens",0),
                    "token_cost":response.get("token_cost",0),
                    "latency_ms":response.get("latency_ms",0)
                }

        except Exception as e:
            logger.exception(
                "Ambiguity check failed",
                query=user_query,
                error=str(e)
            )
            return {
                "status":False,
                "total_tokens":0,
                "token_cost":0,
                "latency_ms":0
            }
    
    def refine_query(
        self,
        user_query:str,
        max_iterations:int=3
    )-> Dict[str,Any]:
        """
        Interactively refine an ambiguous query until it is clear or retries are exhausted.

        Prompts the user (via ``input()``) for additional detail on each iteration,
        merges the original query with the new detail through the LLM, and then
        runs :meth:`_check_ambiguity` on the result.  The loop exits as soon as the
        LLM classifies the refined query as unambiguous, or after ``max_iterations``
        attempts — whichever comes first.

        Args:
            user_query (str): The initial natural language query that may be ambiguous
                              or under-specified.  Must be a non-empty string.
            max_iterations (int): Maximum number of clarification rounds to attempt
                                  before giving up.  Defaults to ``3``.

        Returns:
            Dict[str, Any]: A dictionary with the following keys:

            On success (query resolved as unambiguous):
                - ``"status"`` (str): ``"refined"``
                - ``"query"`` (str): The final, clarified natural language query.
                - ``"iterations"`` (int): The refinement round on which success occurred.
                - ``"latency_ms"`` (float | int): LLM latency for the last refinement call.
                - ``"token_cost"`` (float | int): Token cost for the last refinement call.
                - ``"total_tokens"`` (int): Total tokens consumed by the last refinement call.

            On failure (max iterations reached):
                - ``"status"`` (str): ``"failed"``
                - ``"message"`` (str): Human-readable explanation.
                - ``"latency_ms"`` (float | int): LLM latency for the final call.
                - ``"token_cost"`` (float | int): Token cost for the final call.
                - ``"total_tokens"`` (int): Total tokens consumed by the final call.

        Raises:
            ValueError: If ``user_query`` is not a non-empty string, if any
                        ``query_detail`` input is empty, or if an unexpected error
                        occurs during refinement (wraps the underlying exception).

        Example:
            >>> # Simulated interactive session — user types "doctors with most admissions"
            >>> result = agent.refine_query("show me the thing", max_iterations=2)
            Iteration 1: Please provide the query in more specific details: doctors with most admissions
            >>> result["status"]
            'refined'
            >>> result["query"]
            'List the top doctors ranked by total number of patient admissions.'
        """

        if not isinstance(user_query, str) or not user_query.strip():
            logger.error("Invalid user_query", value=user_query)
            raise ValueError("user query must be a non-empty string")
        
        try:
            current_query=user_query

            for iteration in range(1,max_iterations+1):

                logger.info(f"Refinement iteration {iteration}", query=current_query)

                query_detail = input(f"Iteration {iteration}: Please provide the query in more specific details: ")
                
                if not isinstance(query_detail, str) or not query_detail.strip():
                    logger.error("Invalid query_detail", value=query_detail)
                    raise ValueError("query_detail must be a non-empty string")
                
                ## prompt construction
                refine_prompt=f"""
                 Original Query: {current_query}
                 Additional Details: {query_detail}

                 Refine the user query into a clear and complete refine user query.
                """
                
                llm_refine_query = self.llm_call.generate(
                    user_prompt=refine_prompt,
                    system_prompt="You are a query refinement agent. Your task is to refine the original user query based on the provided additional query detail.",
                )
                
                refined_query = llm_refine_query.get("response", "").strip()

                logger.debug("Refine user query", refined_query=refined_query)
                is_ambiguous = self._check_ambiguity(refined_query)

                if is_ambiguous['status']:
                    logger.warning("Refined query is ambiguous, continuing refinement", query=refined_query)
                    current_query = refined_query
                    continue
                
               
                logger.info("Query refinement completed successfully", query=refined_query)
                return {
                    "status": "refined",
                    "query": refined_query,
                    "iterations":iteration,
                    "latency_ms":llm_refine_query.get("latency_ms", 0),
                    "token_cost":llm_refine_query.get("token_cost", 0),
                    "total_tokens":llm_refine_query.get("total_tokens", 0),
                }
                break
            
            # after max attempts
            logger.warning("Max refinement attempts reached", query=current_query)

            return {
            "status": "failed",
            "iterations":max_iterations,
            "message": "Unable to refine query after multiple attempts",
            "latency_ms":llm_refine_query.get("latency_ms", 0),
            "token_cost":llm_refine_query.get("token_cost", 0),
            "total_tokens":llm_refine_query.get("total_tokens", 0),
            }
            
        
        except Exception as e:
            logger.exception(
                "Query refinement failed",
                query=user_query,
                error=str(e)
            )
            raise ValueError("Query refinement failed")
            
            
            
    

        




        


