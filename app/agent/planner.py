"""
Umily — Agent Planner

Receives user command, invokes Gemini AI client, and outputs a validated ActionPlan.
Persists plan into database.
"""

from typing import Optional
from loguru import logger
from sqlalchemy.orm import Session

from app.ai.gemini_client import GeminiClient
from app.agent.schemas import ActionPlan, ActionStep
from app.database.models import TaskStatus
from app.database.repositories import TaskRepository


class AgentPlanner:
    """Decomposes user natural-language commands into structured ActionPlans."""

    def __init__(self, db: Session, gemini_client: Optional[GeminiClient] = None) -> None:
        self.db = db
        self.task_repo = TaskRepository(db)
        self.gemini = gemini_client or GeminiClient()

    def create_plan(self, task_id: int, command: str) -> ActionPlan:
        """Generate an ActionPlan for a task and persist it in the database."""
        logger.info(f"Generating plan for Task #{task_id}: {command!r}")
        self.task_repo.update_status(task_id, TaskStatus.PLANNING)

        raw_plan = self.gemini.generate_plan(command)

        # Parse and validate into ActionPlan model
        try:
            steps = [ActionStep(**s) for s in raw_plan.get("steps", [])]
            plan = ActionPlan(
                summary=raw_plan.get("summary", f"Plan for: {command}"),
                intent_type=raw_plan.get("intent_type", "COMPUTER_TASK"),
                answer=raw_plan.get("answer"),
                steps=steps,
            )
        except Exception as e:
            logger.error(f"Failed to parse plan schema: {e}. Falling back to default plan.")
            plan = ActionPlan(
                summary=f"Execution plan for: {command}",
                intent_type="COMPUTER_TASK",
                steps=[
                    ActionStep(
                        step_id=1,
                        tool="desktop",
                        action="execute_command",
                        resource_type="tool",
                        resource_name="Command Executor",
                        parameters={"command": command},
                        description=f"Process command: {command}",
                        requires_confirmation=False,
                    )
                ],
            )

        # Persist plan in task database record
        self.task_repo.update_plan(task_id, plan.model_dump())
        logger.info(f"Plan created for Task #{task_id} (intent={plan.intent_type}) with {len(plan.steps)} step(s)")
        return plan
