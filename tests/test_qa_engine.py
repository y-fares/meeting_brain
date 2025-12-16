"""
Tests for Q&A engine functions.
"""

from datetime import datetime
import pytest

from database import create_meeting, add_todos, add_decisions
from qa_engine import build_qa_context, render_context_as_text


def test_build_qa_context(session):
    """Test that build_qa_context returns structured context with meetings, todos, and decisions."""
    # Create a meeting
    meeting_id = create_meeting(
        session=session,
        raw_text="Test meeting notes",
        summary="Test summary",
        title="Test Meeting",
        date=datetime(2025, 1, 15, 10, 0, 0)
    )
    
    # Add decisions
    decisions = ["Decision 1", "Decision 2"]
    add_decisions(session, meeting_id, decisions)
    
    # Add todos (some pending, some completed)
    todos_data = [
        {"task": "Pending task", "owner": "Alice", "due_date": "2025-02-01"},
        {"task": "Another pending", "owner": "Bob", "due_date": ""},
    ]
    add_todos(session, meeting_id, todos_data)
    
    # Build context
    context = build_qa_context(session, "What are the pending tasks?")
    
    # Verify structure
    assert "question" in context
    assert "generated_at" in context
    assert "meetings" in context
    assert "todos" in context
    assert "decisions" in context
    
    # Verify meetings
    assert len(context["meetings"]) > 0
    # Find our meeting in the list (may not be first if other tests created meetings)
    meeting = next((m for m in context["meetings"] if m["id"] == meeting_id), None)
    assert meeting is not None, f"Meeting {meeting_id} not found in context"
    assert meeting["title"] == "Test Meeting"
    
    # Verify decisions
    assert len(context["decisions"]) >= 2
    decision_texts = [d["text"] for d in context["decisions"]]
    assert "Decision 1" in decision_texts or "Decision 2" in decision_texts
    
    # Verify todos
    assert len(context["todos"]) >= 2
    todo_tasks = [t["task"] for t in context["todos"]]
    assert "Pending task" in todo_tasks or "Another pending" in todo_tasks


def test_render_context_as_text(session):
    """Test that render_context_as_text produces non-empty formatted text."""
    # Create a meeting with data
    meeting_id = create_meeting(
        session=session,
        raw_text="Test",
        summary="Test summary",
        title="Test Meeting",
        date=datetime(2025, 1, 15, 10, 0, 0)
    )
    
    add_decisions(session, meeting_id, ["Test decision"])
    add_todos(session, meeting_id, [{"task": "Test task", "owner": "Alice", "due_date": ""}])
    
    # Build context
    context = build_qa_context(session, "Test question")
    
    # Render as text
    text = render_context_as_text(context)
    
    # Verify it's non-empty and contains expected sections
    assert len(text) > 0
    assert "QUESTION:" in text
    assert "MEETINGS:" in text or "TODOS:" in text or "DECISIONS:" in text

