"""
Tests for insights engine.
"""

from datetime import datetime, date, timedelta
import pytest

from database import create_meeting, add_todos, Todo, TodoEvent
from services.insights_engine import (
    get_overdue_todos,
    get_stale_todos,
    get_owner_load,
    get_bottlenecks,
    get_project_kpis,
    answer_insights_question
)


def test_get_overdue_todos(session):
    """Test getting overdue todos."""
    # Create meeting
    meeting_id = create_meeting(
        session=session,
        raw_text="Test",
        summary="Test",
        title="Test Meeting",
        date=datetime.now()
    )
    
    # Create todos: one overdue, one done, one future
    today = date.today()
    overdue_date = (today - timedelta(days=5)).strftime("%Y-%m-%d")
    future_date = (today + timedelta(days=5)).strftime("%Y-%m-%d")
    
    add_todos(session, meeting_id, [
        {"task": "Overdue task", "owner": "Alice", "due_date": overdue_date},
        {"task": "Done task", "owner": "Bob", "due_date": overdue_date},
        {"task": "Future task", "owner": "Charlie", "due_date": future_date}
    ])
    
    # Mark one as done
    todo_done = session.query(Todo).filter_by(task="Done task").first()
    todo_done.status = "completed"
    session.commit()
    
    # Get overdue
    overdue = get_overdue_todos(session)
    
    assert len(overdue) == 1
    assert overdue[0].task == "Overdue task"


def test_get_stale_todos(session):
    """Test getting stale todos."""
    # Create meeting
    meeting_id = create_meeting(
        session=session,
        raw_text="Test",
        summary="Test",
        title="Test Meeting",
        date=datetime.now()
    )
    
    # Create old todo
    old_date = datetime.now() - timedelta(days=10)
    add_todos(session, meeting_id, [
        {"task": "Old stale task", "owner": "Alice", "due_date": ""}
    ])
    
    # Set created_at to old date
    todo = session.query(Todo).filter_by(task="Old stale task").first()
    todo.created_at = old_date
    session.commit()
    
    # Get stale (7 days default)
    stale = get_stale_todos(session, days=7)
    
    assert len(stale) >= 1
    assert any(t["task"] == "Old stale task" for t in stale)


def test_get_stale_todos_with_events(session):
    """Test getting stale todos when TodoEvent table exists."""
    # Check if TodoEvent exists
    try:
        from database import TodoEvent
        has_events = True
    except ImportError:
        has_events = False
    
    if not has_events:
        pytest.skip("TodoEvent table not available")
    
    # Create meeting and todo
    meeting_id = create_meeting(
        session=session,
        raw_text="Test",
        summary="Test",
        title="Test Meeting",
        date=datetime.now()
    )
    
    add_todos(session, meeting_id, [
        {"task": "Task with old event", "owner": "Alice", "due_date": ""}
    ])
    
    todo = session.query(Todo).filter_by(task="Task with old event").first()
    
    # Create old event
    old_event_date = datetime.now() - timedelta(days=10)
    event = TodoEvent(
        todo_id=todo.id,
        old_status="pending",
        new_status="in_progress",
        source="test",
        created_at=old_event_date
    )
    session.add(event)
    session.commit()
    
    # Get stale
    stale = get_stale_todos(session, days=7)
    
    assert len(stale) >= 1
    assert any(t["task"] == "Task with old event" for t in stale)


def test_get_owner_load(session):
    """Test getting owner load."""
    # Create meeting
    meeting_id = create_meeting(
        session=session,
        raw_text="Test",
        summary="Test",
        title="Test Meeting",
        date=datetime.now()
    )
    
    # Create todos for different owners
    add_todos(session, meeting_id, [
        {"task": "Task 1", "owner": "Alice", "due_date": ""},
        {"task": "Task 2", "owner": "Alice", "due_date": ""},
        {"task": "Task 3", "owner": "Bob", "due_date": ""}
    ])
    
    # Mark one as done
    todo = session.query(Todo).filter_by(task="Task 1").first()
    todo.status = "completed"
    session.commit()
    
    # Get owner load
    load = get_owner_load(session)
    
    assert len(load) >= 2
    alice_load = next((l for l in load if l["owner"] == "Alice"), None)
    assert alice_load is not None
    assert alice_load["total"] == 2
    assert alice_load["completed"] == 1


def test_get_bottlenecks(session):
    """Test getting bottlenecks."""
    # Create meeting
    meeting_id = create_meeting(
        session=session,
        raw_text="Test",
        summary="Test",
        title="Test Meeting",
        date=datetime.now()
    )
    
    # Create overdue todo
    today = date.today()
    overdue_date = (today - timedelta(days=5)).strftime("%Y-%m-%d")
    
    add_todos(session, meeting_id, [
        {"task": "Overdue task", "owner": "Alice", "due_date": overdue_date}
    ])
    
    # Get bottlenecks
    bottlenecks = get_bottlenecks(session)
    
    assert "top_overdue_owners" in bottlenecks
    assert "most_loaded_owners" in bottlenecks
    assert "stale_tasks" in bottlenecks


def test_answer_insights_question_overdue(session):
    """Test answering overdue question."""
    # Create meeting with overdue todo
    meeting_id = create_meeting(
        session=session,
        raw_text="Test",
        summary="Test",
        title="Test Meeting",
        date=datetime.now()
    )
    
    today = date.today()
    overdue_date = (today - timedelta(days=5)).strftime("%Y-%m-%d")
    
    add_todos(session, meeting_id, [
        {"task": "Overdue task", "owner": "Alice", "due_date": overdue_date}
    ])
    
    # Answer question
    result = answer_insights_question(session, "Quelles tâches sont en retard ?", use_llm=False)
    
    assert result["intent"] == "overdue"
    assert "answer" in result
    assert "evidence" in result
    assert "recommended_actions" in result
    assert result["evidence"]["overdue_count"] >= 1


def test_answer_insights_question_owner_load(session):
    """Test answering owner load question."""
    # Create meeting with todos
    meeting_id = create_meeting(
        session=session,
        raw_text="Test",
        summary="Test",
        title="Test Meeting",
        date=datetime.now()
    )
    
    add_todos(session, meeting_id, [
        {"task": "Task 1", "owner": "Alice", "due_date": ""},
        {"task": "Task 2", "owner": "Alice", "due_date": ""}
    ])
    
    # Answer question
    result = answer_insights_question(session, "Qui est surchargé ?", use_llm=False)
    
    assert result["intent"] == "owner_load"
    assert "answer" in result
    assert "evidence" in result
    assert "recommended_actions" in result


def test_answer_insights_question_bottleneck(session):
    """Test answering bottleneck question."""
    # Create meeting with stale todo
    meeting_id = create_meeting(
        session=session,
        raw_text="Test",
        summary="Test",
        title="Test Meeting",
        date=datetime.now()
    )
    
    add_todos(session, meeting_id, [
        {"task": "Stale task", "owner": "Alice", "due_date": ""}
    ])
    
    # Make it stale
    todo = session.query(Todo).filter_by(task="Stale task").first()
    todo.created_at = datetime.now() - timedelta(days=10)
    session.commit()
    
    # Answer question
    result = answer_insights_question(session, "Qu'est-ce qui est bloqué ?", use_llm=False)
    
    assert result["intent"] in ["bottleneck", "stale"]
    assert "answer" in result
    assert "evidence" in result


def test_answer_insights_question_unknown(session):
    """Test answering unknown question."""
    result = answer_insights_question(session, "Random question about nothing", use_llm=False)
    
    assert result["intent"] == "unknown"
    assert "answer" in result

