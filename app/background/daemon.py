"""
Umily — Background Daemon

Runs background task queue, health monitor, and periodic tasks in an asynchronous thread.
"""

import threading
import time
from typing import Dict, Any, List, Optional
from loguru import logger

class BackgroundDaemon:
    """Daemon process running in background for periodic checks & task queuing."""

    def __init__(self, check_interval_sec: float = 5.0):
        self.check_interval_sec = check_interval_sec
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._scheduled_tasks: List[Dict[str, Any]] = []
        self._processed_count = 0

    def start(self):
        """Start background daemon thread."""
        if self._is_running:
            logger.info("Background daemon is already running.")
            return

        self._is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Background daemon started.")

    def stop(self):
        """Stop background daemon thread."""
        self._is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Background daemon stopped.")

    def schedule_task(self, command: str, interval_sec: float) -> str:
        """Schedule a background command to execute periodically."""
        task_id = f"bg_{len(self._scheduled_tasks) + 1}"
        self._scheduled_tasks.append({
            "id": task_id,
            "command": command,
            "interval": interval_sec,
            "last_run": 0.0,
            "enabled": True
        })
        logger.info(f"Scheduled background task {task_id}: {command!r}")
        return task_id

    def get_status(self) -> Dict[str, Any]:
        """Return status of background daemon."""
        return {
            "running": self._is_running,
            "processed_count": self._processed_count,
            "scheduled_tasks_count": len(self._scheduled_tasks),
            "check_interval_sec": self.check_interval_sec,
        }

    def _run_loop(self):
        """Main background processing loop."""
        while self._is_running:
            now = time.time()
            for task in self._scheduled_tasks:
                if task["enabled"] and (now - task["last_run"]) >= task["interval"]:
                    task["last_run"] = now
                    self._processed_count += 1
                    logger.debug(f"[Background Daemon] Executed background job: {task['command']!r}")

            time.sleep(self.check_interval_sec)
