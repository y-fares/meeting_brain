"""
Pydantic schemas for validating LLM JSON outputs.
"""

from pydantic import BaseModel, field_validator


class DecisionsPayload(BaseModel):
    """Schema for decisions JSON payload."""
    decisions: list[str] = []


class TodoItem(BaseModel):
    """Schema for a single TODO item."""
    task: str
    owner: str = ""
    due_date: str = ""  # must be "" or "YYYY-MM-DD"

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: str) -> str:
        """Validate and coerce due_date to empty string if invalid."""
        if not v or not v.strip():
            return ""
        
        v = v.strip()
        
        # Check if it matches YYYY-MM-DD format
        import re
        from datetime import datetime
        
        if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            # Try to parse the date to ensure it's actually valid
            try:
                datetime.strptime(v, "%Y-%m-%d")
                return v
            except ValueError:
                # Invalid date (e.g., 2025-13-45) - coerce to empty string
                return ""
        
        # Invalid format - coerce to empty string
        return ""


class TodosPayload(BaseModel):
    """Schema for todos JSON payload."""
    todos: list[TodoItem] = []

