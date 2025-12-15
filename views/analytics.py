"""
Analytics view for Meeting Brain.
Displays KPIs, summary tables and provides CSV exports for BI tools.
"""

import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from database import create_session, Meeting, Todo, Decision
from datetime import datetime, date


def render_analytics_view() -> None:
    """
    Render the 'Analytics' view in Streamlit.
    
    Displays KPIs, summary tables and provides CSV export buttons
    for Meetings, Todos and Decisions.
    """
    st.subheader("Analytics & Exports")
    st.markdown(
        "Overview of meetings, decisions and TODOs, plus CSV exports for BI tools."
    )
    st.divider()
    
    # Create DB session
    session = create_session()
    
    try:
        # Load Meetings data
        meetings = session.query(Meeting).all()
        meetings_data = []
        for meeting in meetings:
            meetings_data.append({
                "id": meeting.id,
                "date": meeting.date,
                "title": meeting.title or "",
                "summary": meeting.summary or "",
            })
        
        if meetings_data:
            df_meetings = pd.DataFrame(meetings_data)
        else:
            df_meetings = pd.DataFrame(columns=["id", "date", "title", "summary"])
        
        # Create a dictionary of meetings by id for quick lookup
        meetings_by_id = {m.id: m for m in meetings}
        
        # Load Todos data
        todos = session.query(Todo).all()
        todos_data = []
        for todo in todos:
            meeting = meetings_by_id.get(todo.meeting_id)
            todos_data.append({
                "id": todo.id,
                "meeting_id": todo.meeting_id,
                "meeting_date": meeting.date if meeting else None,
                "meeting_title": (meeting.title or "") if meeting else "",
                "task": todo.task,
                "owner": todo.owner or "",
                "status": todo.status or "",
                "due_date": todo.due_date or "",
                "created_at": todo.created_at,
                "acknowledged_at": todo.acknowledged_at,
                "completed_at": todo.completed_at,
                "notion_page_id": todo.notion_page_id or "",
                "trello_card_id": todo.trello_card_id or "",
            })
        
        if todos_data:
            df_todos = pd.DataFrame(todos_data)
        else:
            df_todos = pd.DataFrame(columns=[
                "id", "meeting_id", "meeting_date", "meeting_title", "task",
                "owner", "status", "due_date", "created_at", "acknowledged_at",
                "completed_at", "notion_page_id", "trello_card_id"
            ])
        
        # Load Decisions data
        decisions = session.query(Decision).all()
        decisions_data = []
        for decision in decisions:
            meeting = meetings_by_id.get(decision.meeting_id)
            decisions_data.append({
                "id": decision.id,
                "meeting_id": decision.meeting_id,
                "meeting_date": meeting.date if meeting else None,
                "meeting_title": (meeting.title or "") if meeting else "",
                "text": decision.text,
            })
        
        if decisions_data:
            df_decisions = pd.DataFrame(decisions_data)
        else:
            df_decisions = pd.DataFrame(columns=[
                "id", "meeting_id", "meeting_date", "meeting_title", "text"
            ])
        
        # KPIs section
        st.markdown("### Key Metrics")
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        
        total_meetings = len(df_meetings)
        total_todos = len(df_todos)
        
        # Count completed todos
        if not df_todos.empty:
            done_todos = len(df_todos[df_todos["status"] == "completed"])
            open_todos = len(df_todos[df_todos["status"] != "completed"])
            
            # Count overdue todos
            today = date.today()
            overdue_count = 0
            for _, row in df_todos.iterrows():
                due_date_str = row.get("due_date", "")
                if due_date_str and due_date_str.strip():
                    try:
                        # Parse "YYYY-MM-DD" format
                        due_date = datetime.strptime(due_date_str.strip(), "%Y-%m-%d").date()
                        if due_date < today and row.get("status") != "completed":
                            overdue_count += 1
                    except (ValueError, TypeError):
                        # Skip invalid dates
                        pass
            
            # Calculate percentage done
            pct_done = (done_todos / total_todos * 100) if total_todos > 0 else 0.0
        else:
            done_todos = 0
            open_todos = 0
            overdue_count = 0
            pct_done = 0.0
        
        with kpi_col1:
            st.metric("Total Meetings", total_meetings)
        
        with kpi_col2:
            st.metric("Total TODOs", total_todos)
        
        with kpi_col3:
            st.metric("% Completed", f"{pct_done:.1f}%")
        
        with kpi_col4:
            st.metric("Overdue TODOs", overdue_count)
        
        st.divider()
        
        # Summary tables section
        st.markdown("### Summary Tables")
        
        # a) TODOs by owner and status
        if not df_todos.empty:
            st.markdown("#### TODOs by Owner and Status")
            todos_by_owner_status = df_todos.groupby(["owner", "status"]).size().reset_index(name="count")
            todos_by_owner_status = todos_by_owner_status.sort_values(["owner", "status"])
            st.dataframe(todos_by_owner_status, width='stretch', hide_index=True)
            st.divider()
        
        # b) TODOs by meeting and status
        if not df_todos.empty:
            st.markdown("#### TODOs by Meeting and Status")
            todos_by_meeting_status = df_todos.groupby(["meeting_title", "status"]).size().reset_index(name="count")
            todos_by_meeting_status = todos_by_meeting_status.sort_values(["meeting_title", "status"])
            st.dataframe(todos_by_meeting_status, width='stretch', hide_index=True)
            st.divider()
        
        # c) Decisions by meeting
        if not df_decisions.empty:
            st.markdown("#### Decisions by Meeting")
            decisions_by_meeting = df_decisions.groupby("meeting_title").size().reset_index(name="count")
            decisions_by_meeting = decisions_by_meeting.sort_values("count", ascending=False)
            st.dataframe(decisions_by_meeting, width='stretch', hide_index=True)
            st.divider()
        
        # CSV exports section
        st.markdown("### Exports (CSV for BI tools)")
        
        # Meetings export
        if not df_meetings.empty:
            csv_meetings = df_meetings.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Meetings CSV",
                data=csv_meetings,
                file_name="meetings_export.csv",
                mime="text/csv",
            )
        else:
            st.info("No meetings available yet.")
        
        st.markdown("---")
        
        # Todos export
        if not df_todos.empty:
            csv_todos = df_todos.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download TODOs CSV",
                data=csv_todos,
                file_name="todos_export.csv",
                mime="text/csv",
            )
        else:
            st.info("No TODOs available yet.")
        
        st.markdown("---")
        
        # Decisions export
        if not df_decisions.empty:
            csv_decisions = df_decisions.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Decisions CSV",
                data=csv_decisions,
                file_name="decisions_export.csv",
                mime="text/csv",
            )
        else:
            st.info("No decisions available yet.")
    
    except Exception as exc:
        st.error(f"Error in Analytics view: {exc}")
        st.exception(exc)
    finally:
        session.close()

