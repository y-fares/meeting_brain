"""
Meetings endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db
from api.dtos import MeetingDTO
from api.repositories import list_meetings
from api.security import require_configured_auth
from database import User

router = APIRouter()


@router.get("/meetings", response_model=list[MeetingDTO])
def get_meetings(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of results"),
    from_date: Optional[str] = Query(default=None, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(default=None, alias="to", description="End date (YYYY-MM-DD)"),
    current_user: User | None = Depends(require_configured_auth),
    db: Session = Depends(get_db)
) -> list[MeetingDTO]:
    """
    List meetings with optional date filtering.
    
    Args:
        limit: Maximum number of results (1-200)
        from_date: Optional start date filter (YYYY-MM-DD)
        to_date: Optional end date filter (YYYY-MM-DD)
        db: Database session
    
    Returns:
        List of meetings
    """
    meetings = list_meetings(
        session=db,
        limit=limit,
        date_from=from_date,
        date_to=to_date,
        current_user=current_user,
    )
    return [MeetingDTO(**m) for m in meetings]

