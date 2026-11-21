"""User persistence."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from .. import models
from ..key_cache import key_cache


def get_user_by_username(db: Session, username: str) -> models.User | None:
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, username: str, password_hash: str, role: str = "user") -> models.User:
    user = models.User(username=username, password_hash=password_hash, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: models.User, new_hash: str) -> None:
    """Replace the password hash and invalidate every token minted before now."""
    user.password_hash = new_hash
    user.password_version = (user.password_version or 0) + 1
    db.commit()


def touch_last_login(db: Session, user: models.User) -> None:
    """Record a successful sign-in."""
    user.last_login_at = datetime.now(UTC)
    db.commit()


def get_all_users(db: Session) -> list[models.User]:
    return db.query(models.User).order_by(models.User.id).all()


def delete_user(db: Session, user_id: int) -> bool:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return False
    db.query(models.DailyReport).filter(models.DailyReport.user_id == user_id).delete()
    db.query(models.WeeklyReport).filter(models.WeeklyReport.user_id == user_id).delete()
    db.query(models.MonthlyReport).filter(models.MonthlyReport.user_id == user_id).delete()
    db.query(models.Task).filter(models.Task.user_id == user_id).delete()
    db.query(models.ApiToken).filter(models.ApiToken.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    # Drop the cached DEK too: SQLite reuses the highest rowid, so a later user
    # could otherwise inherit a stale key entry for this id.
    key_cache.remove(user_id)
    return True


def update_user_role(db: Session, user_id: int, role: str) -> models.User | None:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    user.role = role
    db.commit()
    db.refresh(user)
    return user
