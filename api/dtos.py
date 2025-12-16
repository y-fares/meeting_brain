"""
Pydantic DTOs (Data Transfer Objects) for API responses.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MeetingDTO(BaseModel):
    """Meeting data transfer object."""
    id: int
    date: Optional[datetime] = None
    title: str = ""
    summary: str = ""
    
    class Config:
        from_attributes = True


class TodoDTO(BaseModel):
    """Todo data transfer object."""
    id: int
    meeting_id: int
    meeting_date: Optional[datetime] = None
    meeting_title: str = ""
    task: str = ""
    owner: str = ""
    status: str = ""
    due_date: str = ""
    created_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notion_page_id: str = ""
    trello_card_id: str = ""
    
    class Config:
        from_attributes = True


class DecisionDTO(BaseModel):
    """Decision data transfer object."""
    id: int
    meeting_id: int
    meeting_date: Optional[datetime] = None
    meeting_title: str = ""
    text: str = ""
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class KPIsDTO(BaseModel):
    """Key Performance Indicators data transfer object."""
    total_meetings: int = 0
    total_todos: int = 0
    done_todos: int = 0
    overdue_todos: int = 0
    completion_rate: float = 0.0

