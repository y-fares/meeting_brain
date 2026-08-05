"""
Insights Q&A view for project questions.
"""

import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session

from database import create_session
from services.insights_engine import (
    answer_insights_question,
    get_owner_load,
    get_bottlenecks
)


def render_insights_view() -> None:
    """
    Render the 'Insights' view in Streamlit.
    
    Provides Q&A interface for project insights.
    """
    st.subheader("Insights Q&A")
    st.markdown(
        "Posez des questions sur l'état du projet : tâches en retard, goulots d'étranglement, "
        "charge de travail, etc."
    )
    st.divider()
    
    # Create database session
    session = create_session()
    
    try:
        # Question input
        question = st.text_input(
            "Votre question",
            placeholder="Ex: Quelles tâches sont en retard ? Qui est surchargé ?"
        )
        
        use_llm = st.checkbox(
            "Utiliser LLM pour reformuler la réponse",
            value=False,
            help="Améliore la réponse avec une explication en langage naturel (nécessite GROQ_API_KEY)"
        )
        
        if st.button("Poser la question", type="primary"):
            if not question or not question.strip():
                st.warning("Veuillez entrer une question.")
                return
            
            with st.spinner("Analyse en cours..."):
                try:
                    result = answer_insights_question(
                        session=session,
                        question=question.strip(),
                        use_llm=use_llm
                    )
                    
                    # Display intent
                    st.markdown(f"**Intention détectée:** {result['intent']}")
                    st.divider()
                    
                    # Display answer
                    st.markdown("### Réponse")
                    st.info(result["answer"])
                    
                    # Display evidence
                    if result.get("evidence"):
                        with st.expander("📊 Données de preuve"):
                            evidence = result["evidence"]
                            
                            # Try to display as DataFrame if possible
                            if isinstance(evidence, dict):
                                # Check if evidence can be converted to DataFrame
                                if "overdue_todos" in evidence and evidence["overdue_todos"]:
                                    df = pd.DataFrame(evidence["overdue_todos"])
                                    st.dataframe(df)
                                elif "owners" in evidence and evidence["owners"]:
                                    df = pd.DataFrame(evidence["owners"])
                                    st.dataframe(df)
                                elif "stale_tasks" in evidence and evidence["stale_tasks"]:
                                    df = pd.DataFrame(evidence["stale_tasks"])
                                    st.dataframe(df)
                                else:
                                    st.json(evidence)
                            else:
                                st.json(evidence)
                    
                    # Display recommended actions
                    if result.get("recommended_actions"):
                        st.markdown("### Actions recommandées")
                        for i, action in enumerate(result["recommended_actions"], 1):
                            st.markdown(f"{i}. {action}")
                    
                except Exception as exc:
                    st.error(f"Erreur lors du traitement de la question: {exc}")
                    st.exception(exc)
        
        st.divider()
        
        # Quick access to common queries
        st.markdown("### Questions rapides")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📋 Tâches en retard"):
                result = answer_insights_question(session, "Quelles tâches sont en retard ?", use_llm=False)
                st.info(result["answer"])
                if result.get("evidence", {}).get("overdue_todos"):
                    df = pd.DataFrame(result["evidence"]["overdue_todos"])
                    st.dataframe(df)
        
        with col2:
            if st.button("⚡ Goulots d'étranglement"):
                result = answer_insights_question(session, "Qu'est-ce qui est bloqué ?", use_llm=False)
                st.info(result["answer"])
                if result.get("evidence", {}).get("stale_tasks"):
                    df = pd.DataFrame(result["evidence"]["stale_tasks"][:5])
                    st.dataframe(df)
        
        col3, col4 = st.columns(2)
        
        with col3:
            if st.button("👥 Charge de travail"):
                result = answer_insights_question(session, "Qui est surchargé ?", use_llm=False)
                st.info(result["answer"])
                if result.get("evidence", {}).get("owners"):
                    df = pd.DataFrame(result["evidence"]["owners"][:5])
                    st.dataframe(df)
        
        with col4:
            if st.button("📊 Résumé d'avancement"):
                result = answer_insights_question(session, "Quel est l'avancement ?", use_llm=False)
                st.info(result["answer"])
    
    except Exception as exc:
        st.error(f"Erreur dans la vue Insights: {exc}")
        st.exception(exc)
    finally:
        session.close()

