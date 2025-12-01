"""
Meeting Brain - Sprint 1: Text Ingestion, Preprocessing, and LLM Insights
"""

import json
import logging
import os
import re
from collections import Counter
from typing import Any, Dict, List

import google.generativeai as genai
from google.generativeai.types import GenerationConfig
import nltk
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

load_dotenv()

# Default Gemini model can be overridden via GEMINI_MODEL in .env
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def _ensure_nltk_resources() -> None:
    """Download the required NLTK models if they are missing."""
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


_ensure_nltk_resources()


def _api_key_available() -> bool:
    """Return True if the Gemini API key is configured."""
    if not GEMINI_API_KEY:
        st.error("GEMINI_API_KEY environment variable is not set.")
        return False
    return True


def _strip_json_fence(text: str) -> str:
    """Remove Markdown-style ```json fences if present."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        lines = lines[1:]  # drop opening fence
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def _call_gemini(prompt_parts: List[str], temperature: float = 0.2) -> str:
    """
    Call the Gemini model with the provided prompt parts.

    Args:
        prompt_parts: Ordered list combining system + user context.
        temperature: Sampling temperature for the model.

    Returns:
        Text response from Gemini (empty string if something went wrong).
    """
    if not _api_key_available():
        return ""

    try:
        model = genai.GenerativeModel(model_name=GEMINI_MODEL)
        response = model.generate_content(
            prompt_parts,
            generation_config=GenerationConfig(temperature=temperature),
        )
        text = getattr(response, "text", "")
        if text:
            return text.strip()
        LOGGER.warning("Gemini response did not include text: %s", response)
        st.warning("The LLM did not return text.")
        return ""
    except Exception as exc:
        LOGGER.exception("Gemini call failed: %s", exc)
        st.error("An error occurred while calling the LLM.")
        return ""


def preprocess_text(raw_text: str) -> str:
    """
    Basic preprocessing that strips leading/trailing spaces and normalizes whitespace.

    Args:
        raw_text: Original meeting notes entered by the user.

    Returns:
        Cleaned text suitable for analytics and LLM prompts.
    """
    text = raw_text.strip()
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text


def compute_text_analysis(clean_text: str) -> Dict[str, Any]:
    """
    Compute NLP-driven statistics for the cleaned text.

    Args:
        clean_text: Preprocessed text.

    Returns:
        Dictionary containing statistics and token information.
    """
    lower_text = clean_text.lower()
    tokens_raw = word_tokenize(lower_text) if lower_text else []

    try:
        stop_words_en = set(stopwords.words("english"))
        stop_words_fr = set(stopwords.words("french"))
        stop_words = stop_words_en.union(stop_words_fr)
    except LookupError:
        stop_words = set()

    tokens_filtered = [
        token for token in tokens_raw if token not in stop_words and token.isalnum()
    ]

    num_chars = len(clean_text)
    num_lines = len(clean_text.splitlines()) if clean_text else 0
    num_tokens_raw = len(tokens_raw)
    num_tokens_filtered = len(tokens_filtered)

    unique_words_raw = len(set(tokens_raw))
    unique_words_filtered = len(set(tokens_filtered))

    lexical_diversity_raw = (
        unique_words_raw / num_tokens_raw if num_tokens_raw else 0
    )
    lexical_diversity_filtered = (
        unique_words_filtered / num_tokens_filtered if num_tokens_filtered else 0
    )

    avg_word_length = (
        sum(len(token) for token in tokens_filtered) / num_tokens_filtered
        if num_tokens_filtered
        else 0
    )

    try:
        sentences = sent_tokenize(clean_text)
        num_sentences = len(sentences)
        avg_sentence_length = (
            num_tokens_raw / num_sentences if num_sentences else 0
        )
    except Exception:
        num_sentences = 0
        avg_sentence_length = 0

    word_freq = Counter(tokens_filtered)
    top_words = word_freq.most_common(10)

    return {
        "clean_text": clean_text,
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


def generate_summary(meeting_text: str) -> str:
    """
    Use Gemini to produce a concise Markdown summary of the meeting.

    Args:
        meeting_text: Cleaned meeting text.

    Returns:
        Markdown summary string (may be empty on failure).
    """
    if not meeting_text.strip():
        return ""

    prompt_parts = [
        "You are Meeting Brain, an assistant that produces short, faithful meeting summaries in Markdown.",
        "Do not invent information that is not present in the source text.",
        "Write a concise summary covering goals, blockers, and next steps.",
        f"Meeting notes:\n<<<{meeting_text}>>>",
    ]

    summary = _call_gemini(prompt_parts, temperature=0.2)
    return summary


def extract_decisions(meeting_text: str) -> List[str]:
    """
    Use Gemini to extract decisions in a JSON payload.

    Args:
        meeting_text: Cleaned meeting text.

    Returns:
        List of decision strings.
    """
    if not meeting_text.strip():
        return []

    prompt_parts = [
        "You extract explicit decisions from meeting notes.",
        'Return ONLY valid JSON of the form {"decisions": ["Decision 1", ...]}.',
        'If no decisions exist, return {"decisions": []}.',
        "Do not include explanations or additional text.",
        f"Meeting text:\n<<<{meeting_text}>>>",
    ]

    content = _call_gemini(prompt_parts, temperature=0.0)
    if not content:
        return []

    try:
        payload = json.loads(_strip_json_fence(content))
        decisions = payload.get("decisions", [])
        if not isinstance(decisions, list):
            raise ValueError("decisions field is not a list.")
        return [str(item).strip() for item in decisions if str(item).strip()]
    except json.JSONDecodeError as json_err:
        LOGGER.error("Failed to parse decisions JSON: %s", json_err)
        LOGGER.error("Raw LLM response for decisions: %s", content)
        st.warning("Unable to parse decisions from the LLM. Showing an empty list.")
        return []
    except Exception as exc:
        LOGGER.exception("Decision extraction failed: %s", exc)
        st.error("An error occurred while calling the LLM.")
        return []


def extract_todos(meeting_text: str) -> List[Dict[str, str]]:
    """
    Use Gemini to extract actionable TODO items with owner and due date.

    Args:
        meeting_text: Cleaned meeting text.

    Returns:
        List of dictionaries with keys: task, owner, due_date.
    """
    if not meeting_text.strip():
        return []

    prompt_parts = [
        "You extract action items/TODOs from meetings.",
        'Return ONLY valid JSON shaped like {"todos": [{"task": "...", "owner": "...", "due_date": "YYYY-MM-DD"}, ...]}.',
        'Use empty strings for unknown owners or due dates. If nothing exists, return {"todos": []}.',
        "Do not include commentary outside the JSON.",
        f"Meeting text:\n<<<{meeting_text}>>>",
    ]

    content = _call_gemini(prompt_parts, temperature=0.0)
    if not content:
        return []

    try:
        payload = json.loads(_strip_json_fence(content))
        todos = payload.get("todos", [])
        if not isinstance(todos, list):
            raise ValueError("todos field is not a list.")

        normalized: List[Dict[str, str]] = []
        for item in todos:
            if not isinstance(item, dict):
                continue
            task = str(item.get("task", "")).strip()
            owner = str(item.get("owner", "")).strip()
            due_date = str(item.get("due_date", "")).strip()
            if task:
                normalized.append(
                    {"task": task, "owner": owner, "due_date": due_date}
                )
        return normalized
    except json.JSONDecodeError as json_err:
        LOGGER.error("Failed to parse todos JSON: %s", json_err)
        LOGGER.error("Raw LLM response for todos: %s", content)
        st.warning("Unable to parse action items from the LLM. Showing an empty list.")
        return []
    except Exception as exc:
        LOGGER.exception("Todo extraction failed: %s", exc)
        st.error("An error occurred while calling the LLM.")
        return []


def get_user_input() -> str:
    """Render the meeting notes text area."""
    return st.text_area(
        label="Paste your meeting notes here",
        height=300,
        placeholder="Paste the content of your meeting here...",
    )


def display_preprocessing_results(
    raw_text: str, clean_text: str, details: Dict[str, Any]
) -> None:
    """
    Show the original text, cleaned text, and NLP statistics to the user.

    Args:
        raw_text: Original meeting notes.
        clean_text: Preprocessed text.
        details: Dictionary with analytics data.
    """
    st.subheader("Raw meeting notes")
    st.text(raw_text)

    st.subheader("Cleaned text")
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
        st.metric(
            "Lexical diversity (filtered)",
            f"{details['lexical_diversity_filtered']:.3f}",
        )
    with col7:
        st.metric(
            "Avg sentence length", f"{details['avg_sentence_length']:.1f} words"
        )

    if details["top_words"]:
        st.markdown("**Top 10 Most Frequent Words**")
        top_words_text = ", ".join(
            [f"{word} ({count})" for word, count in details["top_words"]]
        )
        st.text(top_words_text)


def display_llm_results(
    summary: str, decisions: List[str], todos: List[Dict[str, str]]
) -> None:
    """
    Render the LLM outputs (summary, decisions, and tasks) in the UI.

    Args:
        summary: Markdown-ready meeting summary.
        decisions: List of decision strings.
        todos: List of dictionaries describing action items.
    """
    st.subheader("Summary")
    if summary:
        st.markdown(summary)
    else:
        st.info("No summary available.")

    st.subheader("Decisions")
    if decisions:
        for decision in decisions:
            st.markdown(f"- {decision}")
    else:
        st.info("No decisions detected.")

    st.subheader("Actions (TODOs)")
    if todos:
        table_rows = [
            {"Task": todo["task"], "Owner": todo["owner"], "Due date": todo["due_date"]}
            for todo in todos
        ]
        st.table(pd.DataFrame(table_rows))
    else:
        st.info("No action items detected.")


def main():
    """Main entry point for the Streamlit UI."""
    st.title("Meeting Brain - Sprint 1")
    st.markdown(
        """
        **Step 1: Text Ingestion** | **Step 2: NLP Preprocessing** | **Step 3: LLM Insights**

        Paste meeting notes, review quick preprocessing metrics, and let the LLM extract
        a faithful summary, decisions, and TODOs.
        """
    )

    st.divider()

    st.subheader("Input")
    meeting_notes = get_user_input()

    if st.button("Analyze meeting", type="primary"):
        if not meeting_notes or not meeting_notes.strip():
            st.warning("Please paste some meeting notes before analyzing.")
            return

        clean_text = preprocess_text(meeting_notes)
        details = compute_text_analysis(clean_text)
        st.success("Meeting notes successfully processed.")

        st.divider()
        display_preprocessing_results(meeting_notes, clean_text, details)

        st.divider()
        summary = generate_summary(clean_text)
        decisions = extract_decisions(clean_text)
        todos = extract_todos(clean_text)

        display_llm_results(summary, decisions, todos)


if __name__ == "__main__":
    main()

