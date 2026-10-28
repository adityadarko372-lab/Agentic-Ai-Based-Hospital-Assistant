"""Measure the optional Ollama rewording on real Nova Health replies.

    backend\\.venv\\Scripts\\python.exe model\\llm_phrasing\\try_rewording.py

Sends eligible questions (hospital information) through the real agents with
LLM_PHRASING_ENABLED=true and a running local Ollama, then records, for each:
the template reply, the model's rewrite, whether the guard accepted it, and
the time taken. Writes model/llm_phrasing/results.json. Uses a throwaway
SQLite file; the demo database is not touched.
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.update(
    {
        "LLM_PHRASING_ENABLED": "true",
        "HEALTH_INFO_ENABLED": "false",
        "DATABASE_PATH": str(Path(tempfile.mkdtemp(prefix="nh_llm_")) / "llm.db"),
        "SESSION_SECRET": "llm-evaluation-only-not-a-real-secret-0123456789",
        "BCRYPT_ROUNDS": "4",
    }
)

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.seed import DEMO_PASSWORD  # noqa: E402
from app.main import create_app  # noqa: E402

QUESTIONS = [
    "What should I bring to my appointment?",
    "What are the visiting hours?",
    "How do I book an appointment?",
    "Where is the help desk?",
    "What are the OPD timings?",
    "Where can I find hospital services?",
    "Which department should I visit for a consultation?",
    "Where is cardiology?",
    "Is there parking?",
    "What are the timings of the laboratory?",
]


def main() -> None:
    settings = get_settings()
    rows = []
    with TestClient(create_app()) as client:
        token = client.post("/api/auth/login", json={"email": "patient@novahealth.demo", "password": DEMO_PASSWORD}).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        for question in QUESTIONS:
            started = time.perf_counter()
            body = client.post("/api/assistant/message", json={"message": question}, headers=headers).json()
            seconds = time.perf_counter() - started
            step = next((s for s in body["run"]["steps"] if s["action"] == "rephrase_reply"), None)
            rows.append(
                {
                    "question": question,
                    "agent": body["agent"],
                    "reply_shown": body["reply"],
                    "outcome": step["status"] if step else "not attempted",
                    "detail": step["detail"] if step else "",
                    "template": (step or {}).get("data", {}).get("original"),
                    "rejected_rewrite": (step or {}).get("data", {}).get("rejected"),
                    "seconds": round(seconds, 2),
                }
            )
            print(f"{seconds:5.1f}s  {rows[-1]['outcome']:8s}  {question}")
    reworded = [r for r in rows if r["detail"].startswith("Reworded")]
    rejected = [r for r in rows if "rejected" in r["detail"]]
    unavailable = [r for r in rows if "unavailable" in r["detail"]]
    summary = {
        "model": settings.ollama_model,
        "questions": len(rows),
        "reworded": len(reworded),
        "rejected_by_guard": len(rejected),
        "ollama_unavailable": len(unavailable),
        "median_seconds": sorted(r["seconds"] for r in rows)[len(rows) // 2],
        "max_seconds": max(r["seconds"] for r in rows),
    }
    out = Path(__file__).with_name("results.json")
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
