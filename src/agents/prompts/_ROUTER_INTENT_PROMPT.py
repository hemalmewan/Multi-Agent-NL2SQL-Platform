"""
_ROUTER_INTENT_PROMPT.py
========================
System prompt for the Intent Router agent.

This module exposes a single string constant ``_ROUTER_INTENT`` that is passed
as the ``system_prompt`` argument in
:meth:`~src.agents.intent_router.RouterIntent.router` to instruct the LLM to
classify an incoming user query into one of two categories.

Classification labels
---------------------
``"SQL"``
    The query involves retrieving, filtering, aggregating, or analysing data
    from one of the hospital database tables (patients, doctors, admissions,
    billing, etc.).

``"GENERAL"``
    The query is conversational, informational, or unrelated to hospital data
    (e.g. "What does this system do?", "Tell me a joke").

Schema context provided to the LLM
-----------------------------------
The prompt lists the following table names so the model can make an informed
classification decision:

    patients, doctors, specialties, appointments, admissions, diagnoses,
    lab orders, prescriptions, billing invoices, payments, departments, staff

Output format
-------------
The LLM is instructed to respond **strictly** with a JSON object and no
surrounding text::

    {"label": "SQL"}   # or  {"label": "GENERAL"}

Usage
-----
::

    from src.agents.prompts._ROUTER_INTENT_PROMPT import _ROUTER_INTENT

    response = llm.generate(
        user_prompt=f"User Query: {user_query}",
        system_prompt=_ROUTER_INTENT,
    )
"""

_ROUTER_INTENT="""
 You are an intent classification agent for a medicore hospital analytics system.

 Classify the user query one of two lables:
   - "SQL" -> requires querying hospital database tables.
   - "GENERAL" -> not related to database querying

 Schema (table names only):
   - patients
   - doctors
   - specialties
   - appointents
   - admissions
   - diagnoses
   - lab orders
   - prescriptions
   - billing invoices
   - payments
   - departments
   - staff

 Classification Rules:
   - Label as "SQL" if the query involves:
      - retrieving, listing, filtering, or analyzing data
      - aggregation (count, sum, average, top, highest, trends)
      - entities related to the schema (patients, doctors, revenue, departments, etc.)
  
   - Label as "GENERAL" if the query:
      - is unrelated to hospital data
      - asks about the system itself
      - is conversational or informational without data retrieval
 
 Output ONLY the following JSON — no markdown, no explanation, no extra text:

 {"label":"SQL"}   or   {"label":"GENERAL"}

 The value of "label" must be exactly "SQL" or "GENERAL" in uppercase.
"""