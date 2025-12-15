"""
Meeting Brain - Sprint 1
A Streamlit app for analyzing meeting notes with NLP preprocessing and Groq LLM.

Features:
    1. Text ingestion
    2. NLP preprocessing & statistics
    3. LLM summary/decisions/todos extraction (Groq)
    4. Result UI display
"""

import json
import logging
import os
import re
from collections import Counter
from typing import Any, Dict, List

from groq import Groq
import nltk
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize

from utils_json import parse_decisions, parse_todos

# Load environment variables from .env file
load_dotenv()

# ---------------------------------------------------------------------------
# Logging & Groq client setup
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Configure Groq API
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
else:
    groq_client = None
    LOGGER.warning("GROQ_API_KEY environment variable is not set.")

# ---------------------------------------------------------------------------
# NLTK resource preparation
# ---------------------------------------------------------------------------

try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    try:
        nltk.download("punkt_tab", quiet=True)
    except Exception:
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt", quiet=True)

try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords", quiet=True)

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _strip_json_fence(text: str) -> str:
    """Remove Markdown ``` fences when the LLM wraps JSON."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        lines = lines[1:]  # drop opening fence line
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


# ---------------------------------------------------------------------------
# Feature 2: NLP preprocessing
# ---------------------------------------------------------------------------


def preprocess_text(raw_text: str) -> Dict[str, Any]:
    """
    Clean and preprocess raw text using NLP techniques.

    Args:
        raw_text: The raw input text to preprocess

    Returns:
        A dictionary containing cleaned text, tokens, and statistics.
    """
    # Strip leading/trailing spaces
    text = raw_text.strip()

    # Normalize multiple spaces and newlines
    text = re.sub(r"\s+", " ", text)  # Replace multiple spaces/newlines with single space
    text = re.sub(r"\n+", "\n", text)  # Normalize multiple newlines

    # Lowercase the text
    clean_text = text.lower()

    # Tokenize the text
    tokens_raw = word_tokenize(clean_text) if clean_text else []

    # Load stopwords for English and French
    try:
        stop_words_en = set(stopwords.words("english"))
        stop_words_fr = set(stopwords.words("french"))
        stop_words = stop_words_en.union(stop_words_fr)
    except LookupError:
        stop_words = set()

    # Filter out stopwords and punctuation-only tokens
    tokens_filtered = [
        token for token in tokens_raw
        if token not in stop_words and token.isalnum()
    ]

    # Calculate basic statistics
    num_chars = len(clean_text)
    num_lines = len(clean_text.splitlines())
    num_tokens_raw = len(tokens_raw)
    num_tokens_filtered = len(tokens_filtered)

    # Calculate additional statistics
    unique_words_raw = len(set(tokens_raw))
    unique_words_filtered = len(set(tokens_filtered))

    # Lexical diversity (unique words / total words)
    lexical_diversity_raw = unique_words_raw / num_tokens_raw if num_tokens_raw > 0 else 0
    lexical_diversity_filtered = unique_words_filtered / num_tokens_filtered if num_tokens_filtered > 0 else 0

    # Average word length
    avg_word_length = sum(len(token) for token in tokens_filtered) / num_tokens_filtered if num_tokens_filtered > 0 else 0

    # Average sentence length (in words)
    try:
        sentences = sent_tokenize(clean_text)
        num_sentences = len(sentences)
        avg_sentence_length = num_tokens_raw / num_sentences if num_sentences > 0 else 0
    except Exception:
        num_sentences = 0
        avg_sentence_length = 0

    # Top 10 most frequent words (filtered)
    word_freq = Counter(tokens_filtered)
    top_words = word_freq.most_common(10)

    return {
        "clean_text": clean_text,
        "tokens_raw": tokens_raw,
        "tokens_filtered": tokens_filtered,
        "num_chars": num_chars,
        "num_lines": num_lines,
        "num_tokens_raw": num_tokens_raw,
        "num_tokens_filtered": num_tokens_filtered,
        "unique_words_raw": unique_words_raw,
        "unique_words_filtered": unique_words_filtered,
        "lexical_diversity_raw": lexical_diversity_raw,
        "lexical_diversity_filtered": lexical_diversity_filtered,
        "avg_word_length": avg_word_length,
        "num_sentences": num_sentences,
        "avg_sentence_length": avg_sentence_length,
        "top_words": top_words,
    }


# ---------------------------------------------------------------------------
# Feature 3: LLM functions (Groq)
# ---------------------------------------------------------------------------


def generate_summary(clean_text: str) -> str:
    """
    Generate a concise summary (5-10 lines) using Groq.

    Args:
        clean_text: The cleaned/preprocessed meeting text

    Returns:
        A string containing the summary, or an empty string if generation fails
    """
    if not clean_text or not clean_text.strip():
        return ""

    if not GROQ_API_KEY or not groq_client:
        LOGGER.error("GROQ_API_KEY environment variable is not set")
        return ""

    try:
        prompt = (
            "You are a meeting summarization assistant. "
            "Generate a concise, faithful summary (5-10 lines) in Markdown format. "
            "Do not invent information. Only summarize what is present in the meeting notes.\n\n"
            f"Meeting notes:\n{clean_text}"
        )

        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        
        summary = response.choices[0].message.content.strip() if response.choices else ""
        return summary

    except Exception as exc:
        LOGGER.exception("Error while generating summary: %s", exc)
        return ""


def extract_decisions(clean_text: str) -> List[str]:
    """
    Extract decisions from meeting notes using Groq.

    Args:
        clean_text: The cleaned/preprocessed meeting text

    Returns:
        A list of decision strings, or an empty list if extraction fails
    """
    if not clean_text or not clean_text.strip():
        return []

    if not GROQ_API_KEY or not groq_client:
        LOGGER.error("GROQ_API_KEY environment variable is not set")
        return []

    try:
        prompt = (
            "Return ONLY valid JSON. No prose. No explanation.\n\n"
            "Extract every explicit decision from the meeting notes below.\n"
            "Return ONLY JSON in this exact format:\n"
            '{"decisions": ["decision 1", "decision 2"]}\n\n'
            "Do not invent decisions not explicitly written.\n\n"
            f"Meeting notes:\n{clean_text}"
        )

        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )
        
        raw_output = response.choices[0].message.content.strip() if response.choices else ""

        if not raw_output:
            return []

        # Parse JSON using safe parsing utility
        return parse_decisions(raw_output)

    except Exception as exc:
        LOGGER.exception("Error while extracting decisions: %s", exc)
        return []


def extract_todos(clean_text: str) -> List[Dict[str, str]]:
    """
    Extract action items (TODOs) from meeting notes using Groq.

    Args:
        clean_text: The cleaned/preprocessed meeting text

    Returns:
        A list of dictionaries with keys 'task', 'owner', 'due_date',
        or an empty list if extraction fails
    """
    if not clean_text or not clean_text.strip():
        return []

    if not GROQ_API_KEY or not groq_client:
        LOGGER.error("GROQ_API_KEY environment variable is not set")
        return []

    try:
        prompt = (
            "Return ONLY valid JSON. No text outside JSON.\n\n"
            "Do not infer. Only extract explicit actions.\n\n"
            "Extract every action item/TODO from the meeting notes below.\n"
            "Return ONLY JSON in this exact format:\n"
            '{\n  "todos": [\n    {"task": "...", "owner": "...", "due_date": "YYYY-MM-DD or empty string"}\n  ]\n}\n\n'
            "Rules:\n"
            "- Use empty string for missing owner\n"
            "- Use empty string for missing due date\n"
            "- Do not invent tasks or owners\n\n"
            f"Meeting notes:\n{clean_text}"
        )

        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )
        
        raw_output = response.choices[0].message.content.strip() if response.choices else ""

        if not raw_output:
            return []

        # Parse JSON using safe parsing utility
        return parse_todos(raw_output)

    except Exception as exc:
        LOGGER.exception("Error while extracting todos: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Feature 4: UI display functions
# ---------------------------------------------------------------------------


def display_preprocessing_results(
    raw_text: str, clean_text: str, details: Dict[str, Any]
) -> None:
    """
    Display the preprocessing results including raw text, cleaned text, tokens, and statistics.

    Args:
        raw_text: The original raw text
        clean_text: The cleaned text
        details: Dictionary containing preprocessing results from preprocess_text()
    """
    st.subheader("Raw meeting notes")
    st.text(raw_text)

    with st.expander("Cleaned text", expanded=False):
        st.text(clean_text)

    st.subheader("Tokens (filtered)")
    tokens_display = " ".join(details["tokens_filtered"])
    st.text(tokens_display if tokens_display else "(no tokens)")

    st.subheader("Text statistics")
    st.markdown("**Basic Statistics**")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Characters", details["num_chars"])
        st.metric("Lines", details["num_lines"])
    with col2:
        st.metric("Sentences", details["num_sentences"])
        st.metric("Tokens (raw)", details["num_tokens_raw"])
    with col3:
        st.metric("Tokens (filtered)", details["num_tokens_filtered"])
        st.metric("Unique words (raw)", details["unique_words_raw"])
    with col4:
        st.metric("Unique words (filtered)", details["unique_words_filtered"])
        st.metric("Avg word length", f"{details['avg_word_length']:.2f}")

    st.markdown("**Advanced Statistics**")
    col5, col6, col7 = st.columns(3)
    with col5:
        st.metric("Lexical diversity (raw)", f"{details['lexical_diversity_raw']:.3f}")
    with col6:
        st.metric("Lexical diversity (filtered)", f"{details['lexical_diversity_filtered']:.3f}")
    with col7:
        st.metric("Avg sentence length", f"{details['avg_sentence_length']:.1f} words")

    if details["top_words"]:
        st.markdown("**Top 10 Most Frequent Words**")
        top_words_text = ", ".join([f"{word} ({count})" for word, count in details["top_words"]])
        st.text(top_words_text)


def display_llm_results(
    summary: str, decisions: List[str], todos: List[Dict[str, str]]
) -> None:
    """
    Display the LLM-generated results (summary, decisions, and TODOs).

    Args:
        summary: Markdown-ready meeting summary
        decisions: List of decision strings
        todos: List of dictionaries describing action items
    """
    st.subheader("Summary")
    if summary:
        st.markdown(summary)
    else:
        st.info("No summary available. The LLM may have encountered an issue.")

    st.subheader("Decisions")
    if decisions:
        for decision in decisions:
            st.markdown(f"- {decision}")
    else:
        st.info("No explicit decisions detected in the meeting notes.")

    st.subheader("Actions (TODOs)")
    if todos:
        df = pd.DataFrame([
            {
                "Task": todo.get("task", ""),
                "Owner": todo.get("owner", "") or "Unassigned",
                "Due date": todo.get("due_date", "") or "Not specified",
            }
            for todo in todos
        ])
        st.table(df)
    else:
        st.info("No action items detected in the meeting notes.")


# ---------------------------------------------------------------------------
# Feature 1 + 2 + 3 + 4: Streamlit application
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for the Streamlit UI."""
    st.set_page_config(page_title="Meeting Brain", layout="wide")
    
    # Sidebar navigation
    st.sidebar.title("🧠 Meeting Brain")
    st.sidebar.markdown("---")
    
    # Navigation menu - using radio for better visibility
    st.sidebar.markdown("### 📋 Navigation")
    page = st.sidebar.radio(
        "Choisir une page",
        ["Analyze Meeting", "History", "All TODOs", "Kanban Sync", "Q&A", "Analytics"],
        label_visibility="visible",
        index=0
    )
    
    st.sidebar.markdown("---")
    
    # Route to appropriate view
    if page == "History":
        from views.history import render_history_view
        render_history_view()
        return
    
    if page == "All TODOs":
        from views.todos import render_todos_view
        render_todos_view()
        return
    
    if page == "Kanban Sync":
        from views.kanban import render_kanban_view
        render_kanban_view()
        return
    
    if page == "Q&A":
        from views.qa import render_qa_view
        render_qa_view()
        return
    
    if page == "Analytics":
        from views.analytics import render_analytics_view
        render_analytics_view()
        return
    
    # Default: Analyze Meeting mode
    st.title("Meeting Brain")
    
    st.markdown(
        """
        **Step 1: Text Ingestion** | **Step 2: NLP Preprocessing** | **Step 3: LLM Insights** | **Step 4: Results**

        Paste your meeting notes below, run preprocessing, and let Groq extract
        the summary, decisions, and action items.
        """
    )

    st.divider()

    st.subheader("Input")
    meeting_notes = st.text_area(
        label="Paste your meeting notes here",
        height=300,
        placeholder="Paste the content of your meeting here...",
    )

    if st.button("Analyze meeting", type="primary"):
        if not meeting_notes or not meeting_notes.strip():
            st.warning("Please paste some meeting notes before analyzing.")
            return

        with st.spinner("Analyzing meeting with AI..."):
            try:
                # Step 1: Preprocess the text
                preprocessed = preprocess_text(meeting_notes)
                clean_text = preprocessed["clean_text"]

                # Step 2: Call Groq LLM functions
                summary = generate_summary(clean_text)
                decisions = extract_decisions(clean_text)
                todos = extract_todos(clean_text)

            except Exception as exc:
                LOGGER.exception("Unexpected error during analysis: %s", exc)
                st.error("An unexpected error occurred during analysis. Please try again.")
                return

        st.success("Meeting analysis completed successfully!")
        st.divider()

        # Display preprocessing results
        display_preprocessing_results(meeting_notes, clean_text, preprocessed)
        st.divider()

        # Display LLM results
        display_llm_results(summary, decisions, todos)
        
        # Save results to database
        try:
            from database import create_session, create_meeting, add_decisions, add_todos, add_participants
            from datetime import datetime
            
            session = create_session()
            
            # Extract participants from todos owners
            participants = list(set([todo.get("owner", "") for todo in todos if todo.get("owner")]))
            
            # Create meeting record
            meeting_id = create_meeting(
                session=session,
                raw_text=meeting_notes,
                summary=summary,
                title=None,
                date=datetime.now()
            )
            
            # Add decisions
            if decisions:
                add_decisions(session, meeting_id, decisions)
            
            # Add todos
            if todos:
                add_todos(session, meeting_id, todos)
            
            # Add participants
            if participants:
                add_participants(session, meeting_id, participants)
            
            st.success(f"Meeting saved to database (ID: {meeting_id})")
            LOGGER.info("Successfully saved meeting %d to database", meeting_id)
            
        except Exception as db_exc:
            if 'session' in locals():
                session.rollback()
            LOGGER.error("Error while saving meeting to database: %s", db_exc)
            st.warning("Meeting analysis completed, but failed to save to database. Check logs for details.")


if __name__ == "__main__":
    main()
