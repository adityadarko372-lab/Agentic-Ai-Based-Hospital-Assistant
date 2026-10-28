"""Application settings.

All settings come from environment variables or the repository-level `.env`
file (see `.env.example`). Optional AI features are OFF by default so the
required demonstration never depends on a GPU model, a dataset download, or
a running local LLM.
"""

import logging
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> repository root is three levels up from app/
REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "backend"

logger = logging.getLogger("nova_health.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Nova Health"
    app_version: str = "0.1.0-required-scope"
    # "demo" makes it explicit that all data is synthetic.
    environment: Literal["demo", "development", "test"] = "demo"

    # Comma-separated list of browser origins allowed to call the API.
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    # SQLite database file. The folder is created on start-up; the file is
    # gitignored and can be deleted to reset all demo data.
    database_path: Path = BACKEND_DIR / "data" / "nova_health.db"

    # Secret used to sign login session tokens. If it is empty, a random secret
    # is generated for this process only (everyone is signed out on restart).
    # scripts/start.ps1 writes a persistent random value into `.env`.
    session_secret: str = ""
    session_hours: int = 8
    # bcrypt work factor. 12 is a sensible default; tests lower it for speed.
    bcrypt_rounds: int = 12

    # Appointment request policy (fictional demo hospital rules).
    appointment_max_days_ahead: int = 90

    # Feature flags for optional enhancements (Phase 5). Defaults keep the
    # required journey fully rule-based and offline.
    intent_classifier: Literal["rules", "transformer"] = "rules"
    health_info_enabled: bool = False
    llm_phrasing_enabled: bool = False
    front_desk_enabled: bool = False

    # Optional MedQuAD index (built by model/health_info/build_index.py).
    health_info_index_dir: Path = REPO_ROOT / "model" / "artifacts" / "health_info"
    # Below this cosine similarity the agent says it has no reliable answer.
    # Chosen on the hand-written evaluation set (model/health_info/evaluate.py).
    health_info_min_score: float = 0.6

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read once per process)."""
    settings = Settings()
    if not settings.session_secret:
        settings.session_secret = secrets.token_urlsafe(48)
        logger.warning(
            "SESSION_SECRET is not set; using a temporary secret. "
            "Users will be signed out when the server restarts."
        )
    return settings
