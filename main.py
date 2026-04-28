"""
main.py — Medicore FastAPI server
Exposes the NL2SQL orchestration pipeline as a REST API consumed by the React frontend.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
import pandas as pd
import uvicorn

app = FastAPI(
    title="Medicore NL2SQL API",
    description="AI-powered medical analytics — natural language to SQL pipeline",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Lazy singleton so import cost is paid only on first request ────────────────
_orchestrator = None


def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        from src.infrastructure.llm.llm_providers import _global_llm_provider
        from src.agents.orchestrator import Orchestrator
        _orchestrator = Orchestrator(llm=_global_llm_provider())
    return _orchestrator


def _make_serializable(obj):
    """Recursively convert Decimal / DataFrame values to JSON-safe Python types."""
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_serializable(v) for v in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


# ── Request / response schemas ─────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str
    refined_query: Optional[str] = None


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "Medicore NL2SQL API"}


@app.post("/query")
async def process_query(request: QueryRequest):
    """
    Run the NL2SQL pipeline for a single user query.

    Possible response statuses:
      - success   — SQL executed and result visualised
      - ambiguous — query needs clarification (frontend shows refinement modal)
      - ignored   — input is not a SQL-related question
      - error     — unexpected pipeline failure
    """
    try:
        orchestrator = _get_orchestrator()

        # When the user refines their query via the ambiguity modal the frontend
        # sends the clarified text as refined_query — use that instead so the
        # pipeline receives the clearer phrasing and can skip the ambiguity gate.
        query = (
            request.refined_query.strip()
            if request.refined_query and request.refined_query.strip()
            else request.query.strip()
        )

        print(f"\nUser Query: {query}")

        result = orchestrator.agent_orchestrator(user_query=query)

        # The orchestrator generates a chart internally but never includes it in its
        # return dict.  Re-run SQL + chart generation here so the frontend can render
        # the visualisation.  This is non-critical: if it fails the client still gets
        # the SQL query and metrics.
        if result.get("status") == "success" and result.get("sql_query"):
            try:
                from src.infrastructure.db.supabase_client import _execute_sql_query
                sql_data = _execute_sql_query(sql_query=result["sql_query"])
                rows = sql_data.get("data") or []
                if rows:
                    viz = orchestrator.result_interpreter._chart_generator(
                        user_query=query,
                        sql_result=rows,
                    )
                    result["visualization"] = viz
            except Exception:
                pass

        return JSONResponse(content=_make_serializable(result))

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
