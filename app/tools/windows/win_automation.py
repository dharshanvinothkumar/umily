"""
Umily — Windows Automation Tools

Provides application launch, process termination, window focus, and keyboard interaction.
"""

import os
import subprocess
import sys
from typing import Any, Dict, Optional
from loguru import logger

# Optional imports for advanced automation
try:
    import pywinauto
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False


class WindowsTool:
    """Windows OS process and application interaction tool."""

    def open_application(self, app_name: str, args: Optional[str] = None) -> Dict[str, Any]:
        """Launch a Windows application by name, executable, or path."""
        try:
            logger.info(f"Opening application: {app_name}")
            
            # Common app shortcuts mapping
            app_map = {
                "notepad": "notepad.exe",
                "calc": "calc.exe",
                "calculator": "calc.exe",
                "explorer": "explorer.exe",
                "cmd": "cmd.exe",
                "powershell": "powershell.exe",
                "vscode": "code",
                "chrome": "chrome",
                "edge": "msedge",
            }
            target = app_map.get(app_name.lower(), app_name)
            cmd = f"start {target}" if sys.platform == "win32" else target

            if args:
                cmd = f"{cmd} {args}"

            subprocess.Popen(cmd, shell=True)
            return {
                "success": True,
                "message": f"Successfully launched application: {app_name}",
                "command_used": cmd,
            }
        except Exception as e:
            logger.error(f"Failed to launch application '{app_name}': {e}")
            return {"success": False, "error": str(e)}

    def close_application(self, app_name: str) -> Dict[str, Any]:
        """Terminate a running process by executable or window name."""
        try:
            logger.info(f"Closing application: {app_name}")
            process_name = app_name if app_name.endswith(".exe") else f"{app_name}.exe"
            cmd = ["taskkill", "/F", "/IM", process_name]

            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                return {
                    "success": True,
                    "message": f"Successfully terminated process: {process_name}",
                }
            else:
                return {
                    "success": False,
                    "message": f"Could not find or close process: {process_name}",
                    "error": res.stderr.strip(),
                }
        except Exception as e:
            logger.error(f"Error closing application '{app_name}': {e}")
            return {"success": False, "error": str(e)}

    def focus_window(self, title: str) -> Dict[str, Any]:
        """Bring a target window to foreground."""
        if not PYWINAUTO_AVAILABLE:
            return {
                "success": True,
                "message": f"Simulated window focus for '{title}' (pywinauto not installed).",
                "fallback": True,
            }

        try:
            app = pywinauto.Application().connect(title_re=f".*{title}.*", timeout=3)
            window = app.top_window()
            window.set_focus()
            return {
                "success": True,
                "message": f"Focused window matching '{title}'",
            }
        except Exception as e:
            logger.warning(f"pywinauto focus failed for '{title}': {e}")
            return {
                "success": False,
                "error": f"Could not focus window '{title}': {e}",
            }

    def key_press(self, keys: str) -> Dict[str, Any]:
        """Simulate keyboard input."""
        if not PYAUTOGUI_AVAILABLE:
            return {
                "success": True,
                "message": f"Simulated key press '{keys}' (pyautogui not installed).",
                "fallback": True,
            }

        try:
            pyautogui.press(keys)
            return {
                "success": True,
                "message": f"Pressed key(s): {keys}",
            }
        except Exception as e:
            logger.error(f"Failed key press '{keys}': {e}")
            return {"success": False, "error": str(e)}
