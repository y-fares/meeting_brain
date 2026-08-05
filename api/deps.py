"""FastAPI dependencies for database sessions."""

import logging
from typing import Generator
from sqlalchemy.orm import Session

import database

LOGGER = logging.getLogger(__name__)

LOGGER.info("Using database configured by database.py")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session.
    """
    session = database.create_session()
    try:
        yield session
    finally:
        session.close()

