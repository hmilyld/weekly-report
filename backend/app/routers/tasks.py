"""Task (todo) router: CRUD for work tasks."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud
from ..auth import get_authenticated_user
from ..database import get_db
from ..models import User
from ..schemas import (
    CompletedTaskListResponse,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def _list_response(tasks: list) -> TaskListResponse:
    return TaskListResponse(
        tasks=tasks,
        decryption_failed=any(getattr(task, "_decryption_failed", False) for task in tasks),
    )


@router.get("", response_model=TaskListResponse)
def list_tasks(
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """List all tasks for the current user."""
    return _list_response(crud.get_tasks(db, user.id))


@router.get("/completed", response_model=CompletedTaskListResponse)
def list_completed_tasks(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """List completed tasks with pagination."""
    tasks = crud.get_completed_tasks(db, user.id, offset, limit)
    return CompletedTaskListResponse(
        tasks=tasks,
        decryption_failed=any(getattr(task, "_decryption_failed", False) for task in tasks),
        total=crud.get_completed_tasks_count(db, user.id),
        offset=offset,
        limit=limit,
    )


@router.get("/pending", response_model=TaskListResponse)
def list_pending_tasks(
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """List incomplete tasks (canonical equivalent of the old /external/tasks/pending)."""
    return _list_response(crud.get_pending_tasks(db, user.id))


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    body: TaskCreate,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """Create a new task."""
    return crud.create_task(db, user.id, body.content, body.deadline)


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    body: TaskUpdate,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """Update a task."""
    task = crud.update_task(db, user.id, task_id, body.content, body.deadline, body.is_completed)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """Delete a task."""
    if not crud.delete_task(db, user.id, task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Deleted"}
