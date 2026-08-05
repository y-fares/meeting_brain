"""
TODOs endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_db
from api.dtos import TodoAssignRequest, TodoDTO, TodoStatusUpdateRequest
from api.repositories import list_todos
from api.security import require_configured_auth
from database import Meeting, Todo, User, update_todo_status

router = APIRouter()


def _can_modify_todo(todo: Todo, meeting: Meeting, current_user: User | None) -> bool:
    if current_user is None:
        return True
    if current_user.role == "admin":
        return True
    if current_user.role == "viewer":
        return False
    return todo.assigned_user_id == current_user.id or meeting.created_by_user_id == current_user.id


def _load_todo_with_meeting(db: Session, todo_id: int) -> tuple[Todo, Meeting]:
    row = (
        db.query(Todo, Meeting)
        .join(Meeting, Todo.meeting_id == Meeting.id)
        .filter(Todo.id == todo_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    return row


def _todo_to_dto(todo: Todo, meeting: Meeting) -> TodoDTO:
    return TodoDTO(
        id=todo.id,
        meeting_id=todo.meeting_id,
        meeting_date=meeting.date,
        meeting_title=meeting.title or "",
        task=todo.task or "",
        owner=todo.owner or "",
        status=todo.status or "",
        due_date=todo.due_date or "",
        created_at=todo.created_at,
        acknowledged_at=todo.acknowledged_at,
        completed_at=todo.completed_at,
        notion_page_id=todo.notion_page_id or "",
        trello_card_id=todo.trello_card_id or "",
        assigned_user_id=todo.assigned_user_id,
    )


@router.get("/todos", response_model=list[TodoDTO])
def get_todos(
    status: Optional[str] = Query(default=None, description="Filter by status (case-insensitive)"),
    owner: Optional[str] = Query(default=None, description="Filter by owner (case-insensitive contains)"),
    overdue: Optional[str] = Query(default=None, description="Filter overdue todos (true/false/1/0)"),
    current_user: User | None = Depends(require_configured_auth),
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
        overdue=overdue_bool,
        current_user=current_user,
    )
    return [TodoDTO(**t) for t in todos]


@router.patch("/todos/{todo_id}/status", response_model=TodoDTO)
def patch_todo_status(
    todo_id: int,
    payload: TodoStatusUpdateRequest,
    current_user: User | None = Depends(require_configured_auth),
    db: Session = Depends(get_db),
) -> TodoDTO:
    """Update a TODO status with role/ownership checks."""
    allowed_statuses = {"pending", "in_progress", "completed", "done"}
    new_status = payload.status.strip().lower()
    if new_status not in allowed_statuses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    todo, meeting = _load_todo_with_meeting(db, todo_id)
    if not _can_modify_todo(todo, meeting, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    update_todo_status(
        session=db,
        todo_id=todo_id,
        new_status=new_status,
        source="api",
        note=payload.note.strip() or None,
    )
    db.expire_all()
    todo, meeting = _load_todo_with_meeting(db, todo_id)
    return _todo_to_dto(todo, meeting)


@router.patch("/todos/{todo_id}/assignee", response_model=TodoDTO)
def patch_todo_assignee(
    todo_id: int,
    payload: TodoAssignRequest,
    current_user: User | None = Depends(require_configured_auth),
    db: Session = Depends(get_db),
) -> TodoDTO:
    """Assign a TODO to a user. Admins and meeting creators can assign."""
    todo, meeting = _load_todo_with_meeting(db, todo_id)
    can_assign = (
        current_user is None
        or current_user.role == "admin"
        or meeting.created_by_user_id == current_user.id
    )
    if not can_assign:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if payload.assigned_user_id is not None:
        assignee = db.query(User).filter(User.id == payload.assigned_user_id).first()
        if assignee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found")

    todo.assigned_user_id = payload.assigned_user_id
    db.commit()
    db.refresh(todo)
    return _todo_to_dto(todo, meeting)

