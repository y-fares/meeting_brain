"""
Tests for TodoEvent audit trail functionality.
"""

from datetime import datetime
import pytest

from database import (
    create_meeting,
    add_todos,
    acknowledge_todo,
    complete_todo,
    update_todo_status,
    Todo,
    TodoEvent,
)


def test_acknowledge_todo_creates_event(session):
    """Test that acknowledge_todo creates a TodoEvent."""
    # Create meeting and todo
    meeting_id = create_meeting(session, "Test", "Test", "Test", None)
    add_todos(session, meeting_id, [{"task": "Test task", "owner": "Alice", "due_date": ""}])
    
    todo = session.query(Todo).filter_by(meeting_id=meeting_id).first()
    todo_id = todo.id
    
    # Initially pending
    assert todo.status == "pending"
    
    # Acknowledge
    acknowledge_todo(session, todo_id)
    
    # Verify status updated
    session.refresh(todo)
    assert todo.status == "in_progress"
    
    # Verify event created
    events = session.query(TodoEvent).filter_by(todo_id=todo_id).all()
    assert len(events) == 1
    
    event = events[0]
    assert event.old_status == "pending"
    assert event.new_status == "in_progress"
    assert event.source == "ui"
    assert "acknowledged" in event.note.lower()


def test_complete_todo_creates_event(session):
    """Test that complete_todo creates a TodoEvent."""
    # Create meeting and todo
    meeting_id = create_meeting(session, "Test", "Test", "Test", None)
    add_todos(session, meeting_id, [{"task": "Test task", "owner": "Alice", "due_date": ""}])
    
    todo = session.query(Todo).filter_by(meeting_id=meeting_id).first()
    todo_id = todo.id
    
    # Complete
    complete_todo(session, todo_id)
    
    # Verify status updated
    session.refresh(todo)
    assert todo.status == "completed"
    
    # Verify event created
    events = session.query(TodoEvent).filter_by(todo_id=todo_id).all()
    assert len(events) == 1
    
    event = events[0]
    assert event.old_status == "pending"
    assert event.new_status == "completed"
    assert event.source == "ui"
    assert "done" in event.note.lower() or "completed" in event.note.lower()


def test_multiple_status_changes_create_multiple_events(session):
    """Test that multiple status changes create multiple events."""
    # Create meeting and todo
    meeting_id = create_meeting(session, "Test", "Test", "Test", None)
    add_todos(session, meeting_id, [{"task": "Test task", "owner": "Alice", "due_date": ""}])
    
    todo = session.query(Todo).filter_by(meeting_id=meeting_id).first()
    todo_id = todo.id
    
    # Acknowledge
    acknowledge_todo(session, todo_id)
    
    # Complete
    complete_todo(session, todo_id)
    
    # Verify two events
    events = session.query(TodoEvent).filter_by(todo_id=todo_id).order_by(TodoEvent.created_at).all()
    assert len(events) == 2
    
    # First event: pending -> in_progress
    assert events[0].old_status == "pending"
    assert events[0].new_status == "in_progress"
    
    # Second event: in_progress -> completed
    assert events[1].old_status == "in_progress"
    assert events[1].new_status == "completed"


def test_update_todo_status_no_duplicate_events(session):
    """Test that calling update_todo_status twice with same status does not create duplicate events."""
    # Create meeting and todo
    meeting_id = create_meeting(session, "Test", "Test", "Test", None)
    add_todos(session, meeting_id, [{"task": "Test task", "owner": "Alice", "due_date": ""}])
    
    todo = session.query(Todo).filter_by(meeting_id=meeting_id).first()
    todo_id = todo.id
    
    # Update to in_progress
    update_todo_status(session, todo_id, "in_progress", "test", "First update")
    
    # Update to same status again
    update_todo_status(session, todo_id, "in_progress", "test", "Second update")
    
    # Verify only one event (status didn't change)
    events = session.query(TodoEvent).filter_by(todo_id=todo_id).all()
    assert len(events) == 1


def test_update_todo_status_with_notion_source(session):
    """Test that update_todo_status works with notion_sync source."""
    # Create meeting and todo
    meeting_id = create_meeting(session, "Test", "Test", "Test", None)
    add_todos(session, meeting_id, [{"task": "Test task", "owner": "Alice", "due_date": ""}])
    
    todo = session.query(Todo).filter_by(meeting_id=meeting_id).first()
    todo_id = todo.id
    
    # Update via notion sync
    update_todo_status(
        session,
        todo_id,
        "completed",
        "notion_sync",
        "Synced from Notion column 'Done'"
    )
    
    # Verify event
    events = session.query(TodoEvent).filter_by(todo_id=todo_id).all()
    assert len(events) == 1
    
    event = events[0]
    assert event.source == "notion_sync"
    assert "Notion" in event.note

