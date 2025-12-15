"""
Todo Events view for displaying audit trail of TODO status changes.
"""

import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session

from database import create_session, TodoEvent, Todo


def render_todo_events_view() -> None:
    """
    Render the 'Todo Events' view in Streamlit.
    
    Displays a table of TodoEvents with joined Todo information.
    """
    st.title("Todo Events - Audit Trail")
    st.markdown("View the complete history of TODO status changes.")
    st.divider()
    
    # Create database session
    session = create_session()
    
    try:
        # Check if there are any TODOs at all
        todo_count = session.query(Todo).count()
        
        # Query all todo events with joined todo information
        events = (
            session.query(TodoEvent, Todo)
            .join(Todo, TodoEvent.todo_id == Todo.id)
            .order_by(TodoEvent.created_at.desc())
            .all()
        )
        
        if not events:
            st.info("No status change events recorded yet.")
            st.markdown("---")
            
            if todo_count == 0:
                st.warning("⚠️ You don't have any TODOs yet!")
                st.markdown("""
                **First steps:**
                1. Go to **"Analyze Meeting"** view
                2. Paste meeting notes and analyze them
                3. This will create TODOs
                4. Then come back here and change their statuses to see events
                """)
            else:
                st.markdown("### 📝 How to generate events:")
                st.markdown(f"""
                You have **{todo_count} TODO(s)** in your database. To see events:
                
                1. **Go to "All TODOs" view** (in the sidebar)
                2. **Select a TODO** from the dropdown
                3. **Click "Mark as Acknowledged"** or **"Mark as Done"**
                4. **Return to this view** to see the event
                
                Events are also created when:
                - Syncing from Notion (if status changes)
                - Any status change through the UI
                """)
            return
        
        # Build dataframe
        events_data = []
        for event, todo in events:
            events_data.append({
                "todo_id": event.todo_id,
                "task": todo.task[:50] + "..." if len(todo.task) > 50 else todo.task,
                "old_status": event.old_status or "",
                "new_status": event.new_status,
                "source": event.source,
                "note": event.note or "",
                "created_at": event.created_at,
            })
        
        df_events = pd.DataFrame(events_data)
        
        # Filter by todo_id
        st.markdown("### Filter by TODO")
        todo_ids = sorted(df_events["todo_id"].unique().tolist())
        selected_todo_id = st.selectbox(
            "Select TODO ID (or 'All'):",
            ["All"] + todo_ids,
            index=0
        )
        
        if selected_todo_id != "All":
            df_events = df_events[df_events["todo_id"] == selected_todo_id]
        
        # Display table
        st.markdown("### Status Change History")
        st.dataframe(
            df_events,
            width='stretch',
            hide_index=True
        )
        
        # Summary statistics
        st.divider()
        st.markdown("### Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Events", len(df_events))
        with col2:
            unique_todos = df_events["todo_id"].nunique()
            st.metric("Unique TODOs", unique_todos)
        with col3:
            sources = df_events["source"].value_counts().to_dict()
            most_common_source = max(sources.items(), key=lambda x: x[1])[0] if sources else "N/A"
            st.metric("Most Common Source", most_common_source)
    
    except Exception as exc:
        st.error(f"Error in Todo Events view: {exc}")
        st.exception(exc)
    finally:
        session.close()

