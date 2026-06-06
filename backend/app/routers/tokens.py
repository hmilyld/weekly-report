"""Token management router (JWT protected)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..models_token import ApiToken, generate_api_token

router = APIRouter(prefix="/api/v1/tokens", tags=["tokens"])


# ─── Schemas ────────────────────────────────────────────


class TokenCreate(BaseModel):
    name: str = Field(default="default", max_length=100)


class TokenResponse(BaseModel):
    id: int
    name: str
    token: str | None = None  # Only returned on creation
    created_at: datetime
    last_used_at: datetime | None = None

    model_config = {"from_attributes": True}


class TokenCreatedResponse(BaseModel):
    id: int
    name: str
    token: str  # Full token, only shown once
    created_at: datetime


# ─── Endpoints ──────────────────────────────────────────


@router.get("", response_model=list[TokenResponse])
def list_tokens(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all API tokens (token value hidden)."""
    tokens = (
        db.query(ApiToken)
        .filter(ApiToken.user_id == user.id)
        .order_by(ApiToken.created_at.desc())
        .all()
    )
    result = []
    for t in tokens:
        result.append(
            TokenResponse(
                id=t.id,
                name=t.name,
                token=None,  # Hide token value in list
                created_at=t.created_at,
                last_used_at=t.last_used_at,
            )
        )
    return result


@router.post("", response_model=TokenCreatedResponse)
def create_token(
    body: TokenCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new API token. The token is only shown once."""
    token_value = generate_api_token()
    api_token = ApiToken(
        user_id=user.id,
        name=body.name,
        token=token_value,
    )
    db.add(api_token)
    db.commit()
    db.refresh(api_token)
    return TokenCreatedResponse(
        id=api_token.id,
        name=api_token.name,
        token=token_value,
        created_at=api_token.created_at,
    )


@router.delete("/{token_id}")
def delete_token(
    token_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an API token."""
    token = (
        db.query(ApiToken)
        .filter(
            ApiToken.id == token_id,
            ApiToken.user_id == user.id,
        )
        .first()
    )
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    db.delete(token)
    db.commit()
    return {"message": "Token deleted"}
