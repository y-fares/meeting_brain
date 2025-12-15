"""
Tests for database workflow functions.
"""

from datetime import datetime
import pytest

from database import (
    create_session,
    create_meeting,
    add_todos,
    add_decisions,
    acknowledge_todo,
    complete_todo,
    set_notion_page_id,
    Meeting,
    Todo,
    Decision,
)


def test_create_meeting(session):
    """Test that create_meeting creates a meeting row."""
    meeting_id = create_meeting(
        session=session,
        raw_text="Test meeting notes",
        summary="Test summary",
        title="Test Meeting",
        date=datetime(2025, 1, 15, 10, 0, 0)
    )
    
    assert meeting_id > 0
    
    # Verify in database
    meeting = session.query(Meeting).filter_by(id=meeting_id).first()
    assert meeting is not None
    assert meeting.title == "Test Meeting"
    assert meeting.summary == "Test summary"
    assert meeting.raw_text == "Test meeting notes"


def test_add_todos(session):
    """Test that add_todos adds todos to a meeting."""
    # Create meeting first
    meeting_id = create_meeting(
        session=session,
        raw_text="Test",
        summary="Test",
        title="Test",
        date=None
    )
    
    # Add todos
    todos_data = [
        {"task": "Task 1", "owner": "Alice", "due_date": "2025-02-01"},
        {"task": "Task 2", "owner": "Bob", "due_date": ""},
    ]
    add_todos(session, meeting_id, todos_data)
    
    # Verify in database
    todos = session.query(Todo).filter_by(meeting_id=meeting_id).all()
    assert len(todos) == 2
    
    todo1 = todos[0]
    assert todo1.task == "Task 1"
    assert todo1.owner == "Alice"
    assert todo1.due_date == "2025-02-01"
    assert todo1.status == "pending"
    
    todo2 = todos[1]
    assert todo2.task == "Task 2"
    assert todo2.owner == "Bob"
    assert todo2.due_date == ""


def test_acknowledge_todo(session):
    """Test that acknowledge_todo updates status to in_progress and sets acknowledged_at."""
    # Create meeting and todo
    meeting_id = create_meeting(session, "Test", "Test", "Test", None)
    add_todos(session, meeting_id, [{"task": "Test task", "owner": "Alice", "due_date": ""}])
    
    todo = session.query(Todo).filter_by(meeting_id=meeting_id).first()
    todo_id = todo.id
    
    # Initially pending
    assert todo.status == "pending"
    assert todo.acknowledged_at is None
    
    # Acknowledge
    acknowledge_todo(session, todo_id)
    
    # Refresh from DB
    session.refresh(todo)
    assert todo.status == "in_progress"
    assert todo.acknowledged_at is not None
    assert isinstance(todo.acknowledged_at, datetime)


def test_complete_todo(session):
    """Test that complete_todo updates status to completed and sets completed_at."""
    # Create meeting and todo
    meeting_id = create_meeting(session, "Test", "Test", "Test", None)
    add_todos(session, meeting_id, [{"task": "Test task", "owner": "Alice", "due_date": ""}])
    
    todo = session.query(Todo).filter_by(meeting_id=meeting_id).first()
    todo_id = todo.id
    
    # Initially pending
    assert todo.status == "pending"
    assert todo.completed_at is None
    
    # Complete
    complete_todo(session, todo_id)
    
    # Refresh from DB
    session.refresh(todo)
    assert todo.status == "completed"
    assert todo.completed_at is not None
    assert isinstance(todo.completed_at, datetime)


def test_set_notion_page_id(session):
    """Test that set_notion_page_id stores the page id."""
    # Create meeting and todo
    meeting_id = create_meeting(session, "Test", "Test", "Test", None)
    add_todos(session, meeting_id, [{"task": "Test task", "owner": "Alice", "due_date": ""}])
    
    todo = session.query(Todo).filter_by(meeting_id=meeting_id).first()
    todo_id = todo.id
    
    # Initially None
    assert todo.notion_page_id is None
    
    # Set notion page id
    test_page_id = "abc123-def456"
    set_notion_page_id(session, todo_id, test_page_id)
    
    # Refresh from DB
    session.refresh(todo)
    assert todo.notion_page_id == test_page_id

