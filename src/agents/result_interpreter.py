##============================
## Import Required Libraries
##============================
from typing import Dict, Any, Optional, List
from loguru import logger
import time
import json
import plotly.express as px
import pandas as pd
from decimal import Decimal

##==================================
## Import User Define Python Modules
##==================================
from src.agents.prompts._CHART_INTERPRETER import _CHART_INTERPRETER_PROMPT


##============================
## Result Interpreter Agent
##============================
class ResultInterpreter:
    """
    Transforms raw SQL query results into human-readable visualizations and insights.

    This agent sits at the final stage of the NL2SQL pipeline. After the SQL Generator
    produces and executes a query, ResultInterpreter decides the best way to present
    the data — as a Plotly chart, a tabular view, or a plain-text summary — and
    optionally enriches the output with LLM-generated narrative insights.

    Decision logic overview:
        - Single-row result           → text summary (via LLM)
        - Wide result (>3 columns)    → table
        - 2-column result             → line (time-based), pie (≤5 rows), or bar
        - 3-column result             → grouped line or grouped bar
        - No numeric + categorical mix → falls back to text or table

    Attributes:
        llm_call: An LLM client instance that exposes a ``generate(user_prompt,
            system_prompt=None)`` method. Used for producing text summaries and
            chart insights.

    Example:
        >>> interpreter = ResultInterpreter(llm=my_llm_client)
        >>> result = interpreter._chart_generator(
        ...     user_query="Show monthly revenue",
        ...     sql_result=[{"month": "Jan", "revenue": 5000}, ...]
        ... )
        >>> print(result["type"])   # "chart"
    """

    def __init__(self, llm):
        """
        Initialize the ResultInterpreter with an LLM client.

        Args:
            llm: An LLM client object with a ``generate(user_prompt, system_prompt=None)``
                method. The method must return a dict containing at least a ``"response"``
                key, and optionally ``"total_tokens"``, ``"token_cost"``, and
                ``"latency_ms"`` for cost/performance tracking.
        """
        self.llm_call = llm

    ##==========================================
    ## Check SQL Result can be visualized or not
    ##==========================================
    def _can_visualize(
        self,
        sql_result: List[Dict[str, Any]]
    ) -> bool:
        """
        Determine whether an SQL result set has enough structure to be charted.

        A result is considered visualizable when it contains at least one numeric
        column (int, float, or Decimal) **and** at least one non-numeric (categorical)
        column. This guards against trying to chart purely textual or purely numeric
        results, both of which produce meaningless axes.

        Args:
            sql_result: A list of row dicts returned by the database. Each dict maps
                column name → cell value. An empty list is treated as non-visualizable.

        Returns:
            True if the first row contains ≥1 numeric and ≥1 categorical value,
            False otherwise (including when ``sql_result`` is empty).

        Example:
            >>> self._can_visualize([{"doctor": "Alice", "patients": 42}])
            True
            >>> self._can_visualize([{"total": 100}])   # no categorical column
            False
        """
        if not sql_result:
            return False

        sample = sql_result[0]

        numeric_count = 0
        categorical_count = 0

        for value in sample.values():
            if isinstance(value, (int, float, Decimal)):
                numeric_count += 1
            else:
                categorical_count += 1

        return numeric_count >= 1 and categorical_count >= 1

    ##============================
    ## Detect Chart Type
    ##============================
    def _detect_chart_type(
        self,
        sql_result: List[Dict[str, Any]]
    ) -> str:
        """
        Infer the most appropriate visualization type from the result set shape.

        The heuristic inspects column count and row count to pick the chart type
        that communicates the data most clearly to a non-technical audience:

        +----------------+--------------------+----------------------------------+
        | Columns        | Rows               | Chosen type                      |
        +================+====================+==================================+
        | > 3            | > 1                | ``"table"``                      |
        | ≥ 1            | == 1               | ``"text"``  (single-value result)|
        | 3              | any                | ``"line"`` (time) / ``"bar"``    |
        | 2              | any                | ``"line"`` (time) / ``"pie"``    |
        |                |                    | (≤5 rows) / ``"bar"``            |
        +----------------+--------------------+----------------------------------+

        Args:
            sql_result: A non-empty list of row dicts from the database.

        Returns:
            One of ``"table"``, ``"text"``, ``"line"``, ``"bar"``, or ``"pie"``.

        Warns:
            Logs a warning if ``sql_result`` is ``None`` or empty, but continues
            processing using the first available row.

        Example:
            >>> self._detect_chart_type([{"month": "Jan", "revenue": 5000}])
            'line'
            >>> self._detect_chart_type([{"name": "Bob", "age": 30, "dept": "ICU", "score": 9}])
            'table'
        """
        if sql_result is None or len(sql_result) == 0:
            logger.warning("No result returned from database")

        columns = list(sql_result[0].keys())

        if len(columns) > 3 and len(sql_result) > 1:
            return "table"

        if len(columns) >= 1 and len(sql_result) == 1:
            return "text"

        if len(columns) == 3:
            if self._is_time_based(sql_result=sql_result):
                return "line"
            else:
                return "bar"

        if len(columns) == 2:
            if self._is_time_based(sql_result=sql_result):
                return "line"
            elif len(sql_result) <= 5:
                return "pie"
            else:
                return "bar"

    ##=========================================
    ## Check if sql result is time based or not
    ##=========================================
    def _is_time_based(
        self,
        sql_result: List[Dict[str, Any]]
    ) -> bool:
        """
        Detect whether any column in the result carries temporal meaning.

        Temporal columns are identified by keyword matching on the column name
        (case-insensitive). The keywords checked are: ``date``, ``time``,
        ``year``, ``month``, ``day``. This drives the decision to render a
        line chart (which implies continuity over time) instead of a bar or pie.

        Args:
            sql_result: A list of row dicts. Only the first row's keys are
                inspected; an empty list returns ``False`` immediately.

        Returns:
            True if at least one column name contains a temporal keyword,
            False otherwise.

        Example:
            >>> self._is_time_based([{"admission_date": "2024-01-01", "count": 10}])
            True
            >>> self._is_time_based([{"doctor": "Alice", "patients": 42}])
            False
        """
        if not sql_result:
            return False

        sample_key = sql_result[0]

        for key, value in sample_key.items():
            key_lower = key.lower()
            if any(key_word in key_lower for key_word in ["date", "time", "year", "month", "day"]):
                return True

        return False

    ##=============================
    ## Extract the Column names
    ##=============================
    def _extract_columns(self, sql_result: List[Dict[str, Any]]):
        """
        Determine the best x-axis, y-axis, and optional grouping column for charting.

        Delegates column classification to :meth:`_classify_columns` and then applies
        a priority-based assignment:

        1. **Time + numeric** — time column becomes x, first numeric becomes y,
           first categorical becomes the optional group.
        2. **Two categoricals + numeric** — first categorical → x, second → group,
           numeric → y (produces a grouped bar/line chart).
        3. **One categorical + numeric** — straightforward two-axis assignment.
        4. **None of the above** — logs a warning and returns ``(None, None, None)``.

        Args:
            sql_result: A non-empty list of row dicts from the database.

        Returns:
            A tuple of 2 or 3 elements:
            - ``(x, y)`` for two-column charts, or
            - ``(x, y, group)`` for three-column grouped charts, or
            - ``(None, None, None)`` if axis assignment fails.

        Example:
            >>> self._extract_columns([{"month": "Jan", "revenue": 5000}])
            ('month', 'revenue')
            >>> self._extract_columns([{"month": "Jan", "dept": "ICU", "patients": 30}])
            ('month', 'patients', 'dept')
        """
        numeric, categorical, time_cols = self._classify_columns(sql_result)

        if time_cols and numeric:
            x = time_cols[0]
            y = numeric[0]
            group = categorical[0] if categorical else None
            return x, y, group

        if len(categorical) >= 2 and numeric:
            x = categorical[0]
            group = categorical[1]
            y = numeric[0]
            return x, y, group

        if len(categorical) >= 1 and numeric:
            return categorical[0], numeric[0]

        logger.warning("Could not determine chart axes properly")
        return None, None, None

    ##=========================================================
    ## Classify Columns as numeric, categorical and time based
    ##=========================================================
    def _classify_columns(
        self,
        sql_result: List[Dict[str, Any]]
    ):
        """
        Partition result-set columns into numeric, categorical, and time-based buckets.

        Classification rules (applied in order, first match wins per column):

        - **Numeric** — cell value is an instance of ``int``, ``float``, or
          ``decimal.Decimal``.
        - **Time-based** — column name (case-insensitive) contains any of:
          ``date``, ``time``, ``day``, ``month``, ``year``.
        - **Categorical** — everything else (strings, booleans, etc.).

        Only the first row of ``sql_result`` is inspected; this is sufficient
        because SQL result sets have a uniform schema.

        Args:
            sql_result: A non-empty list of row dicts. The first element is used
                as the schema sample.

        Returns:
            A 3-tuple ``(numeric_cols, categorical_cols, time_based_cols)`` where
            each element is a list of column-name strings. Lists may be empty.

        Example:
            >>> rows = [{"admission_date": "2024-01", "dept": "ICU", "patients": 42}]
            >>> self._classify_columns(rows)
            (['patients'], ['dept'], ['admission_date'])
        """
        sample = sql_result[0]
        numeric_cols = []
        categorical_cols = []
        time_based_cols = []

        for column, value in sample.items():
            col_lower = column.lower()

            if isinstance(value, (int, float, Decimal)):
                numeric_cols.append(column)

            elif any(col in col_lower for col in ["date", "time", "day", "month", "year"]):
                time_based_cols.append(column)

            else:
                categorical_cols.append(column)

        return numeric_cols, categorical_cols, time_based_cols

    ##=====================================
    ## Generate chart based on sql result
    ##=====================================
    def _chart_generator(
        self,
        user_query: str,
        sql_result: List[Dict[str, Any]]
    ):
        """
        Produce the best visual or textual representation for an SQL result set.

        This is the primary entry point for result rendering. It orchestrates the
        full pipeline:

        1. Guard against empty results (returns a ``"text"`` dict immediately).
        2. Detect the appropriate output type via :meth:`_detect_chart_type`.
        3. Delegate to one of three render paths:
           - **text** — single-value results; calls :meth:`_generate_text_summary`.
           - **table** — wide results; wraps the first row in a Pandas DataFrame.
           - **chart** — bar, line, or pie via Plotly Express; enriches with
             LLM-generated insights from :meth:`_generate_insights`.
        4. Fall back to a table dict on any chart-rendering exception.

        Args:
            user_query: The original natural-language question entered by the user.
                Passed to the LLM when generating text summaries so the response
                is contextually relevant.
            sql_result: A list of row dicts returned by the database after SQL
                execution. May be empty.

        Returns:
            A dict with a ``"type"`` key set to one of ``"text"``, ``"table"``,
            or ``"chart"``, plus type-specific payload keys:

            - **text**: ``{"type": "text", "content": <str>}``
            - **table**: ``{"type": "table", "data": <DataFrame>, "content": <int>}``
              where ``content`` is the total row count.
            - **chart**: ``{"type": "chart", "chart_type": <str>, "figure": <None>,
              "insights": <str>, "total_tokens": <int>, "token_cost": <float>}``
              (``figure`` is ``None`` because ``fig.show()`` is called for side-effects
              in the current implementation).

        Example:
            >>> result = interpreter._chart_generator(
            ...     user_query="Show revenue by month",
            ...     sql_result=[{"month": "Jan", "revenue": 12000},
            ...                  {"month": "Feb", "revenue": 15000}]
            ... )
            >>> result["type"]
            'chart'
            >>> result["chart_type"]
            'line'
        """
        if not sql_result:
            logger.warning("No data available from database")
            return {
                "type": "text",
                "content": "No data available."
            }

        chart_type = self._detect_chart_type(sql_result=sql_result)
        logger.info("Chart type detected as: {}".format(chart_type))

        if chart_type == "text":
            logger.info("Generating text summary via LLM")
            summary = self._generate_text_summary(
                user_query=user_query,
                sql_result=sql_result
            )
            return {
                "type": "text",
                "content": summary
            }

        if chart_type == "table":
            logger.info("Returning table visualization")
            df = pd.DataFrame(sql_result)
            return {
                "type": "table",
                "data": df.head(50).to_dict(orient="records"),
                "columns": list(df.columns),
                "content": len(df)
            }

        try:
            columns = self._extract_columns(sql_result)
            sql_result = pd.DataFrame(sql_result)

            if len(columns) == 2:
                x_key, y_key = columns

                if chart_type == "bar":
                    fig = px.bar(
                        sql_result,
                        x=x_key,
                        y=y_key,
                        title=f"Bar chart of {y_key} by {x_key}"
                    )

                elif chart_type == "line":
                    fig = px.line(
                        sql_result,
                        x=x_key,
                        y=y_key,
                        title=f"Line chart of {y_key} by {x_key}"
                    )

                elif chart_type == "pie":
                    fig = px.pie(
                        sql_result,
                        names=x_key,
                        values=y_key,
                        title=f"Pie chart of {x_key} by {y_key}"
                    )

                else:
                    logger.warning(f"Unsupported chart type: {chart_type}")
                    return {
                        "type": "table",
                        "content": sql_result
                    }

            elif len(columns) == 3:
                x_key, y_key, group_key = columns

                if chart_type == "bar":
                    fig = px.bar(
                        sql_result,
                        x=x_key,
                        y=y_key,
                        color=group_key,
                        barmode="group",
                        title=f"Bar chart of {y_key} by {x_key} and {group_key}"
                    )

                elif chart_type == "line":
                    fig = px.line(
                        sql_result,
                        x=x_key,
                        y=y_key,
                        color=group_key,
                        title=f"Line chart of {y_key} by {x_key} and {group_key}"
                    )

                else:
                    logger.warning(f"Chart type {chart_type} not ideal for 3 columns")
                    return {
                        "type": "table",
                        "content": sql_result
                    }

            else:
                logger.warning("Unsupported column structure → fallback to table")
                return {
                    "type": "table",
                    "content": sql_result
                }

            fig.update_layout(
                title_x=0.5,
                title_font=dict(size=16)
            )

            logger.info("Generating chart insights")
            group_col = group_key if len(columns) == 3 else None
            insights = self._generate_insights(
                chart_type=chart_type,
                x_axis=x_key,
                y_axis=y_key,
                group_col=group_col,
                sql_result=sql_result.head(5)
            )
            logger.info("Chart insights generated.")

            return {
                "type": "chart",
                "chart_type": chart_type,
                "figure": json.loads(fig.to_json()),
                "insights": insights["insights"],
                "total_tokens": insights["total_tokens"],
                "token_cost": insights["token_cost"],
            }

        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            return {
                "type": "table",
                "content": sql_result
            }

    ##===================================
    ## Generate text summary using LLM
    ##===================================
    def _generate_text_summary(
        self,
        user_query: str,
        sql_result: List[Dict[str, Any]]
    ) -> str:
        """
        Produce a concise, plain-English explanation of a single-row SQL result.

        Called when :meth:`_detect_chart_type` returns ``"text"`` — typically for
        aggregate queries that resolve to one row (e.g., ``SELECT COUNT(*) …``).
        The LLM receives both the original user question and the raw result so it
        can frame the answer in terms the user will understand.

        Args:
            user_query: The natural-language question the user originally asked.
                Gives the LLM the context needed to phrase the answer correctly.
            sql_result: The raw list of row dicts returned by the database.
                Usually a single-element list for text-path queries.

        Returns:
            A human-readable string summarizing the result. Falls back to
            ``"Unable to generate summary."`` if the LLM call raises an exception.

        Example:
            >>> summary = interpreter._generate_text_summary(
            ...     user_query="How many patients were admitted last month?",
            ...     sql_result=[{"count": 312}]
            ... )
            >>> print(summary)
            "312 patients were admitted last month."
        """
        prompt = f"""
        You are an expert data analyst.
        Your goal is to provide a short, clear, human-readable explanation of the SQL query result.

        User query:
        {user_query}

        SQL Result:
        {sql_result}

        Keep it concise and user-friendly.
        """

        try:
            response = self.llm_call.generate(prompt)
            return response.get("response", "No summary generated.")
        except Exception as e:
            logger.error(f"LLM summary failed: {e}")
            return "Unable to generate summary."

    ##===============================
    ## Interpret the Chart Types
    ##===============================
    def _generate_insights(
        self,
        chart_type: str,
        x_axis: str,
        y_axis: str,
        sql_result: List[Dict[str, Any]],
        group_col: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate LLM-powered narrative insights for a rendered chart.

        Sends a structured prompt — containing the chart type, axis names, optional
        grouping column, and a sample of the underlying data — to the LLM. The
        system prompt is the domain-specific ``_CHART_INTERPRETER_PROMPT``, which
        instructs the model to act as a medical data analyst.

        Only the first 5 rows of data are sent to stay within typical token budgets
        while still giving the LLM enough context for meaningful observations.

        Args:
            chart_type: The Plotly chart type that was rendered (``"bar"``,
                ``"line"``, or ``"pie"``). Helps the LLM frame its language
                appropriately (e.g., "trends" for line, "distribution" for pie).
            x_axis: Name of the column mapped to the x-axis (or ``names`` for pie).
            y_axis: Name of the column mapped to the y-axis (or ``values`` for pie).
            sql_result: A list of row dicts (or a Pandas-compatible structure)
                representing the chart data. Should already be sliced to ≤5 rows
                before calling this method.
            group_col: Optional name of the column used for color-grouping in
                multi-series charts. Pass ``None`` for single-series charts.

        Returns:
            A dict with the following keys:
            - ``"insights"`` (str): The LLM-generated narrative. Empty string on
              failure.
            - ``"total_tokens"`` (int): Total tokens consumed by the LLM call.
            - ``"token_cost"`` (float): Estimated monetary cost of the call.
            - ``"latency_ms"`` (float): Round-trip time of the LLM call in
              milliseconds.

            Falls back to the string ``"Insight could not be generated."`` if an
            exception is raised (note: this is a string, not a dict — callers
            should guard accordingly).

        Example:
            >>> insights = interpreter._generate_insights(
            ...     chart_type="bar",
            ...     x_axis="department",
            ...     y_axis="avg_patients",
            ...     sql_result=[{"department": "ICU", "avg_patients": 18}, ...],
            ...     group_col=None
            ... )
            >>> print(insights["insights"])
            "The ICU department handles the highest average patient load at 18 per day..."
        """
        prompt = f"""
        Chart Type:
        {chart_type}

        X axis: {x_axis}
        Y axis: {y_axis}
        Group column: {group_col}

        SQL sample:
        {sql_result}
        """

        try:
            response = self.llm_call.generate(
                user_prompt=prompt,
                system_prompt=_CHART_INTERPRETER_PROMPT
            )

            return {
                "insights": response.get("response", "").strip(),
                "total_tokens": response.get("total_tokens", 0),
                "token_cost": response.get("token_cost", 0),
                "latency_ms": response.get("latency_ms", 0)
            }

        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            return "Insight could not be generated."
