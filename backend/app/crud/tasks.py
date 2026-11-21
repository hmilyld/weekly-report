"""Task (todo) persistence."""

from datetime import UTC, date, datetime

from sqlalchemy import nullslast
from sqlalchemy.orm import Session

from .. import models
from ..encryption_utils import (
    decrypt_model_content,
    decrypt_record_content,
    encrypt_model_content,
)


def _validate_deadline(deadline: date | None) -> None:
    if deadline and deadline < date.today():
        raise ValueError("截止日期不能早于今天")


def get_tasks(db: Session, user_id: int) -> list[models.Task]:
    """All tasks for a user, ordered by deadline (nulls last), then newest first."""
    tasks = (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id)
        .order_by(nullslast(models.Task.deadline.asc()), models.Task.created_at.desc())
        .all()
    )
    for task in tasks:
        decrypt_model_content(task, user_id)
    return tasks


def get_pending_tasks(db: Session, user_id: int) -> list[models.Task]:
    """Incomplete tasks for a user."""
    tasks = (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id, models.Task.is_completed.is_(False))
        .order_by(nullslast(models.Task.deadline.asc()), models.Task.created_at.desc())
        .all()
    )
    for task in tasks:
        decrypt_model_content(task, user_id)
    return tasks


def get_completed_tasks(
    db: Session, user_id: int, offset: int = 0, limit: int = 20
) -> list[models.Task]:
    """Completed tasks for a user, newest deadline first."""
    tasks = (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id, models.Task.is_completed)
        .order_by(nullslast(models.Task.deadline.desc()), models.Task.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    for task in tasks:
        decrypt_model_content(task, user_id)
    return tasks


def get_completed_tasks_count(db: Session, user_id: int) -> int:
    return (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id, models.Task.is_completed)
        .count()
    )


def create_task(
    db: Session, user_id: int, content: str, deadline: date | None = None
) -> models.Task:
    _validate_deadline(deadline)
    task = models.Task(user_id=user_id, content="", deadline=deadline)
    encrypt_model_content(task, content, user_id)
    db.add(task)
    db.commit()
    db.refresh(task)
    decrypt_model_content(task, user_id)
    return task


def update_task(
    db: Session,
    user_id: int,
    task_id: int,
    content: str | None = None,
    deadline: date | None = None,
    is_completed: bool | None = None,
) -> models.Task | None:
    _validate_deadline(deadline)
    task = (
        db.query(models.Task)
        .filter(models.Task.id == task_id, models.Task.user_id == user_id)
        .first()
    )
    if not task:
        return None
    if content is not None:
        encrypt_model_content(task, content, user_id)
    if deadline is not None:
        task.deadline = deadline
    if is_completed is not None:
        task.is_completed = is_completed
    task.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(task)
    decrypt_model_content(task, user_id)
    return task


def delete_task(db: Session, user_id: int, task_id: int) -> bool:
    task = (
        db.query(models.Task)
        .filter(models.Task.id == task_id, models.Task.user_id == user_id)
        .first()
    )
    if task:
        db.delete(task)
        db.commit()
        return True
    return False


def get_task_decrypted(db: Session, user_id: int, task_id: int) -> str | None:
    """Return decrypted task content, or None if the task does not exist.

    Raises ContentDecryptionError when encrypted content is unreadable.
    """
    task = (
        db.query(models.Task)
        .filter(models.Task.id == task_id, models.Task.user_id == user_id)
        .first()
    )
    if not task:
        return None
    if task.content_encrypted:
        return decrypt_record_content(task, user_id)
    return task.content
