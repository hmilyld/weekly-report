"""Task (todo) router: CRUD for work tasks."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud
from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..schemas import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all tasks for the current user."""
    return crud.get_tasks(db, user.id)


@router.get("/completed")
def list_completed_tasks(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List completed tasks with pagination."""
    tasks = crud.get_completed_tasks(db, user.id, offset, limit)
    total = crud.get_completed_tasks_count(db, user.id)
    return {
        "tasks": [
            {
                "id": t.id,
                "user_id": t.user_id,
                "content": t.content,
                "deadline": str(t.deadline) if t.deadline else None,
                "is_completed": t.is_completed,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
            }
            for t in tasks
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    body: TaskCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new task."""
    try:
        return crud.create_task(db, user.id, body.content, body.deadline)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    body: TaskUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a task."""
    try:
        task = crud.update_task(
            db, user.id, task_id, body.content, body.deadline, body.is_completed
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a task."""
    deleted = crud.delete_task(db, user.id, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Deleted"}
