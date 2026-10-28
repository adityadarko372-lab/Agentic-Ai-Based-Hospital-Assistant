"""Evaluate the MedQuAD retriever on the hand-written queries.

    backend\\.venv\\Scripts\\python.exe model\\health_info\\evaluate.py [--index DIR] [--out FILE]

Reports, on model/health_info/eval_queries.json:
- Recall@1, Recall@3 and MRR@10 for answerable queries (a hit = the focus of a
  returned record is one of the expected focus names)
- for each similarity threshold: how many answerable queries would still be
  answered with a correct top result, and how many unanswerable (off-topic)
  queries would wrongly get a passage.
Results are written to model/health_info/results.json (committed).
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.health_info.retriever import MedQuADRetriever  # noqa: E402

QUERIES = Path(__file__).with_name("eval_queries.json")
DEFAULT_INDEX = ROOT / "model" / "artifacts" / "health_info"
THRESHOLDS = [0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7]


def evaluate(retriever: MedQuADRetriever, data: dict) -> dict:
    answerable = data["answerable"]
    known_foci = {record["focus"].lower() for record in retriever._records}  # noqa: SLF001
    usable = [item for item in answerable if any(name.lower() in known_foci for name in item["expected"])]
    skipped = [item["query"] for item in answerable if item not in usable]

    recall1 = recall3 = reciprocal = 0.0
    rows = []
    for item in usable:
        expected = {name.lower() for name in item["expected"]}
        hits = retriever.search(item["query"], k=10)
        ranks = [i for i, hit in enumerate(hits, start=1) if hit.record["focus"].lower() in expected]
        rank = ranks[0] if ranks else None
        recall1 += rank == 1
        recall3 += rank is not None and rank <= 3
        reciprocal += 1 / rank if rank else 0
        rows.append({"query": item["query"], "top": hits[0].record["focus"], "score": round(hits[0].score, 3), "rank": rank})

    off_topic = [{"query": q, "top": (h := retriever.search(q, k=1)[0]).record["focus"], "score": round(h.score, 3)} for q in data["unanswerable"]]

    n = len(usable)
    sweep = []
    for threshold in THRESHOLDS:
        answered_correct = sum(1 for row in rows if row["rank"] == 1 and row["score"] >= threshold)
        answered_wrong = sum(1 for row in rows if row["rank"] != 1 and row["score"] >= threshold)
        false_answers = sum(1 for row in off_topic if row["score"] >= threshold)
        sweep.append(
            {
                "threshold": threshold,
                "answerable_answered_correctly": f"{answered_correct}/{n}",
                "answerable_answered_with_wrong_topic": answered_wrong,
                "off_topic_wrongly_answered": f"{false_answers}/{len(off_topic)}",
            }
        )
    return {
        "encoder": retriever.manifest.get("model"),
        "index_records": len(retriever._records),  # noqa: SLF001
        "answerable_queries": n,
        "skipped_queries_topic_not_in_index": skipped,
        "recall_at_1": round(recall1 / n, 3),
        "recall_at_3": round(recall3 / n, 3),
        "mrr_at_10": round(reciprocal / n, 3),
        "threshold_sweep": sweep,
        "per_query": rows,
        "off_topic": off_topic,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("results.json"))
    args = parser.parse_args()
    data = json.loads(QUERIES.read_text(encoding="utf-8"))
    result = evaluate(MedQuADRetriever(args.index), data)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    summary = {k: v for k, v in result.items() if k not in ("per_query", "off_topic")}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
