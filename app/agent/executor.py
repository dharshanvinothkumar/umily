"""
Umily — Agent Executor

Executes steps of an ActionPlan in order via ToolRegistry.
Integrates with PermissionManager to enforce permission checks before step execution.
Includes adaptive error recovery via ErrorRecoveryManager.
"""

from typing import List, Optional
from loguru import logger
from sqlalchemy.orm import Session

from app.agent.schemas import ActionPlan, ActionResult, ActionStep
from app.agent.error_recovery import ErrorRecoveryManager
from app.database.models import PermissionLevel, TaskStatus
from app.database.repositories import TaskRepository
from app.permissions.manager import PermissionManager
from app.tools.registry import ToolRegistry


class AgentExecutor:
    """Dispatches action steps to appropriate tools while enforcing security permissions."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.task_repo = TaskRepository(db)
        self.perm_manager = PermissionManager(db)
        self.tool_registry = ToolRegistry()
        self.recovery_manager = ErrorRecoveryManager(db)

    def execute_plan(self, task_id: int, plan: ActionPlan, start_step_idx: int = 0) -> ActionResult:
        """
        Execute steps starting from `start_step_idx`.
        Pauses if a step requires confirmation or is blocked.
        """
        task = self.task_repo.get(task_id)
        if not task:
            return ActionResult(
                success=False,
                status="failed",
                message="Task not found",
                completed_steps=0,
                total_steps=len(plan.steps),
                error="Task not found in DB",
            )

        executed_actions: List[dict] = task.actions or []
        completed_count = start_step_idx

        for idx in range(start_step_idx, len(plan.steps)):
            step = plan.steps[idx]
            logger.info(f"Processing Task #{task_id} Step {step.step_id}: {step.description}")

            # Update status to permission check
            self.task_repo.update_status(task_id, TaskStatus.PERMISSION_CHECK)

            # Evaluate permissions
            perm_level = self.perm_manager.evaluate_step(step)

            if perm_level == PermissionLevel.BLOCK:
                step.status = "blocked"
                step.error = f"Permission BLOCKED for {step.resource_type}:{step.resource_name} ({step.action})"
                executed_actions.append(step.model_dump())
                self.task_repo.update_actions(task_id, executed_actions)
                self.task_repo.update_status(
                    task_id,
                    TaskStatus.FAILED,
                    error=step.error,
                )
                logger.warning(f"Task #{task_id} step {step.step_id} BLOCKED")
                return ActionResult(
                    success=False,
                    status="failed",
                    message=f"Action blocked by permission policy: {step.description}",
                    completed_steps=completed_count,
                    total_steps=len(plan.steps),
                    error=step.error,
                )

            if perm_level == PermissionLevel.ASK:
                step.status = "waiting_confirmation"
                executed_actions.append(step.model_dump())
                self.task_repo.update_actions(task_id, executed_actions)
                self.task_repo.update_status(
                    task_id,
                    TaskStatus.WAITING_CONFIRMATION,
                    result=f"Awaiting user confirmation for: {step.description}",
                )
                logger.info(f"Task #{task_id} step {step.step_id} WAITING FOR CONFIRMATION")
                return ActionResult(
                    success=False,
                    status="waiting_confirmation",
                    message=f"Confirmation required: {step.description}",
                    completed_steps=completed_count,
                    total_steps=len(plan.steps),
                    pending_confirmation_step=step,
                )

            # Execution (ALLOW)
            self.task_repo.update_status(task_id, TaskStatus.EXECUTING)
            step_result = self._dispatch_tool_action(step)

            # Handle potential step failure with error recovery
            if not step_result.get("success", True):
                logger.warning(f"Step #{step.step_id} failed. Attempting error recovery...")
                recovery_step = self.recovery_manager.generate_recovery_step(step, step_result.get("error", "Unknown error"))
                step_result = self._dispatch_tool_action(recovery_step)

            step.status = "completed" if step_result.get("success", True) else "failed"
            step.result = step_result.get("message") or step_result.get("stdout") or "Executed successfully"
            step.error = step_result.get("error")

            executed_actions.append(step.model_dump())
            self.task_repo.update_actions(task_id, executed_actions)

            if step.status == "failed":
                self.task_repo.update_status(task_id, TaskStatus.FAILED, error=step.error)
                return ActionResult(
                    success=False,
                    status="failed",
                    message=f"Step failed: {step.description}",
                    completed_steps=completed_count,
                    total_steps=len(plan.steps),
                    error=step.error,
                )

            completed_count += 1

        # All steps completed successfully
        summary_msg = f"Task #{task_id} completed successfully ({completed_count}/{len(plan.steps)} steps)."
        self.task_repo.update_status(task_id, TaskStatus.COMPLETED, result=summary_msg)
        logger.info(summary_msg)

        return ActionResult(
            success=True,
            status="completed",
            message=summary_msg,
            completed_steps=completed_count,
            total_steps=len(plan.steps),
        )

    def resume_after_confirmation(self, task_id: int) -> ActionResult:
        """Resume execution of a task after user confirms pending action."""
        task = self.task_repo.get(task_id)
        if not task or task.status != TaskStatus.WAITING_CONFIRMATION:
            return ActionResult(
                success=False,
                status="failed",
                message="Task is not awaiting confirmation",
                completed_steps=0,
                total_steps=0,
                error="Invalid task state for resume",
            )

        plan_dict = task.plan or {}
        plan = ActionPlan(**plan_dict)
        actions = task.actions or []

        # Find index of step awaiting confirmation
        resume_idx = len(actions) - 1
        if resume_idx >= 0 and resume_idx < len(plan.steps):
            step = plan.steps[resume_idx]
            logger.info(f"Resuming task #{task_id} step {step.step_id} after confirmation")
            
            # Execute confirmed step
            self.task_repo.update_status(task_id, TaskStatus.EXECUTING)
            step_result = self._dispatch_tool_action(step)
            step.status = "completed" if step_result.get("success", True) else "failed"
            step.result = step_result.get("message") or "Executed after user confirmation"
            
            actions[-1] = step.model_dump()
            self.task_repo.update_actions(task_id, actions)

            # Continue executing remaining steps
            return self.execute_plan(task_id, plan, start_step_idx=resume_idx + 1)

        return ActionResult(
            success=False,
            status="failed",
            message="Could not locate pending step to resume",
            completed_steps=0,
            total_steps=len(plan.steps),
        )

    def _dispatch_tool_action(self, step: ActionStep) -> dict:
        """Dispatch action step via ToolRegistry."""
        logger.info(f"Dispatching tool={step.tool} action={step.action} params={step.parameters}")
        return self.tool_registry.dispatch(
            tool=step.tool,
            action=step.action,
            resource_type=step.resource_type,
            resource_name=step.resource_name,
            parameters=step.parameters,
        )
