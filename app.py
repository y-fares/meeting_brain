"""
Meeting Brain - Sprint 1: Text Ingestion and NLP Preprocessing
A Streamlit app for ingesting, cleaning, and preprocessing raw meeting notes.
"""

import streamlit as st
import nltk
import re
from collections import Counter
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords

# Download required NLTK resources safely
# Try punkt_tab first (newer NLTK versions), then fallback to punkt
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    try:
        nltk.download('punkt_tab', quiet=True)
    except:
        # Fallback to old punkt for older NLTK versions
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)


def get_text_statistics(text: str) -> dict:
    """
    Calculate basic statistics about the input text.
    
    Args:
        text: The input text string
        
    Returns:
        A dictionary containing character count and line count
    """
    return {
        "characters": len(text),
        "lines": len(text.splitlines())
    }


def preprocess_text(raw_text: str) -> dict:
    """
    Clean and preprocess raw text using NLP techniques.
    
    This function:
    - Strips leading/trailing spaces
    - Normalizes multiple spaces and newlines
    - Lowercases the text
    - Tokenizes the text
    - Removes English and French stopwords
    - Filters out punctuation-only tokens
    
    Args:
        raw_text: The raw input text to preprocess
        
    Returns:
        A dictionary containing:
        - clean_text: The cleaned text string
        - tokens_raw: List of tokens before stopword removal
        - tokens_filtered: List of tokens after stopword removal
        - num_chars: Number of characters in cleaned text
        - num_lines: Number of lines in cleaned text
        - num_tokens_raw: Number of tokens before filtering
        - num_tokens_filtered: Number of tokens after filtering
        - unique_words_raw: Number of unique words before filtering
        - unique_words_filtered: Number of unique words after filtering
        - lexical_diversity_raw: Ratio of unique words to total words (raw)
        - lexical_diversity_filtered: Ratio of unique words to total words (filtered)
        - avg_word_length: Average length of filtered words
        - num_sentences: Number of sentences in the text
        - avg_sentence_length: Average number of words per sentence
        - top_words: List of tuples (word, count) for top 10 most frequent words
    """
    # Strip leading/trailing spaces
    text = raw_text.strip()
    
    # Normalize multiple spaces and newlines
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces/newlines with single space
    text = re.sub(r'\n+', '\n', text)  # Normalize multiple newlines
    
    # Lowercase the text
    clean_text = text.lower()
    
    # Tokenize the text
    tokens_raw = word_tokenize(clean_text)
    
    # Load stopwords for English and French
    try:
        stop_words_en = set(stopwords.words('english'))
        stop_words_fr = set(stopwords.words('french'))
        stop_words = stop_words_en.union(stop_words_fr)
    except LookupError:
        # Fallback if stopwords are not available
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
    except:
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
        "top_words": top_words
    }


def get_user_input() -> str:
    """
    Display the text area input widget and return the user's input.
    
    Returns:
        The text entered by the user in the text area
    """
    return st.text_area(
        label="Paste your meeting notes here",
        height=300,
        placeholder="Paste the content of your meeting here..."
    )


def display_preprocessing_results(raw_text: str, preprocessed: dict) -> None:
    """
    Display the preprocessing results including raw text, cleaned text, tokens, and statistics.
    
    Args:
        raw_text: The original raw text
        preprocessed: Dictionary containing preprocessing results from preprocess_text()
    """
    # Display raw meeting notes
    st.subheader("Raw meeting notes")
    st.text(raw_text)
    
    # Display cleaned text
    st.subheader("Cleaned text")
    st.text(preprocessed["clean_text"])
    
    # Display filtered tokens
    st.subheader("Tokens (filtered)")
    tokens_display = " ".join(preprocessed["tokens_filtered"])
    st.text(tokens_display)
    
    # Display text statistics
    st.subheader("Text statistics")
    
    # Basic statistics
    st.markdown("**Basic Statistics**")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Characters", preprocessed["num_chars"])
        st.metric("Lines", preprocessed["num_lines"])
    with col2:
        st.metric("Sentences", preprocessed["num_sentences"])
        st.metric("Tokens (raw)", preprocessed["num_tokens_raw"])
    with col3:
        st.metric("Tokens (filtered)", preprocessed["num_tokens_filtered"])
        st.metric("Unique words (raw)", preprocessed["unique_words_raw"])
    with col4:
        st.metric("Unique words (filtered)", preprocessed["unique_words_filtered"])
        st.metric("Avg word length", f"{preprocessed['avg_word_length']:.2f}")
    
    # Advanced statistics
    st.markdown("**Advanced Statistics**")
    col5, col6, col7 = st.columns(3)
    with col5:
        st.metric("Lexical diversity (raw)", f"{preprocessed['lexical_diversity_raw']:.3f}")
    with col6:
        st.metric("Lexical diversity (filtered)", f"{preprocessed['lexical_diversity_filtered']:.3f}")
    with col7:
        st.metric("Avg sentence length", f"{preprocessed['avg_sentence_length']:.1f} words")
    
    # Top words
    if preprocessed["top_words"]:
        st.markdown("**Top 10 Most Frequent Words**")
        top_words_text = ", ".join([f"{word} ({count})" for word, count in preprocessed["top_words"]])
        st.text(top_words_text)


def main():
    """
    Main function that builds and runs the Streamlit UI.
    """
    # Set page title
    st.title("Meeting Brain - Sprint 1")
    
    # Display description at the top
    st.markdown("""
    **Step 1: Text Ingestion** | **Step 2: NLP Preprocessing**
    
    This app allows you to:
    1. Paste your raw meeting notes
    2. Clean and preprocess the text using NLP techniques (tokenization, stopword removal)
    
    The app will display the cleaned text, filtered tokens, and useful statistics.
    """)
    
    st.divider()
    
    # Get user input
    st.subheader("Input")
    meeting_notes = get_user_input()
    
    # Add analyze button
    if st.button("Analyze meeting", type="primary"):
        # Validate input
        if not meeting_notes or meeting_notes.strip() == "":
            st.warning("Please paste some meeting notes before analyzing.")
        else:
            # Preprocess the text
            preprocessed = preprocess_text(meeting_notes)
            
            # Show success message
            st.success("Meeting notes successfully preprocessed.")
            
            st.divider()
            
            # Display preprocessing results
            display_preprocessing_results(meeting_notes, preprocessed)


if __name__ == "__main__":
    main()
