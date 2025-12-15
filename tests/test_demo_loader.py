"""
Tests for demo loader service.
"""

from datetime import datetime
import pytest
from unittest.mock import patch, MagicMock

from database import Meeting, Todo, Decision, Participant, create_meeting
from services.demo_loader import (
    load_demo_files,
    seed_demo_dataset,
    reset_database,
    _meeting_exists,
)


def test_load_demo_files():
    """Test that load_demo_files loads all 4 demo files."""
    files = load_demo_files()
    
    assert len(files) == 4
    
    # Check structure
    for meeting in files:
        assert "title" in meeting
        assert "date" in meeting
        assert "raw_text" in meeting
        assert "[DEMO]" in meeting["title"]
        assert isinstance(meeting["date"], datetime)


def test_seed_demo_dataset_inserts_data(session):
    """Test that seed_demo_dataset inserts data into database."""
    # Mock LLM functions
    def mock_generate_summary(clean_text):
        return "Test summary"
    
    def mock_extract_decisions(clean_text):
        return ["Decision 1", "Decision 2"]
    
    def mock_extract_todos(clean_text):
        return [
            {"task": "Task 1", "owner": "Alice", "due_date": "2025-02-20"},
            {"task": "Task 2", "owner": "Bob", "due_date": ""},
        ]
    
    # Seed dataset
    result = seed_demo_dataset(
        session=session,
        generate_summary_func=mock_generate_summary,
        extract_decisions_func=mock_extract_decisions,
        extract_todos_func=mock_extract_todos,
    )
    
    # Verify counts
    assert result["meetings_created"] >= 4
    assert result["todos_created"] > 0
    assert result["decisions_created"] > 0
    
    # Verify in database
    meetings_count = session.query(Meeting).count()
    assert meetings_count >= 4
    
    todos_count = session.query(Todo).count()
    assert todos_count > 0
    
    decisions_count = session.query(Decision).count()
    assert decisions_count > 0


def test_seed_demo_dataset_is_idempotent(session):
    """Test that seed_demo_dataset is idempotent (can run twice without duplicating)."""
    # Mock LLM functions
    def mock_generate_summary(clean_text):
        return "Test summary"
    
    def mock_extract_decisions(clean_text):
        return ["Decision 1"]
    
    def mock_extract_todos(clean_text):
        return [{"task": "Task 1", "owner": "Alice", "due_date": ""}]
    
    # First run
    result1 = seed_demo_dataset(
        session=session,
        generate_summary_func=mock_generate_summary,
        extract_decisions_func=mock_extract_decisions,
        extract_todos_func=mock_extract_todos,
    )
    
    meetings_count_1 = session.query(Meeting).count()
    todos_count_1 = session.query(Todo).count()
    
    # Second run
    result2 = seed_demo_dataset(
        session=session,
        generate_summary_func=mock_generate_summary,
        extract_decisions_func=mock_extract_decisions,
        extract_todos_func=mock_extract_todos,
    )
    
    meetings_count_2 = session.query(Meeting).count()
    todos_count_2 = session.query(Todo).count()
    
    # Counts should not double (or second run created 0)
    assert meetings_count_2 == meetings_count_1
    assert todos_count_2 == todos_count_1
    assert result2["meetings_created"] == 0  # All already exist


def test_reset_database_deletes_all_rows(session):
    """Test that reset_database deletes all rows from all tables."""
    # Create some test data
    meeting_id = create_meeting(
        session=session,
        raw_text="Test",
        summary="Test",
        title="Test Meeting",
        date=datetime(2025, 1, 1)
    )
    
    from database import add_todos, add_decisions, add_participants
    add_todos(session, meeting_id, [{"task": "Test task", "owner": "Alice", "due_date": ""}])
    add_decisions(session, meeting_id, ["Test decision"])
    add_participants(session, meeting_id, ["Alice"])
    
    # Verify data exists
    assert session.query(Meeting).count() > 0
    assert session.query(Todo).count() > 0
    assert session.query(Decision).count() > 0
    assert session.query(Participant).count() > 0
    
    # Reset
    reset_database(session)
    
    # Verify all tables are empty
    assert session.query(Meeting).count() == 0
    assert session.query(Todo).count() == 0
    assert session.query(Decision).count() == 0
    assert session.query(Participant).count() == 0


def test_meeting_exists(session):
    """Test _meeting_exists function."""
    # No meeting exists
    assert not _meeting_exists(session, "Test Title", "Test text")
    
    # Create meeting
    create_meeting(
        session=session,
        raw_text="Test text",
        summary="Summary",
        title="Test Title",
        date=datetime(2025, 1, 1)
    )
    
    # Now exists
    assert _meeting_exists(session, "Test Title", "Test text")
    
    # Different title, same text
    assert _meeting_exists(session, "Different Title", "Test text")

