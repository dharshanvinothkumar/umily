"""
Umily — Permission Routes

GET  /permissions      — list all configured permissions
POST /permissions      — create or update a permission
"""

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import PermissionLevel
from app.database.repositories import PermissionRepository
from app.schemas.permissions import (
    PermissionListResponse,
    PermissionRequest,
    PermissionResponse,
)

router = APIRouter(tags=["permissions"])


@router.get("/permissions", response_model=PermissionListResponse)
def list_permissions(db: Session = Depends(get_db)):
    """Return all configured permissions."""
    repo = PermissionRepository(db)
    perms = repo.list_all()
    return PermissionListResponse(
        permissions=[
            PermissionResponse(
                id=p.id,
                resource_type=p.resource_type,
                resource_name=p.resource_name,
                action=p.action,
                level=p.level.value,
            )
            for p in perms
        ],
        count=len(perms),
    )


@router.post("/permissions", response_model=PermissionResponse)
def set_permission(body: PermissionRequest, db: Session = Depends(get_db)):
    """Create or update a permission entry."""
    logger.info(
        f"Setting permission: {body.resource_type}/{body.resource_name} "
        f"{body.action} → {body.level}"
    )
    repo = PermissionRepository(db)
    try:
        level = PermissionLevel(body.level)
    except ValueError:
        level = PermissionLevel.ASK

    perm = repo.set_permission(
        resource_type=body.resource_type,
        resource_name=body.resource_name,
        action=body.action,
        level=level,
    )
    return PermissionResponse(
        id=perm.id,
        resource_type=perm.resource_type,
        resource_name=perm.resource_name,
        action=perm.action,
        level=perm.level.value,
    )
