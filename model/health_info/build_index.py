"""Build the MedQuAD search index used by the optional Health Information Agent.

    backend\\.venv\\Scripts\\python.exe model\\health_info\\build_index.py [--encoder PATH]

Input:  datasets/processed/medquad.jsonl   (datasets/prepare_medquad.py)
Output: model/artifacts/health_info/
            encoder/         the sentence encoder, saved locally (offline use)
            embeddings.npy   one normalised vector per question
            records.jsonl    the records in the same order
            manifest.json    model, counts, build time, device

Each record is embedded as "<focus>: <question>" so the topic name carries
weight. Runs on the GPU if available (about a minute on an RTX 4060).
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datasets" / "processed" / "medquad.jsonl"
OUT = ROOT / "model" / "artifacts" / "health_info"
BASE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def embed_text(record: dict) -> str:
    return f"{record['focus']}: {record['question']}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--encoder", default=BASE_MODEL, help="model name or path (e.g. a fine-tuned encoder)")
    args = parser.parse_args()

    import numpy as np
    import torch
    from sentence_transformers import SentenceTransformer

    if not DATA.exists():
        sys.exit("datasets/processed/medquad.jsonl is missing; run datasets/prepare_medquad.py first.")
    records = [json.loads(line) for line in DATA.open(encoding="utf-8")]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"{len(records)} records, encoder {args.encoder}, device {device}")

    encoder = SentenceTransformer(args.encoder, device=device)
    started = time.perf_counter()
    embeddings = encoder.encode(
        [embed_text(r) for r in records], batch_size=256, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=True
    ).astype(np.float32)
    seconds = time.perf_counter() - started

    OUT.mkdir(parents=True, exist_ok=True)
    encoder.save(str(OUT / "encoder"))
    np.save(OUT / "embeddings.npy", embeddings)
    with (OUT / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    manifest = {
        "model": args.encoder,
        "records": len(records),
        "dimensions": int(embeddings.shape[1]),
        "embedded_text": "focus: question",
        "device": device,
        "encode_seconds": round(seconds, 1),
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": "MedQuAD (CC BY 4.0), https://github.com/abachaa/MedQuAD",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
