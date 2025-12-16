"""
Safe JSON parsing utilities for LLM outputs.
Handles fenced JSON, validation, and error recovery.
"""

import json
import logging
from typing import List, Dict

from schemas import DecisionsPayload, TodosPayload

# Setup logging
LOGGER = logging.getLogger(__name__)


def strip_json_fence(text: str) -> str:
    """
    Remove Markdown ``` fences when the LLM wraps JSON.
    
    Args:
        text: Raw text that may contain JSON wrapped in markdown fences
        
    Returns:
        Text with markdown fences removed
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        lines = lines[1:]  # drop opening fence line
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def safe_load_json(text: str) -> dict:
    """
    Safely load JSON from text, handling fenced JSON.
    
    Args:
        text: Text containing JSON (possibly fenced)
        
    Returns:
        Parsed JSON dictionary, or empty dict on error
    """
    if not text or not text.strip():
        return {}
    
    try:
        cleaned = strip_json_fence(text)
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError as json_err:
        LOGGER.error("Failed to parse JSON: %s", json_err)
        LOGGER.debug("Raw text: %s", text[:200])
        return {}
    except Exception as exc:
        LOGGER.exception("Unexpected error in safe_load_json: %s", exc)
        return {}


def parse_decisions(text: str) -> List[str]:
    """
    Parse and validate decisions from LLM JSON output.
    
    Args:
        text: JSON string from LLM (may be fenced)
        
    Returns:
        List of non-empty decision strings, or empty list on error
    """
    if not text or not text.strip():
        return []
    
    try:
        parsed = safe_load_json(text)
        if not parsed:
            return []
        
        # Validate with Pydantic
        payload = DecisionsPayload(**parsed)
        
        # Return cleaned list of non-empty strings
        decisions = [str(dec).strip() for dec in payload.decisions if str(dec).strip()]
        return decisions
    
    except Exception as exc:
        LOGGER.error("Failed to parse decisions: %s", exc)
        LOGGER.debug("Raw text: %s", text[:200])
        return []


def parse_todos(text: str) -> List[Dict[str, str]]:
    """
    Parse and validate todos from LLM JSON output.
    
    Args:
        text: JSON string from LLM (may be fenced)
        
    Returns:
        List of dicts with keys: task, owner, due_date (all strings)
        Returns empty list on error
    """
    if not text or not text.strip():
        return []
    
    try:
        parsed = safe_load_json(text)
        if not parsed:
            return []
        
        # Validate with Pydantic
        payload = TodosPayload(**parsed)
        
        # Convert to list of dicts with cleaned values
        todos = []
        for todo_item in payload.todos:
            task = str(todo_item.task).strip()
            if not task:
                continue  # Skip todos with empty task
            
            todos.append({
                "task": task,
                "owner": str(todo_item.owner).strip() if todo_item.owner else "",
                "due_date": todo_item.due_date,  # Already validated/coerced by Pydantic
            })
        
        return todos
    
    except Exception as exc:
        LOGGER.error("Failed to parse todos: %s", exc)
        LOGGER.debug("Raw text: %s", text[:200])
        return []

