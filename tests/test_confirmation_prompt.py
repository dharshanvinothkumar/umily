"""
Umily — Verification Test Suite for Confirmation Prompt Flow & Permissions

Verifies:
1. ALLOW state: Action executes immediately without confirmation prompt
2. ASK state: Action pauses with status WAITING_CONFIRMATION, exposes pending_step payload
3. ALLOW user decision: POST /api/confirm resumes task to COMPLETED
4. DENY user decision: POST /api/cancel updates task to CANCELLED
5. BLOCK state: Action fails immediately with status FAILED and clear explanation error
"""

import pytest
from app.database.models import PermissionLevel, TaskStatus
from app.database.repositories import PermissionRepository, TaskRepository
from app.agent.executor import AgentExecutor
from app.agent.planner import AgentPlanner
from app.agent.schemas import ActionPlan, ActionStep


def test_confirmation_required_flow_allow_resume(client, db_session):
    """Test ASK permission -> WAITING_CONFIRMATION -> POST /confirm -> COMPLETED."""
    perm_repo = PermissionRepository(db_session)
    perm_repo.set_permission("website", "LeetCode", "submit", PermissionLevel.ASK)

    # Submit command asking to submit LeetCode solution
    resp = client.post("/api/command", json={"command": "Submit solution to LeetCode"})
    assert resp.status_code == 200
    data = resp.json()
    task_id = data["task_id"]

    # 1. Verify task is in WAITING_CONFIRMATION
    assert data["status"] == "waiting_confirmation"
    assert data["confirmation_required"] is True
    assert data["pending_step"] is not None
    assert data["pending_step"]["resource_name"] == "LeetCode"

    # 2. Verify GET /api/tasks/{id} exposes confirmation fields
    task_resp = client.get(f"/api/tasks/{task_id}")
    assert task_resp.status_code == 200
    task_data = task_resp.json()
    assert task_data["status"] == "waiting_confirmation"
    assert task_data["confirmation_required"] is True
    assert task_data["pending_step"]["action"] in ["submit", "navigate"]

    # 3. Confirm task via POST /api/confirm
    conf_resp = client.post(f"/api/confirm?task_id={task_id}")
    assert conf_resp.status_code == 200
    conf_data = conf_resp.json()
    assert conf_data["status"] == "completed"

    # 4. Verify DB status is COMPLETED
    task_final = client.get(f"/api/tasks/{task_id}").json()
    assert task_final["status"] == "completed"


def test_confirmation_required_flow_deny_cancel(client, db_session):
    """Test ASK permission -> WAITING_CONFIRMATION -> POST /cancel -> CANCELLED."""
    perm_repo = PermissionRepository(db_session)
    perm_repo.set_permission("website", "LeetCode", "submit", PermissionLevel.ASK)

    resp = client.post("/api/command", json={"command": "Submit solution to LeetCode"})
    task_id = resp.json()["task_id"]

    # Cancel task via POST /api/cancel
    cancel_resp = client.post(f"/api/cancel?task_id={task_id}")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # Verify DB status is CANCELLED
    task_final = client.get(f"/api/tasks/{task_id}").json()
    assert task_final["status"] == "cancelled"


def test_block_permission_fails_immediately(client, db_session):
    """Test BLOCK permission -> FAILED immediately with explanation error."""
    perm_repo = PermissionRepository(db_session)
    perm_repo.set_permission("website", "LeetCode", "navigate", PermissionLevel.BLOCK)

    resp = client.post("/api/command", json={"command": "Open LeetCode"})
    assert resp.status_code == 200
    data = resp.json()
    task_id = data["task_id"]

    assert data["status"] == "failed"

    task_data = client.get(f"/api/tasks/{task_id}").json()
    assert task_data["status"] == "failed"
    assert "blocked by permission policy" in task_data["error"].lower() or "blocked" in task_data["error"].lower()


def test_allow_permission_executes_immediately(client, db_session):
    """Test ALLOW permission -> COMPLETED immediately without confirmation."""
    perm_repo = PermissionRepository(db_session)
    perm_repo.set_permission("tool", "System Command", "execute_command", PermissionLevel.ALLOW)

    resp = client.post("/api/command", json={"command": "Check system info"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "completed"
    assert data["confirmation_required"] is False
