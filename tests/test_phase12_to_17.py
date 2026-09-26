"""
Umily — Tests for Phases 12–17 (Voice Pipeline, Background Daemon, System Tray, System Integration)
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.voice.stt import STTEngine
from app.voice.tts import TTSEngine
from app.voice.wakeword import WakeWordDetector
from app.voice.manager import VoiceManager
from app.background.daemon import BackgroundDaemon
from app.background.tray import SystemTrayController


client = TestClient(app)


def test_stt_engine_fallback():
    stt = STTEngine(model_size="tiny")
    transcript = stt.transcribe_bytes(b"Open chrome browser")
    assert isinstance(transcript, str)
    assert len(transcript) > 0


def test_tts_engine_synthesis():
    tts = TTSEngine()
    audio = tts.synthesize("Task completed successfully")
    assert isinstance(audio, bytes)
    assert len(audio) > 0


def test_wakeword_detector():
    detector = WakeWordDetector()
    assert detector.is_wake_word("Hey Umily, set a timer") is True
    assert detector.is_wake_word("Hello world") is False


def test_voice_manager(db_session):
    vm = VoiceManager()
    res = vm.process_voice_audio(db_session, b"Check system status")
    assert "transcript" in res
    assert "message" in res
    assert "status" in res


def test_voice_endpoints():
    # 1. Voice Command Endpoint
    resp = client.post("/api/voice", data={"text_fallback": "Test voice command"})
    assert resp.status_code == 200
    data = resp.json()
    assert "transcript" in data
    assert "message" in data

    # 2. Voice Transcribe Endpoint
    resp_transcribe = client.post(
        "/api/voice/transcribe",
        files={"file": ("test.wav", b"Sample audio data", "audio/wav")}
    )
    assert resp_transcribe.status_code == 200
    assert "transcript" in resp_transcribe.json()

    # 3. Voice Synthesize Endpoint
    resp_synth = client.post("/api/voice/synthesize", json={"text": "Hello world"})
    assert resp_synth.status_code == 200
    assert len(resp_synth.content) > 0


def test_background_daemon():
    daemon = BackgroundDaemon(check_interval_sec=0.1)
    status_before = daemon.get_status()
    assert status_before["running"] is False

    daemon.start()
    status_running = daemon.get_status()
    assert status_running["running"] is True

    task_id = daemon.schedule_task("Health Check", interval_sec=0.05)
    assert task_id.startswith("bg_")

    daemon.stop()
    status_after = daemon.get_status()
    assert status_after["running"] is False


def test_background_api_endpoints():
    # Get status
    resp = client.get("/api/background/status")
    assert resp.status_code == 200
    assert "status" in resp.json()

    # Schedule task
    resp_sched = client.post("/api/background/schedule", json={"command": "Check background", "interval_sec": 30.0})
    assert resp_sched.status_code == 200
    assert "task_id" in resp_sched.json()


def test_system_tray_controller():
    tray = SystemTrayController()
    assert tray.is_active is False
    tray.start()
    # Should safely start or default to headless fallback
    tray.stop()
    assert tray.is_active is False
