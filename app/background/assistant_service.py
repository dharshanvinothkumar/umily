"""
Umily — Background Voice Assistant Service

Runs independently of the web frontend as an always-available Windows AI Assistant.
- Automatically starts with Windows (no admin rights required)
- Waits silently for wake word ("Hey Umily") using real-time microphone stream
- Displays floating status overlay popup
- Handles dual intent: General Knowledge Questions (no computer permission required) vs Computer Tasks
- Remembers granted permissions so subsequent identical actions execute directly
- Supports conversational follow-up without repeating wake word during active session
- Supports stop/cancel interrupts ("stop", "cancel", "never mind", "umily stop")
"""

import sys
from pathlib import Path

# Ensure root workspace directory is in sys.path when executed directly
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import time
import threading
from typing import Optional, Dict, Any, List
from loguru import logger
from sqlalchemy.orm import Session

from app.database.database import SessionLocal

from app.database.models import TaskStatus, PermissionLevel
from app.database.repositories import TaskRepository, PermissionRepository
from app.agent.planner import AgentPlanner
from app.agent.executor import AgentExecutor
from app.background.popup import FloatingOverlayPopup
from app.background.startup import WindowsStartupManager
from app.voice.stt import STTEngine
from app.voice.tts import TTSEngine
from app.voice.wakeword import WakeWordDetector


class BackgroundVoiceAssistant:
    """Background Voice Assistant service running independently of the web frontend."""

    def __init__(self, tts_voice: str = "en-US-AriaNeural", follow_up_timeout_sec: float = 12.0):
        self.stt = STTEngine()
        self.tts = TTSEngine(voice=tts_voice)
        self.wakeword_detector = WakeWordDetector(
            wake_words=["wake bro", "hey bro", "hey umily", "umily", "hey family", "family", "hey emily", "emily", "hey humily", "humily"]
        )

        self.popup = FloatingOverlayPopup()
        self.follow_up_timeout_sec = follow_up_timeout_sec

        self._is_running = False
        self._is_paused = False
        self._state = "IDLE"
        self._thread: Optional[threading.Thread] = None
        
        self.active_task_id: Optional[int] = None
        self.conversation_history: List[Dict[str, str]] = []
        self.last_interaction_time: float = 0.0

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._is_running

    def enable_windows_startup(self) -> bool:
        """Enable Umily Assistant to start with Windows boot."""
        return WindowsStartupManager.enable_startup()

    def disable_windows_startup(self) -> bool:
        """Disable Windows auto-startup."""
        return WindowsStartupManager.disable_startup()

    def start(self):
        """Start background voice assistant thread and microphone wake-word listener."""
        if self._is_running:
            logger.info("Background Voice Assistant is already running.")
            return

        self._is_running = True
        self._is_paused = False
        self._state = "LISTENING_FOR_WAKE_WORD"
        
        # Start real-time microphone wake word detector
        self.wakeword_detector.start_listening(on_wake=self.trigger_wake_word_activation)

        self._thread = threading.Thread(target=self._assistant_loop, daemon=True)
        self._thread.start()
        logger.info("Background Voice Assistant started. Listening for 'Hey Umily' on microphone...")

    def stop(self):
        """Stop background voice assistant."""
        self._is_running = False
        self._state = "STOPPED"
        self.wakeword_detector.stop_listening()
        self.popup.hide(0.1)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Background Voice Assistant stopped.")

    def pause(self):
        """Pause microphone listening."""
        self._is_paused = True
        self._state = "PAUSED"
        self.wakeword_detector.stop_listening()
        self.popup.update_text("UMILY: Paused")
        self.popup.hide(1.5)
        logger.info("Background Voice Assistant paused.")

    def resume(self):
        """Resume microphone listening."""
        self._is_paused = False
        self._state = "LISTENING_FOR_WAKE_WORD"
        self.wakeword_detector.start_listening(on_wake=self.trigger_wake_word_activation)
        logger.info("Background Voice Assistant resumed.")

    def _speak(self, text: str):
        """Speak response via TTS out loud through computer speakers."""
        self._state = "SPEAKING"
        logger.info(f"[TTS Output] Umily speaks: {text!r}")
        try:
            self.tts.speak_out_loud(text)
        except Exception as e:
            logger.error(f"Error speaking text {text!r}: {e}")


    def process_voice_command_pipeline(self, command_text: str) -> Dict[str, Any]:
        """
        Execute command through the SAME Agent, Planner, Permission Manager, and Tool Executor architecture.
        Handles both GENERAL QUESTIONS (no permissions required) and COMPUTER TASKS.
        """
        if not command_text:
            return {"status": "failed", "message": "No command captured."}

        cmd_lower = command_text.lower().strip()

        # 1. Handle Full Application Shutdown ("umily stop" or "stop running")
        stop_app_keywords = ["umily stop", "stop running", "exit app", "shutdown"]
        if any(cmd_lower == k for k in stop_app_keywords):
            self.popup.show("UMILY: Stopping...")
            self._speak("Umily is stopping.")
            self.popup.hide(1.5)
            self.stop()
            return {"status": "stopped", "message": "Stopped by user command"}

        # 2. Handle Current Command Cancel ("stop", "cancel", "never mind")
        interrupt_keywords = ["stop", "cancel", "never mind", "abort"]
        if any(cmd_lower == k for k in interrupt_keywords):
            self.popup.show("UMILY: Cancelled")
            self._speak("Okay, cancelled.")
            self.popup.hide(1.5)
            self._state = "LISTENING_FOR_WAKE_WORD"
            return {"status": "cancelled", "message": "Cancelled by user interrupt"}


        db: Session = SessionLocal()
        try:
            repo = TaskRepository(db)
            perm_repo = PermissionRepository(db)

            context_cmd = command_text
            if self.conversation_history and len(command_text.split()) < 6:
                last_turn = self.conversation_history[-1]
                context_cmd = f"Context: Previous question was '{last_turn.get('user')}'. Current request: '{command_text}'"

            task = repo.create(command=f"[Voice] {command_text}")
            self.active_task_id = task.id
            self.last_interaction_time = time.time()

            # 1. Intent Classification & Planning via Gemini Agent
            self._state = "PLANNING"
            self.popup.show("UMILY: Thinking...")
            logger.info(f"[Voice Assistant] Processing command for Task #{task.id}: {command_text!r}")

            planner = AgentPlanner(db)
            plan = planner.create_plan(task.id, context_cmd)

            self.conversation_history.append({"user": command_text, "intent": plan.intent_type})

            # 2. General Knowledge Question Flow (No computer permissions required!)
            if plan.intent_type == "QUESTION" or (len(plan.steps) == 0 and plan.answer):
                ans = plan.answer or f"Answer for '{command_text}'"
                repo.update_status(task.id, TaskStatus.COMPLETED, result=ans)
                
                self.popup.show(f"UMILY: Answering...")
                self._speak(ans)
                self.popup.show("UMILY: Done")
                self.popup.hide(2.0)
                
                self._state = "ACTIVE_CONVERSATION"
                return {
                    "task_id": task.id,
                    "intent_type": "QUESTION",
                    "status": "completed",
                    "message": ans,
                    "speech": ans,
                }

            # 3. Computer Task Execution Flow (with Permissions)
            self._state = "EXECUTING"
            self.popup.show(f"UMILY: {plan.summary}...")

            executor = AgentExecutor(db)
            exec_result = executor.execute_plan(task.id, plan)

            updated_task = repo.get(task.id)
            status_str = updated_task.status if updated_task else exec_result.status

            if status_str == TaskStatus.WAITING_CONFIRMATION or exec_result.status == "waiting_confirmation":
                self._state = "WAITING_CONFIRMATION"
                step = exec_result.pending_confirmation_step
                desc = step.description if step else command_text
                
                prompt_msg = f"I need your permission to {desc}. Would you like to allow this?"
                self.popup.show("UMILY: Permission Required")
                self._speak(prompt_msg)

                # Record microphone audio for verbal user permission response ('yes'/'allow' vs 'no'/'cancel')
                self.popup.show("UMILY: Say Yes or No...")
                conf_audio_bytes = self.wakeword_detector.record_microphone_audio(duration_sec=3.0)
                if conf_audio_bytes:
                    conf_text = self.stt.transcribe_bytes(conf_audio_bytes).lower().strip()
                    logger.info(f"[Voice Assistant] Captured verbal permission response: {conf_text!r}")
                    if any(w in conf_text for w in ["yes", "allow", "sure", "ok", "okay", "yeah", "do it"]):
                        return self.handle_voice_confirmation(task.id, confirmed=True)
                    elif any(w in conf_text for w in ["no", "cancel", "stop", "don't", "deny"]):
                        return self.handle_voice_confirmation(task.id, confirmed=False)
                
                return {
                    "task_id": task.id,
                    "intent_type": "COMPUTER_TASK",
                    "status": "waiting_confirmation",
                    "message": prompt_msg,
                    "speech": prompt_msg,
                    "confirmation_required": True,
                    "pending_step": step.model_dump() if step else None,
                }


            if status_str == TaskStatus.COMPLETED or exec_result.success:
                res_msg = exec_result.message or "Task executed successfully."
                if "camera" in cmd_lower:
                    speech_msg = "Camera is open."
                elif "explorer" in cmd_lower or "file" in cmd_lower:
                    speech_msg = "File Explorer is open."
                else:
                    speech_msg = res_msg

                self.popup.show("UMILY: Done")
                self._speak(speech_msg)
                self.popup.hide(2.0)

                self._state = "ACTIVE_CONVERSATION"
                return {
                    "task_id": task.id,
                    "intent_type": "COMPUTER_TASK",
                    "status": "completed",
                    "message": res_msg,
                    "speech": speech_msg,
                }
            else:
                err_msg = exec_result.error or exec_result.message or "Action failed."
                speech_msg = f"I couldn't complete that request. {err_msg}"
                self.popup.show("UMILY: Action Failed")
                self._speak(speech_msg)
                self.popup.hide(2.5)

                self._state = "ACTIVE_CONVERSATION"
                return {
                    "task_id": task.id,
                    "intent_type": "COMPUTER_TASK",
                    "status": "failed",
                    "message": err_msg,
                    "speech": speech_msg,
                }
        finally:
            db.close()

    def handle_voice_confirmation(self, task_id: int, confirmed: bool) -> Dict[str, Any]:
        """Handle verbal confirmation response ('yes'/'allow' vs 'no'/'cancel') and save granted permissions."""
        db: Session = SessionLocal()
        try:
            repo = TaskRepository(db)
            perm_repo = PermissionRepository(db)
            task = repo.get(task_id)
            if not task:
                return {"success": False, "error": "Task not found"}

            if confirmed:
                self.popup.show("UMILY: Executing...")
                self._speak("Resuming execution.")

                actions = task.actions or []
                if actions:
                    last_step = actions[-1]
                    res_name = (last_step.get("resource_name") or "").lower()
                    res_type = (last_step.get("resource_type") or "").lower()
                    desc = (last_step.get("description") or "").lower()
                    privacy_keywords = ["camera", "webcam", "mic", "microphone", "privacy", "video_capture"]

                    # Auto-save permission ONLY for non-privacy resources (cameras/webcams always require asking permission)
                    if not any(kw in res_name or kw in res_type or kw in desc for kw in privacy_keywords):
                        perm_repo.set_permission(
                            resource_type=last_step.get("resource_type", "application"),
                            resource_name=last_step.get("resource_name", "system"),
                            action=last_step.get("action", "open"),
                            level=PermissionLevel.ALLOW
                        )


                executor = AgentExecutor(db)
                exec_res = executor.resume_after_confirmation(task_id)
                speech_msg = exec_res.message or "Action complete."
                self.popup.show("UMILY: Done")
                self._speak(speech_msg)
                self.popup.hide(2.0)
                self._state = "ACTIVE_CONVERSATION"
                return {"success": True, "status": "completed", "speech": speech_msg}
            else:
                repo.update_status(task_id, TaskStatus.CANCELLED)
                self.popup.show("UMILY: Cancelled")
                speech_msg = "Task cancelled."
                self._speak(speech_msg)
                self.popup.hide(1.5)
                self._state = "ACTIVE_CONVERSATION"
                return {"success": True, "status": "cancelled", "speech": speech_msg}
        finally:
            db.close()

    def trigger_wake_word_activation(self):
        """Triggered automatically when wake word ('Hey Umily') is detected on microphone stream."""
        if self._is_paused or self._state in ["PLANNING", "EXECUTING", "SPEAKING"]:
            return

        logger.info("[Voice Assistant] Wake word trigger activated via microphone.")
        self._state = "WAKE_DETECTED"
        self.last_interaction_time = time.time()
        
        # 1. Popup + Initial Voice Response
        self.popup.show("UMILY: Listening...")
        self._speak("Hey bro, I'm listening.")

        # 2. Capture user command audio from microphone (3.5 sec audio buffer)
        self.popup.show("UMILY: Listening to request...")
        logger.info("[Voice Assistant] Recording user command from microphone...")
        cmd_audio_bytes = self.wakeword_detector.record_microphone_audio(duration_sec=3.5)
        
        if cmd_audio_bytes:
            cmd_text = self.stt.transcribe_bytes(cmd_audio_bytes)
            logger.info(f"[Voice Assistant] Captured user command text: {cmd_text!r}")
            if cmd_text and len(cmd_text.strip()) > 1:
                self.process_voice_command_pipeline(cmd_text.strip())
                return

        # If no clear command audio captured, keep popup active for conversational follow-up
        self._state = "ACTIVE_CONVERSATION"

    def _assistant_loop(self):
        """Main background loop polling for wake word triggers and managing conversational timeouts."""
        while self._is_running:
            if self._is_paused:
                time.sleep(1.0)
                continue

            now = time.time()
            if self._state == "ACTIVE_CONVERSATION":
                if (now - self.last_interaction_time) > self.follow_up_timeout_sec:
                    logger.info("Conversational window expired. Returning to wake-word mode.")
                    self._state = "LISTENING_FOR_WAKE_WORD"
                    self.conversation_history.clear()

            time.sleep(0.5)


if __name__ == "__main__":
    assistant = BackgroundVoiceAssistant()
    assistant.start()
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Stopping Umily Background Voice Assistant...")
        assistant.stop()

