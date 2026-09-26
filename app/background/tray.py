"""
Umily — System Tray Icon Controller

Manages system tray icon using pystray when available, or headless manager fallback.
"""

import threading
import webbrowser
from typing import Optional
from loguru import logger

class SystemTrayController:
    """Controls the Windows system tray icon and context menu."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        self.host = host
        self.port = port
        self.dashboard_url = f"http://{host}:{port}"
        self._icon = None
        self._thread: Optional[threading.Thread] = None
        self._is_active = False

    def open_dashboard(self):
        """Open Control Center dashboard in default web browser."""
        logger.info(f"Opening dashboard at {self.dashboard_url}")
        webbrowser.open(self.dashboard_url)

    def start(self):
        """Start system tray icon in background thread."""
        try:
            import pystray
            from PIL import Image, ImageDraw

            def create_image():
                # Create a 64x64 icon image dynamically
                image = Image.new('RGB', (64, 64), color=(106, 27, 45))
                d = ImageDraw.Draw(image)
                d.ellipse((16, 16, 48, 48), fill=(255, 255, 255))
                return image

            menu = pystray.Menu(
                pystray.MenuItem("Open Control Center", lambda icon, item: self.open_dashboard()),
                pystray.MenuItem("Status: Active", None, enabled=False),
                pystray.MenuItem("Exit", lambda icon, item: icon.stop())
            )

            self._icon = pystray.Icon("Umily", create_image(), "Umily Agent", menu)
            self._thread = threading.Thread(target=self._icon.run, daemon=True)
            self._thread.start()
            self._is_active = True
            logger.info("System tray icon started successfully.")
        except Exception as e:
            logger.info(f"pystray not active or in headless mode: {e}. System tray fallback enabled.")
            self._is_active = False

    def stop(self):
        """Stop system tray icon."""
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
        self._is_active = False
        logger.info("System tray icon stopped.")

    @property
    def is_active(self) -> bool:
        return self._is_active
