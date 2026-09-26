"""
Umily — Task Schemas

Request/response models for task-related endpoints, exposing structured confirmation details and live activity steps.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, model_validator


class TaskResponse(BaseModel):
    """Serialized view of a task record, including explicit confirmation payload and live step progress."""
    id: int
    command: str
    status: str
    plan: Optional[Dict[str, Any]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    result: Optional[str] = None
    error: Optional[str] = None
    confirmation_required: bool = False
    pending_step: Optional[Dict[str, Any]] = None
    live_steps: List[Dict[str, Any]] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def populate_confirmation_and_live_steps(self) -> "TaskResponse":
        """Compute confirmation_required, pending_step, and unified live_steps progress array."""
        is_waiting = (self.status == "waiting_confirmation")
        self.confirmation_required = is_waiting

        actions_by_id = {}
        if self.actions:
            for action in self.actions:
                if isinstance(action, dict) and "step_id" in action:
                    actions_by_id[action["step_id"]] = action
                    if is_waiting and action.get("status") == "waiting_confirmation":
                        self.pending_step = action

        live = []
        plan_steps = (self.plan or {}).get("steps", [])
        
        for idx, step_dict in enumerate(plan_steps):
            sid = step_dict.get("step_id", idx + 1)
            if sid in actions_by_id:
                live.append(actions_by_id[sid])
            else:
                step_copy = dict(step_dict)
                # If earlier steps are done and task is executing, mark current step as executing
                if self.status in ["executing", "permission_check"] and idx == len(actions_by_id):
                    step_copy["status"] = "executing"
                else:
                    step_copy["status"] = "pending"
                live.append(step_copy)

        self.live_steps = live
        return self


class TaskListResponse(BaseModel):
    """Wrapper for a list of tasks."""
    tasks: List[TaskResponse]
    count: int
