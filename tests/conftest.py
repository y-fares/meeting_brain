"""
Pytest configuration and fixtures for Meeting Brain tests.
"""

import os
import sys
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base, create_session, SessionLocal, engine


@pytest.fixture(scope="session")
def test_db():
    """Create a temporary SQLite database for testing."""
    # Create temporary file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    # Create engine for test database
    test_engine = create_engine(f"sqlite:///{db_path}", echo=False)
    
    # Create all tables
    Base.metadata.create_all(test_engine)
    
    yield test_engine
    
    # Cleanup
    os.unlink(db_path)


@pytest.fixture(scope="function")
def session(test_db, monkeypatch):
    """Provide a SQLAlchemy session for each test."""
    # Monkeypatch the database module to use test database
    TestSessionLocal = sessionmaker(bind=test_db)
    
    # Patch create_session to return test session
    def create_test_session():
        return TestSessionLocal()
    
    monkeypatch.setattr("database.create_session", create_test_session)
    monkeypatch.setattr("database.SessionLocal", TestSessionLocal)
    monkeypatch.setattr("database.engine", test_db)
    
    # Create session
    test_session = TestSessionLocal()
    
    yield test_session
    
    # Cleanup: rollback and close
    test_session.rollback()
    test_session.close()

