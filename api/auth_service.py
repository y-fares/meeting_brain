"""
User authentication helpers.

Uses standard-library PBKDF2 password hashing and bearer tokens stored as
SHA-256 hashes so no plaintext credentials are persisted.
"""

import hashlib
import hmac
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from database import User

PASSWORD_ITERATIONS = 260_000


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a stored PBKDF2 hash."""
    try:
        algorithm, iterations_raw, salt, expected = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations_raw),
        ).hex()
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


def hash_token(token: str) -> str:
    """Hash an API token before storing or comparing it."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_api_token() -> str:
    """Generate a bearer token suitable for API use."""
    return secrets.token_urlsafe(32)


def has_users(session: Session) -> bool:
    """Return True when at least one user exists."""
    return session.query(User.id).first() is not None


def create_user(
    session: Session,
    email: str,
    password: str,
    display_name: Optional[str] = None,
    role: str = "member",
) -> tuple[User, str]:
    """
    Create a user and return the plaintext token once.

    The caller is responsible for returning or displaying the token because only
    its hash is stored.
    """
    token = generate_api_token()
    user = User(
        email=_normalize_email(email),
        display_name=(display_name or "").strip() or None,
        role=role,
        password_hash=hash_password(password),
        api_token_hash=hash_token(token),
        created_at=datetime.utcnow(),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user, token


def authenticate_password(session: Session, email: str, password: str) -> Optional[tuple[User, str]]:
    """Authenticate a user by password and rotate their API token."""
    user = (
        session.query(User)
        .filter(User.email == _normalize_email(email), User.disabled_at.is_(None))
        .first()
    )
    if not user or not verify_password(password, user.password_hash):
        return None

    token = generate_api_token()
    user.api_token_hash = hash_token(token)
    session.commit()
    session.refresh(user)
    return user, token


def get_user_by_token(session: Session, token: str) -> Optional[User]:
    """Find an active user by bearer token."""
    if not token:
        return None
    return (
        session.query(User)
        .filter(User.api_token_hash == hash_token(token), User.disabled_at.is_(None))
        .first()
    )
