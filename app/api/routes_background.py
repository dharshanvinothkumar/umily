"""
Umily — Background Daemon API Routes

Endpoints to view status, start, stop, and schedule background daemon tasks.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, Optional

from app.background.daemon import BackgroundDaemon

router = APIRouter(tags=["background"])

daemon_service = BackgroundDaemon()
daemon_service.start()


class ScheduleTaskRequest(BaseModel):
    command: str
    interval_sec: float = 60.0


class BackgroundStatusResponse(BaseModel):
    status: Dict[str, Any]


@router.get("/background/status", response_model=BackgroundStatusResponse)
def get_background_status():
    """Get current status of background daemon."""
    return BackgroundStatusResponse(status=daemon_service.get_status())


@router.post("/background/start")
def start_background_daemon():
    """Start background daemon."""
    daemon_service.start()
    return {"message": "Background daemon started", "status": daemon_service.get_status()}


@router.post("/background/stop")
def stop_background_daemon():
    """Stop background daemon."""
    daemon_service.stop()
    return {"message": "Background daemon stopped", "status": daemon_service.get_status()}


@router.post("/background/schedule")
def schedule_background_task(req: ScheduleTaskRequest):
    """Schedule a recurring background task."""
    task_id = daemon_service.schedule_task(req.command, req.interval_sec)
    return {"message": "Task scheduled", "task_id": task_id}
