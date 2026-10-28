"""Semantic search over the prepared MedQuAD questions.

The index is built offline by model/health_info/build_index.py into
model/artifacts/health_info/:

    encoder/          sentence-transformers all-MiniLM-L6-v2 (saved locally)
    embeddings.npy    one L2-normalised vector per record (float32)
    records.jsonl     the records, in the same order
    manifest.json     model name, record count, build date

Nothing here is required for the main app. If the libraries or the index are
missing, `get_retriever()` returns an `Unavailable` with the reason, and the
Health Information Agent says the feature is unavailable instead of guessing.
"""

import json
import logging
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from app.core.config import get_settings

logger = logging.getLogger("nova_health.health_info")

REQUIRED_FILES = ("embeddings.npy", "records.jsonl", "manifest.json")


@dataclass(frozen=True)
class SearchHit:
    record: dict[str, str]
    score: float  # cosine similarity, -1..1


@dataclass(frozen=True)
class Unavailable:
    reason: str


class Retriever(Protocol):
    name: str

    def search(self, query: str, k: int = 3) -> list[SearchHit]: ...


class MedQuADRetriever:
    """Embeds the query with the saved encoder and ranks records by cosine similarity."""

    name = "medquad-minilm"

    def __init__(self, index_dir: Path) -> None:
        import numpy as np
        from sentence_transformers import SentenceTransformer

        self._np = np
        self.manifest: dict[str, Any] = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
        self._embeddings = np.load(index_dir / "embeddings.npy")
        with (index_dir / "records.jsonl").open(encoding="utf-8") as handle:
            self._records = [json.loads(line) for line in handle]
        if len(self._records) != self._embeddings.shape[0]:
            raise ValueError("records.jsonl and embeddings.npy have different lengths; rebuild the index.")
        encoder_dir = index_dir / "encoder"
        # CPU is enough for one short query and keeps the GPU free.
        self._encoder = SentenceTransformer(str(encoder_dir) if encoder_dir.exists() else self.manifest["model"], device="cpu")
        self._lock = threading.Lock()

    def search(self, query: str, k: int = 3) -> list[SearchHit]:
        with self._lock:
            vector = self._encoder.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
        scores = self._embeddings @ vector
        top = self._np.argsort(-scores)[:k]
        return [SearchHit(self._records[int(i)], float(scores[int(i)])) for i in top]


def index_dir() -> Path:
    return get_settings().health_info_index_dir


def index_present() -> bool:
    """Cheap check used by /api/health (does not load the model)."""
    directory = index_dir()
    return all((directory / name).exists() for name in REQUIRED_FILES)


@lru_cache
def get_retriever() -> Retriever | Unavailable:
    """Load the retriever once per process, or explain why it cannot be used."""
    directory = index_dir()
    missing = [name for name in REQUIRED_FILES if not (directory / name).exists()]
    if missing:
        return Unavailable(f"index not built (missing {', '.join(missing)}); run model/health_info/build_index.py")
    try:
        return MedQuADRetriever(directory)
    except ImportError as error:
        return Unavailable(f"optional libraries not installed ({error.name}); see backend/requirements-optional.txt")
    except Exception as error:  # noqa: BLE001 - any load failure means "unavailable", never a crash
        logger.exception("Could not load the MedQuAD index")
        return Unavailable(f"index could not be loaded ({type(error).__name__})")
