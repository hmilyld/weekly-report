"""Token management router (JWT protected)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import ApiToken, User, generate_api_token
from ..schemas import (
    ApiTokenCreate,
    ApiTokenCreatedResponse,
    ApiTokenResponse,
    ApiTokenRevokeResponse,
    MessageResponse,
)

router = APIRouter(prefix="/api/v1/tokens", tags=["tokens"])


@router.get("", response_model=list[ApiTokenResponse])
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
    return [
        ApiTokenResponse(
            id=token.id,
            name=token.name,
            token=None,
            created_at=token.created_at,
            last_used_at=token.last_used_at,
        )
        for token in tokens
    ]


@router.post("", response_model=ApiTokenCreatedResponse)
def create_token(
    body: ApiTokenCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new API token. The token is only shown once."""
    token_value = generate_api_token()
    api_token = ApiToken(user_id=user.id, name=body.name, token=token_value)
    db.add(api_token)
    db.commit()
    db.refresh(api_token)
    return ApiTokenCreatedResponse(
        id=api_token.id,
        name=api_token.name,
        token=token_value,
        created_at=api_token.created_at,
    )


@router.delete("", response_model=ApiTokenRevokeResponse)
def revoke_all_tokens(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke every API token of the current user.

    API tokens are independent of the login password, so changing the password
    does not invalidate them. This is the explicit "sign out my scripts and
    other devices" action.
    """
    revoked = (
        db.query(ApiToken).filter(ApiToken.user_id == user.id).delete(synchronize_session=False)
    )
    db.commit()
    return {"revoked": revoked}


@router.delete("/{token_id}", response_model=MessageResponse)
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
