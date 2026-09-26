"""
Umily — Error Recovery Manager

Analyzes step execution failures and dynamically formulates adaptive recovery plans.
"""

from typing import Optional
from loguru import logger
from sqlalchemy.orm import Session

from app.agent.schemas import ActionPlan, ActionStep
from app.ai.gemini_client import GeminiClient


class ErrorRecoveryManager:
    """Manages failure feedback loops and adaptive plan repairs."""

    def __init__(self, db: Session, gemini_client: Optional[GeminiClient] = None) -> None:
        self.db = db
        self.gemini = gemini_client or GeminiClient()

    def generate_recovery_step(self, step: ActionStep, error: str) -> ActionStep:
        """Formulate a corrective action step after a failure occurs."""
        logger.info(f"Generating error recovery for Step #{step.step_id} failed with error: {error}")

        # If browser navigation failed, fallback to system search or desktop notify
        if step.tool == "browser":
            return ActionStep(
                step_id=step.step_id,
                tool="desktop",
                action="execute_command",
                resource_type="tool",
                resource_name="Fallback Command",
                parameters={"command": f"start {step.parameters.get('url', 'https://google.com')}"},
                description=f"Fallback recovery: open URL via OS shell after browser error: {error}",
                requires_confirmation=False,
            )
        elif step.tool == "filesystem":
            return ActionStep(
                step_id=step.step_id,
                tool="desktop",
                action="notify",
                resource_type="tool",
                resource_name="Filesystem Alert",
                parameters={"title": "File Error", "message": f"File operation failed: {error}"},
                description=f"Notify user of filesystem error: {error}",
                requires_confirmation=False,
            )
        else:
            return ActionStep(
                step_id=step.step_id,
                tool="desktop",
                action="notify",
                resource_type="tool",
                resource_name="System Recovery",
                parameters={"title": "Task Error", "message": f"Step #{step.step_id} failed: {error}"},
                description=f"Log and notify error: {error}",
                requires_confirmation=False,
            )
