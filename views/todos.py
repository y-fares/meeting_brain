"""
Global TODO view backed by the FastAPI API.
"""

from typing import Any, Optional

import pandas as pd
import streamlit as st

from services.api_client import (
    ApiClientError,
    MeetingBrainApiClient,
    get_api_base_url,
    get_default_api_token,
)


def _get_api_token() -> Optional[str]:
    token = st.session_state.get("api_token")
    if token:
        return token
    default_token = get_default_api_token()
    if default_token:
        st.session_state["api_token"] = default_token
    return default_token


def _get_client() -> MeetingBrainApiClient:
    return MeetingBrainApiClient(base_url=get_api_base_url(), token=_get_api_token())


def _render_auth_panel() -> None:
    with st.sidebar.expander("API session", expanded=False):
        st.caption(f"API: {get_api_base_url()}")

        current_token = _get_api_token()
        if current_token:
            st.success("Bearer token configured")
            if st.button("Clear API token"):
                st.session_state.pop("api_token", None)
                st.rerun()
        else:
            st.info("No API token configured")

        with st.form("api_login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")

        if submitted:
            try:
                token = MeetingBrainApiClient(base_url=get_api_base_url()).login(email, password)
                st.session_state["api_token"] = token
                st.success("Logged in")
                st.rerun()
            except ApiClientError as exc:
                st.error(f"Login failed: {exc}")

        pasted_token = st.text_input("Bearer token", type="password")
        if st.button("Use token") and pasted_token.strip():
            st.session_state["api_token"] = pasted_token.strip()
            st.rerun()


def _format_datetime(value: Any) -> str:
    if not value:
        return "N/A"
    text = str(value)
    return text.replace("T", " ")[:16]


def _build_table_data(todos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    table_data = []
    for todo in todos:
        table_data.append(
            {
                "ID": todo.get("id"),
                "Task": todo.get("task") or "",
                "Owner": todo.get("owner") or "Unassigned",
                "Assignee ID": todo.get("assigned_user_id") or "",
                "Status": todo.get("status") or "",
                "Due date": todo.get("due_date") or "Not specified",
                "Meeting ID": todo.get("meeting_id"),
                "Meeting title": todo.get("meeting_title") or "",
                "Meeting date": _format_datetime(todo.get("meeting_date")),
                "Created": _format_datetime(todo.get("created_at")),
                "Acknowledged": _format_datetime(todo.get("acknowledged_at")),
                "Completed": _format_datetime(todo.get("completed_at")),
            }
        )
    return table_data


def _render_status_actions(client: Optional[MeetingBrainApiClient], selected_id: int, use_local_db: bool = False) -> bool:
    col1, col2 = st.columns(2)
    updated = False

    with col1:
        if st.button("Mark as acknowledged", type="primary"):
            if use_local_db:
                try:
                    from database import create_session, Todo
                    from datetime import datetime
                    db_session = create_session()
                    todo = db_session.query(Todo).filter(Todo.id == selected_id).first()
                    if todo:
                        todo.status = "in_progress"
                        todo.acknowledged_at = datetime.utcnow()
                        db_session.commit()
                        st.success(f"TODO #{selected_id} marked as acknowledged (local DB).")
                        updated = True
                    else:
                        st.error(f"TODO #{selected_id} not found in local database.")
                    db_session.close()
                except Exception as exc:
                    st.error(f"Error acknowledging TODO in local DB: {exc}")
            else:
                try:
                    client.update_todo_status(selected_id, "in_progress", "Marked acknowledged in Streamlit")
                    st.success(f"TODO #{selected_id} marked as acknowledged.")
                    updated = True
                except ApiClientError as exc:
                    st.error(f"Error acknowledging TODO: {exc}")

    with col2:
        if st.button("Mark as done", type="primary"):
            if use_local_db:
                try:
                    from database import create_session, Todo
                    from datetime import datetime
                    db_session = create_session()
                    todo = db_session.query(Todo).filter(Todo.id == selected_id).first()
                    if todo:
                        todo.status = "completed"
                        todo.completed_at = datetime.utcnow()
                        db_session.commit()
                        st.success(f"TODO #{selected_id} marked as done (local DB).")
                        updated = True
                    else:
                        st.error(f"TODO #{selected_id} not found in local database.")
                    db_session.close()
                except Exception as exc:
                    st.error(f"Error completing TODO in local DB: {exc}")
            else:
                try:
                    client.update_todo_status(selected_id, "completed", "Marked done in Streamlit")
                    st.success(f"TODO #{selected_id} marked as done.")
                    updated = True
                except ApiClientError as exc:
                    st.error(f"Error completing TODO: {exc}")

    return updated


def _render_assignment_action(client: Optional[MeetingBrainApiClient], selected_id: int, use_local_db: bool = False) -> bool:
    updated = False
    st.subheader("Assignment")

    if use_local_db:
        st.info("⚠️ Assignment requires API (multi-user feature). Local mode supports status updates only.")
        return False

    assignee_raw = st.text_input(
        "Assigned user ID",
        help="Leave empty to unassign. Admins and meeting creators can assign TODOs.",
    )
    if st.button("Update assignee"):
        try:
            assigned_user_id = int(assignee_raw) if assignee_raw.strip() else None
            client.assign_todo(selected_id, assigned_user_id)
            st.success(f"TODO #{selected_id} assignment updated.")
            updated = True
        except ValueError:
            st.error("Assigned user ID must be a number.")
        except ApiClientError as exc:
            st.error(f"Error assigning TODO: {exc}")

    return updated


def render_todos_view() -> None:
    """
    Render the 'All TODOs' view through the FastAPI backend or local database.
    """
    _render_auth_panel()

    st.title("All TODOs")
    st.markdown("View and manage action items.")
    st.divider()

    todos = None
    client = _get_client()
    use_local_db = False
    api_url = get_api_base_url()

    # If API is disabled in config, skip API and go straight to local DB
    if not api_url:
        use_local_db = True
        st.info("📌 API disabled — Using local database mode")
    else:
        try:
            todos = client.list_todos()
        except Exception as exc:
            st.warning(f"⚠️ API unavailable: {exc}")
            st.info("Loading from local database instead...")
            use_local_db = True
            st.session_state["use_local_db"] = True
            try:
                from database import create_session, Todo, Meeting
                db_session = create_session()
                db_todos = db_session.query(Todo).all()
                db_meetings = {m.id: m for m in db_session.query(Meeting).all()}

                todos = []
                for todo in db_todos:
                    meeting = db_meetings.get(todo.meeting_id)
                    todos.append({
                        "id": todo.id,
                        "task": todo.task,
                        "owner": todo.owner,
                        "assigned_user_id": None,
                        "status": todo.status,
                        "due_date": todo.due_date,
                        "meeting_id": todo.meeting_id,
                        "meeting_title": meeting.title if meeting else "",
                        "meeting_date": meeting.date if meeting else None,
                        "created_at": todo.created_at,
                        "acknowledged_at": todo.acknowledged_at,
                        "completed_at": todo.completed_at,
                    })
                db_session.close()
            except Exception as db_exc:
                st.error(f"Error loading TODOs from local database: {db_exc}")
                st.info("Start FastAPI with `uvicorn api.main:app --reload` or configure local database.")
                return

    if not todos:
        st.info("No TODOs found yet. Analyze a meeting to create action items.")
        return

    table_data = _build_table_data(todos)
    st.dataframe(pd.DataFrame(table_data))

    st.divider()

    todo_options = {
        f"#{row['ID']}: {row['Task'][:50]}..." if len(row["Task"]) > 50 else f"#{row['ID']}: {row['Task']}": row["ID"]
        for row in table_data
    }
    selected_label = st.selectbox("Select a TODO to update", list(todo_options.keys()))
    selected_id = int(todo_options[selected_label])

    st.divider()
    st.subheader("Status")

    # Use session state to ensure flag is preserved across reruns
    use_local_db = st.session_state.get("use_local_db", use_local_db)

    # Debug: show current mode
    if use_local_db:
        st.info("📌 Running in LOCAL DB mode (API unavailable)")
    else:
        st.info("📌 Running in API mode")

    updated = _render_status_actions(client if not use_local_db else None, selected_id, use_local_db=use_local_db)
    st.divider()
    updated = _render_assignment_action(client if not use_local_db else None, selected_id, use_local_db=use_local_db) or updated

    if updated:
        st.rerun()
