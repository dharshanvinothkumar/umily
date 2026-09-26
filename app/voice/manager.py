"""
Umily — Voice Manager

Orchestrates Voice pipeline: STT Audio Transcription -> Agent Command Processing -> TTS Audio Synthesis.
"""

from typing import Dict, Any, Optional
from loguru import logger
from sqlalchemy.orm import Session

from app.voice.stt import STTEngine
from app.voice.tts import TTSEngine
from app.voice.wakeword import WakeWordDetector
from app.agent.planner import AgentPlanner
from app.agent.executor import AgentExecutor
from app.database.repositories import TaskRepository

class VoiceManager:
    """Voice manager tying together STT, Agent Execution, and TTS."""

    def __init__(self, stt_model: str = "tiny", tts_voice: str = "en-US-AriaNeural"):
        self.stt = STTEngine(model_size=stt_model)
        self.tts = TTSEngine(voice=tts_voice)
        self.wakeword = WakeWordDetector()

    def process_voice_audio(self, db: Session, audio_bytes: bytes, filename: str = "command.wav") -> Dict[str, Any]:
        """Process incoming voice audio and execute user command synchronously."""
        # 1. Transcribe audio to text
        transcript = self.stt.transcribe_bytes(audio_bytes, filename=filename)
        if not transcript:
            return {
                "transcript": "",
                "message": "Could not recognize audio input.",
                "status": "failed",
                "audio_response": None
            }

        logger.info(f"[Voice Manager] Transcribed text: {transcript!r}")

        # 2. Execute command using Agent
        repo = TaskRepository(db)
        task = repo.create(command=f"[Voice] {transcript}")

        planner = AgentPlanner(db)
        plan = planner.create_plan(task.id, transcript)

        executor = AgentExecutor(db)
        result = executor.execute_plan(task.id, plan)

        updated_task = repo.get(task.id)
        final_status = updated_task.status if updated_task else result.status
        response_text = result.message or f"Task execution finished with status {final_status}"

        # 3. Synthesize speech for response
        audio_output = self.tts.synthesize(response_text)

        return {
            "task_id": task.id,
            "transcript": transcript,
            "message": response_text,
            "status": final_status,
            "audio_response": audio_output,
        }

    async def process_voice_audio_async(self, db: Session, audio_bytes: bytes, filename: str = "command.wav") -> Dict[str, Any]:
        """Process incoming voice audio asynchronously."""
        transcript = self.stt.transcribe_bytes(audio_bytes, filename=filename)
        if not transcript:
            return {
                "transcript": "",
                "message": "Could not recognize audio input.",
                "status": "failed",
                "audio_response": None
            }

        logger.info(f"[Voice Manager] Transcribed text: {transcript!r}")

        repo = TaskRepository(db)
        task = repo.create(command=f"[Voice] {transcript}")

        planner = AgentPlanner(db)
        plan = planner.create_plan(task.id, transcript)

        executor = AgentExecutor(db)
        result = executor.execute_plan(task.id, plan)

        updated_task = repo.get(task.id)
        final_status = updated_task.status if updated_task else result.status
        response_text = result.message or f"Task execution finished with status {final_status}"

        audio_output = await self.tts.synthesize_async(response_text)

        return {
            "task_id": task.id,
            "transcript": transcript,
            "message": response_text,
            "status": final_status,
            "audio_response": audio_output,
        }
