"""
Umily — Voice Routes

Endpoints for STT transcription, TTS synthesis, and end-to-end voice command execution.
"""

from typing import Optional
from fastapi import APIRouter, Depends, File, UploadFile, Response, Form
from fastapi.responses import Response
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.voice.manager import VoiceManager
from app.voice.stt import STTEngine
from app.voice.tts import TTSEngine

router = APIRouter(tags=["voice"])

voice_manager = VoiceManager()
stt_engine = STTEngine()
tts_engine = TTSEngine()


class VoiceCommandResponse(BaseModel):
    task_id: Optional[int] = None
    transcript: str
    message: str
    status: str
    has_audio: bool = False


class TranscribeResponse(BaseModel):
    transcript: str


class SynthesizeRequest(BaseModel):
    text: str


@router.post("/voice", response_model=VoiceCommandResponse)
async def handle_voice_command(
    file: Optional[UploadFile] = File(None),
    text_fallback: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Handle voice command input.
    Accepts an audio file upload or text payload, transcribes it, runs the command, and returns the result.
    """
    logger.info("Voice command endpoint triggered.")

    audio_bytes = b""
    filename = "input.wav"
    if file:
        audio_bytes = await file.read()
        filename = file.filename or "input.wav"
    elif text_fallback:
        audio_bytes = text_fallback.encode("utf-8")

    result = await voice_manager.process_voice_audio_async(db, audio_bytes, filename=filename)

    return VoiceCommandResponse(
        task_id=result.get("task_id"),
        transcript=result.get("transcript", ""),
        message=result.get("message", ""),
        status=result.get("status", "completed"),
        has_audio=bool(result.get("audio_response")),
    )


@router.post("/voice/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe uploaded audio file to text."""
    audio_bytes = await file.read()
    transcript = stt_engine.transcribe_bytes(audio_bytes, filename=file.filename or "audio.wav")
    return TranscribeResponse(transcript=transcript)


@router.post("/voice/synthesize")
async def synthesize_speech(req: SynthesizeRequest):
    """Synthesize text into audio response (audio/wav or audio/mpeg)."""
    audio_bytes = await tts_engine.synthesize_async(req.text)
    return Response(content=audio_bytes, media_type="audio/wav")
