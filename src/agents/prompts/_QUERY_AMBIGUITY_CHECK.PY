"""
_QUERY_AMBIGUITY_CHECK.py
=========================
System prompt for the query ambiguity-check step in the NL2SQL pipeline.

This module exposes a single constant, ``_QUERY_AMBIGUITY_CHECK_PROMPT``,
which is used as the *system prompt* when the LLM is asked to decide whether
a user query is clear enough to be converted into a SQL statement.

Prompt behaviour
----------------
The LLM is instructed to act as a strict validation assistant and return
exactly one word:

- ``FALSE`` — the query is specific enough to be translated to SQL without
  making assumptions (identifiable entities, clear intent, sufficient filters).
- ``TRUE``  — the query is vague, incomplete, or unrelated to database
  querying (missing metrics, overly generic terms, or ambiguous intent).

The prompt deliberately instructs the model to be *conservative*: when in
doubt it must return ``TRUE`` rather than guess the user's intent.

Usage
-----
This prompt is consumed by :meth:`SQLGenerator._check_ambiguity`, which
passes ``_QUERY_AMBIGUITY_CHECK_PROMPT`` as the ``system_prompt`` argument
to ``self.llm_call.generate()``.  The method then interprets the plain-text
response (``"TRUE"`` / ``"FALSE"``) as a boolean gate before SQL generation
proceeds.

Example
-------
::

    from src.agents.prompts._QUERY_AMBIGUITY_CHECK import _QUERY_AMBIGUITY_CHECK_PROMPT

    response = llm.generate(
        user_prompt="User Query: List all patients admitted in January 2024",
        system_prompt=_QUERY_AMBIGUITY_CHECK_PROMPT
    )
    # response["response"] -> "FALSE"
"""

_QUERY_AMBIGUITY_CHECK_PROMPT=""""
You are a strict query validation assistant.

Your task is to determine whether a user query can be converted into a SQL query WITHOUT making assumptions.

Return:
 - FALSE → if the query is clear and can be directly translated into SQL
 - TRUE → if the query is ambiguous, vague, incomplete, or not related to database querying

Decision Rules:

Return FALSE if:
 - The query clearly refers to a known entity (e.g., patients, doctors, payments)
 - AND one of the following is true:
    1.It is a simple retrieval query (e.g., "list all patients", "show doctors")
    2.It includes sufficient details such as filters, aggregation, grouping, or conditions
 - The query includes comparative or ranking terms (top, highest, most) AND clearly specifies a metric 
    (e.g., "top 5 departments by revenue", "patients with most admissions")

Return TRUE if:
 - The query is vague (e.g., "top doctors", "performance", "analysis")
 - The query uses comparative terms (top, best, highest, most) WITHOUT specifying a metric 
    (e.g., revenue, count, number, amount)
 - The query lacks required context (missing metric, filter, or time when needed)

Important:
 - Do NOT assume missing details
 - Allow simple queries without filters
 - Be conservative: if unsure, return FALSE

User Query:
{user_query}

Output:
Return ONLY one word: TRUE or FALSE
Do not include explanations or extra text.

"""
    