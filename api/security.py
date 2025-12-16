"""
API authentication and security utilities.
"""

import os
import logging
from fastapi import Request, HTTPException, status

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
    
    # Production mode: require token
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )
    
    provided_token = auth_header[7:].strip()  # Remove "Bearer " prefix
    
    if provided_token != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )

