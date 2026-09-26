"""
Umily — Central Tool Registry

Routes action step execution requests to appropriate underlying tools:
- Browser (Playwright)
- Filesystem
- Windows (Process & Apps)
- Desktop (Shell & System)
"""

from typing import Any, Dict
from loguru import logger

from app.tools.browser.playwright_tool import BrowserTool
from app.tools.filesystem.file_tool import FilesystemTool
from app.tools.windows.win_automation import WindowsTool
from app.tools.desktop.system_tool import DesktopTool


class ToolRegistry:
    """Central registry and dispatcher for all tool operations."""

    def __init__(self) -> None:
        self.browser = BrowserTool()
        self.filesystem = FilesystemTool()
        self.windows = WindowsTool()
        self.desktop = DesktopTool()

    def dispatch(
        self,
        tool: str,
        action: str,
        resource_type: str,
        resource_name: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Dispatch action step to the appropriate tool instance."""
        tool_lower = (tool or "").lower()
        action_lower = (action or "").lower()

        logger.info(f"ToolRegistry dispatching tool='{tool}' action='{action}' resource='{resource_name}'")

        try:
            # 1. Browser tools
            if tool_lower == "browser" or resource_type == "website":
                if action_lower == "navigate":
                    url = parameters.get("url") or parameters.get("query") or resource_name
                    return self.browser.navigate(url)
                elif action_lower == "click":
                    selector = parameters.get("selector", "button")
                    return self.browser.click(selector)
                elif action_lower == "type" or action_lower == "type_text":
                    selector = parameters.get("selector", "input")
                    text = parameters.get("text", "")
                    return self.browser.type_text(selector, text)
                elif action_lower == "get_content" or action_lower == "read_page":
                    return self.browser.get_content(parameters.get("selector"))
                elif action_lower == "screenshot":
                    return self.browser.take_screenshot(parameters.get("path"))

            # 2. Filesystem tools
            elif tool_lower == "filesystem" or resource_type == "filesystem":
                path = parameters.get("path") or resource_name
                if action_lower == "read" or action_lower == "read_file":
                    return self.filesystem.read_file(path)
                elif action_lower == "write" or action_lower == "write_file":
                    content = parameters.get("content", "")
                    append = parameters.get("append", False)
                    return self.filesystem.write_file(path, content, append)
                elif action_lower == "list" or action_lower == "list_dir" or action_lower == "list_directory":
                    return self.filesystem.list_directory(path)
                elif action_lower == "search" or action_lower == "search_files":
                    pattern = parameters.get("pattern", "*")
                    return self.filesystem.search_files(path, pattern)
                elif action_lower == "delete" or action_lower == "delete_file":
                    return self.filesystem.delete_file(path)

            # 3. Windows tools
            elif tool_lower == "windows" or resource_type == "application":
                app_target = parameters.get("app_name") or resource_name
                if action_lower == "open" or action_lower == "open_app" or action_lower == "launch":
                    return self.windows.open_application(app_target, parameters.get("args"))
                elif action_lower == "close" or action_lower == "close_app" or action_lower == "terminate":
                    return self.windows.close_application(app_target)
                elif action_lower == "focus" or action_lower == "focus_window":
                    return self.windows.focus_window(app_target)
                elif action_lower == "key_press":
                    return self.windows.key_press(parameters.get("keys", "enter"))

            # 4. Desktop / System tools
            elif tool_lower == "desktop" or tool_lower == "system" or resource_type == "tool":
                if action_lower == "execute" or action_lower == "execute_command" or action_lower == "run_shell":
                    cmd = parameters.get("command") or parameters.get("cmd") or resource_name
                    return self.desktop.execute_command(cmd)
                elif action_lower == "info" or action_lower == "system_info":
                    return self.desktop.system_info()
                elif action_lower == "notify":
                    title = parameters.get("title", "Umily Agent")
                    msg = parameters.get("message", "Task step update")
                    return self.desktop.notify(title, msg)

            # Fallback dispatch for unspecified/custom actions
            cmd = parameters.get("command") or f"echo {action} on {resource_name}"
            return self.desktop.execute_command(cmd)

        except Exception as e:
            logger.error(f"Error during ToolRegistry dispatch: {e}")
            return {"success": False, "error": f"Tool execution failed: {e}"}
