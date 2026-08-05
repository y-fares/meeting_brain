"""
Repository functions for database queries.
Pure functions that return data structures ready for DTOs.
"""

import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy import or_
from sqlalchemy.orm import Session
import pandas as pd

from database import Meeting, Todo, Decision, User

LOGGER = logging.getLogger(__name__)


def _can_see_all(user: Optional[User]) -> bool:
    return user is None or user.role == "admin"


def _apply_meeting_visibility(query, user: Optional[User]):
    if _can_see_all(user):
        return query
    return query.filter(
        or_(
            Meeting.created_by_user_id == user.id,
            Meeting.todos.any(Todo.assigned_user_id == user.id),
        )
    )


def _apply_todo_visibility(query, user: Optional[User]):
    if _can_see_all(user):
        return query
    return query.filter(
        or_(
            Todo.assigned_user_id == user.id,
            Meeting.created_by_user_id == user.id,
        )
    )


def list_meetings(
    session: Session,
    limit: int = 50,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: Optional[User] = None,
) -> List[Dict[str, Any]]:
    """
    List meetings with optional date filtering.
    
    Args:
        session: SQLAlchemy session
        limit: Maximum number of results (clamped to 200)
        date_from: Start date filter (YYYY-MM-DD format)
        date_to: End date filter (YYYY-MM-DD format)
    
    Returns:
        List of meeting dictionaries
    """
    try:
        # Clamp limit
        limit = min(max(1, limit), 200)
        
        query = session.query(Meeting).order_by(Meeting.date.desc())
        query = _apply_meeting_visibility(query, current_user)
        
        # Apply date filters
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(Meeting.date >= from_date)
            except ValueError:
                LOGGER.warning("Invalid date_from format: %s", date_from)
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
                query = query.filter(Meeting.date <= to_date)
            except ValueError:
                LOGGER.warning("Invalid date_to format: %s", date_to)
        
        meetings = query.limit(limit).all()
        
        return [
            {
                "id": m.id,
                "date": m.date,
                "title": m.title or "",
                "summary": m.summary or "",
                "created_by_user_id": m.created_by_user_id,
            }
            for m in meetings
        ]
    except Exception as exc:
        LOGGER.exception("Error listing meetings: %s", exc)
        return []


def list_todos(
    session: Session,
    status: Optional[str] = None,
    owner: Optional[str] = None,
    overdue: Optional[bool] = None,
    current_user: Optional[User] = None,
) -> List[Dict[str, Any]]:
    """
    List todos with optional filtering.
    
    Args:
        session: SQLAlchemy session
        status: Filter by status (case-insensitive exact match)
        owner: Filter by owner (case-insensitive contains)
        overdue: If True, only include overdue todos
    
    Returns:
        List of todo dictionaries with meeting info
    """
    try:
        query = (
            session.query(Todo, Meeting)
            .join(Meeting, Todo.meeting_id == Meeting.id)
            .order_by(Todo.created_at.desc())
        )
        query = _apply_todo_visibility(query, current_user)
        
        # Apply filters
        if status:
            query = query.filter(Todo.status.ilike(status))
        
        if owner:
            query = query.filter(Todo.owner.ilike(f"%{owner}%"))
        
        if overdue:
            today = date.today()
            query = query.filter(
                Todo.due_date.isnot(None),
                Todo.status.notin_(["done", "completed"])
            )
            # Note: due_date is stored as string, so we filter in Python
            # This is not ideal but works for the current schema
        
        rows = query.all()
        
        result = []
        today = date.today()
        
        for todo, meeting in rows:
            # Check overdue if filter is active
            is_overdue = False
            if todo.due_date and todo.due_date.strip():
                try:
                    due_date = datetime.strptime(todo.due_date.strip(), "%Y-%m-%d").date()
                    if due_date < today and todo.status.lower() not in ["done", "completed"]:
                        is_overdue = True
                except ValueError:
                    pass
            
            # Apply overdue filter
            if overdue is not None and overdue != is_overdue:
                continue
            
            result.append({
                "id": todo.id,
                "meeting_id": todo.meeting_id,
                "meeting_date": meeting.date if meeting else None,
                "meeting_title": (meeting.title or "") if meeting else "",
                "task": todo.task or "",
                "owner": todo.owner or "",
                "status": todo.status or "",
                "due_date": todo.due_date or "",
                "created_at": todo.created_at,
                "acknowledged_at": todo.acknowledged_at,
                "completed_at": todo.completed_at,
                "notion_page_id": todo.notion_page_id or "",
                "trello_card_id": todo.trello_card_id or "",
                "assigned_user_id": todo.assigned_user_id,
            })
        
        return result
    except Exception as exc:
        LOGGER.exception("Error listing todos: %s", exc)
        return []


def list_decisions(
    session: Session,
    meeting_id: Optional[int] = None,
    current_user: Optional[User] = None,
) -> List[Dict[str, Any]]:
    """
    List decisions with optional meeting filter.
    
    Args:
        session: SQLAlchemy session
        meeting_id: Optional filter by meeting ID
    
    Returns:
        List of decision dictionaries with meeting info
    """
    try:
        query = (
            session.query(Decision, Meeting)
            .join(Meeting, Decision.meeting_id == Meeting.id)
            .order_by(Decision.id.desc())
        )
        query = _apply_meeting_visibility(query, current_user)
        
        if meeting_id:
            query = query.filter(Decision.meeting_id == meeting_id)
        
        rows = query.all()
        
        return [
            {
                "id": d.id,
                "meeting_id": d.meeting_id,
                "meeting_date": m.date if m else None,
                "meeting_title": (m.title or "") if m else "",
                "text": d.text or "",
                "created_at": None,  # Decision model doesn't have created_at
            }
            for d, m in rows
        ]
    except Exception as exc:
        LOGGER.exception("Error listing decisions: %s", exc)
        return []


def compute_kpis(session: Session, current_user: Optional[User] = None) -> Dict[str, Any]:
    """
    Compute key performance indicators.
    
    Args:
        session: SQLAlchemy session
    
    Returns:
        Dictionary with KPI values
    """
    try:
        # Total meetings
        meetings_query = _apply_meeting_visibility(session.query(Meeting), current_user)
        todos_query = _apply_todo_visibility(
            session.query(Todo).join(Meeting, Todo.meeting_id == Meeting.id),
            current_user,
        )

        total_meetings = meetings_query.count()
        
        # Total todos
        total_todos = todos_query.count()
        
        # Done todos (case-insensitive)
        done_todos = todos_query.filter(
            Todo.status.in_(["done", "completed"])
        ).count()
        
        # Also check case variations
        done_query = todos_query.filter(
            Todo.status.ilike("done")
        ).count()
        completed_query = todos_query.filter(
            Todo.status.ilike("completed")
        ).count()
        done_todos = max(done_todos, done_query, completed_query)
        
        # Overdue todos
        today = date.today()
        all_todos = todos_query.all()
        overdue_count = 0
        
        for todo in all_todos:
            if todo.due_date and todo.due_date.strip():
                try:
                    due_date = datetime.strptime(todo.due_date.strip(), "%Y-%m-%d").date()
                    status_lower = (todo.status or "").lower()
                    if due_date < today and status_lower not in ["done", "completed"]:
                        overdue_count += 1
                except ValueError:
                    pass
        
        # Completion rate
        completion_rate = (done_todos / total_todos * 100.0) if total_todos > 0 else 0.0
        
        return {
            "total_meetings": total_meetings,
            "total_todos": total_todos,
            "done_todos": done_todos,
            "overdue_todos": overdue_count,
            "completion_rate": completion_rate,
        }
    except Exception as exc:
        LOGGER.exception("Error computing KPIs: %s", exc)
        return {
            "total_meetings": 0,
            "total_todos": 0,
            "done_todos": 0,
            "overdue_todos": 0,
            "completion_rate": 0.0,
        }


def export_meetings_df(session: Session, current_user: Optional[User] = None) -> pd.DataFrame:
    """
    Export meetings as pandas DataFrame.
    
    Returns:
        DataFrame with columns: id, date, title, summary
    """
    try:
        meetings = _apply_meeting_visibility(session.query(Meeting), current_user).all()
        data = []
        for m in meetings:
            data.append({
                "id": m.id,
                "date": m.date,
                "title": m.title or "",
                "summary": m.summary or "",
                "created_by_user_id": m.created_by_user_id,
            })
        
        if data:
            return pd.DataFrame(data)
        else:
            return pd.DataFrame(columns=["id", "date", "title", "summary", "created_by_user_id"])
    except Exception as exc:
        LOGGER.exception("Error exporting meetings: %s", exc)
        return pd.DataFrame(columns=["id", "date", "title", "summary", "created_by_user_id"])


def export_todos_df(session: Session, current_user: Optional[User] = None) -> pd.DataFrame:
    """
    Export todos as pandas DataFrame.
    
    Returns:
        DataFrame with columns matching todos_export.csv
    """
    try:
        rows = (
            session.query(Todo, Meeting)
            .join(Meeting, Todo.meeting_id == Meeting.id)
        )
        rows = _apply_todo_visibility(rows, current_user).all()
        
        data = []
        for todo, meeting in rows:
            data.append({
                "id": todo.id,
                "meeting_id": todo.meeting_id,
                "meeting_date": meeting.date if meeting else None,
                "meeting_title": (meeting.title or "") if meeting else "",
                "task": todo.task or "",
                "owner": todo.owner or "",
                "status": todo.status or "",
                "due_date": todo.due_date or "",
                "created_at": todo.created_at,
                "acknowledged_at": todo.acknowledged_at,
                "completed_at": todo.completed_at,
                "notion_page_id": todo.notion_page_id or "",
                "trello_card_id": todo.trello_card_id or "",
                "assigned_user_id": todo.assigned_user_id,
            })
        
        if data:
            return pd.DataFrame(data)
        else:
            return pd.DataFrame(columns=[
                "id", "meeting_id", "meeting_date", "meeting_title", "task",
                "owner", "status", "due_date", "created_at", "acknowledged_at",
                "completed_at", "notion_page_id", "trello_card_id", "assigned_user_id"
            ])
    except Exception as exc:
        LOGGER.exception("Error exporting todos: %s", exc)
        return pd.DataFrame(columns=[
            "id", "meeting_id", "meeting_date", "meeting_title", "task",
            "owner", "status", "due_date", "created_at", "acknowledged_at",
            "completed_at", "notion_page_id", "trello_card_id", "assigned_user_id"
        ])


def export_decisions_df(session: Session, current_user: Optional[User] = None) -> pd.DataFrame:
    """
    Export decisions as pandas DataFrame.
    
    Returns:
        DataFrame with columns: id, meeting_id, meeting_date, meeting_title, text, created_at
    """
    try:
        rows = (
            session.query(Decision, Meeting)
            .join(Meeting, Decision.meeting_id == Meeting.id)
        )
        rows = _apply_meeting_visibility(rows, current_user).all()
        
        data = []
        for decision, meeting in rows:
            data.append({
                "id": decision.id,
                "meeting_id": decision.meeting_id,
                "meeting_date": meeting.date if meeting else None,
                "meeting_title": (meeting.title or "") if meeting else "",
                "text": decision.text or "",
                "created_at": None,  # Decision model doesn't have created_at
            })
        
        if data:
            return pd.DataFrame(data)
        else:
            return pd.DataFrame(columns=[
                "id", "meeting_id", "meeting_date", "meeting_title", "text", "created_at"
            ])
    except Exception as exc:
        LOGGER.exception("Error exporting decisions: %s", exc)
        return pd.DataFrame(columns=[
            "id", "meeting_id", "meeting_date", "meeting_title", "text", "created_at"
        ])

