"""Auth router: login, setup, password change."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import crud
from ..auth import create_access_token, get_current_user, hash_password, verify_password
from ..database import get_db
from ..models import User
from ..schemas import LoginRequest, PasswordChange, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ─── Schemas ────────────────────────────────────────────


class SetupRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=100)


class SetupStatus(BaseModel):
    needs_setup: bool


# ─── Endpoints ──────────────────────────────────────────


@router.get("/status", response_model=SetupStatus)
def get_auth_status(db: Session = Depends(get_db)):
    """Check if initial setup is needed (no users exist yet)."""
    user_count = db.query(User).count()
    return SetupStatus(needs_setup=user_count == 0)


@router.post("/setup", response_model=TokenResponse)
def initial_setup(body: SetupRequest, db: Session = Depends(get_db)):
    """Create the first user account. Only works when no users exist."""
    user_count = db.query(User).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup has already been completed",
        )

    # Validate username
    if not body.username.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username cannot be empty",
        )

    user = crud.create_user(db, body.username.strip(), hash_password(body.password))
    token = create_access_token({"sub": str(user.id), "username": user.username})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, body.username)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token({"sub": str(user.id), "username": user.username})
    return TokenResponse(access_token=token)


@router.post("/change-password")
def change_password(
    body: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_hash = hash_password(body.new_password)
    crud.change_password(db, user, new_hash)
    return {"message": "Password changed successfully"}
