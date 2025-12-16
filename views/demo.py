"""
Demo mode view for loading sample data and resetting database.
"""

import streamlit as st
from sqlalchemy.orm import Session

from database import create_session
from services.demo_loader import seed_demo_dataset, reset_database, load_demo_files
from services.text_pipeline import preprocess_text, extract_participants_from_raw

# Import LLM functions from app.py
from app import generate_summary, extract_decisions, extract_todos


def render_demo_view() -> None:
    """
    Render the 'Demo' view in Streamlit.
    
    Provides UI for loading demo dataset and resetting database.
    """
    st.title("Demo Mode")
    st.markdown(
        "Load sample meetings into the database for demonstrations. "
        "**Warning**: Reset database will permanently delete all data."
    )
    st.divider()
    
    # Create database session
    session = create_session()
    
    try:
        # Load demo dataset section
        st.markdown("### Load Demo Dataset")
        st.markdown(
            "Loads 4 sample meetings with decisions, TODOs, and participants. "
            "Safe to run multiple times (skips duplicates)."
        )
        
        if st.button("Load Demo Dataset", type="primary"):
            with st.spinner("Loading demo dataset..."):
                try:
                    result = seed_demo_dataset(
                        session=session,
                        generate_summary_func=generate_summary,
                        extract_decisions_func=extract_decisions,
                        extract_todos_func=extract_todos,
                    )
                    
                    st.success("Demo dataset loaded successfully!")
                    st.json(result)
                    
                    st.info(
                        f"Created: {result['meetings_created']} meetings, "
                        f"{result['todos_created']} TODOs, "
                        f"{result['decisions_created']} decisions, "
                        f"{result['participants_created']} participants"
                    )
                except Exception as exc:
                    st.error(f"Error loading demo dataset: {exc}")
                    st.exception(exc)
        
        st.divider()
        
        # Reset database section
        st.markdown("### Reset Database (DEV ONLY)")
        st.warning(
            "⚠️ **DANGER ZONE**: This will permanently delete ALL data from the database. "
            "This action cannot be undone."
        )
        
        confirmation_text = st.text_input(
            "Type 'RESET' to confirm database reset:",
            value="",
            type="default"
        )
        
        reset_enabled = confirmation_text.strip().upper() == "RESET"
        
        if st.button(
            "Reset Database",
            type="secondary",
            disabled=not reset_enabled,
            help="Type 'RESET' in the field above to enable this button"
        ):
            with st.spinner("Resetting database..."):
                try:
                    reset_database(session)
                    st.success("Database reset completed successfully!")
                    st.info("All meetings, TODOs, decisions, and participants have been deleted.")
                except Exception as exc:
                    st.error(f"Error resetting database: {exc}")
                    st.exception(exc)
        
        st.divider()
        
        # Demo script section
        with st.expander("📋 Demo Script (6-step presentation guide)"):
            st.markdown("""
            ### Step-by-step demo presentation
            
            1. **Load Demo Dataset**
               - Click "Load Demo Dataset" button above
               - Verify success message shows 4 meetings created
            
            2. **Show History**
               - Navigate to "History" view
               - Show the 4 loaded meetings
               - Select one to show details (summary, decisions, TODOs)
            
            3. **Show All TODOs**
               - Navigate to "All TODOs" view
               - Show all action items from demo meetings
               - Select a TODO and mark it as "Done" to demonstrate status updates
            
            4. **Show Q&A**
               - Navigate to "Q&A" view
               - Ask: "What are the overdue tasks?"
               - Show how AI answers based on database context
            
            5. **Show Analytics**
               - Navigate to "Analytics" view
               - Show KPIs (total meetings, TODOs, completion rate)
               - Show summary tables
               - Download CSV exports for Power BI
            
            6. **Show API & Power BI Integration**
               - Start FastAPI server: `uvicorn api.main:app --reload`
               - Open API docs: http://localhost:8000/docs
               - Show GET endpoints (meetings, todos, decisions, analytics)
               - Show CSV export endpoints
               - Demonstrate Power BI data refresh using API endpoints
            """)
        
        # Show demo files info
        with st.expander("📁 Demo Files Information"):
            try:
                demo_files = load_demo_files()
                st.markdown(f"**{len(demo_files)} demo meeting files available:**")
                for meeting in demo_files:
                    st.markdown(f"- **{meeting['title']}** ({meeting['date'].strftime('%Y-%m-%d')})")
            except Exception as exc:
                st.error(f"Error loading demo files info: {exc}")
    
    except Exception as exc:
        st.error(f"Error in Demo view: {exc}")
        st.exception(exc)
    finally:
        session.close()

