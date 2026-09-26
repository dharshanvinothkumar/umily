"""
Umily — Tests for Windows Auto-Startup, Dual Intent (General Questions vs Computer Tasks), Conversational Memory & Interrupts
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.background.assistant_service import BackgroundVoiceAssistant
from app.background.startup import WindowsStartupManager
from app.background.popup import FloatingOverlayPopup
from app.database.models import PermissionLevel
from app.database.repositories import PermissionRepository


client = TestClient(app)


def test_general_knowledge_question_no_permissions():
    """Test general question pipeline returns direct answer without computer permissions."""
    resp = client.post("/api/command", json={"command": "What is machine learning?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert "Machine learning is" in data["message"] or "Machine learning" in data["message"]
    # Verify no steps required confirmation
    assert data["confirmation_required"] is False


def test_deep_learning_question():
    """Test general question for deep learning."""
    resp = client.post("/api/command", json={"command": "Explain deep learning"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert len(data["message"]) > 10


def test_computer_task_open_file_explorer():
    """Test computer task command for File Explorer."""
    resp = client.post("/api/command", json={"command": "Open File Explorer"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["completed", "executing"]


def test_assistant_dual_intent(db_session):
    assistant = BackgroundVoiceAssistant()
    
    # 1. Test General Question
    res_q = assistant.process_voice_command_pipeline("What is Python?")
    assert res_q["intent_type"] == "QUESTION"
    assert res_q["status"] == "completed"
    assert "Python" in res_q["speech"]

    # 2. Test Computer Task
    res_t = assistant.process_voice_command_pipeline("Open Camera")
    assert res_t["intent_type"] == "COMPUTER_TASK"
    assert res_t["status"] in ["completed", "waiting_confirmation"]


def test_assistant_interrupt():
    assistant = BackgroundVoiceAssistant()
    res = assistant.process_voice_command_pipeline("stop")
    assert res["status"] == "cancelled"


def test_permission_saving_on_confirmation(db_session):
    assistant = BackgroundVoiceAssistant()
    perm_repo = PermissionRepository(db_session)
    
    # Set explicit ASK for test resource
    perm_repo.set_permission("application", "TestCalculator", "open", PermissionLevel.ASK)
    
    # Simulate confirmation approval
    res_confirm = assistant.handle_voice_confirmation(task_id=1, confirmed=True)
    assert res_confirm["success"] is True


def test_windows_startup_manager():
    # Verify startup command generation
    cmd = WindowsStartupManager.get_executable_command()
    assert "assistant_service.py" in cmd
    assert isinstance(WindowsStartupManager.is_enabled(), bool)


def test_floating_overlay_popup():
    popup = FloatingOverlayPopup()
    popup.show("UMILY: Testing...")
    popup.update_text("UMILY: Thinking...")
    popup.hide(0.1)
