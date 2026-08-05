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
    
    # Provider selection with proper defaults
    st.markdown("### 🤖 LLM Provider Selection")

    # Get available providers in priority order (groq → mistral → gemini)
    from llm_providers import get_available_providers, provider_is_available

    available_providers = get_available_providers()

    if not available_providers:
        st.error("❌ No LLM providers configured. Please set at least one: GROQ_API_KEY, MISTRAL_API_KEY, or GOOGLE_API_KEY")
        return

    provider = st.selectbox(
        "Choose LLM provider:",
        available_providers,
        index=0,
        help="Auto-configured by available API keys. Groq is fastest, Mistral is reliable, Gemini is accurate."
    )

    # Show provider status
    col1, col2, col3 = st.columns(3)
    with col1:
        groq_status = "✅ Available (fastest)" if provider_is_available("groq") else "❌ Not configured"
        st.caption(f"Groq: {groq_status}")
    with col2:
        mistral_status = "✅ Available (reliable)" if provider_is_available("mistral") else "❌ Not configured"
        st.caption(f"Mistral: {mistral_status}")
    with col3:
        gemini_status = "✅ Available (accurate)" if provider_is_available("gemini") else "❌ Not configured"
        st.caption(f"Gemini: {gemini_status}")
    
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
