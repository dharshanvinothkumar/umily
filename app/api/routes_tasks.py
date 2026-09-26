"""
Umily — Task Routes

GET /tasks        — list recent tasks
GET /tasks/{id}   — get a specific task
POST /confirm     — confirm a pending action and resume execution
POST /cancel      — cancel a task
"""

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.orm import Session

from app.agent.executor import AgentExecutor
from app.database.database import get_db
from app.database.models import TaskStatus
from app.database.repositories import TaskRepository
from app.schemas.tasks import TaskListResponse, TaskResponse

router = APIRouter(tags=["tasks"])


@router.get("/tasks", response_model=TaskListResponse)
def list_tasks(limit: int = 50, db: Session = Depends(get_db)):
    """Return the most recent tasks."""
    repo = TaskRepository(db)
    tasks = repo.list_all(limit=limit)
    return TaskListResponse(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        count=len(tasks),
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Return details for a single task."""
    repo = TaskRepository(db)
    task = repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.post("/confirm")
def confirm_action(task_id: int, db: Session = Depends(get_db)):
    """Confirm a pending consequential action and resume agent execution."""
    logger.info(f"[USER] Confirmation = APPROVE for Task #{task_id}")
    logger.info(f"[API] Confirmation received for Task #{task_id}")
    repo = TaskRepository(db)
    task = repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != TaskStatus.WAITING_CONFIRMATION:
        raise HTTPException(status_code=400, detail="Task is not awaiting confirmation")

    logger.info(f"[AGENT] Resuming task {task_id}")
    executor = AgentExecutor(db)
    exec_result = executor.resume_after_confirmation(task_id)

    updated_task = repo.get(task_id)
    status_str = updated_task.status.value if updated_task else exec_result.status

    return {
        "task_id": task_id,
        "message": f"Task #{task_id} confirmed and resumed.",
        "status": status_str,
        "detail": exec_result.message,
    }


@router.post("/cancel")
def cancel_task(task_id: int, db: Session = Depends(get_db)):
    """Cancel an active or pending task."""
    logger.info(f"[USER] Confirmation = DENY for Task #{task_id}")
    logger.info(f"[AGENT] Cancelling task {task_id}")
    repo = TaskRepository(db)
    task = repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    repo.update_status(task_id, TaskStatus.CANCELLED)
    return {"task_id": task_id, "message": f"Task #{task_id} cancelled.", "status": "cancelled"}
