"""
Umily — Logging Configuration

Structured logging using loguru. Replaces Python's default logger
with formatted, colorized output and optional file logging.
"""

import sys
from pathlib import Path

from loguru import logger

from app.config import settings, BASE_DIR


def setup_logging() -> None:
    """Configure application logging with loguru."""

    # Remove default handler
    logger.remove()

    # Console handler — colorized, structured
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    logger.add(
        sys.stderr,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=True,
    )

    # File handler — rotating log file
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)

    logger.add(
        str(log_dir / "umily_{time:YYYY-MM-DD}.log"),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
    )

    logger.info(f"Logging initialized — level={settings.LOG_LEVEL}")
