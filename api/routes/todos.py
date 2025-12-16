"""
TODOs endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db
from api.dtos import TodoDTO
from api.repositories import list_todos
from api.security import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/todos", response_model=list[TodoDTO])
def get_todos(
    status: Optional[str] = Query(default=None, description="Filter by status (case-insensitive)"),
    owner: Optional[str] = Query(default=None, description="Filter by owner (case-insensitive contains)"),
    overdue: Optional[str] = Query(default=None, description="Filter overdue todos (true/false/1/0)"),
    db: Session = Depends(get_db)
) -> list[TodoDTO]:
    """
    List TODOs with optional filtering.
    
    Args:
        status: Optional status filter (case-insensitive)
        owner: Optional owner filter (case-insensitive contains)
        overdue: Optional overdue filter (accepts "true", "false", "1", "0")
        db: Database session
    
    Returns:
        List of TODOs
    """
    # Parse overdue boolean
    overdue_bool = None
    if overdue is not None:
        overdue_lower = str(overdue).lower()
        if overdue_lower in ["true", "1", "yes"]:
            overdue_bool = True
        elif overdue_lower in ["false", "0", "no"]:
            overdue_bool = False
    
    todos = list_todos(
        session=db,
        status=status,
        owner=owner,
        overdue=overdue_bool
    )
    return [TodoDTO(**t) for t in todos]

