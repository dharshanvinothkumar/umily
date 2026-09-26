"""
Umily — Database Models

SQLAlchemy ORM models for tasks, permissions, and settings.
These define the schema for the SQLite database.
"""

import enum

from sqlalchemy import Column, DateTime, Enum as SQLEnum, Integer, JSON, String, Text
from sqlalchemy.sql import func

from app.database.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TaskStatus(str, enum.Enum):
    """Lifecycle states for a task."""
    PENDING = "pending"
    PLANNING = "planning"
    PERMISSION_CHECK = "permission_check"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    WAITING_CONFIRMATION = "waiting_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PermissionLevel(str, enum.Enum):
    """Access level for a resource/action pair."""
    ALLOW = "allow"
    ASK = "ask"
    BLOCK = "block"


class AssistantState(str, enum.Enum):
    """Background assistant operational states."""
    IDLE = "idle"
    LISTENING_FOR_WAKE_WORD = "listening_for_wake_word"
    WAKE_DETECTED = "wake_detected"
    LISTENING_FOR_COMMAND = "listening_for_command"
    PROCESSING = "processing"
    PERMISSION_CHECK = "permission_check"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    RESPONDING = "responding"


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

class Task(Base):
    """Record of a single user-requested task."""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    command = Column(Text, nullable=False)
    status = Column(
        SQLEnum(TaskStatus),
        default=TaskStatus.PENDING,
        nullable=False,
    )
    plan = Column(JSON, nullable=True)
    actions = Column(JSON, nullable=True)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} status={self.status}>"


class Permission(Base):
    """Granular permission for a resource + action pair."""
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    resource_type = Column(String(50), nullable=False)   # website | application | filesystem | tool
    resource_name = Column(String(255), nullable=False)   # e.g. "LeetCode", "VS Code", "Projects/"
    action = Column(String(50), nullable=False)           # e.g. "read", "write", "submit", "push"
    level = Column(
        SQLEnum(PermissionLevel),
        default=PermissionLevel.ASK,
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Permission {self.resource_type}:{self.resource_name} {self.action}={self.level}>"


class Setting(Base):
    """Key-value application settings persisted in the database."""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Setting {self.key}={self.value!r}>"
