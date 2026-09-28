"""
Umily — Command Routes

POST /command — accepts a natural-language command, creates a task, plans actions via Gemini,
and executes steps with permission checks.
"""

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy.orm import Session

from app.agent.executor import AgentExecutor
from app.agent.planner import AgentPlanner
from app.database.database import get_db
from app.database.repositories import TaskRepository
from app.schemas.commands import CommandRequest, CommandResponse
from app.schemas.tasks import TaskResponse

router = APIRouter(tags=["commands"])


@router.post("/command", response_model=CommandResponse)
def handle_command(body: CommandRequest, db: Session = Depends(get_db)):
    """
    Accept a natural-language command from the user.
    Routes command through Agent Planner (Gemini) → Permission Manager → Agent Executor.
    """
    logger.info(f"Received command: {body.command!r}")

    repo = TaskRepository(db)
    task = repo.create(command=body.command)

    # 1. Plan actions via Gemini AI
    planner = AgentPlanner(db)
    plan = planner.create_plan(task.id, body.command)

    # 2. Execute plan with permission enforcement
    executor = AgentExecutor(db)
    exec_result = executor.execute_plan(task.id, plan)

    # Get latest updated task and convert to TaskResponse for live steps extraction
    updated_task = repo.get(task.id)
    t_resp = TaskResponse.model_validate(updated_task) if updated_task else None

    status_str = t_resp.status if t_resp else exec_result.status

    if t_resp and t_resp.confirmation_required:
        logger.info(f"[CONFIRMATION] Task #{task.id} requires user confirmation. Exposing request to client.")

    logger.info(f"Task #{task.id} finished step processing — status={status_str}")

    return CommandResponse(
        task_id=task.id,
        message=t_resp.result or exec_result.message if t_resp else exec_result.message,
        status=status_str,
        confirmation_required=t_resp.confirmation_required if t_resp else (status_str == "waiting_confirmation"),
        pending_step=t_resp.pending_step if t_resp else None,
        live_steps=t_resp.live_steps if t_resp else [],
        result=t_resp.result if t_resp else None,
        error=t_resp.error if t_resp else None,
    )
