"""
Health check endpoint.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db
from database import Meeting

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    """
    Health check endpoint.
    
    Returns:
        Status information including database connectivity
    """
    db_ok = False
    try:
        # Simple query to check DB connectivity
        db.query(Meeting).limit(1).all()
        db_ok = True
    except Exception:
        db_ok = False
    
    return {
        "status": "ok",
        "time": datetime.utcnow().isoformat(),
        "db": "ok" if db_ok else "error"
    }

