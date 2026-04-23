"""
orchestrator.py
===============
Multi-agent orchestrator for the NL2SQL pipeline.

This module contains ``Orchestrator``, the top-level controller that coordinates
all agents — intent routing, query ambiguity checking, query refinement, and SQL
generation — into a single, coherent request-handling pipeline.

Pipeline overview
-----------------
1. **Intent routing** (:class:`~src.agents.intent_router.RouterIntent`): classify
   the incoming natural language query as ``"SQL"`` or a non-SQL intent.
2. **Ambiguity check** (:meth:`~src.agents.sql_generator.SQLGenerator._check_ambiguity`):
   if the intent is ``"SQL"``, verify the query is clear enough to translate directly.
3. **Query refinement** (:meth:`~src.agents.sql_generator.SQLGenerator.refine_query`):
   if the query is ambiguous, interactively refine it with the user before proceeding.
4. **SQL generation** (:meth:`~src.agents.sql_generator.SQLGenerator.generate_sql`):
   translate the (possibly refined) query into an executable PostgreSQL statement.
5. Aggregate token usage and wall-clock latency across all agent calls and return a
   unified response dictionary.

Dependencies
------------
- ``src.agents.intent_router.RouterIntent``
    Classifies user intent and returns an ``"intent"`` field of ``"SQL"`` or other.
- ``src.agents.sql_generator.SQLGenerator``
    Checks ambiguity, refines queries, and generates SQL from natural language.
- ``loguru`` — structured logging throughout the pipeline.

Example
-------
::

    from src.infrastructure.llm.llm_providers import _global_llm_provider
    from src.agents.orchestrator import Orchestrator

    orchestrator = Orchestrator(llm=_global_llm_provider())
    result = orchestrator.agent_orchestrator(
        "List the top 5 doctors by number of admissions"
    )
    print(result["sql_query"])
"""

##===========================
## Import Required Libraries
##===========================
from typing import Dict,Any,Optional
from loguru import logger
import time

##===================================
## Import User Define Python Modules
##===================================
from src.agents.intent_router import RouterIntent
from src.agents.sql_generator import SQLGenerator
from src.infrastructure.guardrails.guardrails import SQLGuardRails
from src.infrastructure.db.supabase_client import _execute_sql_query
#from src.agents.result_interpreter import ResultInterpreter

##===================================
## Mutli Agent Orchestrator Class
##===================================
class Orchestrator:
    """
    Top-level controller that wires together all NL2SQL pipeline agents.

    ``Orchestrator`` owns one instance of each sub-agent and exposes a single
    entry-point method (:meth:`agent_orchestrator`) that accepts a natural language
    query, routes it through the appropriate agents, and returns a unified result
    dictionary with the generated SQL (or a rejection message) together with
    aggregated token-usage and latency metadata.

    Attributes:
        router (RouterIntent): Intent-routing agent that classifies the query as
            ``"SQL"`` or a non-SQL intent before any further processing occurs.
        sql_generator (SQLGenerator): Schema-aware agent responsible for ambiguity
            checking, interactive query refinement, and final SQL generation.

    Example:
        >>> from src.infrastructure.llm.llm_providers import _global_llm_provider
        >>> orchestrator = Orchestrator(llm=_global_llm_provider())
        >>> result = orchestrator.agent_orchestrator("Show all admitted patients in 2024")
        >>> result["status"]
        'success'
        >>> result["sql_query"]
        "SELECT * FROM admissions WHERE YEAR(admission_date) = 2024;"
    """

    def __init__(self, llm):
        """
        Initialise the Orchestrator and all sub-agents with a shared LLM client.

        A single LLM client is injected and shared across every sub-agent so that
        all pipeline components use the same provider configuration, rate-limit
        quota, and cost tracking.

        Args:
            llm: An LLM client object exposing at minimum a
                 ``generate(prompt: str) -> dict`` method (and optionally a
                 ``generate(user_prompt, system_prompt)`` signature used by the
                 ambiguity-check and refinement steps).  Compatible with
                 ``OpenRouterProvider``, ``OpenAIProvider``, and ``DummyProvider``.
        """
        self.router=RouterIntent(llm=llm)
        self.sql_generator=SQLGenerator(llm=llm)
        self.guardrails=SQLGuardRails(llm=llm)
        #self.result_interpreter=ResultInterpreter(llm=llm)
    
    def agent_orchestrator(
        self,
        user_query: str,
        schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full NL2SQL pipeline for a single user query.

        The method coordinates the sub-agents in the following order:

        1. **Intent routing** — :class:`RouterIntent` classifies the query.
           If the intent is not ``"SQL"``, the pipeline short-circuits and returns
           an ``"ignored"`` response immediately.
        2. **Ambiguity check** — :meth:`SQLGenerator._check_ambiguity` determines
           whether the SQL-bound query is clear enough to translate directly.
        3. **Query refinement** (conditional) — if the query is ambiguous,
           :meth:`SQLGenerator.refine_query` prompts the user interactively for
           additional detail.  If refinement succeeds the clarified query is used
           downstream; if it fails the pipeline logs a warning and returns without
           a SQL result.
        4. **SQL generation** — :meth:`SQLGenerator.generate_sql` translates the
           (possibly refined) query into a PostgreSQL statement using the filtered
           schema context.

        Token counts and token costs are accumulated across every agent call and
        reported in the final response.  End-to-end wall-clock latency is measured
        from the start of the method to the point of return.

        Args:
            user_query (str): The natural language question or instruction from the
                              user (e.g. ``"List the top 5 doctors by admissions"``).
                              Must be a non-empty string.
            schema (Optional[Dict[str, Any]]): An optional database schema dictionary
                passed through to :meth:`SQLGenerator.generate_sql`.  When ``None``
                the SQL generator loads the default schema via :func:`_get_schema`.
                See :meth:`SQLGenerator.generate_sql` for the expected structure.

        Returns:
            Dict[str, Any]: A unified response dictionary. The exact keys depend on
            the execution path taken:

            SQL query generated successfully:
                - ``"sql_query"`` (str): The generated PostgreSQL statement.
                - ``"message"`` (str): ``"SQL query generated successfully"``
                - ``"status"`` (str): ``"success"``
                - ``"latency_ms"`` (int): End-to-end wall-clock time in milliseconds.
                - ``"total_tokens"`` (int): Cumulative tokens used across all agents.
                - ``"token_cost"`` (float): Cumulative token cost across all agents.

            Non-SQL intent detected:
                - ``"message"`` (str): ``"Not a SQL query"``
                - ``"status"`` (str): ``"ignored"``
                - ``"latency_ms"`` (int): End-to-end wall-clock time in milliseconds.
                - ``"total_tokens"`` (int): Tokens consumed by the router call.
                - ``"token_cost"`` (float): Cost consumed by the router call.

        Example:
            >>> orchestrator = Orchestrator(llm=_global_llm_provider())

            >>> # Happy path — unambiguous SQL query
            >>> result = orchestrator.agent_orchestrator(
            ...     "How many patients were admitted in January 2024?"
            ... )
            >>> result["status"]
            'success'
            >>> result["sql_query"]
            "SELECT COUNT(*) FROM admissions WHERE admission_date >= '2024-01-01' ..."

            >>> # Non-SQL input — immediately ignored
            >>> result = orchestrator.agent_orchestrator("What is the weather today?")
            >>> result["status"]
            'ignored'
        """

        

        ## token counter and token cost
        total_tokens=0
        total_token_cost=0
        
        start_time=time.time()

        ## Router intent call
        logger.info("Router intent agent is called")
        router_result=self.router.router(user_query=user_query)

        ## add token count and cost 
        total_tokens+=router_result['total_tokens']
        total_token_cost+=router_result['token_cost']

        ## Router intent call completed
        logger.info("Router intent agent is completed")

        if router_result['intent'] == "SQL":
            ## check SQL query is ambiguity or not
            logger.info("Checking SQL query ambiguity")
            is_ambiguous=self.sql_generator._check_ambiguity(user_query=user_query)

            if is_ambiguous:
                logger.warning("Query is ambiguous, starting refinement")
                refined_result=self.sql_generator.refine_query(user_query=user_query)

                if refined_result["status"]=="refined":
                    user_query=refined_result["query"]
                    total_tokens+=refined_result["total_tokens"]
                    total_token_cost+=refined_result["token_cost"]
                
                    logger.info("Refined user query",query=user_query)
                    logger.info(f"Refinement iterations: {refined_result['iterations']}")

                    ## SQL generator call
                    logger.info("SQL generator agent is called")
                    sql_query_result=self.sql_generator.generate_sql(user_query=user_query)

                    if not sql_query_result["sql_query"]:
                        logger.warning("SQL query is not generated.Please check you prompt or schema")
                    
                    else:
                        ## add token count and cost 
                        total_tokens+=sql_query_result['total_tokens']
                        total_token_cost+=sql_query_result['token_cost']

                        ## SQL generator call completed
                        logger.info("SQL generator agent is completed")

                        ## print SQL query
                        logger.info(f"Generated SQL query: {sql_query_result['sql_query']}")
                        ## print User query
                        logger.info(f"User query: {user_query}")

                        ## check if sql query is safe using guardrails
                        is_safe=self.guardrails.is_validate(sql_query=sql_query_result['sql_query'])

                        if is_safe:
                            logger.info("SQL query is safe and valid")

                             ## execute sql auery using supabase
                            sql_exe_result=_execute_sql_query(sql_query=sql_query_result['sql_query'])
                
                        end_time=time.time()

                        latency_ms=int((end_time-start_time)*1000)

                        logger.info(f"Latency: {latency_ms}ms")
                        logger.info(f"Total Tokens: {total_tokens}")
                        logger.info(f"Total Token Cost: ${total_token_cost:.6f}")

                        return {
                            "sql_query":sql_query_result['sql_query'],
                            "message":"SQL query generated successfully",
                            "status":"success",
                            "latency_ms":latency_ms,
                            "total_tokens":total_tokens,
                            "token_cost":total_token_cost
                        }

                else:
                    logger.warning("Query is not refined.Please Try Again Later!!!!!")
                    

            else:
                ## SQL generator call
                logger.info("SQL generator agent is called")
                sql_query_result=self.sql_generator.generate_sql(user_query=user_query)

                if not sql_query_result["sql_query"]:
                    logger.warning("SQL query is not generated.Please check you prompt or schema")
                else:
                    ## add token count and cost 
                    total_tokens+=sql_query_result['total_tokens']
                    total_token_cost+=sql_query_result['token_cost']

                    ## SQL generator call completed
                    logger.info("SQL generator agent is completed")

                    ## print SQL query
                    logger.info(f"Generated SQL query: {sql_query_result['sql_query']}")
                    ## print User query
                    logger.info(f"User query: {user_query}")

                    ## check if sql query is safe using guardrails
                    is_safe=self.guardrails.is_validate(sql_query=sql_query_result['sql_query'])

                    if is_safe:
                        logger.info("SQL query is safe and valid")

                        ## execute sql auery using supabase
                        sql_exe_result=_execute_sql_query(sql_query=sql_query_result['sql_query'])
                    
                    end_time=time.time()

                    latency_ms=int((end_time-start_time)*1000)

                    logger.info(f"Latency: {latency_ms}ms")
                    logger.info(f"Total Tokens: {total_tokens}")
                    logger.info(f"Total Token Cost: ${total_token_cost:.6f}")

                    return {
                        "sql_query":sql_query_result['sql_query'],
                        "message":"SQL query generated successfully",
                        "status":"success",
                        "latency_ms":latency_ms,
                        "total_tokens":total_tokens,
                        "token_cost":total_token_cost
                    }

        else:
            end_time=time.time()
            latency_ms=int((end_time-start_time)*1000)
            logger.info("Not a SQL query")
            logger.info(f"Latency: {latency_ms}ms")
            logger.info(f"Total Tokens:{router_result['total_tokens']}")
            logger.info(f"Total Token Cost: ${router_result['token_cost']:.6f}")
            print("="*100,"\n")

            return {
                "message":"Not a SQL query",
                "status":"ignored",
                "latency_ms":latency_ms,
                "total_tokens":router_result['total_tokens'],
                "token_cost":router_result['token_cost']
            }


        

       