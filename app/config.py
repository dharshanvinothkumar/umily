"""
Umily — Application Configuration

Central configuration loaded from environment variables and .env file.
All settings are validated through Pydantic.
"""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Application ---
    APP_NAME: str = "Umily"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # --- Database ---
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'umily.db'}"

    # --- Gemini API ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # --- Voice ---
    WAKE_WORD: str = "hey umily"

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    # --- Security ---
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # --- Agent ---
    MAX_RETRIES: int = 2
    COMMAND_TIMEOUT: int = 30  # seconds

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
