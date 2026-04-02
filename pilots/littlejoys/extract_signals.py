"""Extract grounding signals from Littlejoys data.

Feeds into run_grounding_pipeline() via a flat list of plain text strings.
Signal sources (richest first):
  1. first_person_summary — authentic voice, 50-100 words each
  2. purchase_decision_bullets — concrete behavioural triggers
  3. narrative first 200 words — rich behavioural texture
  4. Hardcoded journey insights — validated simulation findings

Usage:
    python pilots/littlejoys/extract_signals.py
"""
from __future__ import annotations

import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LITTLEJOYS_ROOT = os.path.join(
    os.path.dirname(PROJECT_ROOT),
    "1. LittleJoys",
)

PERSONAS_PATH = os.path.join(LITTLEJOYS_ROOT, "data", "population", "personas_generated.json")
SIGNALS_OUT_PATH = os.path.join(LITTLEJOYS_ROOT, "data", "signals", "littlejoys_signals.json")

# ---------------------------------------------------------------------------
# Hardcoded journey insights (validated from journey_A_insights.md + sim data)
# ---------------------------------------------------------------------------

JOURNEY_INSIGHTS = [
    "Pediatrician recommendation is the single strongest first-purchase trigger — 12 of the top first-purchase drivers involved a pediatrician mention of iron deficiency",
    "82.6% reorder rate among first-time buyers who found the product within budget",
    "Price drop was a top first-purchase trigger for price-sensitive parents",
    "Close friend positive WOM was as powerful as pediatrician recommendation for first purchase",
    "Child acceptance/taste was the top reason for lapse — if the child refused it, mothers stopped buying",
    "Subscribe and Save pricing converted hesitant buyers by reducing perceived financial risk",
    "Parents with school fee pressure above 0.8 always evaluated supplements as non-essential first",
    "Willingness to pay mean was ₹656, median ₹649 — products priced above ₹700 face strong price barrier",
    "Authority trust (doctor, FSSAI badge) accelerated trial decision for analytical decision-makers",
    "Joint family elders vetoed supplement purchases in 30% of households with high elder influence",
]


# ---------------------------------------------------------------------------
# Signal extraction
# ---------------------------------------------------------------------------

def _strip_markdown_headers(text: str) -> str:
    """Remove lines starting with # (markdown headers)."""
    lines = [line for line in text.split("\n") if not line.startswith("#")]
    return "\n".join(lines)


def extract_littlejoys_signals() -> list[str]:
    """Extract all grounding signals from Littlejoys data.

    Returns a flat list of text strings for run_grounding_pipeline().
    """
    signals: list[str] = []
    counts: dict[str, int] = {
        "first_person_summary": 0,
        "purchase_decision_bullets": 0,
        "narrative_excerpt": 0,
        "journey_insights": 0,
    }

    # -----------------------------------------------------------------------
    # 1. Load personas
    # -----------------------------------------------------------------------
    if not os.path.exists(PERSONAS_PATH):
        print(f"[ERROR] Personas file not found: {PERSONAS_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(PERSONAS_PATH, encoding="utf-8") as f:
        personas = json.load(f)

    for p in personas:
        # 1a. first_person_summary (50-100 words each — authentic voice)
        summary = p.get("first_person_summary", "")
        if summary and summary.strip():
            signals.append(summary.strip())
            counts["first_person_summary"] += 1

        # 1b. purchase_decision_bullets (8-10 per persona — concrete triggers)
        for bullet in p.get("purchase_decision_bullets", []):
            if bullet and bullet.strip():
                signals.append(bullet.strip())
                counts["purchase_decision_bullets"] += 1

        # 1c. narrative first 200 words (rich behavioural texture)
        narrative = p.get("narrative", "")
        if narrative and narrative.strip():
            clean = _strip_markdown_headers(narrative)
            words = clean.split()[:200]
            excerpt = " ".join(words)
            if excerpt.strip():
                signals.append(excerpt)
                counts["narrative_excerpt"] += 1

    # -----------------------------------------------------------------------
    # 2. Hardcoded journey insights
    # -----------------------------------------------------------------------
    for insight in JOURNEY_INSIGHTS:
        signals.append(insight)
        counts["journey_insights"] += 1

    return signals, counts


# ---------------------------------------------------------------------------
# Save + report
# ---------------------------------------------------------------------------

def save_signals(signals: list[str], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(signals, f, ensure_ascii=False, indent=2)


def main() -> None:
    print("Extracting Littlejoys grounding signals...")
    signals, counts = extract_littlejoys_signals()

    save_signals(signals, SIGNALS_OUT_PATH)

    total = len(signals)
    print(f"\nSignal extraction complete.")
    print(f"  Total signals : {total}")
    print(f"  Breakdown:")
    for source, count in counts.items():
        pct = (count / total * 100) if total else 0
        print(f"    {source:<30} {count:>5}  ({pct:.1f}%)")
    print(f"\nOutput saved to: {SIGNALS_OUT_PATH}")

    if total < 200:
        print(
            f"\n[WARNING] Only {total} signals extracted (pipeline threshold: 200). "
            "Results may be unstable."
        )
    else:
        print(f"\n[OK] Signal count ({total}) exceeds pipeline minimum threshold of 200.")


if __name__ == "__main__":
    main()
