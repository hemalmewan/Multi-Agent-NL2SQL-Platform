
##===========================
## Import Required Libraries
##==========================
from loguru import logger
##===================================
## Import User Define Python Modules
##===================================
from src.infrastructure.db.supabase_client import (
    _test_connection,
    _check_pgvector_installed,
)


def main():

    logger.info("Testing database connection…")
    success = _test_connection()

    if success:
        logger.success("All checks passed! Supabase is ready.")
        return 0
    else:
        logger.error("Some checks failed. See errors above.")
        return 1
