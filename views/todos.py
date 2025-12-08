import streamlit as st
import pandas as pd

from typing import List, Dict, Any

from database import (
    create_session,
    Todo,
    Meeting,
    acknowledge_todo,
    complete_todo,
    set_trello_card_id,
)
from integrations.trello_client import create_card_for_todo

def render_todos_view() -> None:
    """
    Render the 'All TODOs' view in Streamlit.
    Shows all TODOs across all meetings and allows status updates.
    """
    st.subheader("All TODOs")

    session = create_session()

    # Query all todos joined with their meeting
    rows = (
        session.query(Todo, Meeting)
        .join(Meeting, Todo.meeting_id == Meeting.id)
        .order_by(Todo.created_at.desc())
        .all()
    )

    if not rows:
        st.info("No actions found yet.")
        return

    # Build table for display
    table_data = []
    for todo, meeting in rows:
        table_data.append(
            {
                "ID": todo.id,
                "Task": todo.task,
                "Owner": todo.owner or "Unassigned",
                "Status": todo.status,
                "Due date": todo.due_date or "Not specified",
                "Meeting ID": meeting.id,
                "Meeting date": meeting.date,
                "Created at": todo.created_at,
                "Acknowledged at": todo.acknowledged_at,
                "Completed at": todo.completed_at,
                "Trello card id": todo.trello_card_id or "",
            }
        )

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)

    # Select a TODO to update
    todo_ids = [row["ID"] for row in table_data]
    selected_id = st.selectbox("Select a TODO to update", todo_ids)

    # Find the selected todo and meeting objects
    selected_todo = None
    selected_meeting = None
    for todo, meeting in rows:
        if todo.id == selected_id:
            selected_todo = todo
            selected_meeting = meeting
            break

    col1, col2, col3 = st.columns(3)
    updated = False

    with col1:
        if st.button("Mark as acknowledged"):
            acknowledge_todo(session, selected_id)
            st.success(f"TODO {selected_id} marked as in progress.")
            updated = True

    with col2:
        if st.button("Mark as done"):
            complete_todo(session, selected_id)
            st.success(f"TODO {selected_id} marked as done.")
            updated = True

    with col3:
        # Push to Trello button
        if selected_todo and selected_meeting:
            if selected_todo.trello_card_id:
                st.info(f"Trello card linked: {selected_todo.trello_card_id}")
                st.button("Push to Trello", disabled=True)
            else:
                if st.button("Push to Trello"):
                    card_id = create_card_for_todo(selected_todo, selected_meeting)
                    if card_id:
                        set_trello_card_id(session, selected_id, card_id)
                        st.success(f"TODO {selected_id} linked to Trello card {card_id}.")
                        updated = True
                    else:
                        st.error("Failed to create Trello card. Check logs and config.")

    # If we updated something, force a rerun to refresh the table
    if updated:
        st.rerun()



