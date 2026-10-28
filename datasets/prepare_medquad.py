"""Download MedQuAD and turn it into one clean JSONL file.

    backend\\.venv\\Scripts\\python.exe datasets\\prepare_medquad.py

Steps
 1. Download the MedQuAD repository zip from GitHub into datasets/raw/
    (skipped if already there). Source: https://github.com/abachaa/MedQuAD
 2. Parse every XML document (backend/app/health_info/medquad.py):
    drop pairs without an answer, medicine-specific question types and stubs.
 3. Remove duplicates and write datasets/processed/medquad.jsonl plus
    datasets/processed/medquad_stats.json (counts per source and type).

Licence: MedQuAD is CC BY 4.0. Cite: Ben Abacha A, Demner-Fushman D.
"A question-entailment approach to question answering." BMC Bioinformatics
20, 511 (2019). Raw and processed files are gitignored (they are rebuilt).
"""

import json
import re
import sys
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.health_info.medquad import dedupe, parse_document  # noqa: E402

ZIP_URL = "https://github.com/abachaa/MedQuAD/archive/refs/heads/master.zip"
RAW_DIR = ROOT / "datasets" / "raw"
PROCESSED_DIR = ROOT / "datasets" / "processed"
ZIP_PATH = RAW_DIR / "MedQuAD-master.zip"
# Refuse anything unexpectedly large (the real zip is a few tens of MB).
MAX_DOWNLOAD_BYTES = 300 * 1024 * 1024
# <QAPair ...> but not the <QAPairs> wrapper.
QA_PAIR_TAG = re.compile(r"<QAPair[\s>]")


def download() -> None:
    if ZIP_PATH.exists():
        print(f"Using existing {ZIP_PATH.relative_to(ROOT)}")
        return
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {ZIP_URL} ...")
    partial = ZIP_PATH.with_suffix(".part")
    total = 0
    with urllib.request.urlopen(ZIP_URL, timeout=60) as response, partial.open("wb") as out:  # noqa: S310 - fixed https URL
        while chunk := response.read(1 << 20):
            total += len(chunk)
            if total > MAX_DOWNLOAD_BYTES:
                raise SystemExit("Download is larger than expected; stopping.")
            out.write(chunk)
    partial.replace(ZIP_PATH)
    print(f"Saved {total / 1e6:.1f} MB")


def build() -> None:
    records = []
    documents = 0
    pairs_seen = 0
    with zipfile.ZipFile(ZIP_PATH) as archive:
        for name in sorted(archive.namelist()):
            if not name.endswith(".xml"):
                continue
            documents += 1
            xml_text = archive.read(name).decode("utf-8", errors="replace")
            pairs_seen += len(QA_PAIR_TAG.findall(xml_text))
            records.extend(parse_document(xml_text))
    unique = dedupe(records)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "medquad.jsonl"
    with out_path.open("w", encoding="utf-8") as out:
        for record in unique:
            out.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    stats = {
        "documents": documents,
        "qa_pairs_in_files": pairs_seen,
        "usable_after_filtering": len(records),
        "after_dedupe": len(unique),
        "by_source": dict(Counter(r.source for r in unique).most_common()),
        "by_qtype": dict(Counter(r.qtype for r in unique).most_common()),
    }
    (PROCESSED_DIR / "medquad_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in stats.items() if not k.startswith("by_")}, indent=2))
    print(f"Wrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    download()
    build()
