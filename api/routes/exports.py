"""
CSV export endpoints.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from api.deps import get_db
from api.repositories import export_meetings_df, export_todos_df, export_decisions_df
from api.security import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/exports/meetings.csv")
def export_meetings_csv(db: Session = Depends(get_db)) -> StreamingResponse:
    """
    Export meetings as CSV.
    
    Args:
        db: Database session
    
    Returns:
        CSV file download
    """
    df = export_meetings_df(session=db)
    csv_string = df.to_csv(index=False)
    csv_bytes = csv_string.encode("utf-8")
    
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=meetings_export.csv"
        }
    )


@router.get("/exports/todos.csv")
def export_todos_csv(db: Session = Depends(get_db)) -> StreamingResponse:
    """
    Export TODOs as CSV.
    
    Args:
        db: Database session
    
    Returns:
        CSV file download
    """
    df = export_todos_df(session=db)
    csv_string = df.to_csv(index=False)
    csv_bytes = csv_string.encode("utf-8")
    
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=todos_export.csv"
        }
    )


@router.get("/exports/decisions.csv")
def export_decisions_csv(db: Session = Depends(get_db)) -> StreamingResponse:
    """
    Export decisions as CSV.
    
    Args:
        db: Database session
    
    Returns:
        CSV file download
    """
    df = export_decisions_df(session=db)
    csv_string = df.to_csv(index=False)
    csv_bytes = csv_string.encode("utf-8")
    
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=decisions_export.csv"
        }
    )

