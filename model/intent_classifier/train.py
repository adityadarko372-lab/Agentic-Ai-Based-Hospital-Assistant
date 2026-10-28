"""Fine-tune DistilBERT as the optional Nova Health intent classifier.

    backend\\.venv\\Scripts\\python.exe model\\intent_classifier\\train.py [--epochs 4]

Input:  datasets/processed/intent_train.jsonl, intent_val.jsonl (build_dataset.py)
Output: model/artifacts/intent_classifier/ (model, tokenizer, labels.json,
        training_log.json). Uses fp16 mixed precision on a CUDA GPU when
        available (RTX 4060: a few minutes), otherwise CPU.

The checkpoint with the best validation macro-F1 is kept. The hand-written
test set is NOT used here; run evaluate.py afterwards.
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datasets" / "processed"
OUT = ROOT / "model" / "artifacts" / "intent_classifier"
BASE_MODEL = "distilbert-base-uncased"
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.intent.classifier import INTENTS  # noqa: E402
from app.agents.text import normalise  # noqa: E402


def read(name: str) -> list[dict]:
    return [json.loads(line) for line in (DATA / name).open(encoding="utf-8")]


def macro_f1(golds: list[int], preds: list[int], n: int) -> float:
    scores = []
    for label in range(n):
        tp = sum(1 for g, p in zip(golds, preds) if g == p == label)
        fp = sum(1 for g, p in zip(golds, preds) if p == label and g != label)
        fn = sum(1 for g, p in zip(golds, preds) if g == label and p != label)
        if tp + fp + fn == 0:
            continue
        scores.append(2 * tp / (2 * tp + fp + fn))
    return sum(scores) / len(scores)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    labels = list(INTENTS)
    label_id = {label: i for i, label in enumerate(labels)}
    train_rows, val_rows = read("intent_train.jsonl"), read("intent_val.jsonl")
    print(f"train {len(train_rows)}, val {len(val_rows)}, device {device} {torch.cuda.get_device_name(0) if device.type == 'cuda' else ''}")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL, num_labels=len(labels), id2label=dict(enumerate(labels)), label2id=label_id
    ).to(device)

    def collate(batch: list[dict]):
        # Same normalisation as the backend applies before classifying.
        encoded = tokenizer([normalise(row["text"]) for row in batch], padding=True, truncation=True, max_length=64, return_tensors="pt")
        encoded["labels"] = torch.tensor([label_id[row["label"]] for row in batch])
        return encoded

    # Inverse-frequency class weights: small classes (e.g. appointment_status)
    # count as much as large ones (out_of_scope) in the loss.
    counts = [max(1, sum(1 for row in train_rows if row["label"] == label)) for label in labels]
    class_weights = torch.tensor([len(train_rows) / (len(labels) * c) for c in counts], dtype=torch.float32, device=device)
    loss_fn = torch.nn.CrossEntropyLoss(weight=class_weights)

    train_loader = DataLoader(train_rows, batch_size=args.batch_size, shuffle=True, collate_fn=collate)
    val_loader = DataLoader(val_rows, batch_size=128, collate_fn=collate)
    optimiser = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    total_steps = len(train_loader) * args.epochs
    scheduler = get_linear_schedule_with_warmup(optimiser, int(0.1 * total_steps), total_steps)
    use_amp = device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    history, best_f1 = [], -1.0
    started = time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        model.train()
        running = 0.0
        for batch in train_loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            optimiser.zero_grad()
            targets = batch.pop("labels")
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                logits = model(**batch).logits
            loss = loss_fn(logits.float(), targets)
            scaler.scale(loss).backward()
            scaler.unscale_(optimiser)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimiser)
            scaler.update()
            scheduler.step()
            running += loss.item()

        model.eval()
        golds, preds = [], []
        with torch.no_grad():
            for batch in val_loader:
                batch = {k: v.to(device) for k, v in batch.items()}
                with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                    logits = model(**{k: v for k, v in batch.items() if k != "labels"}).logits
                preds += logits.argmax(-1).tolist()
                golds += batch["labels"].tolist()
        accuracy = sum(g == p for g, p in zip(golds, preds)) / len(golds)
        f1 = macro_f1(golds, preds, len(labels))
        record = {"epoch": epoch, "train_loss": round(running / len(train_loader), 4), "val_accuracy": round(accuracy, 4), "val_macro_f1": round(f1, 4)}
        history.append(record)
        print(record)
        if f1 > best_f1:
            best_f1 = f1
            OUT.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(OUT)
            tokenizer.save_pretrained(OUT)

    log = {
        "base_model": BASE_MODEL,
        "labels": labels,
        "train_examples": len(train_rows),
        "val_examples": len(val_rows),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.lr,
        "fp16": use_amp,
        "class_weighted_loss": True,
        "train_label_counts": dict(zip(labels, counts)),
        "device": torch.cuda.get_device_name(0) if use_amp else "cpu",
        "seconds": round(time.perf_counter() - started, 1),
        "best_val_macro_f1": round(best_f1, 4),
        "history": history,
    }
    (OUT / "labels.json").write_text(json.dumps(labels), encoding="utf-8")
    (OUT / "training_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in log.items() if k != "history"}, indent=2))


if __name__ == "__main__":
    main()
