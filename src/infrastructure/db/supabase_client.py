"""
supabase_client.py
==================
High-level Supabase access layer for the AI Engineering Bootcamp project.

This module provides two complementary access paths to the same Supabase
PostgreSQL database:

1. **Supabase PostgREST client** (``supabase-py``) — used for table-level
   CRUD operations via the Supabase REST API (``_get_supabase_client``).
2. **SQLAlchemy engine / ORM session** — used for raw SQL execution and
   ORM-based queries (``_get_supabase_engine``, ``_get_supabase_session_factory``).

Both paths are initialised lazily and cached as module-level singletons so the
process only opens the connection pool once regardless of how many times the
public helpers are called.

Architecture
------------
::

    ┌─────────────────────────────────────┐
    │         supabase_client.py          │
    │                                     │
    │  _get_supabase_client()             │  ← Supabase PostgREST / Storage SDK
    │  _get_supabase_engine()             │  ← SQLAlchemy Engine  (via sql_client)
    │  _get_supabase_session_factory()    │  ← SQLAlchemy Session (via sql_client)
    │  _test_connection()                 │  ← connectivity smoke-test
    │  _check_pgvector_installed()        │  ← pgvector extension probe
    │  _execute_sql_query()               │  ← ad-hoc SQL execution helper
    └─────────────────────────────────────┘
                        │
                        ▼
            src/infrastructure/db/sql_client.py
                (engine + session singletons)

Environment Variables
---------------------
SUPABASE_URL : str
    The full URL of your Supabase project.
    Example: ``https://<project-ref>.supabase.co``

SUPABASE_SERVICE_KEY : str
    The service-role API key for the Supabase project.  This key bypasses
    Row Level Security — keep it secret and never expose it client-side.

SUPABASE_DB_URL : str
    Direct PostgreSQL connection URL consumed by ``sql_client.py``.
    Example: ``postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres``

Typical Usage
-------------
>>> from src.infrastructure.db.supabase_client import (
...     _get_supabase_client,
...     _test_connection,
...     _check_pgvector_installed,
...     _execute_sql_query,
... )
>>> _test_connection()              # True / False
>>> _check_pgvector_installed()     # True if pgvector is enabled
>>> client = _get_supabase_client() # supabase-py Client
>>> result = _execute_sql_query("SELECT * FROM my_table LIMIT 5")
>>> result["data"]                  # list of row dicts

Dependencies
------------
- supabase-py  >= 2.0  (PostgREST + Storage client)
- SQLAlchemy   >= 2.0  (engine / ORM session — via sql_client)
- loguru              (structured logging)
- python-dotenv       (environment variable loading)
"""

##===========================
## Import Required Libraries
##===========================
from signal import raise_signal
import os
from loguru import logger
from typing import Optional,Dict,Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from supabase import create_client,Client
from dotenv import load_dotenv
from pathlib import Path

##=============================
## Load Enviromental Variables
##=============================
_PROJECT_ROOT=Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=_PROJECT_ROOT/".env")

##===================================
## Import User Define Python Modules
##===================================
from .sql_client import _get_supabase_session,_supabase_sql_engine

##==============================
##  Configure Supabase Client
##==============================
_supabase_client:Optional[Client]=None

def _get_supabase_client()-> Client:
    """Return the module-level singleton Supabase PostgREST client.

    Initialises the ``supabase-py`` ``Client`` on the first call using
    ``SUPABASE_URL`` and ``SUPABASE_SERVICE_KEY`` from the environment, then
    caches it in ``_supabase_client`` for all subsequent calls.

    The service-role key is used so that the client has full database access
    regardless of Row Level Security policies — suitable for server-side
    agent operations.

    Returns
    -------
    supabase.Client
        A fully initialised Supabase client ready for table queries, storage
        operations, and RPC calls.

    Raises
    ------
    ValueError
        If either ``SUPABASE_URL`` or ``SUPABASE_SERVICE_KEY`` is absent from
        the environment / ``.env`` file.

    Examples
    --------
    >>> client = _get_supabase_client()
    >>> rows = client.table("my_table").select("*").execute()
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    supabase_url=os.getenv("SUPABASE_URL")
    supabase_key=os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env file"
        )
    
    _supabase_client=create_client(supabase_url=supabase_url,supabase_key=supabase_key)
    logger.info(f"✓ Supabase client created: {supabase_url}")

    return _supabase_client


##========================
## Get Supabase Engine
##========================
def _get_supabase_engine():
    """Return the SQLAlchemy engine for the Supabase PostgreSQL database.

    Thin wrapper around ``sql_client._supabase_sql_engine()`` that exposes
    the singleton engine through this module's public surface, keeping the
    low-level ``sql_client`` implementation detail internal.

    Returns
    -------
    sqlalchemy.engine.Engine
        The shared, connection-pooled SQLAlchemy engine.  See
        ``sql_client._supabase_sql_engine`` for pool configuration details.
    """
    return _supabase_sql_engine()

##========================
## Get Supabase Session
##========================
def _get_supabase_session_factory() -> Session:
    """Return a new SQLAlchemy ORM session for the Supabase PostgreSQL database.

    Thin wrapper around ``sql_client._get_supabase_session()`` that delegates
    session creation to the underlying singleton ``sessionmaker``.  A new
    ``Session`` object is returned on every call; the caller owns its lifecycle
    and must close (and optionally commit/rollback) it.

    Returns
    -------
    sqlalchemy.orm.Session
        A ready-to-use ORM session configured with ``autoflush=False`` and
        ``autocommit=False``.

    Notes
    -----
    Recommended usage pattern::

        session = _get_supabase_session_factory()
        try:
            # … ORM operations …
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    """
    return _get_supabase_session()

##=======================
## Test Connection
##=======================
def _test_connection()->bool:
    """Verify connectivity to the Supabase PostgreSQL database.

    Opens a transient connection via the SQLAlchemy engine and executes the
    lightweight ``SELECT 1`` probe.  Intended to be called during application
    startup to fail fast when the database is unreachable before any real work
    begins.

    Returns
    -------
    bool
        ``True``  if the probe query succeeds and returns ``1``.
        ``False`` if any exception is raised (bad credentials, network error,
        misconfigured ``SUPABASE_DB_URL``, etc.).

    Examples
    --------
    >>> if not _test_connection():
    ...     raise RuntimeError("Database unreachable — aborting agent startup.")
    """
    try:
        engine=_get_supabase_engine()
        with engine.connect() as conn:
            result=conn.execute(text("SELECT 1"))
            assert result.scalar()==1

        logger.info("✅ Supabase connection test: SUCCESS")
        return True
    except Exception as e:
        logger.error(f"❌ Supabase connection test: FAILED - {e}")
        return False
            
##========================
## PgVector Installed
##========================
def _check_pgvector_installed() -> bool:
    """Check whether the ``pgvector`` PostgreSQL extension is enabled.

    Queries the ``pg_extension`` system catalog to determine if the
    ``vector`` extension is installed in the connected Supabase database.
    The extension is required for storing and querying vector embeddings
    (e.g. semantic search, RAG pipelines).

    Returns
    -------
    bool
        ``True``  if ``pgvector`` (extension name ``'vector'``) is present.
        ``False`` if the extension is absent or if the catalog query fails.

    Side Effects
    ------------
    Logs an actionable warning with the install command when the extension is
    missing::

        Run in Supabase SQL Editor: CREATE EXTENSION vector;

    Examples
    --------
    >>> if not _check_pgvector_installed():
    ...     logger.warning("Vector similarity search will not be available.")
    """
    try:
        engine=_get_supabase_engine()
        with engine.connect() as conn:
            result=conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            )
            installed=result.scalar()=="vector"

        if installed:
            logger.info("✅ pgvector extension: INSTALLED")
        else:
            logger.warning("⚠️  pgvector extension: NOT INSTALLED")
            logger.warning("   Run in Supabase SQL Editor: CREATE EXTENSION vector;")

        return installed

    except Exception as e:
        logger.warning(f"❌ Failed to check pgvector: {e}")
        return False

##==========================
## Execute SQL Query
##==========================
def _execute_sql_query(sql_query:str)->Dict[str,Any]:
    """Execute a raw SQL query against the Supabase PostgreSQL database.

    Runs the provided SQL string through the SQLAlchemy engine and returns
    all result rows serialised as a list of dictionaries keyed by column
    name.  Designed for read-heavy, ad-hoc queries generated by the SQL
    agent — not intended as a general-purpose write path.

    Parameters
    ----------
    sql_query : str
        A valid SQL query string to execute.  Must be a non-empty ``str``;
        empty strings or non-string values are rejected before reaching the
        database.

    Returns
    -------
    Dict[str, Any]
        On **success**::

            {
                "status": "success",
                "data":   [{"col1": val, "col2": val, ...}, ...],  # list of row dicts
                "count":  <int>   # number of rows returned
            }

        On **validation failure** (empty / non-string input)::

            {
                "status":  "error",
                "message": "Invalid SQL query"
            }

        On **database error**::

            {
                "status":  "error",
                "message": "<exception message>"
            }

    Notes
    -----
    - Uses ``engine.connect()`` (not a full ORM session), so the connection
      is returned to the pool immediately after the ``with`` block exits.
    - Rows are fetched eagerly with ``fetchall()``; avoid using this function
      for queries that could return millions of rows — add a ``LIMIT`` clause
      at the SQL level instead.

    Examples
    --------
    >>> result = _execute_sql_query("SELECT id, name FROM products LIMIT 10")
    >>> if result["status"] == "success":
    ...     for row in result["data"]:
    ...         print(row["id"], row["name"])
    """
    logger.info("Executing SQL query on Supabase database")

    if not sql_query or not isinstance(sql_query,str):
        logger.error("Invalid SQL query input")
        return{
            "status":"error",
            "message":"Invalid SQL query"
        }
    
    try:
        engine=_get_supabase_engine()
        with engine.connect() as conn:
            result=conn.execute(text(sql_query))

            ## convert result to list of dicts
            columns=result.keys()
            data=[dict(zip(columns,row)) for row in result.fetchall()]

        logger.info(f"✅ Query executed successfully: {len(data)} rows returned")
        return {
            "status":"success",
            "data":data,
            "count":len(data)
        }

    except Exception as e:
        logger.error(f"❌ Error executing SQL query",error=str(e))
        return {
            "status":"error",
            "message":str(e)
        }
        

    
    






