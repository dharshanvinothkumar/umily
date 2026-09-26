"""
Umily — Phase 1 Tests

Verifies that:
- The FastAPI app starts and serves the root
- /api/command accepts text and creates tasks
- /api/status returns system health
- /api/tasks returns task history
- /api/permissions CRUD works
"""

def test_root_serves_frontend(client):
    """GET / should return 200 (frontend or fallback message)."""
    response = client.get("/")
    assert response.status_code == 200


def test_status_endpoint(client):
    """GET /api/status should return system health."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "Umily"
    assert data["status"] == "running"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def test_command_creates_task(client):
    """POST /api/command should create a task and return response."""
    response = client.post("/api/command", json={"command": "Hello Umily"})
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] >= 1
    assert "Hello Umily" in data["message"] or "completed" in data["status"] or "waiting" in data["status"]


def test_command_rejects_empty(client):
    """POST /api/command with empty string should fail validation."""
    response = client.post("/api/command", json={"command": ""})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

def test_list_tasks(client):
    """GET /api/tasks should return task list."""
    client.post("/api/command", json={"command": "Test task"})
    response = client.get("/api/tasks")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1


def test_get_task_by_id(client):
    """GET /api/tasks/{id} should return a specific task."""
    create_resp = client.post("/api/command", json={"command": "Specific task"})
    task_id = create_resp.json()["task_id"]

    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["command"] == "Specific task"


def test_get_task_not_found(client):
    """GET /api/tasks/99999 should return 404."""
    response = client.get("/api/tasks/99999")
    assert response.status_code == 404


def test_cancel_task(client):
    """POST /api/cancel should mark task as cancelled."""
    create_resp = client.post("/api/command", json={"command": "Cancel me"})
    task_id = create_resp.json()["task_id"]

    response = client.post(f"/api/cancel?task_id={task_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

def test_set_and_list_permissions(client):
    """POST /api/permissions + GET /api/permissions should round-trip."""
    perm_data = {
        "resource_type": "website",
        "resource_name": "LeetCode",
        "action": "read",
        "level": "allow",
    }
    set_resp = client.post("/api/permissions", json=perm_data)
    assert set_resp.status_code == 200
    assert set_resp.json()["level"] == "allow"

    list_resp = client.get("/api/permissions")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["count"] >= 1
    names = [p["resource_name"] for p in data["permissions"]]
    assert "LeetCode" in names


# ---------------------------------------------------------------------------
# Voice
# ---------------------------------------------------------------------------

def test_voice_placeholder(client):
    """POST /api/voice should return not-implemented status."""
    response = client.post("/api/voice")
    assert response.status_code == 200
    assert response.json()["status"] == "not_implemented"
