"""Finds which hospital department a message refers to (navigation only).

Two kinds of evidence, both from department_keywords.json:
- alias:   the department is named ("cardiology", "eye doctor")      -> strong
- keyword: a body area or need points to it ("knee", "skin rash")   -> suggestion

A keyword match only says where a patient could be seen. It is never a
statement about what condition they have.
"""

from dataclasses import dataclass
from typing import Literal

from app.agents.text import find_phrase
from app.knowledge import load_department_keywords


@dataclass
class DepartmentMatch:
    department_id: str
    matched: str
    kind: Literal["alias", "keyword"]


def match_departments(normalised_text: str) -> list[DepartmentMatch]:
    """All departments mentioned, aliases first, then keywords, without duplicates."""
    departments = load_department_keywords()["departments"]
    found: dict[str, DepartmentMatch] = {}

    for kind in ("alias", "keyword"):
        field = "aliases" if kind == "alias" else "keywords"
        # Longer phrases first, so "back pain" wins over "pain"-like overlaps.
        candidates = sorted(
            ((dept_id, phrase) for dept_id, record in departments.items() for phrase in record[field]),
            key=lambda item: len(item[1]),
            reverse=True,
        )
        for dept_id, phrase in candidates:
            if dept_id in found:
                continue
            if find_phrase(normalised_text, phrase):
                found[dept_id] = DepartmentMatch(dept_id, phrase, kind)  # type: ignore[arg-type]

    aliases = [match for match in found.values() if match.kind == "alias"]
    keywords = [match for match in found.values() if match.kind == "keyword"]
    return aliases + keywords
