"""Hospital knowledge loaded from versioned JSON files (fictional demo content)."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

KNOWLEDGE_DIR = Path(__file__).resolve().parent


@lru_cache
def load_hospital_info() -> dict[str, Any]:
    """Read hospital_info.json once per process."""
    with (KNOWLEDGE_DIR / "hospital_info.json").open(encoding="utf-8") as file:
        return json.load(file)
