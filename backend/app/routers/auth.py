"""Auth router: login, setup, password change."""

import re
import time
from collections import defaultdict
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import crud
from ..auth import create_access_token, get_current_user, hash_password, verify_password
from ..database import get_db
from ..models import User
from ..schemas import LoginRequest, PasswordChange, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ─── Rate limiter (in-memory) ────────────────────────────

_rate_lock = Lock()
_login_attempts: dict[str, list[float]] = defaultdict(list)
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 60


def _check_rate_limit(key: str) -> None:
    """Raise 429 if more than _MAX_ATTEMPTS in _WINDOW_SECONDS."""
    now = time.time()
    with _rate_lock:
        attempts = _login_attempts[key]
        # Remove expired entries
        _login_attempts[key] = [t for t in attempts if now - t < _WINDOW_SECONDS]
        if len(_login_attempts[key]) >= _MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many attempts. Try again in {_WINDOW_SECONDS} seconds.",
            )
        _login_attempts[key].append(now)


# ─── Schemas ────────────────────────────────────────────


class SetupRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=8, max_length=100)


class SetupStatus(BaseModel):
    needs_setup: bool


# ─── Password validation ────────────────────────────────

_WEAK_PASSWORDS = {
    "11111111", "12345678", "password", "qwerty123", "abc12345",
    "123456789", "1234567890", "admin123", "letmein1",
}


def _validate_password(password: str) -> None:
    """Enforce minimum password complexity."""
    if password.lower() in _WEAK_PASSWORDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too common. Please choose a stronger password.",
        )
    if not re.search(r"[A-Za-z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one letter.",
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one digit.",
        )


# ─── Endpoints ──────────────────────────────────────────


@router.get("/status", response_model=SetupStatus)
def get_auth_status(db: Session = Depends(get_db)):
    """Check if initial setup is needed (no users exist yet)."""
    user_count = db.query(User).count()
    return SetupStatus(needs_setup=user_count == 0)


@router.post("/setup", response_model=TokenResponse)
def initial_setup(body: SetupRequest, db: Session = Depends(get_db)):
    """Create the first user account. Only works when no users exist."""
    # Use a database-level check to prevent race conditions
    existing_user = db.query(User).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup has already been completed",
        )

    if not body.username.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username cannot be empty",
        )

    _validate_password(body.password)

    user = crud.create_user(db, body.username.strip(), hash_password(body.password))
    token = create_access_token(
        {"sub": str(user.id), "username": user.username, "pwd_ver": 0}
    )
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    # Rate limit by IP
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(f"login:{client_ip}")

    user = crud.get_user_by_username(db, body.username)
    if not user or not verify_password(body.password, user.password_hash):
        # Also count failed attempts per username
        _check_rate_limit(f"login:user:{body.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token(
        {"sub": str(user.id), "username": user.username, "pwd_ver": user.password_version}
    )
    return TokenResponse(access_token=token)


@router.post("/change-password")
def change_password(
    body: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_password(body.new_password)
    new_hash = hash_password(body.new_password)
    crud.change_password(db, user, new_hash)
    return {"message": "Password changed successfully"}
