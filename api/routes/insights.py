"""
Insights endpoints for project Q&A.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db
from api.security import require_configured_auth
from database import User
from services.insights_engine import (
    answer_insights_question,
    get_owner_load,
    get_bottlenecks
)

router = APIRouter()


@router.get("/answer")
def get_insights_answer(
    q: str = Query(..., description="Question to answer"),
    use_llm: bool = Query(default=False, description="Use LLM to enhance answer"),
    current_user: User | None = Depends(require_configured_auth),
    db: Session = Depends(get_db)
) -> dict:
    """
    Answer an insights question.
    
    Args:
        q: Question string
        use_llm: Whether to use LLM to enhance the answer
        db: Database session
    
    Returns:
        Dict with intent, answer, evidence, and recommended_actions
    """
    return answer_insights_question(
        session=db,
        question=q,
        use_llm=use_llm,
        current_user=current_user,
    )


@router.get("/owner_load")
def get_owner_load_endpoint(
    current_user: User | None = Depends(require_configured_auth),
    db: Session = Depends(get_db),
) -> list:
    """
    Get owner workload statistics.
    
    Args:
        db: Database session
    
    Returns:
        List of owner load dictionaries
    """
    return get_owner_load(session=db, current_user=current_user)


@router.get("/bottlenecks")
def get_bottlenecks_endpoint(
    current_user: User | None = Depends(require_configured_auth),
    db: Session = Depends(get_db),
) -> dict:
    """
    Get project bottlenecks.
    
    Args:
        db: Database session
    
    Returns:
        Dict with top overdue owners, most loaded owners, and stale tasks
    """
    return get_bottlenecks(session=db, current_user=current_user)

