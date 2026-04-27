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
from src.infrastructure.observerbility_layer import (
   _observe,
   _update_current_trace,
   _update_current_observation,
   _flush
)
from src.agents.result_interpreter import ResultInterpreter

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
        self.result_interpreter=ResultInterpreter(llm=llm)
    
    @_observe(name="NL2SQL Pipeline")
    def agent_orchestrator(
        self,
        user_query: str
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

        ## time measure
        start_time=time.time()

        ## call router intent agent
        router_result=self._router_intent_agent(user_query=user_query)

        ## add token count and cost 
        total_tokens+=router_result['total_tokens']
        total_token_cost+=router_result['token_cost']

        if router_result['intent'] == "SQL":
         
            ## check SQL query is ambiguity or not
            is_ambiguous=self._query_ambiguity_check(user_query=user_query)

            ## add token count and cost
            total_tokens+=is_ambiguous['total_tokens']
            total_token_cost+=is_ambiguous['token_cost']
            
            if is_ambiguous['status']:
                
                ## call query refinement 
                refined_result=self._query_refinement(user_query=user_query)

                ## add token count and cost
                total_tokens+=refined_result['total_tokens']
                total_token_cost+=refined_result['token_cost']

                if refined_result["status"]=="refined":
                    user_query=refined_result["query"]
                
                    logger.info("Refined user query",query=user_query)
                    logger.info(f"Refinement iterations: {refined_result['iterations']}")

                    ## call SQL generator agent
                    sql_query_result=self._sql_generation_agent(user_query=user_query)

                    ## add token count and cost
                    total_tokens+=sql_query_result['total_tokens']
                    total_token_cost+=sql_query_result['token_cost']


                    if not sql_query_result["sql_query"]:
                        logger.warning("SQL query is not generated.Please check you prompt or schema")
                    
                    else:
                        ## print SQL query
                        logger.info(f"Generated SQL query: {sql_query_result['sql_query']}")
                        ## print User query
                        logger.info(f"User query: {user_query}")

                        is_safe=self._guadrails_check(sql_query=sql_query_result['sql_query'])

                        if is_safe:
                            logger.info("SQL query is safe and valid")

                            sql_exe_result=self._database_executor(sql_query=sql_query_result['sql_query'])

                            ## generate a visualization using result interpreter
                            visualization=self._visulization(
                                user_query=user_query,
                                sql_result=sql_exe_result['data']
                            )

                            ## update the observation with 
                            _update_current_observation(
                                input=user_query,
                                output=visualization["type"],
                                metadata={
                                    "stage":"visualization_stage",
                                    "latency_ms":visualization['latency_ms'],
                                },
                                model="gpt-4o-mini",
                                usage={
                                    "input":0,
                                    "output":0,
                                    "total":0
                                }
                            )

                        end_time=time.time()
                        latency_ms=int((end_time-start_time)*1000)

                        logger.info(f"Latency: {latency_ms}ms")
                        logger.info(f"Total Tokens: {total_tokens}")
                        logger.info(f"Total Token Cost: ${total_token_cost:.6f}")

                        ##update the observation with Latency,Total Tokens and Total Cost
                        _update_current_observation(
                            metadata={
                                "token_cost":total_token_cost,
                                "latency_ms":latency_ms,
                            },
                            model="gpt-4o-mini",
                            usage={
                                "input":0,
                                "output":0,
                                "total":total_tokens
                            }
                        )

                        ## flush all 
                        self._flush_observation()

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

                    end_time=time.time()
                    latency_ms=int((end_time-start_time)*1000)
                     ##update the observation with Latency,Total Tokens and Total Cost
                    _update_current_observation(
                         metadata={
                            "token_cost":total_token_cost,
                            "latency_ms":latency_ms,
                            },
                        model="gpt-4o-mini",
                        usage={
                            "input":0,
                            "output":0,
                            "total":total_tokens
                        }
                    )
                    ## flush all
                    self._flush_observation()

                    return {
                        "status": "failed",
                        "message": "Query refinement failed",
                        "latency_ms": latency_ms,
                        "total_tokens": total_tokens,
                        "token_cost": total_token_cost
                    }         

            else:
                ## sql generator agent
                sql_query_result=self._sql_generation_agent(user_query=user_query)

                ## add token count and cost 
                total_tokens+=sql_query_result['total_tokens']
                total_token_cost+=sql_query_result['token_cost']

                if not sql_query_result["sql_query"]:
                    logger.warning("SQL query is not generated.Please check you prompt or schema")
                else:
                    ## print SQL query
                    logger.info(f"Generated SQL query: {sql_query_result['sql_query']}")
                    ## print User query
                    logger.info(f"User query: {user_query}")

                    ## check if sql query is safe using guardrails
                    is_safe=self._guadrails_check(sql_query=sql_query_result['sql_query'])

                    if is_safe:
                        logger.info("SQL query is safe and valid")
                        sql_exe_result=self._database_executor(sql_query=sql_query_result['sql_query'])

                        ## generate a visualization using result interpreter
                        visualization=self._visulization(
                            user_query=user_query,
                            sql_result=sql_exe_result['data']
                        )

                        ## update the observation with 
                        _update_current_observation(
                            input=user_query,
                            output=visualization["type"],
                            metadata={
                                "stage":"visualization_stage",
                                "latency_ms":visualization['latency_ms'],
                            },
                            model="gpt-4o-mini",
                            usage={
                                "input":0,
                                "output":0,
                                "total":0
                            }
                        )
       
                    end_time=time.time()

                    latency_ms=int((end_time-start_time)*1000)

                    logger.info(f"Latency: {latency_ms}ms")
                    logger.info(f"Total Tokens: {total_tokens}")
                    logger.info(f"Total Token Cost: ${total_token_cost:.6f}")

                    ##update the observation with Latency,Total Tokens and Total Cost
                    _update_current_observation(
                        model="gpt-4o-mini",
                        metadata={
                                "token_cost":total_token_cost,
                                "latency_ms":latency_ms,
                            },
                        usage={
                            "input":0,
                            "output":0,
                            "total":total_tokens,
                        }
                    )

                    
                    ## flush all 
                    self._flush_observation()

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

            ## update router observation
            _update_current_observation(
                input=user_query,
                output=router_result["intent"],
                metadata={
                    "stage":"router_stage",
                    "token_cost":router_result['token_cost'],
                    "latency_ms":latency_ms,
                },
                model="gpt-4o-mini",
                usage={
                    "input":0,
                    "output":0,
                    "total":router_result['total_tokens']
                }
            )

            ## flush all 
            _flush()

            return {
                "message":"Not a SQL query",
                "status":"ignored",
                "latency_ms":latency_ms,
                "total_tokens":router_result['total_tokens'],
                "token_cost":router_result['token_cost']
            }
    
    ##======================================
    ## Router agent call and update observer 
    ##======================================
    @_observe(name="Router Intent Agent")
    def _router_intent_agent(
                self,
                user_query:str
                ) -> Dict[str,Any]:
                """
                Invoke the intent-routing agent and record an observation span.

                Calls :meth:`RouterIntent.router` to classify ``user_query`` as
                ``"SQL"`` or a non-SQL intent, then writes the input, output, token
                usage, and latency into the current Langfuse observation span.

                Args:
                    user_query (str): Raw natural language query from the user.

                Returns:
                    Dict[str, Any]: The router result dictionary, which contains at
                    minimum: ``"intent"`` (str), ``"total_tokens"`` (int),
                    ``"input_tokens"`` (int), ``"output_tokens"`` (int),
                    ``"token_cost"`` (float), and ``"latency_ms"`` (int).
                """
                ## Router intent call
                logger.info("Router intent agent is called")
                router_result=self.router.router(user_query=user_query)
        
                ## update router intent observation
                _update_current_observation(
                    input=user_query,
                    output=router_result['intent'],
                    metadata={
                        "stage":"router_stage",
                        "token_cost":router_result['token_cost'],
                        "latency_ms":router_result['latency_ms'],
                    },
                    model="gpt-4o-mini",
                    usage={
                        "input": router_result.get("input_tokens", 0),
                        "output": router_result.get("output_tokens", 0),
                        "total": router_result.get("total_tokens", 0)
                    }
                )

                ## Router intent call completed
                logger.info("Router intent agent is completed")


                return router_result
        
    ##===========================
    ## Check user query ambiguity
    ##===========================
    @_observe(name="User Query Ambiguity Checker")
    def _query_ambiguity_check(
        self,
        user_query:str
        ) -> Dict[str,Any]:
            """
            Check whether a SQL-bound user query is ambiguous.

            Delegates to :meth:`SQLGenerator._check_ambiguity` and records the
            result, token usage, and latency in the current observation span.

            Args:
                user_query (str): The natural language query already classified
                    as SQL-intent by the router.

            Returns:
                Dict[str, Any]: Ambiguity result dictionary containing at minimum:
                ``"status"`` (bool — ``True`` if ambiguous), ``"total_tokens"``
                (int), ``"token_cost"`` (float), and ``"latency_ms"`` (int).
            """
            ## check SQL query is ambiguity or not
            logger.info("Checking SQL query ambiguity")
            is_ambiguous=self.sql_generator._check_ambiguity(user_query=user_query)

            ## update ambiguity result
            _update_current_observation(
                input=user_query,
                output=is_ambiguous["status"],
                metadata={
                    "stage":"ambiguity_check_stage",
                    "token_cost":is_ambiguous['token_cost'],
                    "latency_ms":is_ambiguous['latency_ms'],
                },
                model="gpt-4o-mini",
                usage={
                    "input":0,
                    "output":0,
                    "total":is_ambiguous['total_tokens']
                }
            )

            return is_ambiguous

    ##=======================================
    ## User Query Refinement 
    ##=======================================
    @_observe(name="User Query Refinement")
    def _query_refinement(
        self,
        user_query:str,
        max_iterations:Optional[int]=None,
        ) -> Dict[str,Any]:
        """
        Interactively refine an ambiguous user query.

        Calls :meth:`SQLGenerator.refine_query` to prompt the user for
        clarifying details and returns the refined query once it is
        unambiguous (or after the maximum number of refinement turns is
        reached). Records refinement metadata — iteration count, token
        usage, and latency — in the current observation span.

        Args:
            user_query (str): The ambiguous natural language query to refine.
            max_iterations (Optional[int]): Maximum number of clarification
                rounds. When ``None`` the default configured in
                :class:`SQLGenerator` is used.

        Returns:
            Dict[str, Any]: Refinement result dictionary containing at
            minimum: ``"status"`` (str — ``"refined"`` or ``"failed"``),
            ``"query"`` (str — the clarified query when status is
            ``"refined"``), ``"iterations"`` (int), ``"total_tokens"`` (int),
            ``"token_cost"`` (float), and ``"latency_ms"`` (int).
        """
        logger.warning("Query is ambiguous, starting refinement")
        refined_result=self.sql_generator.refine_query(user_query=user_query)

        ## update user query refinment observation
        _update_current_observation(
            input=user_query,
            output=refined_result["status"],
            metadata={
                "stage":"query_refinement_stage",
                "refinement_iterations":refined_result["iterations"],
                "token_cost":refined_result['token_cost'],
                "latency_ms":refined_result['latency_ms'],
            },
            model="gpt-4o-mini",
            usage={
                "input":0,
                "output":0,
                "total":refined_result['total_tokens']
            }
        )

        return refined_result
    
    ##==============================================
    ## SQL Generation Agent and Update Observation
    ##==============================================
    @_observe(name="SQL Generation Agent")
    def _sql_generation_agent(
        self,
        user_query:str,
        )-> Dict[str,Any]:
        """
        Invoke the SQL generation agent and record an observation span.

        Calls :meth:`SQLGenerator.generate_sql` to translate ``user_query``
        into a PostgreSQL statement using the filtered schema context, then
        writes the generated SQL, token usage, and latency into the current
        observation span.

        Args:
            user_query (str): The (possibly refined) natural language query
                to translate into SQL.

        Returns:
            Dict[str, Any]: SQL generation result dictionary containing at
            minimum: ``"sql_query"`` (str), ``"total_tokens"`` (int),
            ``"token_cost"`` (float), and ``"latency_ms"`` (int).
        """
        ## SQL generator call
        logger.info("SQL generator agent is called")
        sql_query_result=self.sql_generator.generate_sql(user_query=user_query)

        ## update SQL query generation observation --->(refined user query)
        _update_current_observation(
            input=user_query,
            output=sql_query_result["sql_query"],
            metadata={
                "stage":"sql_generation_stage",
                "token_cost":sql_query_result['token_cost'],
                "latency_ms":sql_query_result['latency_ms'],
            },
            model="gpt-4o-mini",
            usage={
                "input":0,
                "output":0,
                "total":sql_query_result['total_tokens']
             }
        )

        ## SQL generator call completed
        logger.info("SQL generator agent is completed")

        return sql_query_result
    
    ##====================
    ## Guadrails check
    ##====================
    @_observe(name="Guadrails Checker")
    def _guadrails_check(
        self,
        sql_query:str
       ) -> bool:
        """
        Validate a generated SQL query through the guardrails layer.

        Calls :meth:`SQLGuardRails.is_validate` to determine whether the
        query is safe to execute (e.g. no destructive DDL/DML, no injection
        patterns), then records the safety verdict and latency in the current
        observation span.

        Args:
            sql_query (str): The raw SQL statement produced by the SQL
                generation agent.

        Returns:
            bool: ``True`` if the query passes all guardrail checks and is
            safe to execute; ``False`` otherwise.
        """
        ## check if sql query is safe using guardrails
        start_time=time.time()
        is_safe=self.guardrails.is_validate(sql_query=sql_query)
        end_time=time.time()
        latency_ms=int((end_time-start_time)*1000)

        ## update guardrails observation
        _update_current_observation(
            input=sql_query,
            output=is_safe,
            metadata={
                "stage":"guardrails_stage",
                "latency_ms":latency_ms,
            }
        )

        return is_safe
    
    ##=============================================
    ## Database Execution and Update Observation
    ##=============================================
    @_observe(name="Database Executor")
    def _database_executor(
        self,
        sql_query:str
        ) -> Dict[str,Any]:
        """
        Execute a validated SQL query against the Supabase database.

        Calls :func:`_execute_sql_query` with the guardrail-approved SQL
        statement and records the execution status, row count, and latency
        in the current observation span.

        Args:
            sql_query (str): A guardrail-validated PostgreSQL statement ready
                for execution.

        Returns:
            Dict[str, Any]: Execution summary containing:
            - ``"status"`` (str): ``"success"`` or ``"error"``.
            - ``"latency_ms"`` (int): Database round-trip time in milliseconds.
            - ``"count"`` (int): Number of rows returned or affected.
        """
        ## execute sql auery using supabase
        start_time=time.time()
        sql_exe_result=_execute_sql_query(sql_query=sql_query)
        end_time=time.time()

        latency_ms=int((end_time-start_time)*1000)
        ## update sql execution observation
        _update_current_observation(
            input=sql_query,
            output=sql_exe_result,
            metadata={
                "stage":"sql_execution_stage",
                "status":sql_exe_result["status"],
                "count":sql_exe_result["count"],
                "latency_ms":latency_ms,
            }
        )

        return{
            "status":sql_exe_result["status"],
            "latency_ms":latency_ms,
            "count":sql_exe_result["count"],
            "data":sql_exe_result["data"]
        }
    
    ##=================================
    ## Visualization agent and update obs
    ##=================================
    @_observe(name="Result Interpreter Agent")
    def _visulization(
        self,
        user_query:str,
        sql_result:str
        ) -> Dict[str,Any]: 
        
        logger.info("Result Interpreter agent is called")
        start_time=time.time()
        visualization=self.result_interpreter._chart_generator(
        user_query=user_query,
        sql_result=sql_result
        )
        end_time=time.time()

        latency_ms=int((end_time-start_time)*1000)

        logger.info("Result Interpreter agent is completed")

        return{
            "type":visualization["type"],
            "latency_ms":latency_ms
        }

        
    
    ##=======================
    ## Flush the observation
    ##=======================
    def _flush_observation(self):
        """Flush all buffered Langfuse observations to the remote backend."""
        _flush()



        
        

        





    
        








        

       