"""
Decisions endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db
from api.dtos import DecisionDTO
from api.repositories import list_decisions
from api.security import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/decisions", response_model=list[DecisionDTO])
def get_decisions(
    meeting_id: Optional[int] = Query(default=None, description="Filter by meeting ID"),
    db: Session = Depends(get_db)
) -> list[DecisionDTO]:
    """
    List decisions with optional meeting filter.
    
    Args:
        meeting_id: Optional filter by meeting ID
        db: Database session
    
    Returns:
        List of decisions
    """
    decisions = list_decisions(
        session=db,
        meeting_id=meeting_id
    )
    return [DecisionDTO(**d) for d in decisions]

