"""
Umily — Database Repositories

Data-access layer encapsulating all direct database queries.
Routes and services call repositories instead of touching sessions directly.
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.database.models import Permission, PermissionLevel, Setting, Task, TaskStatus


# ---------------------------------------------------------------------------
# Task Repository
# ---------------------------------------------------------------------------

class TaskRepository:
    """CRUD operations for Task records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, command: str) -> Task:
        task = Task(command=command, status=TaskStatus.PENDING)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get(self, task_id: int) -> Optional[Task]:
        return self.db.query(Task).filter(Task.id == task_id).first()

    def list_all(self, limit: int = 50) -> List[Task]:
        return (
            self.db.query(Task)
            .order_by(Task.created_at.desc())
            .limit(limit)
            .all()
        )

    def update_status(
        self,
        task_id: int,
        status: TaskStatus,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Optional[Task]:
        task = self.get(task_id)
        if task is None:
            return None
        task.status = status
        if result is not None:
            task.result = result
        if error is not None:
            task.error = error
        task.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        return task

    def update_plan(self, task_id: int, plan: dict) -> Optional[Task]:
        task = self.get(task_id)
        if task is None:
            return None
        task.plan = plan
        task.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        return task

    def update_actions(self, task_id: int, actions: list) -> Optional[Task]:
        task = self.get(task_id)
        if task is None:
            return None
        task.actions = actions
        task.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        return task


# ---------------------------------------------------------------------------
# Permission Repository
# ---------------------------------------------------------------------------

class PermissionRepository:
    """CRUD operations for Permission records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_level(
        self,
        resource_type: str,
        resource_name: str,
        action: str,
    ) -> PermissionLevel:
        """Return the permission level, defaulting to ASK if not configured."""
        perm = (
            self.db.query(Permission)
            .filter(
                Permission.resource_type == resource_type,
                Permission.resource_name == resource_name,
                Permission.action == action,
            )
            .first()
        )
        return perm.level if perm else PermissionLevel.ASK

    def set_permission(
        self,
        resource_type: str,
        resource_name: str,
        action: str,
        level: PermissionLevel,
    ) -> Permission:
        """Create or update a permission entry."""
        perm = (
            self.db.query(Permission)
            .filter(
                Permission.resource_type == resource_type,
                Permission.resource_name == resource_name,
                Permission.action == action,
            )
            .first()
        )
        if perm:
            perm.level = level
            perm.updated_at = datetime.now(timezone.utc)
        else:
            perm = Permission(
                resource_type=resource_type,
                resource_name=resource_name,
                action=action,
                level=level,
            )
            self.db.add(perm)
        self.db.commit()
        self.db.refresh(perm)
        return perm

    def list_all(self) -> List[Permission]:
        return self.db.query(Permission).order_by(Permission.resource_type).all()


# ---------------------------------------------------------------------------
# Settings Repository
# ---------------------------------------------------------------------------

class SettingsRepository:
    """CRUD operations for application settings."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        setting = self.db.query(Setting).filter(Setting.key == key).first()
        return setting.value if setting else default

    def set(self, key: str, value: str) -> Setting:
        setting = self.db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.now(timezone.utc)
        else:
            setting = Setting(key=key, value=value)
            self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def list_all(self) -> List[Setting]:
        return self.db.query(Setting).all()
