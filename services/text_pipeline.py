"""
Text processing pipeline functions (pure Python, no Streamlit dependencies).
"""

import re
import logging
from typing import Dict, Any, List
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize

LOGGER = logging.getLogger(__name__)

# Initialize NLTK resources
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
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    
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
    
    # Lexical diversity
    lexical_diversity_raw = unique_words_raw / num_tokens_raw if num_tokens_raw > 0 else 0
    lexical_diversity_filtered = unique_words_filtered / num_tokens_filtered if num_tokens_filtered > 0 else 0
    
    # Average word length
    avg_word_length = sum(len(token) for token in tokens_filtered) / num_tokens_filtered if num_tokens_filtered > 0 else 0
    
    # Average sentence length
    try:
        sentences = sent_tokenize(clean_text)
        num_sentences = len(sentences)
        avg_sentence_length = num_tokens_raw / num_sentences if num_sentences > 0 else 0
    except Exception:
        num_sentences = 0
        avg_sentence_length = 0
    
    # Top 10 most frequent words (filtered)
    from collections import Counter
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


def extract_participants_from_raw(raw_text: str) -> List[str]:
    """
    Extract participant names from raw meeting text.
    
    Looks for patterns like:
    - "Participants : ..."
    - "Participants: ..."
    - "Attendees: ..."
    
    Args:
        raw_text: Raw meeting notes text
    
    Returns:
        List of participant names (cleaned)
    """
    participants = []
    
    try:
        # Look for participants section
        patterns = [
            r"participants?\s*[:：]\s*(.+?)(?:\n\n|\n\d+\.|$)",
            r"attendees?\s*[:：]\s*(.+?)(?:\n\n|\n\d+\.|$)",
            r"présents?\s*[:：]\s*(.+?)(?:\n\n|\n\d+\.|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE | re.MULTILINE)
            if match:
                participants_text = match.group(1).strip()
                
                # Split by common delimiters
                parts = re.split(r"[,\n\-–—•]", participants_text)
                
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    
                    # Remove role in parentheses (e.g., "Karim (CPO)" -> "Karim")
                    part = re.sub(r"\s*\([^)]+\)", "", part)
                    part = part.strip()
                    
                    if part and len(part) > 1:
                        participants.append(part)
                
                if participants:
                    break
        
        # Also extract from todos owners if found
        # This is a fallback if no explicit participants section
        if not participants:
            # Look for "Owner → task" patterns
            owner_pattern = r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*→"
            owner_matches = re.findall(owner_pattern, raw_text)
            participants.extend(owner_matches)
        
        # Remove duplicates and empty strings
        participants = list(set([p.strip() for p in participants if p.strip()]))
        
    except Exception as exc:
        LOGGER.exception("Error extracting participants: %s", exc)
    
    return participants

