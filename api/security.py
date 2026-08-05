"""
API authentication and security utilities.
"""

import os
import logging
from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from api.auth_service import get_user_by_token
from api.deps import get_db
from database import User

LOGGER = logging.getLogger(__name__)


def get_auth_token() -> str | None:
    """
    Read API_AUTH_TOKEN from environment.
    
    Returns:
        Token string if set, None otherwise
    """
    token = os.getenv("API_AUTH_TOKEN")
    if token and token.strip():
        return token.strip()
    return None


def auth_requires_login() -> bool:
    """
    Return True when per-user login is required.

    Dev remains permissive by default for backward compatibility. Set
    AUTH_REQUIRE_LOGIN=true in deployed environments.
    """
    value = os.getenv("AUTH_REQUIRE_LOGIN", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _extract_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header[7:].strip()


def require_auth(request: Request) -> None:
    """
    Require Bearer token authentication for API endpoints.
    
    If API_AUTH_TOKEN is not set, allows requests (dev mode).
    If set, requires Authorization: Bearer <token> header.
    
    Args:
        request: FastAPI request object
    
    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    token = get_auth_token()
    
    # Dev mode: no token required
    if token is None:
        return
    
    provided_token = _extract_bearer_token(request)

    if not provided_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )

    if provided_token != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    """
    Authenticate a request and return the current user.

    Supports the legacy API_AUTH_TOKEN as a service token. When used, no user is
    attached and the dependency returns None.
    """
    global_token = get_auth_token()
    provided_token = _extract_bearer_token(request)

    if global_token:
        if provided_token and provided_token == global_token:
            return None
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    if not auth_requires_login():
        return None

    if not provided_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    user = get_user_by_token(db, provided_token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user


def require_configured_auth(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    """
    Route dependency for protected API endpoints.

    Backward-compatible behavior:
    - API_AUTH_TOKEN set: require that service token.
    - AUTH_REQUIRE_LOGIN=true: require a user token.
    - otherwise: allow dev access.
    """
    if get_auth_token():
        return get_current_user(request, db)
    if auth_requires_login():
        return get_current_user(request, db)
    return None

