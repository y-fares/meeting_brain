"""
Analytics endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db
from api.dtos import KPIsDTO
from api.repositories import compute_kpis
from api.security import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/analytics/kpis", response_model=KPIsDTO)
def get_kpis(db: Session = Depends(get_db)) -> KPIsDTO:
    """
    Get key performance indicators.
    
    Args:
        db: Database session
    
    Returns:
        KPI metrics
    """
    kpis = compute_kpis(session=db)
    return KPIsDTO(**kpis)

