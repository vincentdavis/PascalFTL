"""Application configuration and environment variables handling.

This module loads environment variables from a .env file (if present) and
exposes a simple Settings object with defaults suitable for development.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


# Load .env from project root if it exists
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./pftl.db")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "true").lower() in {"1", "true", "yes"}


settings = Settings()
