"""
Tests for JSON parsing utilities.
"""

import pytest

from utils_json import parse_decisions, parse_todos, strip_json_fence, safe_load_json


def test_strip_json_fence():
    """Test that strip_json_fence removes markdown fences."""
    # Fenced JSON
    fenced = "```json\n{\"key\": \"value\"}\n```"
    assert strip_json_fence(fenced) == "{\"key\": \"value\"}"
    
    # Already clean
    clean = "{\"key\": \"value\"}"
    assert strip_json_fence(clean) == "{\"key\": \"value\"}"


def test_parse_decisions_valid_json():
    """Test parse_decisions with valid JSON."""
    valid_json = '{"decisions": ["Decision 1", "Decision 2", "Decision 3"]}'
    result = parse_decisions(valid_json)
    
    assert len(result) == 3
    assert "Decision 1" in result
    assert "Decision 2" in result
    assert "Decision 3" in result


def test_parse_decisions_fenced_json():
    """Test parse_decisions with fenced JSON."""
    fenced = '```json\n{"decisions": ["Decision 1"]}\n```'
    result = parse_decisions(fenced)
    
    assert len(result) == 1
    assert result[0] == "Decision 1"


def test_parse_decisions_invalid_json():
    """Test parse_decisions with invalid JSON returns empty list."""
    invalid_json = "This is not JSON"
    result = parse_decisions(invalid_json)
    
    assert result == []


def test_parse_decisions_empty_list():
    """Test parse_decisions with empty decisions list."""
    empty_json = '{"decisions": []}'
    result = parse_decisions(empty_json)
    
    assert result == []


def test_parse_decisions_filters_empty_strings():
    """Test that parse_decisions filters out empty strings."""
    json_with_empty = '{"decisions": ["Valid", "", "  ", "Also Valid"]}'
    result = parse_decisions(json_with_empty)
    
    assert len(result) == 2
    assert "Valid" in result
    assert "Also Valid" in result


def test_parse_todos_valid_json():
    """Test parse_todos with valid JSON."""
    valid_json = '''{
        "todos": [
            {"task": "Task 1", "owner": "Alice", "due_date": "2025-02-01"},
            {"task": "Task 2", "owner": "", "due_date": ""}
        ]
    }'''
    result = parse_todos(valid_json)
    
    assert len(result) == 2
    assert result[0]["task"] == "Task 1"
    assert result[0]["owner"] == "Alice"
    assert result[0]["due_date"] == "2025-02-01"
    assert result[1]["task"] == "Task 2"
    assert result[1]["owner"] == ""
    assert result[1]["due_date"] == ""


def test_parse_todos_missing_owner():
    """Test parse_todos handles missing owner."""
    json_missing_owner = '''{
        "todos": [
            {"task": "Task 1"}
        ]
    }'''
    result = parse_todos(json_missing_owner)
    
    assert len(result) == 1
    assert result[0]["task"] == "Task 1"
    assert result[0]["owner"] == ""
    assert result[0]["due_date"] == ""


def test_parse_todos_invalid_due_date_format():
    """Test parse_todos coerces invalid due_date format to empty string."""
    json_invalid_date = '''{
        "todos": [
            {"task": "Task 1", "owner": "Alice", "due_date": "invalid-date"},
            {"task": "Task 2", "owner": "Bob", "due_date": "2025-13-45"},
            {"task": "Task 3", "owner": "Charlie", "due_date": "2025-02-01"}
        ]
    }'''
    result = parse_todos(json_invalid_date)
    
    assert len(result) == 3
    assert result[0]["due_date"] == ""  # Invalid format coerced
    assert result[1]["due_date"] == ""  # Invalid format coerced
    assert result[2]["due_date"] == "2025-02-01"  # Valid format kept


def test_parse_todos_filters_empty_task():
    """Test that parse_todos filters out todos with empty task."""
    json_empty_task = '''{
        "todos": [
            {"task": "Valid Task", "owner": "Alice", "due_date": ""},
            {"task": "", "owner": "Bob", "due_date": ""},
            {"task": "   ", "owner": "Charlie", "due_date": ""}
        ]
    }'''
    result = parse_todos(json_empty_task)
    
    assert len(result) == 1
    assert result[0]["task"] == "Valid Task"


def test_parse_todos_invalid_json():
    """Test parse_todos with invalid JSON returns empty list."""
    invalid_json = "This is not JSON"
    result = parse_todos(invalid_json)
    
    assert result == []


def test_safe_load_json_valid():
    """Test safe_load_json with valid JSON."""
    valid_json = '{"key": "value", "number": 42}'
    result = safe_load_json(valid_json)
    
    assert result == {"key": "value", "number": 42}


def test_safe_load_json_invalid():
    """Test safe_load_json with invalid JSON returns empty dict."""
    invalid_json = "Not JSON"
    result = safe_load_json(invalid_json)
    
    assert result == {}


def test_safe_load_json_empty():
    """Test safe_load_json with empty string returns empty dict."""
    result = safe_load_json("")
    assert result == {}

