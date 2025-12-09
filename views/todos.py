"""
Global TODO view for displaying and managing all TODOs across all meetings.
"""

import streamlit as st
import pandas as pd

from database import (
    create_session,
    Todo,
    Meeting,
    acknowledge_todo,
    complete_todo,
)


def render_todos_view() -> None:
    """
    Render the 'All TODOs' view in Streamlit.
    
    Shows all TODOs across all meetings and allows status updates.
    Displays TODOs in a dataframe with all relevant information.
    Provides buttons to mark TODOs as acknowledged or done.
    """
    st.title("All TODOs")
    st.markdown("View and manage all action items from all meetings.")
    st.divider()
    
    # Create database session
    session = create_session()
    
    try:
        # Query all TODOs joined with their parent meetings
        rows = (
            session.query(Todo, Meeting)
            .join(Meeting, Todo.meeting_id == Meeting.id)
            .order_by(Todo.created_at.desc())
            .all()
        )
        
        # Handle empty case
        if not rows:
            st.info("No TODOs found yet. Analyze a meeting to create action items!")
            return
        
        # Build table data
        table_data = []
        for todo, meeting in rows:
            table_data.append({
                "ID": todo.id,
                "Task": todo.task,
                "Owner": todo.owner or "Unassigned",
                "Status": todo.status,
                "Due date": todo.due_date or "Not specified",
                "Meeting ID": meeting.id,
                "Meeting date": meeting.date.strftime("%Y-%m-%d") if meeting.date else "N/A",
                "Created": todo.created_at.strftime("%Y-%m-%d %H:%M") if todo.created_at else "N/A",
                "Acknowledged": todo.acknowledged_at.strftime("%Y-%m-%d %H:%M") if todo.acknowledged_at else "N/A",
                "Completed": todo.completed_at.strftime("%Y-%m-%d %H:%M") if todo.completed_at else "N/A",
            })
        
        # Display dataframe
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Selectbox to pick a TODO
        todo_options = {f"#{row['ID']}: {row['Task'][:50]}..." if len(row['Task']) > 50 else f"#{row['ID']}: {row['Task']}": row['ID'] for row in table_data}
        selected_label = st.selectbox("Select a TODO to update", list(todo_options.keys()))
        selected_id = todo_options[selected_label]
        
        st.divider()
        
        # Action buttons
        col1, col2 = st.columns(2)
        updated = False
        
        with col1:
            if st.button("Mark as acknowledged", type="primary", use_container_width=True):
                try:
                    acknowledge_todo(session, selected_id)
                    st.success(f"✅ TODO #{selected_id} marked as acknowledged (in progress).")
                    updated = True
                except Exception as exc:
                    st.error(f"❌ Error acknowledging TODO: {exc}")
        
        with col2:
            if st.button("Mark as done", type="primary", use_container_width=True):
                try:
                    complete_todo(session, selected_id)
                    st.success(f"✅ TODO #{selected_id} marked as done.")
                    updated = True
                except Exception as exc:
                    st.error(f"❌ Error completing TODO: {exc}")
        
        # Rerun after any update to refresh the table
        if updated:
            st.rerun()
    
    except Exception as exc:
        st.error(f"Error loading TODOs: {exc}")
        st.exception(exc)
    finally:
        session.close()
