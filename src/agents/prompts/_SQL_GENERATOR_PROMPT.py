"""
_SQL_GENERATOR_PROMPT.py
========================
System prompt template for the SQL Generator agent.

This module exposes a single string constant ``_SQL_GENERATOR_PROMPT`` that is
injected into :meth:`~src.agents.sql_generator.SQLGenerator.generate_sql` to
instruct the LLM to produce a syntactically correct PostgreSQL query from a
natural-language request.

Template variables
------------------
The prompt contains three ``.format()`` placeholders that **must** be supplied
by the caller before the string is sent to the LLM:

``{relevant_tables}``
    A comma-separated list of table names selected as relevant to the user's
    query (e.g. ``"orders, customers"``).

``{relevant_relationships}``
    Newline-separated join conditions in ``table_a.col = table_b.col`` form,
    derived from the schema's relationship definitions.

``{user_prompt}``
    The original natural-language question entered by the user.

LLM instructions embedded in the prompt
----------------------------------------
- Use appropriate ``JOIN`` conditions based on the supplied relationships.
- Apply aggregation functions (``SUM``, ``COUNT``, ``AVG``, etc.) where needed.
- Add ``LIMIT`` for queries that request "top N" results.
- Use clear column aliases for readability.
- Return **only** the SQL statement — no explanations, no markdown code fences.

Usage
-----
::

    from src.agents.prompts._SQL_GENERATOR_PROMPT import _SQL_GENERATOR_PROMPT

    prompt = _SQL_GENERATOR_PROMPT.format(
        relevant_tables="orders, customers",
        relevant_relationships="orders.customer_id = customers.id",
        user_prompt="How many orders did each customer place last month?",
    )
"""

_SQL_GENERATOR_PROMPT="""
    You are an expert PostgreSQL query generator.

    Generate a syntactically correct SQL query based on the user request.

    Relevant schema:
    {relevant_tables}

    Relationships:
    {relevant_relationships}

    Guidelines:
     - Use appropriate JOIN conditions based on relationships
     - Use aggregations functions when required (SUM,COUNT,AVG etc)
     - Apply LIMIT when the query asks for top results
     - Use clear aliases where needed

    User Query:
    {user_prompt}
    
    Return ONLY the SQL query.
    Do not include explanations or comments.
 
 """