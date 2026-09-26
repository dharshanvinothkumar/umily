"""
Umily — Tests for Command Pipeline Fixes & Background Voice Assistant
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.background.assistant_service import BackgroundVoiceAssistant
from app.tools.windows.win_automation import WindowsTool

client = TestClient(app)


def test_open_camera_command():
    """Test 'open camera' text command end-to-end (requires permission confirmation)."""
    resp = client.post("/api/command", json={"command": "open camera"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["completed", "executing", "waiting_confirmation"]
    assert "task_id" in data



def test_open_project_command():
    """Test 'open my AI attendance project' command."""
    resp = client.post("/api/command", json={"command": "open my AI attendance project"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["completed", "executing"]


def test_windows_tool_project_discovery():
    tool = WindowsTool()
    res = tool.open_application("AI attendance project")
    assert res["success"] is True
    assert "opened project folder" in res["message"] or "launched" in res["message"]


def test_background_voice_assistant_pipeline():
    assistant = BackgroundVoiceAssistant()
    assert assistant.state == "IDLE"
    
    assistant.start()
    assert assistant.is_running is True

    # Process command through SAME agent architecture
    res = assistant.process_voice_command_pipeline("open camera")
    assert "task_id" in res
    assert res["status"] in ["completed", "waiting_confirmation"]

    assistant.stop()
    assert assistant.is_running is False
