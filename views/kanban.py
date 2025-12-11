"""
Kanban Sync view for displaying and synchronizing Notion Kanban with local database.
"""

import streamlit as st
import pandas as pd

from database import create_session, Todo
from integrations.notion_client import (
    fetch_notion_kanban,
    sync_from_notion,
    sync_to_notion,
)


def render_kanban_view() -> None:
    """
    Render the 'Kanban Sync' view in Streamlit.
    
    Shows Notion Kanban snapshot, DB TODOs snapshot,
    and provides sync controls.
    """
    st.title("Kanban Sync (Notion ↔ DB)")
    st.markdown(
        "View and synchronize statuses between your Notion Kanban board and the local database. "
        "Only TODOs that are already linked to Notion pages (have notion_page_id) are shown and synchronized."
    )
    st.divider()
    
    # Create database session
    session = create_session()
    
    try:
        # Layout: two columns for side-by-side comparison
        col_left, col_right = st.columns(2)
        
        # Left column: Notion Kanban snapshot
        with col_left:
            st.subheader("📋 Notion Kanban Board")
            
            kanban_data = fetch_notion_kanban()
            
            if not kanban_data:
                st.info("No data from Notion Kanban. Check your Notion configuration or sharing settings.")
            else:
                total_cards = sum(len(cards) for cards in kanban_data.values())
                st.metric("Total Cards in Notion", total_cards)
                st.divider()
                
                for column_name, cards in kanban_data.items():
                    st.markdown(f"### {column_name} ({len(cards)} cards)")
                    
                    if cards:
                        # Build DataFrame from cards
                        cards_data = []
                        for card in cards:
                            cards_data.append({
                                "Title": card.get("title", "Untitled"),
                                "Owner": card.get("owner") or "Unassigned",
                                "Due": card.get("due") or "Not specified",
                                "Page ID": card.get("page_id", "")[:16] + "..." if card.get("page_id") else "N/A"
                            })
                        
                        df_cards = pd.DataFrame(cards_data)
                        st.dataframe(df_cards, width='stretch', hide_index=True)
                    else:
                        st.info("No cards in this column.")
                    
                    st.divider()
        
        # Right column: DB TODOs snapshot
        with col_right:
            st.subheader("💾 Database TODOs (Linked to Notion)")
            
            todos = session.query(Todo).filter(Todo.notion_page_id.isnot(None)).all()
            
            if not todos:
                st.info("No TODOs linked to Notion yet (notion_page_id is null). Use 'Push to Notion' in All TODOs view to link them.")
            else:
                st.metric("Linked TODOs", len(todos))
                st.divider()
                
                # Build list of dicts for DataFrame
                todos_data = []
                for todo in todos:
                    todos_data.append({
                        "ID": todo.id,
                        "Task": todo.task[:50] + "..." if len(todo.task) > 50 else todo.task,
                        "Owner": todo.owner or "Unassigned",
                        "Status": todo.status or "",
                        "Due date": todo.due_date or "Not specified",
                        "Notion page": todo.notion_page_id[:16] + "..." if todo.notion_page_id else "N/A",
                        "Acknowledged": todo.acknowledged_at.strftime("%Y-%m-%d") if todo.acknowledged_at else "N/A",
                        "Completed": todo.completed_at.strftime("%Y-%m-%d") if todo.completed_at else "N/A",
                    })
                
                df_todos = pd.DataFrame(todos_data)
                st.dataframe(df_todos, width='stretch', hide_index=True)
        
        st.divider()
        
        # Sync controls
        st.subheader("🔄 Synchronization Controls")
        st.markdown("Synchronize statuses between Notion and the database.")
        
        sync_col1, sync_col2, sync_col3 = st.columns(3)
        updated = False
        
        with sync_col1:
            if st.button("📥 Sync from Notion → DB", type="primary"):
                try:
                    with st.spinner("Syncing from Notion..."):
                        updated_count = sync_from_notion(session)
                        if updated_count > 0:
                            st.success(f"✅ Sync from Notion completed. {updated_count} TODO(s) updated in DB.")
                            updated = True
                        else:
                            st.info("ℹ️ Sync from Notion completed. No TODO needed update.")
                except Exception as exc:
                    st.error(f"❌ Error syncing from Notion: {exc}")
                    st.exception(exc)
        
        with sync_col2:
            if st.button("📤 Sync from DB → Notion", type="primary"):
                try:
                    with st.spinner("Syncing to Notion..."):
                        updated_count = sync_to_notion(session)
                        if updated_count > 0:
                            st.success(f"✅ Sync to Notion completed. {updated_count} card(s) updated in Notion.")
                            updated = True
                        else:
                            st.info("ℹ️ Sync to Notion completed. No card needed update.")
                except Exception as exc:
                    st.error(f"❌ Error syncing to Notion: {exc}")
                    st.exception(exc)
        
        with sync_col3:
            if st.button("🔄 Full Sync (Notion ↔ DB)", type="secondary"):
                try:
                    with st.spinner("Performing full sync..."):
                        updated_from = sync_from_notion(session)
                        updated_to = sync_to_notion(session)
                        st.success(
                            f"✅ Full sync completed. "
                            f"{updated_from} TODO(s) updated from Notion, "
                            f"{updated_to} card(s) updated in Notion."
                        )
                        updated = True
                except Exception as exc:
                    st.error(f"❌ Error during full sync: {exc}")
                    st.exception(exc)
        
        # Rerun after any update to refresh the views
        if updated:
            st.rerun()
    
    except Exception as exc:
        st.error(f"Error loading Kanban sync view: {exc}")
        st.exception(exc)
    finally:
        session.close()

