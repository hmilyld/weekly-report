"""User management router — admin only (except /me)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud
from ..auth import get_current_user, hash_password, require_admin, validate_password
from ..database import get_db
from ..models import User
from ..schemas import ChangeRoleRequest, UserCreate, UserListResponse, UserResponse

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    """Get current user info."""
    return user


@router.get("", response_model=UserListResponse)
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all users (admin only)."""
    users = crud.get_all_users(db)
    return UserListResponse(users=[UserResponse.model_validate(u) for u in users])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new user (admin only)."""
    existing = crud.get_user_by_username(db, body.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )
    validate_password(body.password)
    pwd_hash = hash_password(body.password)
    user = crud.create_user(db, body.username, pwd_hash, role=body.role)
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a user (admin only, cannot delete self)."""
    if admin.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )
    if not crud.delete_user(db, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


@router.put("/{user_id}/role", response_model=UserResponse)
def update_role(
    user_id: int,
    body: ChangeRoleRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update a user's role (admin only)."""
    if admin.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )
    # Prevent demoting the last admin
    if body.role != "admin":
        admin_count = db.query(User).filter(User.role == "admin").count()
        target_user = db.query(User).filter(User.id == user_id).first()
        if target_user and target_user.role == "admin" and admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last admin",
            )
    user = crud.update_user_role(db, user_id, body.role)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse.model_validate(user)
