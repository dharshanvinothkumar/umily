"""
Umily — Voice Routes

POST /voice — placeholder for voice input handling.
Actual STT integration is Phase 12.
"""

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel

router = APIRouter(tags=["voice"])


class VoiceResponse(BaseModel):
    message: str
    status: str


@router.post("/voice", response_model=VoiceResponse)
def handle_voice():
    """
    Placeholder for voice command input.

    Phase 12+ will accept audio data and run STT.
    """
    logger.info("Voice endpoint called (not yet implemented)")
    return VoiceResponse(
        message="Voice input is not yet available. Use the /command endpoint or the Control Center.",
        status="not_implemented",
    )
