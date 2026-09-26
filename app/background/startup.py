"""
Umily — Windows Auto-Startup Configurator

Configures Umily Background Assistant to start automatically when the user logs into Windows.
Uses user-level Windows Registry (HKCU) or Startup Folder shortcut (no admin rights required).
"""

import sys
import os
import winreg
from pathlib import Path
from loguru import logger

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "UmilyBackgroundAssistant"

class WindowsStartupManager:
    """Manages user-level Windows startup entry for Umily Background Assistant."""

    @staticmethod
    def get_executable_command() -> str:
        """Construct the background startup command using pythonw/python."""
        python_exe = sys.executable
        if python_exe.endswith("python.exe"):
            pythonw = python_exe.replace("python.exe", "pythonw.exe")
            if os.path.exists(pythonw):
                python_exe = pythonw

        script_path = Path(__file__).parent.parent / "background" / "assistant_service.py"
        return f'"{python_exe}" "{script_path.resolve()}"'

    @classmethod
    def enable_startup(cls) -> bool:
        """Add Umily Background Assistant to Windows Startup (Registry HKCU)."""
        if sys.platform != "win32":
            logger.info("Windows Startup is only applicable on Win32 systems.")
            return False

        try:
            cmd = cls.get_executable_command()
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            logger.info(f"Successfully enabled Windows startup entry: {cmd}")
            return True
        except Exception as e:
            logger.error(f"Failed to set Windows startup registry key: {e}")
            return False

    @classmethod
    def disable_startup(cls) -> bool:
        """Remove Umily Background Assistant from Windows Startup."""
        if sys.platform != "win32":
            return False

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, APP_NAME)
            winreg.CloseKey(key)
            logger.info("Successfully removed Windows startup entry.")
            return True
        except FileNotFoundError:
            return True
        except Exception as e:
            logger.error(f"Failed to remove Windows startup entry: {e}")
            return False

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if Windows startup entry exists."""
        if sys.platform != "win32":
            return False

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return bool(val)
        except Exception:
            return False
