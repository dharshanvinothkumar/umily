"""
Umily — Command Schemas

Request/response models for the /command endpoint.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CommandRequest(BaseModel):
    """User-submitted natural-language command."""
    command: str = Field(..., min_length=1, max_length=2000, description="Natural-language command")


class CommandResponse(BaseModel):
    """Response after processing a command."""
    task_id: int
    message: str
    status: str
    confirmation_required: bool = False
    pending_step: Optional[Dict[str, Any]] = None
    live_steps: List[Dict[str, Any]] = []
    result: Optional[str] = None
    error: Optional[str] = None
