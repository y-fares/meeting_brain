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
    set_notion_page_id,
)
from integrations.notion_client import (
    push_todo_to_notion,
    sync_from_notion,
    sync_to_notion,
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
        st.dataframe(df, width='stretch', hide_index=True)
        
        st.divider()
        
        # Selectbox to pick a TODO
        todo_options = {f"#{row['ID']}: {row['Task'][:50]}..." if len(row['Task']) > 50 else f"#{row['ID']}: {row['Task']}": row['ID'] for row in table_data}
        selected_label = st.selectbox("Select a TODO to update", list(todo_options.keys()))
        selected_id = todo_options[selected_label]
        
        # Find the selected todo and meeting objects
        selected_todo = None
        selected_meeting = None
        for todo, meeting in rows:
            if todo.id == selected_id:
                selected_todo = todo
                selected_meeting = meeting
                break
        
        st.divider()
        
        # Action buttons for status updates and integrations
        st.subheader("Actions")
        col1, col2, col3 = st.columns(3)
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
        
        with col3:
            # Push to Notion button
            if selected_todo and selected_meeting:
                if selected_todo.notion_page_id:
                    st.info("This TODO is already linked to Notion.")
                    st.button("Push to Notion", disabled=True, use_container_width=True)
                else:
                    if st.button("Push to Notion", type="primary", use_container_width=True):
                        try:
                            page_id = push_todo_to_notion(selected_todo, selected_meeting)
                            if page_id:
                                set_notion_page_id(session, selected_id, page_id)
                                st.success(f"✅ Pushed to Notion: {page_id}")
                                updated = True
                            else:
                                st.error("❌ Failed to push TODO to Notion. Check logs.")
                        except Exception as exc:
                            st.error(f"❌ Error pushing to Notion: {exc}")
            else:
                st.button("Push to Notion", disabled=True, use_container_width=True)
        
        st.divider()
        
        # Synchronization section
        st.subheader("🔄 Synchronization")
        st.markdown("Synchronize statuses between Notion and the database.")
        
        sync_col1, sync_col2 = st.columns(2)
        
        with sync_col1:
            if st.button("📥 Sync from Notion", type="secondary", use_container_width=True):
                try:
                    with st.spinner("Syncing from Notion..."):
                        updated_count = sync_from_notion(session)
                        if updated_count > 0:
                            st.success(f"✅ Synced {updated_count} TODO(s) from Notion to database.")
                            updated = True
                        else:
                            st.info("ℹ️ No TODOs needed updating. Everything is already in sync.")
                except Exception as exc:
                    st.error(f"❌ Error syncing from Notion: {exc}")
                    st.exception(exc)
        
        with sync_col2:
            if st.button("📤 Sync to Notion", type="secondary", use_container_width=True):
                try:
                    with st.spinner("Syncing to Notion..."):
                        updated_count = sync_to_notion(session)
                        if updated_count > 0:
                            st.success(f"✅ Synced {updated_count} TODO(s) from database to Notion.")
                        else:
                            st.info("ℹ️ No TODOs needed updating. Everything is already in sync.")
                except Exception as exc:
                    st.error(f"❌ Error syncing to Notion: {exc}")
                    st.exception(exc)
        
        # Rerun after any update to refresh the table
        if updated:
            st.rerun()
    
    except Exception as exc:
        st.error(f"Error loading TODOs: {exc}")
        st.exception(exc)
    finally:
        session.close()
