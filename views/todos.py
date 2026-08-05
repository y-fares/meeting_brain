"""
All TODOs view - displays and manages action items from the database.
Direct database access (no API dependency).
"""

from datetime import datetime
from typing import Any, List

import pandas as pd
import streamlit as st

from database import create_session, Todo, Meeting


def _format_datetime(value: Any) -> str:
    """Format datetime for display."""
    if not value:
        return "N/A"
    text = str(value)
    return text.replace("T", " ")[:16]


def _build_table_data(todos: List[Todo], meetings_by_id: dict) -> List[dict]:
    """Convert TODO objects to table rows."""
    table_data = []
    for todo in todos:
        meeting = meetings_by_id.get(todo.meeting_id)
        table_data.append({
            "ID": todo.id,
            "Task": todo.task or "",
            "Owner": todo.owner or "Unassigned",
            "Status": todo.status or "pending",
            "Due date": todo.due_date or "Not specified",
            "Meeting": meeting.title if meeting else f"Meeting #{todo.meeting_id}",
            "Created": _format_datetime(todo.created_at),
            "Acknowledged": _format_datetime(todo.acknowledged_at),
            "Completed": _format_datetime(todo.completed_at),
        })
    return table_data


def _update_todo_status(session, todo_id: int, new_status: str) -> bool:
    """Update TODO status in database."""
    try:
        todo = session.query(Todo).filter(Todo.id == todo_id).first()
        if not todo:
            st.error(f"TODO #{todo_id} not found")
            return False

        todo.status = new_status
        if new_status == "in_progress":
            todo.acknowledged_at = datetime.utcnow()
        elif new_status == "completed":
            todo.completed_at = datetime.utcnow()

        session.commit()
        return True

    except Exception as exc:
        st.error(f"Error updating TODO: {exc}")
        return False


def render_todos_view() -> None:
    """
    Render the 'All TODOs' view.

    Displays all TODOs from the database and allows status updates.
    """
    st.title("All TODOs")
    st.markdown("View and manage action items from your meetings.")
    st.divider()

    # Load data from database
    session = create_session()

    try:
        # Fetch TODOs and meetings
        todos = session.query(Todo).order_by(Todo.created_at.desc()).all()
        meetings = session.query(Meeting).all()
        meetings_by_id = {m.id: m for m in meetings}

        if not todos:
            st.info("No TODOs found yet. Analyze a meeting to create action items.")
            return

        # Display table
        table_data = _build_table_data(todos, meetings_by_id)
        st.dataframe(pd.DataFrame(table_data), use_container_width=True)

        st.divider()

        # TODO selection and actions
        st.subheader("Update TODO Status")

        # Build options for selectbox
        todo_options = {
            f"#{row['ID']}: {row['Task'][:50]}{'...' if len(row['Task']) > 50 else ''}": row["ID"]
            for row in table_data
        }

        if not todo_options:
            st.info("No TODOs to update")
            return

        selected_label = st.selectbox("Select a TODO", list(todo_options.keys()))
        selected_id = todo_options[selected_label]

        # Show selected TODO details
        selected_todo = next(t for t in todos if t.id == selected_id)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Status", selected_todo.status or "pending")
        with col2:
            st.metric("Owner", selected_todo.owner or "Unassigned")
        with col3:
            st.metric("Due Date", selected_todo.due_date or "Not set")

        st.divider()

        # Status update buttons
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Mark as In Progress", type="primary", use_container_width=True):
                if _update_todo_status(session, selected_id, "in_progress"):
                    st.success(f"TODO #{selected_id} marked as in progress")
                    st.rerun()

        with col2:
            if st.button("Mark as Completed", type="primary", use_container_width=True):
                if _update_todo_status(session, selected_id, "completed"):
                    st.success(f"TODO #{selected_id} marked as completed")
                    st.rerun()

        with col3:
            if st.button("Reset to Pending", use_container_width=True):
                if _update_todo_status(session, selected_id, "pending"):
                    st.success(f"TODO #{selected_id} reset to pending")
                    st.rerun()

    except Exception as exc:
        st.error(f"Error loading TODOs: {exc}")
    finally:
        session.close()
