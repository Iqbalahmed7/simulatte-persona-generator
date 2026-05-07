"""Grounding extractor baseline runner.

Runs src.grounding.signal_extractor.extract_signals against the silver fixture
corpus and computes per-signal-type precision/recall/F1.

Output: benchmarks/grounding_extractor_baseline.json

Usage:
    python -m tests.grounding_baseline.run_baseline

This baseline is post-PR0 (synthetic price_mention fallback removed).
Numbers are silver — they reflect the silver labels Iqbal must adjudicate.
After adjudication, re-run to lock the gold baseline.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from collections import defaultdict

from src.grounding.signal_extractor import extract_signals

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = REPO_ROOT / "tests/fixtures/grounding_baseline/corpus.json"
OUTPUT_PATH = REPO_ROOT / "benchmarks/grounding_extractor_baseline.json"

SIGNAL_TYPES = ["price_mention", "purchase_trigger", "rejection", "switching", "trust_citation"]


def main() -> None:
    corpus = json.loads(CORPUS_PATH.read_text())
    items = corpus["items"]

    # Per-signal-type confusion counters
    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)

    # Per-item details for debugging
    per_item = []

    start = time.perf_counter()
    for item in items:
        text = item["text"]
        expected = set(item["expected_signals"])

        signals = extract_signals([text])
        produced = {s.signal_type for s in signals}

        for st in SIGNAL_TYPES:
            in_exp = st in expected
            in_prod = st in produced
            if in_exp and in_prod:
                tp[st] += 1
            elif in_prod and not in_exp:
                fp[st] += 1
            elif in_exp and not in_prod:
                fn[st] += 1
        per_item.append({
            "id": item["id"],
            "expected": sorted(expected),
            "produced": sorted(produced),
            "missing": sorted(expected - produced),
            "spurious": sorted(produced - expected),
        })
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Compute metrics
    metrics_per_type = {}
    for st in SIGNAL_TYPES:
        precision = tp[st] / (tp[st] + fp[st]) if (tp[st] + fp[st]) else 0.0
        recall = tp[st] / (tp[st] + fn[st]) if (tp[st] + fn[st]) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        metrics_per_type[st] = {
            "tp": tp[st],
            "fp": fp[st],
            "fn": fn[st],
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    # Macro averages
    macro_p = sum(m["precision"] for m in metrics_per_type.values()) / len(SIGNAL_TYPES)
    macro_r = sum(m["recall"] for m in metrics_per_type.values()) / len(SIGNAL_TYPES)
    macro_f1 = sum(m["f1"] for m in metrics_per_type.values()) / len(SIGNAL_TYPES)

    output = {
        "generated_at": "2026-05-01",
        "corpus_id": corpus["corpus_id"],
        "labeler_role": corpus["labeler_role"],
        "adjudication_status": corpus["adjudication_status"],
        "extractor_version": "post-PR0 (synthetic price_mention fallback removed)",
        "n_items": len(items),
        "elapsed_ms": round(elapsed_ms, 2),
        "metrics_per_signal_type": metrics_per_type,
        "macro_average": {
            "precision": round(macro_p, 4),
            "recall": round(macro_r, 4),
            "f1": round(macro_f1, 4),
        },
        "per_item": per_item,
        "notes": [
            "These numbers are silver. Iqbal must adjudicate corpus.json before locking the gold baseline.",
            "Phase 1 acceptance criterion (d) was waived for PR0; this baseline now exists for Phase 4 extractor upgrade comparisons.",
            "When extractor changes, re-run and compare. CI should block any extractor PR without a refreshed baseline.",
        ],
    }

    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Macro F1: {macro_f1:.3f} (precision {macro_p:.3f}, recall {macro_r:.3f})")
    for st, m in metrics_per_type.items():
        print(f"  {st:18s}  P={m['precision']:.2f} R={m['recall']:.2f} F1={m['f1']:.2f}  "
              f"(tp={m['tp']} fp={m['fp']} fn={m['fn']})")


if __name__ == "__main__":
    main()
