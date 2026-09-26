"""
Umily — Permission Manager

Enforces granular security permissions for all resource access and computer actions.
Evaluates steps against database permissions before execution.
"""

from typing import Optional
from loguru import logger
from sqlalchemy.orm import Session

from app.database.models import PermissionLevel
from app.database.repositories import PermissionRepository
from app.agent.schemas import ActionStep


class PermissionManager:
    """Evaluates security rules and permissions for agent actions."""

    def __init__(self, db: Session) -> None:
        self.repo = PermissionRepository(db)

    def evaluate_step(self, step: ActionStep) -> PermissionLevel:
        """
        Evaluate whether an action step is ALLOWED, requires ASK (user confirmation), or BLOCKED.
        """
        level = self.repo.get_level(
            resource_type=step.resource_type,
            resource_name=step.resource_name,
            action=step.action,
        )

        # Force ASK if step explicitly requires confirmation (e.g. destructive action flagged by AI)
        if level == PermissionLevel.ALLOW and step.requires_confirmation:
            level = PermissionLevel.ASK

        logger.info(
            f"Permission check: [{step.resource_type}:{step.resource_name}] "
            f"action='{step.action}' → Level={level.value}"
        )
        return level
