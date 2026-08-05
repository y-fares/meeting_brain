"""
Authentication endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.auth_service import authenticate_password, create_user, has_users
from api.deps import get_db
from api.dtos import (
    AuthBootstrapRequest,
    AuthCreateUserRequest,
    AuthLoginRequest,
    AuthTokenDTO,
    CreatedUserDTO,
    CurrentUserDTO,
)
from api.security import get_current_user
from database import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_current_user_dto(user: User) -> CurrentUserDTO:
    return CurrentUserDTO(
        id=user.id,
        email=user.email,
        display_name=user.display_name or "",
        role=user.role,
    )


@router.post("/bootstrap", response_model=AuthTokenDTO, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(payload: AuthBootstrapRequest, db: Session = Depends(get_db)) -> AuthTokenDTO:
    """
    Create the first admin user.

    This endpoint only works while the users table is empty.
    """
    if has_users(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bootstrap is already completed",
        )
    if len(payload.password) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least 10 characters",
        )

    _, token = create_user(
        session=db,
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
        role="admin",
    )
    return AuthTokenDTO(access_token=token)


@router.post("/login", response_model=AuthTokenDTO)
def login(payload: AuthLoginRequest, db: Session = Depends(get_db)) -> AuthTokenDTO:
    """Authenticate by email/password and return a bearer token."""
    auth_result = authenticate_password(db, payload.email, payload.password)
    if auth_result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    _, token = auth_result
    return AuthTokenDTO(access_token=token)


@router.get("/me", response_model=CurrentUserDTO)
def me(current_user: User | None = Depends(get_current_user)) -> CurrentUserDTO:
    """Return the current authenticated user."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated with service token, no user profile is attached",
        )
    return _to_current_user_dto(current_user)


@router.post("/users", response_model=CreatedUserDTO, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    payload: AuthCreateUserRequest,
    current_user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CreatedUserDTO:
    """Create another user. Requires an authenticated admin user."""
    if current_user is None or current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if payload.role not in {"admin", "member", "viewer"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    if len(payload.password) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least 10 characters",
        )
    existing = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    user, token = create_user(
        session=db,
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
        role=payload.role,
    )
    return CreatedUserDTO(user=_to_current_user_dto(user), access_token=token)
