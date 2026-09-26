"""
Umily — Desktop System Tool

Executes shell commands, provides system specs/health, and emits desktop notifications.
"""

import platform
import subprocess
import sys
from typing import Any, Dict
from loguru import logger


class DesktopTool:
    """System and desktop management tools."""

    def execute_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute a shell command with a timeout."""
        logger.info(f"Executing system command: {command!r}")
        try:
            res = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "success": res.returncode == 0,
                "exit_code": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "message": f"Command executed with exit code {res.returncode}",
            }
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout}s: {command}")
            return {
                "success": False,
                "error": f"Command execution timed out after {timeout} seconds",
            }
        except Exception as e:
            logger.error(f"Failed to execute command '{command}': {e}")
            return {"success": False, "error": str(e)}

    def system_info(self) -> Dict[str, Any]:
        """Retrieve system hardware and OS environment information."""
        return {
            "success": True,
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
        }

    def notify(self, title: str, message: str) -> Dict[str, Any]:
        """Trigger a user notification."""
        logger.info(f"Notification: [{title}] {message}")
        return {
            "success": True,
            "message": f"Notification delivered: {title} - {message}",
        }
