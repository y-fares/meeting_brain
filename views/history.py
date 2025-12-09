"""
History view for displaying all past meetings.

This view shows all meetings stored in the database, ordered by date (most recent first).
Each meeting is displayed in an expander with its details: summary, decisions, todos, and participants.
"""

import streamlit as st
from datetime import datetime

from database import create_session, Meeting, Decision, Todo, Participant


def render_history_view() -> None:
    """
    Render the history view showing all meetings.
    
    Displays:
    - Meeting ID
    - Date
    - Summary
    - Decisions
    - Todos with status
    - Participants
    
    Uses Streamlit expanders for readability.
    Handles empty database case.
    """
    st.title("Meeting History")
    st.markdown("View all past meetings and their details.")
    st.divider()
    
    # Connect to database
    session = create_session()
    
    try:
        # Query all meetings ordered by date desc
        meetings = session.query(Meeting).order_by(Meeting.date.desc()).all()
        
        # Handle empty database
        if not meetings:
            st.info("No meetings found yet. Analyze a meeting to get started!")
            return
        
        # Display meeting count
        st.metric("Total Meetings", len(meetings))
        st.divider()
        
        # Display each meeting in an expander
        for meeting in meetings:
            # Format meeting header
            meeting_date = meeting.date.strftime("%Y-%m-%d %H:%M") if meeting.date else "Date not set"
            meeting_title = f"Meeting #{meeting.id} - {meeting_date}"
            
            with st.expander(meeting_title, expanded=False):
                # Meeting ID and Date
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Meeting ID:** {meeting.id}")
                with col2:
                    st.markdown(f"**Date:** {meeting_date}")
                
                st.divider()
                
                # Summary
                st.subheader("Summary")
                if meeting.summary:
                    st.markdown(meeting.summary)
                else:
                    st.info("No summary available.")
                
                st.divider()
                
                # Decisions
                st.subheader("Decisions")
                decisions = session.query(Decision).filter_by(meeting_id=meeting.id).all()
                if decisions:
                    for decision in decisions:
                        st.markdown(f"- {decision.text}")
                else:
                    st.info("No decisions recorded for this meeting.")
                
                st.divider()
                
                # Todos with status
                st.subheader("Actions (TODOs)")
                todos = session.query(Todo).filter_by(meeting_id=meeting.id).all()
                if todos:
                    # Create a DataFrame for better display
                    import pandas as pd
                    todos_data = []
                    for todo in todos:
                        todos_data.append({
                            "Task": todo.task,
                            "Owner": todo.owner or "Unassigned",
                            "Due Date": todo.due_date or "Not specified",
                            "Status": todo.status,
                            "Created": todo.created_at.strftime("%Y-%m-%d") if todo.created_at else "N/A"
                        })
                    df = pd.DataFrame(todos_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("No TODOs registered for this meeting.")
                
                st.divider()
                
                # Participants
                st.subheader("Participants")
                participants = session.query(Participant).filter_by(meeting_id=meeting.id).all()
                if participants:
                    for participant in participants:
                        st.markdown(f"- {participant.name}")
                else:
                    st.info("No participants detected for this meeting.")
                
                st.divider()
                
                # Raw notes (in a nested expander)
                with st.expander("Raw Meeting Notes", expanded=False):
                    if meeting.raw_text:
                        st.text(meeting.raw_text)
                    else:
                        st.info("No raw text available.")
    
    except Exception as exc:
        st.error(f"Error loading meeting history: {exc}")
        st.exception(exc)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Integration Instructions for app.py
# ---------------------------------------------------------------------------
"""
To integrate this view into app.py via sidebar navigation:

1. Add sidebar navigation in the main() function:

    def main() -> None:
        st.set_page_config(page_title="Meeting Brain", layout="wide")
        
        # Sidebar navigation
        st.sidebar.title("Navigation")
        page = st.sidebar.radio(
            "Choose a page",
            ["Analyze Meeting", "History", "TODOs"]
        )
        
        if page == "Analyze Meeting":
            # Existing analyze meeting code
            ...
        elif page == "History":
            from views.history import render_history_view
            render_history_view()
        elif page == "TODOs":
            from views.todos import render_todos_view
            render_todos_view()

2. Alternatively, use st.navigation() (Streamlit 1.28+):

    def main() -> None:
        st.set_page_config(page_title="Meeting Brain", layout="wide")
        
        pages = {
            "Analyze Meeting": analyze_meeting_page,
            "History": lambda: render_history_view(),
            "TODOs": lambda: render_todos_view(),
        }
        
        selected = st.navigation(list(pages.keys()))
        pages[selected]()
"""
