"""
Umily — Test Suite for Phases 5 to 11

Tests:
- Phase 5: Browser Tool (Playwright / simulation fallback)
- Phase 6–8: LeetCode Agent & Error Recovery Manager
- Phase 9–11: Filesystem, Windows Automation, & Desktop Tools
- Tool Registry dispatching
"""

import tempfile
from pathlib import Path

from app.agent.leetcode import LeetCodeAgent
from app.agent.error_recovery import ErrorRecoveryManager
from app.agent.schemas import ActionStep
from app.tools.browser.playwright_tool import BrowserTool
from app.tools.filesystem.file_tool import FilesystemTool
from app.tools.windows.win_automation import WindowsTool
from app.tools.desktop.system_tool import DesktopTool
from app.tools.registry import ToolRegistry


# ---------------------------------------------------------------------------
# Phase 5 — Browser Tools
# ---------------------------------------------------------------------------

def test_browser_tool_navigation():
    """Verify BrowserTool navigation (real or simulation fallback)."""
    browser = BrowserTool()
    res = browser.navigate("https://example.com")
    assert res["success"] is True
    assert "example.com" in res["url"]


def test_browser_tool_click_and_type():
    """Verify BrowserTool click and type methods."""
    browser = BrowserTool()
    click_res = browser.click("button.submit")
    assert click_res["success"] is True

    type_res = browser.type_text("input.search", "test query")
    assert type_res["success"] is True


# ---------------------------------------------------------------------------
# Phase 6 — LeetCode Agent
# ---------------------------------------------------------------------------

def test_leetcode_agent_plan_creation():
    """Verify LeetCodeAgent builds multi-step ActionPlan."""
    agent = LeetCodeAgent()
    plan = agent.build_leetcode_plan("Two Sum", "python")
    assert len(plan.steps) >= 3
    assert "LeetCode" in plan.steps[0].resource_name


# ---------------------------------------------------------------------------
# Phase 7 — Error Recovery Manager
# ---------------------------------------------------------------------------

def test_error_recovery_manager(db_session):
    """Verify ErrorRecoveryManager generates adaptive recovery step."""
    erm = ErrorRecoveryManager(db_session)
    failed_step = ActionStep(
        step_id=1,
        tool="browser",
        action="navigate",
        resource_type="website",
        resource_name="FaultySite",
        parameters={"url": "https://invalid.local"},
        description="Navigate to site",
    )
    recovery_step = erm.generate_recovery_step(failed_step, "Connection error")
    assert recovery_step.tool == "desktop"
    assert "Fallback" in recovery_step.description


# ---------------------------------------------------------------------------
# Phase 9–11 — Filesystem, Windows & Desktop Tools
# ---------------------------------------------------------------------------

def test_filesystem_tool_crud():
    """Verify FilesystemTool write, read, list, and delete operations."""
    fs = FilesystemTool()
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "umily_test.txt"
        
        # Write
        write_res = fs.write_file(str(test_file), "Hello Umily Agent!")
        assert write_res["success"] is True

        # Read
        read_res = fs.read_file(str(test_file))
        assert read_res["success"] is True
        assert read_res["content"] == "Hello Umily Agent!"

        # List
        list_res = fs.list_directory(tmpdir)
        assert list_res["success"] is True
        assert list_res["count"] == 1

        # Delete
        del_res = fs.delete_file(str(test_file))
        assert del_res["success"] is True


def test_windows_tool():
    """Verify WindowsTool application launcher."""
    win = WindowsTool()
    res = win.open_application("cmd")
    assert res["success"] is True


def test_desktop_tool():
    """Verify DesktopTool command execution and system info."""
    dt = DesktopTool()
    cmd_res = dt.execute_command("echo Hello")
    assert cmd_res["success"] is True
    assert "Hello" in cmd_res["stdout"]

    info_res = dt.system_info()
    assert info_res["success"] is True
    assert "os" in info_res


# ---------------------------------------------------------------------------
# Tool Registry Integration
# ---------------------------------------------------------------------------

def test_tool_registry_dispatch():
    """Verify ToolRegistry dispatches actions to correct handlers."""
    registry = ToolRegistry()

    # Browser dispatch
    b_res = registry.dispatch("browser", "navigate", "website", "Google", {"url": "https://google.com"})
    assert b_res["success"] is True

    # Desktop command dispatch
    d_res = registry.dispatch("desktop", "execute", "tool", "Shell", {"command": "echo test"})
    assert d_res["success"] is True
