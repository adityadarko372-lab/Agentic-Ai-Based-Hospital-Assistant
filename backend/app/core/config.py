"""Application settings.

All settings come from environment variables or the repository-level `.env`
file (see `.env.example`). Optional AI features are OFF by default so the
required demonstration never depends on a GPU model, a dataset download, or
a running local LLM.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> repository root is three levels up from app/
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Nova Health"
    app_version: str = "0.1.0-phase1"
    # "demo" makes it explicit that all data is synthetic.
    environment: Literal["demo", "development", "test"] = "demo"

    # Comma-separated list of browser origins allowed to call the API.
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    # Feature flags for optional enhancements (Phase 5). Defaults keep the
    # required journey fully rule-based and offline.
    intent_classifier: Literal["rules", "transformer"] = "rules"
    health_info_enabled: bool = False
    llm_phrasing_enabled: bool = False
    front_desk_enabled: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read once per process)."""
    return Settings()
