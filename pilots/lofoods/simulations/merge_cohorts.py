"""merge_cohorts.py — Merge multiple archetype cohorts into a single CohortEnvelope.

Used to combine e.g. C1 + C2 + C3 into a single cohort file for multi-archetype
simulation runs.

Usage:
    python3 merge_cohorts.py C1 C2 C3 --output merged_C1_C2_C3.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PERSONAS_DIR = Path(__file__).resolve().parent.parent / "personas"
OUTPUT_DIR = Path(__file__).resolve().parent / "merged_cohorts"


def _rekey_persona(persona: dict, archetype: str, seen_ids: set) -> dict:
    """Return a copy of persona with a unique ID, re-keyed if the original collides."""
    pid = persona.get("persona_id", "")
    if pid not in seen_ids:
        seen_ids.add(pid)
        return persona
    # Collision: prefix with archetype to make ID unique
    new_pid = f"{archetype.lower()}-{pid}"
    # Keep incrementing suffix until unique
    candidate = new_pid
    counter = 2
    while candidate in seen_ids:
        candidate = f"{new_pid}-{counter}"
        counter += 1
    seen_ids.add(candidate)
    p = dict(persona)
    p["persona_id"] = candidate
    return p


def merge(archetypes: list[str], output_path: Path | None = None) -> Path:
    """Merge cohort files for the given archetypes into one envelope."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    merged_personas = []
    seen_ids: set = set()
    base_envelope = None

    for archetype in archetypes:
        cohort_path = PERSONAS_DIR / f"cohort_{archetype}.json"
        if not cohort_path.exists():
            print(f"  WARNING: cohort_{archetype}.json not found — skipping", file=sys.stderr)
            continue

        with open(cohort_path) as f:
            data = json.load(f)

        personas = data["envelope"]["personas"]
        rekeyed = [_rekey_persona(p, archetype, seen_ids) for p in personas]
        merged_personas.extend(rekeyed)

        if base_envelope is None:
            base_envelope = data.copy()

        collisions = len(personas) - len([p for p in rekeyed if not p["persona_id"].startswith(archetype.lower() + "-")])
        print(f"  + {archetype}: {len(personas)} personas loaded" + (f" ({len(personas) - collisions} re-keyed)" if collisions < len(personas) else ""))

    if not merged_personas:
        raise ValueError(f"No personas found for archetypes: {archetypes}")

    # Build merged envelope
    slug = "_".join(archetypes)
    merged = base_envelope.copy()
    merged["envelope"] = base_envelope["envelope"].copy()
    merged["envelope"]["personas"] = merged_personas
    merged["envelope"]["cohort_id"] = f"merged-{slug}"
    merged["envelope"]["business_problem"] = f"Multi-archetype simulation: {slug}"

    if output_path is None:
        output_path = OUTPUT_DIR / f"merged_{slug}.json"

    with open(output_path, "w") as f:
        json.dump(merged, f, indent=2)

    print(f"  Merged {len(merged_personas)} personas → {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Merge archetype cohorts for simulation")
    parser.add_argument("archetypes", nargs="+", help="Archetype codes e.g. C1 C2 C3")
    parser.add_argument("--output", "-o", type=Path, default=None)
    args = parser.parse_args()

    result = merge(args.archetypes, args.output)
    print(str(result))


if __name__ == "__main__":
    main()
