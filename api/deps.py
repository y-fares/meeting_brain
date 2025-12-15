"""
FastAPI dependencies for database sessions.
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from database import create_session, Base

LOGGER = logging.getLogger(__name__)

# Check for custom DB URL
MEETING_BRAIN_DB_URL = os.getenv("MEETING_BRAIN_DB_URL")

if MEETING_BRAIN_DB_URL:
    # Use custom DB URL if provided
    LOGGER.info("Using custom database URL from MEETING_BRAIN_DB_URL")
    api_engine = create_engine(
        MEETING_BRAIN_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False} if "sqlite" in MEETING_BRAIN_DB_URL else {}
    )
    ApiSessionLocal = sessionmaker(bind=api_engine)
else:
    # Use default from database.py
    LOGGER.info("Using default database from database.py")
    api_engine = None
    ApiSessionLocal = None


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session.
    
    Uses custom engine if MEETING_BRAIN_DB_URL is set, otherwise
    falls back to database.py's create_session().
    """
    if ApiSessionLocal:
        # Use custom engine
        session = ApiSessionLocal()
        try:
            yield session
        finally:
            session.close()
    else:
        # Use default from database.py
        session = create_session()
        try:
            yield session
        finally:
            session.close()

