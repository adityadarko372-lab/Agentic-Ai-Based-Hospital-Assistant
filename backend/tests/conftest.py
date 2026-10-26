"""Shared pytest setup.

Environment variables take precedence over the developer's `.env` file, so
pinning them here keeps tests deterministic even if optional features are
switched on locally.
"""

import os

os.environ.update(
    {
        "ENVIRONMENT": "test",
        "INTENT_CLASSIFIER": "rules",
        "HEALTH_INFO_ENABLED": "false",
        "LLM_PHRASING_ENABLED": "false",
        "FRONT_DESK_ENABLED": "false",
        "CORS_ORIGINS": "http://127.0.0.1:5173,http://localhost:5173",
    }
)
