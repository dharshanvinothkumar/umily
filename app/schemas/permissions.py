"""
Umily — Permission Schemas

Request/response models for the permission endpoints.
"""

from typing import List

from pydantic import BaseModel, Field


class PermissionRequest(BaseModel):
    """Request to set a permission."""
    resource_type: str = Field(..., description="website | application | filesystem | tool")
    resource_name: str = Field(..., description="Name or path of the resource")
    action: str = Field(..., description="The action, e.g. read, write, submit")
    level: str = Field(..., description="allow | ask | block")


class PermissionResponse(BaseModel):
    """Serialized permission entry."""
    id: int
    resource_type: str
    resource_name: str
    action: str
    level: str

    model_config = {"from_attributes": True}


class PermissionListResponse(BaseModel):
    """Wrapper for a list of permissions."""
    permissions: List[PermissionResponse]
    count: int
