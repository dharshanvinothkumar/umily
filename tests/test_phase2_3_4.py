"""
Umily — Test Suite for Phases 2, 3, and 4

Tests:
- Phase 2: Gemini Client initialization and plan fallback
- Phase 3: Agent Planner & Action Plan generation
- Phase 4: Permission Manager evaluation (ALLOW, ASK, BLOCK)
- End-to-End Task Execution & Confirmation Flow via API
"""

from app.database.models import PermissionLevel, TaskStatus
from app.database.repositories import PermissionRepository, TaskRepository
from app.ai.gemini_client import GeminiClient
from app.agent.planner import AgentPlanner
from app.agent.executor import AgentExecutor
from app.agent.schemas import ActionPlan, ActionStep
from app.permissions.manager import PermissionManager


# ---------------------------------------------------------------------------
# Phase 2 — Gemini API Client Tests
# ---------------------------------------------------------------------------

def test_gemini_client_fallback():
    """Verify GeminiClient generates a valid fallback plan when API key is unconfigured."""
    gc = GeminiClient(api_key="")
    assert gc.is_configured is False
    plan = gc.generate_plan("Open LeetCode")
    assert "summary" in plan
    assert "steps" in plan
    assert len(plan["steps"]) >= 1


def test_gemini_client_cleaning_json():
    """Verify Markdown fence cleaning."""
    gc = GeminiClient(api_key="")
    raw_markdown = "```json\n{\"summary\": \"test\", \"steps\": []}\n```"
    cleaned = gc._clean_json_response(raw_markdown)
    assert cleaned == '{"summary": "test", "steps": []}'


# ---------------------------------------------------------------------------
# Phase 3 — Agent Planner & Executor Tests
# ---------------------------------------------------------------------------

def test_planner_creates_action_plan(db_session):
    """Verify AgentPlanner parses command into ActionPlan model."""
    task_repo = TaskRepository(db_session)
    task = task_repo.create(command="Search for two sum")

    planner = AgentPlanner(db_session)
    plan = planner.create_plan(task.id, task.command)

    assert isinstance(plan, ActionPlan)
    assert len(plan.steps) > 0
    assert task_repo.get(task.id).plan is not None


def test_executor_successful_flow(db_session):
    """Verify AgentExecutor runs allowed steps to completion."""
    task_repo = TaskRepository(db_session)
    task = task_repo.create(command="Read test file")

    # Set permission ALLOW
    perm_repo = PermissionRepository(db_session)
    perm_repo.set_permission("tool", "System Command", "execute_command", PermissionLevel.ALLOW)

    planner = AgentPlanner(db_session)
    plan = planner.create_plan(task.id, task.command)

    executor = AgentExecutor(db_session)
    res = executor.execute_plan(task.id, plan)

    assert res.success is True
    assert res.status == "completed"
    assert task_repo.get(task.id).status == TaskStatus.COMPLETED


# ---------------------------------------------------------------------------
# Phase 4 — Permission Manager & Gatekeeping Tests
# ---------------------------------------------------------------------------

def test_permission_manager_block(db_session):
    """Verify PermissionManager blocks action step configured as BLOCK."""
    perm_repo = PermissionRepository(db_session)
    perm_repo.set_permission("website", "LeetCode", "navigate", PermissionLevel.BLOCK)

    pm = PermissionManager(db_session)
    step = ActionStep(
        step_id=1,
        tool="browser",
        action="navigate",
        resource_type="website",
        resource_name="LeetCode",
        parameters={},
        description="Navigate to LeetCode",
    )

    level = pm.evaluate_step(step)
    assert level == PermissionLevel.BLOCK


def test_executor_handles_blocked_step(db_session):
    """Verify AgentExecutor aborts task when step is BLOCKED."""
    task_repo = TaskRepository(db_session)
    task = task_repo.create(command="Open LeetCode")

    perm_repo = PermissionRepository(db_session)
    perm_repo.set_permission("website", "LeetCode", "navigate", PermissionLevel.BLOCK)

    planner = AgentPlanner(db_session)
    plan = planner.create_plan(task.id, task.command)

    executor = AgentExecutor(db_session)
    res = executor.execute_plan(task.id, plan)

    assert res.success is False
    assert res.status == "failed"
    assert task_repo.get(task.id).status == TaskStatus.FAILED


def test_executor_handles_ask_and_confirmation(db_session):
    """Verify AgentExecutor pauses on ASK and resumes on user confirmation."""
    task_repo = TaskRepository(db_session)
    task = task_repo.create(command="Open LeetCode")

    perm_repo = PermissionRepository(db_session)
    perm_repo.set_permission("website", "LeetCode", "navigate", PermissionLevel.ASK)

    planner = AgentPlanner(db_session)
    plan = planner.create_plan(task.id, task.command)

    executor = AgentExecutor(db_session)
    res = executor.execute_plan(task.id, plan)

    # Should pause waiting confirmation
    assert res.status == "waiting_confirmation"
    assert task_repo.get(task.id).status == TaskStatus.WAITING_CONFIRMATION

    # Now confirm task
    resume_res = executor.resume_after_confirmation(task.id)
    assert resume_res.success is True
    assert task_repo.get(task.id).status == TaskStatus.COMPLETED


# ---------------------------------------------------------------------------
# API Endpoint Integration Tests
# ---------------------------------------------------------------------------

def test_api_command_end_to_end(client):
    """Test POST /api/command endpoint triggers planning and execution."""
    resp = client.post("/api/command", json={"command": "Check system status"})
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data
    assert data["status"] in ["completed", "waiting_confirmation"]


def test_api_confirm_flow(client):
    """Test POST /api/confirm flow via HTTP client."""
    # First set permission ASK
    client.post("/api/permissions", json={
        "resource_type": "website",
        "resource_name": "LeetCode",
        "action": "navigate",
        "level": "ask",
    })

    # Submit command
    cmd_resp = client.post("/api/command", json={"command": "Open LeetCode"})
    task_id = cmd_resp.json()["task_id"]

    # Verify task is waiting confirmation
    task_resp = client.get(f"/api/tasks/{task_id}")
    assert task_resp.json()["status"] == "waiting_confirmation"

    # Confirm task
    conf_resp = client.post(f"/api/confirm?task_id={task_id}")
    assert conf_resp.status_code == 200
    assert conf_resp.json()["status"] == "completed"
