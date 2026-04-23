"""
sql_client.py
=============
Supabase PostgreSQL connectivity layer for the AI Engineering Bootcamp project.

This module manages the lifecycle of a SQLAlchemy engine and session factory
that connect to a Supabase-hosted PostgreSQL database. It follows the singleton
pattern so that only one engine and one session factory are ever instantiated per
process, preventing unnecessary connection-pool churn.

Architecture
------------
- Module-level singletons ``_engine`` and ``_session_factory`` are lazily
  initialised on first use and reused for all subsequent calls within the same
  process lifetime.
- Connection parameters (URL) are loaded from a ``.env`` file located at the
  project root, keeping credentials out of source control.

Environment Variables
---------------------
SUPABASE_DB_URL : str
    Full SQLAlchemy-compatible PostgreSQL connection URL.
    Expected format:
    ``postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres``

Connection Pool Settings
------------------------
pool_size=5        — number of persistent connections kept open.
max_overflow=10    — extra connections allowed beyond pool_size under load.
pool_pre_ping=True — validates connections before use to avoid stale handles.
pool_recycle=3600  — recycles connections every hour to prevent server-side
                     timeout disconnections.

Typical Usage
-------------
>>> from src.infrastructure.db.sql_client import _get_supabase_session, _test_connection
>>> ok = _test_connection()          # quick smoke-test on startup
>>> session = _get_supabase_session()
>>> try:
...     results = session.execute(text("SELECT * FROM my_table"))
... finally:
...     session.close()

Dependencies
------------
- SQLAlchemy  >= 2.0  (ORM + core engine)
- loguru             (structured logging)
- python-dotenv      (environment variable loading)
"""

##===========================
## Import Required Libraries
##===========================
from loguru import logger
from sqlalchemy.orm import sessionmaker
from typing import Optional
from pathlib import Path
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine,text

##=============================
## Load Enviromental Variables
##=============================
_PROJECT_ROOT=Path(__file__).parent.parent.parent

load_dotenv(dotenv_path=_PROJECT_ROOT/".env")

##==========================
## Globa Singleton Engine
##=========================
_engine:Optional[object]=None
_session_factory:Optional[object]=None


def _supabase_sql_engine():
    """Return the module-level singleton SQLAlchemy engine for Supabase.

    Creates the engine on the first call using the ``SUPABASE_DB_URL``
    environment variable, then caches it in the module-level ``_engine``
    global so subsequent calls return the same object without re-initialising
    the connection pool.

    Returns
    -------
    sqlalchemy.engine.Engine
        A configured SQLAlchemy engine connected to the Supabase PostgreSQL
        instance.

    Raises
    ------
    ValueError
        If ``SUPABASE_DB_URL`` is not set in the environment / ``.env`` file.

    Notes
    -----
    Engine configuration:
    - ``pool_size=5``       : maintain up to 5 persistent connections.
    - ``max_overflow=10``   : allow up to 10 additional connections under load.
    - ``pool_pre_ping=True``: health-check connections before checkout.
    - ``pool_recycle=3600`` : recycle connections every 3 600 s (1 hour).
    - ``echo=False``        : SQL statements are not logged to stdout.
    """
    global _engine

    if _engine is None:
        db_url=os.getenv("SUPABASE_DB_URL")

        if not db_url:
            raise ValueError(
               "SUPABASE_DB_URL must be set in .env file. "
                "Format: postgresql://postgres:[password]@db.xxxxx.supabase.co:5432/postgres"
            )

        _engine=create_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )

        logger.info(f"✓ Supabase SQL engine created")

    return _engine


def _get_supabase_session():
    """Return a new SQLAlchemy ORM session bound to the Supabase engine.

    Lazily creates the module-level ``_session_factory`` (a
    ``sessionmaker``) on the first call, then uses it to produce a fresh
    ``Session`` object on every call.  The caller is responsible for
    committing, rolling back, and closing the session.

    Returns
    -------
    sqlalchemy.orm.Session
        A new, ready-to-use ORM session.  The session is configured with
        ``autoflush=False`` and ``autocommit=False`` so all writes must be
        explicitly committed.

    Notes
    -----
    Session lifecycle best practice::

        session = _get_supabase_session()
        try:
            # … perform queries / writes …
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    """
    global _session_factory

    if _session_factory is None:
        engine=_supabase_sql_engine()
        _session_factory=sessionmaker(bind=engine,autoflush=False,autocommit=False)

    return _session_factory()


def _test_connection():
    """Verify that the application can reach the Supabase PostgreSQL database.

    Obtains the singleton engine, opens a transient connection, and executes
    the lightweight ``SELECT 1`` probe query.  Logs a success or failure
    message and returns a boolean result so callers can gate further
    initialisation on connectivity.

    Returns
    -------
    bool
        ``True``  if the connection succeeds and ``SELECT 1`` returns ``1``.
        ``False`` if any exception is raised (network error, bad credentials,
        unreachable host, etc.).

    Examples
    --------
    >>> if not _test_connection():
    ...     raise RuntimeError("Cannot reach database; aborting startup.")
    """
    try:
        engine=_supabase_sql_engine()

        with engine.connect() as conn:
            result=conn.execute(text("SELECT 1"))
            assert result.scalar()==1

        logger.info("✅ Supabase connection test: SUCCESS")
        return True

    except Exception as e:
        logger.error(f"❌ Supabase connection test: FAILED - {e}")
        return False
        

