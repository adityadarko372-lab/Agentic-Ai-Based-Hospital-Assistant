"""Hospital knowledge loaded from versioned JSON files (fictional demo content).

- hospital_info.json        departments, hours, booking guidance (fictional hospital)
- department_keywords.json  words that point a request to a department (navigation only)
- care_rules.json           preliminary care-navigation rules (not clinically reviewed)
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

KNOWLEDGE_DIR = Path(__file__).resolve().parent


def _load(name: str) -> dict[str, Any]:
    with (KNOWLEDGE_DIR / name).open(encoding="utf-8") as file:
        return json.load(file)


@lru_cache
def load_hospital_info() -> dict[str, Any]:
    return _load("hospital_info.json")


@lru_cache
def load_department_keywords() -> dict[str, Any]:
    return _load("department_keywords.json")


@lru_cache
def load_care_rules() -> dict[str, Any]:
    return _load("care_rules.json")
