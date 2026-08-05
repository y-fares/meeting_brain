"""
Analytics endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db
from api.dtos import KPIsDTO
from api.repositories import compute_kpis
from api.security import require_configured_auth
from database import User

router = APIRouter()


@router.get("/analytics/kpis", response_model=KPIsDTO)
def get_kpis(
    current_user: User | None = Depends(require_configured_auth),
    db: Session = Depends(get_db),
) -> KPIsDTO:
    """
    Get key performance indicators.
    
    Args:
        db: Database session
    
    Returns:
        KPI metrics
    """
    kpis = compute_kpis(session=db, current_user=current_user)
    return KPIsDTO(**kpis)

