"""
Q&A view for asking questions about meetings, decisions, and TODOs.
"""

import streamlit as st
import pandas as pd
from database import create_session
from qa_engine import answer_question


def render_qa_view() -> None:
    """
    Render the 'Q&A' view in Streamlit.
    
    Allows the user to ask questions about meetings, decisions, and TODOs.
    """
    st.title("Q&A - Ask Meeting Brain")
    st.markdown(
        "Ask questions about your meetings, decisions, and action items. "
        "Answers are based only on data stored in the database and formatted by AI."
    )
    st.divider()
    
    # Provider selection
    st.markdown("### 🤖 LLM Provider Selection")
    provider = st.selectbox(
        "Choose LLM provider:",
        ["mistral", "gemini", "groq"],
        index=0,
        help="Select which LLM provider to use for answering questions. Mistral requires MISTRAL_API_KEY, Gemini requires GOOGLE_API_KEY, Groq requires GROQ_API_KEY."
    )
    
    # Show provider status
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        mistral_status = "✅ Available" if os.getenv("MISTRAL_API_KEY") else "❌ Not configured"
        st.caption(f"Mistral: {mistral_status}")
    with col2:
        gemini_status = "✅ Available" if os.getenv("GOOGLE_API_KEY") else "❌ Not configured"
        st.caption(f"Gemini: {gemini_status}")
    with col3:
        groq_status = "✅ Available" if os.getenv("GROQ_API_KEY") else "❌ Not configured"
        st.caption(f"Groq: {groq_status}")
    
    st.divider()
    
    # Create database session
    session = create_session()
    
    try:
        # Input area
        question = st.text_area(
            "Ask a question about your meetings / actions:",
            height=100,
            placeholder="Example: What are the pending tasks? / Quelles sont les tâches en attente?"
        )
        
        # Ask button
        if st.button("Ask Meeting Brain", type="primary"):
            # Validate
            if not question.strip():
                st.warning("Please enter a question.")
                return
            
            # Show spinner and get answer
            with st.spinner("Thinking..."):
                result = answer_question(session, question, provider=provider)
            
            # Extract results
            answer = result.get("answer", "")
            context = result.get("context", {})
            
            # Display answer
            st.markdown("### Answer")
            if answer:
                st.markdown(answer)
            else:
                st.info("No answer generated.")
            
            # Display underlying data
            st.markdown("---")
            st.markdown("### Data used for this answer")
            
            # Meetings
            meetings = context.get("meetings", [])
            if meetings:
                st.markdown("#### Meetings")
                df_meetings = pd.DataFrame(meetings)
                st.dataframe(df_meetings)
            
            # Decisions
            decisions = context.get("decisions", [])
            if decisions:
                st.markdown("#### Decisions")
                df_decisions = pd.DataFrame(decisions)
                st.dataframe(df_decisions)
            
            # Todos
            todos = context.get("todos", [])
            if todos:
                st.markdown("#### TODOs")
                df_todos = pd.DataFrame(todos)
                st.dataframe(df_todos)
            
            # Show message if no data
            if not meetings and not decisions and not todos:
                st.info("No relevant data found in the database for this question.")
    
    except Exception as exc:
        st.error(f"Error in Q&A view: {exc}")
        st.exception(exc)
    finally:
        session.close()
