"""Reads settings from the environment (and an optional .env file).

Phase 1 needs no secrets. The only setting is where the SQLite file lives.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "whatsapp_manager.db"


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_path: Path


def _db_path_from_url(url: str) -> Path:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise ValueError("Phase 1 only supports DATABASE_URL values that start with sqlite:///")
    path = Path(url[len(prefix):])
    return path if path.is_absolute() else PROJECT_ROOT / path


def get_settings() -> Settings:
    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env")
    url = os.environ.get("DATABASE_URL", "").strip()
    return Settings(
        app_env=os.environ.get("APP_ENV", "local"),
        database_path=_db_path_from_url(url) if url else DEFAULT_DB_PATH,
    )
