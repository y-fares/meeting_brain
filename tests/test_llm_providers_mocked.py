"""
Tests for LLM providers with mocked calls.
"""

import pytest
from unittest.mock import patch, MagicMock

from qa_engine import answer_question_with_llm


def test_answer_question_with_llm_mocked():
    """Test that answer_question_with_llm returns the mocked LLM response."""
    # Mock llm_generate to return a fixed string
    mock_response = "This is a mocked LLM response."
    
    with patch("qa_engine.llm_generate", return_value=mock_response):
        result = answer_question_with_llm(
            question="What are the pending tasks?",
            context_text="TODOS:\n- Task 1\n- Task 2",
            provider="gemini"
        )
        
        assert result == mock_response


def test_answer_question_with_llm_calls_llm_generate():
    """Test that answer_question_with_llm calls llm_generate with correct parameters."""
    mock_response = "Mocked answer"
    
    with patch("qa_engine.llm_generate", return_value=mock_response) as mock_llm:
        answer_question_with_llm(
            question="Test question",
            context_text="Test context",
            provider="groq"
        )
        
        # Verify llm_generate was called
        assert mock_llm.called
        
        # Verify it was called with provider
        call_args = mock_llm.call_args
        assert call_args[0][0] == "groq"  # provider
        assert "Test question" in call_args[0][1]  # prompt contains question
        assert "Test context" in call_args[0][1]  # prompt contains context

