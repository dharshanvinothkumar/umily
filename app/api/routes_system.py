"""
Umily — System Routes

GET /status — returns current system status, assistant state, and health information.
"""

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel

from app.config import settings

router = APIRouter(tags=["system"])


class SystemStatus(BaseModel):
    """Current system health and assistant state."""
    app_name: str
    version: str
    status: str
    assistant_state: str
    gemini_configured: bool
    voice_available: bool


@router.get("/status", response_model=SystemStatus)
def get_status():
    """Return current system status and health."""
    logger.debug("Status endpoint called")

    gemini_configured = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here")

    return SystemStatus(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        status="running",
        assistant_state="idle",          # Phase 15+ will read from background service
        gemini_configured=gemini_configured,
        voice_available=False,           # Phase 12+ enables this
    )
