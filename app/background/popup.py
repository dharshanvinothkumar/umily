"""
Umily — Floating Overlay Popup

Small floating overlay status window that displays real-time status during voice interaction.
Appears when wake word ("Hey Umily") is triggered and automatically hides after completion.
"""

import os
import sys
import threading
import time
from typing import Optional
from loguru import logger

class FloatingOverlayPopup:
    """Floating overlay status indicator for background voice assistant."""

    def __init__(self):
        self._root = None
        self._label = None
        self._is_visible = False
        self._current_text = "UMILY: Listening..."
        self._gui_enabled = os.environ.get("PYTEST_CURRENT_TEST") is None

    def show(self, text: str = "UMILY: Listening..."):
        """Show floating overlay popup with status text."""
        self._current_text = text
        logger.info(f"[Overlay Popup] Status: {text}")

        if not self._gui_enabled:
            return

        if not self._is_visible:
            self._is_visible = True
            try:
                thread = threading.Thread(target=self._run_gui, daemon=True)
                thread.start()
            except Exception as e:
                logger.debug(f"Popup GUI thread failed: {e}")
                self._is_visible = False
        elif self._label and self._root:
            try:
                self._root.after(0, lambda: self._update_gui(text))
            except Exception:
                pass

    def update_text(self, text: str):
        """Update text on visible overlay."""
        self._current_text = text
        logger.info(f"[Overlay Popup] Update: {text}")
        if self._gui_enabled and self._label and self._root:
            try:
                self._root.after(0, lambda: self._update_gui(text))
            except Exception:
                pass

    def _update_gui(self, text: str):
        if self._label:
            try:
                self._label.config(text=text)
            except Exception:
                pass

    def hide(self, delay_sec: float = 1.0):
        """Hide overlay safely."""
        self._is_visible = False
        if self._gui_enabled and self._root:
            try:
                self._root.after(int(delay_sec * 1000), self._destroy_gui)
            except Exception:
                pass

    def _destroy_gui(self):
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
            self._root = None

    def _run_gui(self):
        """Initialize Tkinter borderless floating window."""
        try:
            import tkinter as tk
            self._root = tk.Tk()
            self._root.title("Umily Assistant")
            self._root.overrideredirect(True)
            self._root.attributes("-topmost", True)
            try:
                self._root.attributes("-alpha", 0.92)
            except Exception:
                pass

            screen_width = self._root.winfo_screenwidth()
            window_width = 300
            window_height = 60
            x_pos = max(screen_width - window_width - 30, 10)
            y_pos = 40
            self._root.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")

            bg_color = "#1f0913"
            fg_color = "#ffffff"
            border_color = "#e83e8c"

            frame = tk.Frame(self._root, bg=bg_color, highlightbackground=border_color, highlightthickness=2)
            frame.pack(fill="both", expand=True)

            display_text = self._current_text
            if not display_text.startswith("🤖"):
                display_text = f"🤖 {display_text}"

            self._label = tk.Label(
                frame,
                text=display_text,
                font=("Segoe UI", 11, "bold"),
                bg=bg_color,
                fg=fg_color,
                wraplength=280
            )
            self._label.pack(expand=True, pady=8)

            self._root.mainloop()
        except Exception as e:
            logger.info(f"GUI overlay fallback mode: {e}")
            self._is_visible = False

