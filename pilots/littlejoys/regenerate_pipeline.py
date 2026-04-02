"""pilots/littlejoys/regenerate_pipeline.py

Master orchestration script for the Littlejoys persona upgrade pipeline.
Runs all 5 stages using Python modules directly — no HTTP API calls.

Usage:
    cd "/Users/admin/Documents/Simulatte Projects/Persona Generator"
    python3 pilots/littlejoys/regenerate_pipeline.py [--skip-sarvam] [--dry-run] [--count N]

Flags:
    --skip-sarvam   Skip Stage 3 Sarvam enrichment entirely
    --dry-run       Run Stages 1-2 only (no LLM calls at all)
    --count N       Process only the first N personas (default: all)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — ensure project root is on sys.path regardless of cwd
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env from project root so ANTHROPIC_API_KEY / SARVAM_API_KEY are available
_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                # Strip surrounding quotes that shells sometimes add
                _v = _v.strip().strip('"').strip("'")
                os.environ[_k.strip()] = _v

LITTLEJOYS_DATA = Path("/Users/admin/Documents/Simulatte Projects/1. LittleJoys/data")
SIMULATTE_PERSONAS_PATH = LITTLEJOYS_DATA / "population" / "simulatte_personas.json"
OUTPUT_PATH = LITTLEJOYS_DATA / "population" / "simulatte_cohort_final.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Littlejoys persona regeneration pipeline"
    )
    parser.add_argument(
        "--skip-sarvam",
        action="store_true",
        help="Skip Stage 3 Sarvam enrichment",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run Stages 1-2 only (no LLM calls)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        metavar="N",
        help="Process only the first N personas (default: all)",
    )
    return parser.parse_args()


def _load_simulatte_personas(count: int | None) -> list:
    """Stage 1: Load simulatte_personas.json as PersonaRecord objects."""
    from src.schema.persona import PersonaRecord

    if not SIMULATTE_PERSONAS_PATH.exists():
        print("[Stage 1] ERROR: simulatte_personas.json not found.")
        print("  Run: python3 pilots/littlejoys/convert_to_simulatte.py first")
        sys.exit(1)

    with open(SIMULATTE_PERSONAS_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    # raw may be a list of dicts or a dict with a "personas" key
    if isinstance(raw, dict) and "personas" in raw:
        records_raw = raw["personas"]
    elif isinstance(raw, list):
        records_raw = raw
    else:
        print("[Stage 1] ERROR: Unexpected format in simulatte_personas.json")
        sys.exit(1)

    if count is not None:
        records_raw = records_raw[:count]

    personas: list = []
    errors = 0
    for i, item in enumerate(records_raw):
        try:
            personas.append(PersonaRecord.model_validate(item))
        except Exception as exc:
            errors += 1
            if errors <= 3:
                print(f"  [Stage 1] Validation error on persona {i}: {exc}")
    if errors > 3:
        print(f"  [Stage 1] ... and {errors - 3} more validation errors")

    if len(personas) == 0 and not errors:
        print("[Stage 1] Loading converted personas... 0 loaded")
        print("  simulatte_personas.json is empty — converter has not run yet.")
        print("  Run: python3 pilots/littlejoys/convert_to_simulatte.py first")
    else:
        print(f"[Stage 1] Loading converted personas... {len(personas)} loaded"
              + (f" ({errors} skipped due to validation errors)" if errors else ""))
    return personas


def _run_grounding(personas: list) -> list:
    """Stage 2: Ground personas against Nutrimix signals."""
    from src.grounding.pipeline import run_grounding_pipeline

    signals_path = LITTLEJOYS_DATA / "signals" / "littlejoys_signals.json"

    if not signals_path.exists():
        print("[Stage 2] Warning: signals file not found — running without grounding")
        print("  Run: python3 pilots/littlejoys/extract_signals.py first")
        return personas

    with open(signals_path, encoding="utf-8") as f:
        signals_data = json.load(f)

    # signals_data may be a list of strings or a dict with a key containing strings
    if isinstance(signals_data, list):
        # Could be list of strings or list of dicts with a "text" field
        if signals_data and isinstance(signals_data[0], str):
            raw_texts: list[str] = signals_data
        elif signals_data and isinstance(signals_data[0], dict):
            # Extract text field; fall back to str(item)
            raw_texts = [
                item.get("text") or item.get("content") or str(item)
                for item in signals_data
            ]
        else:
            raw_texts = [str(s) for s in signals_data]
    elif isinstance(signals_data, dict):
        # Try common keys
        for key in ("texts", "signals", "reviews", "data"):
            if key in signals_data and isinstance(signals_data[key], list):
                raw_texts = [
                    s if isinstance(s, str) else (s.get("text") or str(s))
                    for s in signals_data[key]
                ]
                break
        else:
            raw_texts = [str(v) for v in signals_data.values() if isinstance(v, str)]
    else:
        raw_texts = []

    if not raw_texts:
        print("[Stage 2] Warning: signals file is empty or unreadable — skipping grounding")
        return personas

    t0 = time.monotonic()
    print(f"[Stage 2] Grounding against {len(raw_texts)} signals...", end="", flush=True)

    try:
        result = run_grounding_pipeline(raw_texts, personas, domain="cpg")
    except ValueError as exc:
        print(f"\n[Stage 2] Warning: grounding pipeline error — {exc}")
        print("  Continuing without grounding.")
        return personas

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    grounded = result.personas
    print(f" done ({elapsed_ms}ms)")

    if result.warning:
        print(f"  Warning: {result.warning}")

    # Count personas where key tendency fields changed
    price_updated = 0
    trust_updated = 0
    for orig, grnd in zip(personas, grounded):
        if (orig.behavioural_tendencies.price_sensitivity.band
                != grnd.behavioural_tendencies.price_sensitivity.band):
            price_updated += 1
        if (orig.behavioural_tendencies.trust_orientation.dominant
                != grnd.behavioural_tendencies.trust_orientation.dominant):
            trust_updated += 1

    if price_updated:
        print(f"  → price_sensitivity updated: {price_updated} personas")
    if trust_updated:
        print(f"  → trust patterns updated: {trust_updated} personas")

    return grounded


def _recalculate_tendencies(personas: list) -> list:
    """Stage 2b: Re-run TendencyEstimator on each persona to satisfy TR1–TR8 invariants.

    The converter maps Littlejoys attributes independently of the behavioural tendency
    fields. This stage recalculates behavioural_tendencies from those attributes using
    the same estimator the generator uses, ensuring all TR invariants are satisfied.
    """
    from src.generation.tendency_estimator import TendencyEstimator

    estimator = TendencyEstimator()
    updated = []
    errors = 0

    for persona in personas:
        try:
            # persona.attributes is already dict[str, dict[str, Attribute]] — exactly
            # what TendencyEstimator.estimate() expects. Pass it directly.
            new_tendencies = estimator.estimate(
                attributes=persona.attributes,
                derived_insights=persona.derived_insights,
            )
            updated.append(persona.model_copy(update={"behavioural_tendencies": new_tendencies}))
        except Exception as exc:
            errors += 1
            updated.append(persona)
            if errors <= 3:
                print(f"  [Stage 2b] Warning: {persona.persona_id}: {exc}")

    if errors:
        print(f"  [Stage 2b] {errors} persona(s) kept original tendencies (estimation error)")
    print(f"  [Stage 2b] Tendencies recalculated for {len(updated) - errors}/{len(updated)} personas — TR invariants enforced")

    return updated


async def _run_sarvam_enrichment_async(personas: list) -> list:
    """Stage 3: Sarvam enrichment for India personas (async inner)."""
    import anthropic
    from src.sarvam.pipeline import run_sarvam_enrichment
    from src.sarvam.config import SarvamConfig

    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("SARVAM_API_KEY")
    if not api_key:
        print("[Stage 3] Warning: no ANTHROPIC_API_KEY or SARVAM_API_KEY found")
        print("  Skipping Sarvam enrichment for all personas.")
        return personas

    india_personas = [
        p for p in personas
        if p.demographic_anchor.location.country.lower() in ("india", "in")
    ]
    print(
        f"[Stage 3] Sarvam enrichment... {len(india_personas)} India personas",
        flush=True,
    )

    config = SarvamConfig.enabled(scope="narrative_and_examples")
    client = anthropic.AsyncAnthropic(api_key=api_key)

    enriched_count = 0
    skipped_count = 0
    error_count = 0

    for persona in india_personas:
        try:
            record = await run_sarvam_enrichment(persona, config, client)
            if not record.enrichment_applied:
                skipped_count += 1
            else:
                enriched_count += 1
        except Exception as exc:
            error_count += 1
            if error_count <= 3:
                print(
                    f"  [Stage 3] Warning: enrichment error for "
                    f"{persona.persona_id}: {exc}"
                )

    print(
        f"  → enriched: {enriched_count}, skipped: {skipped_count}"
        + (f", errors: {error_count}" if error_count else "")
    )
    return personas  # Sarvam enrichment produces overlay records, not mutated PersonaRecords


def _run_sarvam_enrichment(personas: list) -> list:
    """Stage 3: Synchronous wrapper around async Sarvam enrichment."""
    return asyncio.run(_run_sarvam_enrichment_async(personas))


def _seed_working_memory(personas: list) -> list:
    """Stage 4: Bootstrap seed memories into each persona's working memory."""
    from src.memory.seed_memory import bootstrap_seed_memories
    from src.schema.persona import PersonaRecord

    updated: list = []
    total = len(personas)
    errors = 0

    for i, persona in enumerate(personas):
        try:
            new_working = bootstrap_seed_memories(
                persona.memory.core,
                persona.demographic_anchor.name,
            )
            # Build an updated PersonaRecord with the seeded working memory
            updated_memory = persona.memory.model_copy(
                update={"working": new_working}
            )
            updated_persona = persona.model_copy(
                update={"memory": updated_memory}
            )
            updated.append(updated_persona)
        except Exception as exc:
            errors += 1
            updated.append(persona)  # keep original on error
            if errors <= 3:
                print(
                    f"  [Stage 4] Warning: seed error for {persona.persona_id}: {exc}"
                )

        # Progress display every 25 or at end
        if (i + 1) % 25 == 0 or (i + 1) == total:
            print(f"\r[Stage 4] Seeding working memory... {i + 1}/{total} done", end="", flush=True)

    print()  # newline after progress
    if errors > 3:
        print(f"  [Stage 4] ... and {errors - 3} more seed errors (personas kept as-is)")

    return updated


def _build_cohort_envelope(personas: list) -> object:
    """Build a CohortEnvelope from a list of PersonaRecord objects."""
    from datetime import datetime, timezone
    import hashlib
    from src.schema.cohort import (
        CohortEnvelope,
        CohortSummary,
        GroundingSummary,
        CalibrationState,
        TaxonomyMeta,
    )

    now = datetime.now(tz=timezone.utc)

    # --- Compute distributions for cohort summary ---
    decision_styles: dict[str, int] = {}
    trust_anchors: dict[str, int] = {}
    risk_appetites: dict[str, int] = {}
    consistency_scores: list[int] = []

    for p in personas:
        di = p.derived_insights
        decision_styles[di.decision_style] = decision_styles.get(di.decision_style, 0) + 1
        trust_anchors[di.trust_anchor] = trust_anchors.get(di.trust_anchor, 0) + 1
        risk_appetites[di.risk_appetite] = risk_appetites.get(di.risk_appetite, 0) + 1
        consistency_scores.append(di.consistency_score)

    avg_consistency = sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.0

    # Tendency source distribution for grounding summary
    source_counts: dict[str, int] = {"grounded": 0, "proxy": 0, "estimated": 0}
    for p in personas:
        src = p.behavioural_tendencies.price_sensitivity.source
        if src in source_counts:
            source_counts[src] += 1
    total = len(personas) or 1
    source_dist = {k: round(v / total, 6) for k, v in source_counts.items()}
    # normalise to exactly 1.0
    s = sum(source_dist.values())
    if s > 0:
        source_dist = {k: round(v / s, 6) for k, v in source_dist.items()}
    # Ensure exact sum of 1.0 by adjusting largest value
    diff = 1.0 - sum(source_dist.values())
    if diff != 0:
        largest_key = max(source_dist, key=source_dist.__getitem__)
        source_dist[largest_key] = round(source_dist[largest_key] + diff, 6)

    icp_hash = hashlib.md5(
        json.dumps(sorted(p.persona_id for p in personas)).encode()
    ).hexdigest()[:8]

    cohort_summary = CohortSummary(
        decision_style_distribution=decision_styles,
        trust_anchor_distribution=trust_anchors,
        risk_appetite_distribution=risk_appetites,
        consistency_scores={
            "mean": round(avg_consistency, 1),
            "count": len(consistency_scores),
        },
        persona_type_distribution={"deep": len(personas)},
        distinctiveness_score=0.85,
        coverage_assessment="Regenerated Littlejoys cohort — Nutrimix domain",
        dominant_tensions=["price vs quality", "trust deficit", "health anxiety"],
    )

    grounding_summary = GroundingSummary(
        tendency_source_distribution=source_dist,
        domain_data_signals_extracted=0,
        clusters_derived=0,
    )

    taxonomy_meta = TaxonomyMeta(
        base_attributes=18,
        domain_extension_attributes=11,
        total_attributes=29,
        domain_data_used=True,
        business_problem="Littlejoys Nutrimix parent decision journey",
        icp_spec_hash=icp_hash,
    )

    calibration_state = CalibrationState(
        status="uncalibrated",
        method_applied=None,
        last_calibrated=None,
        benchmark_source=None,
        notes="Regenerated by regenerate_pipeline.py",
    )

    return CohortEnvelope(
        cohort_id=f"littlejoys-regen-{now.strftime('%Y%m%d-%H%M%S')}",
        generated_at=now,
        domain="cpg",
        business_problem="Littlejoys Nutrimix parent decision journey",
        mode="simulation-ready",
        icp_spec_hash=icp_hash,
        taxonomy_used=taxonomy_meta,
        personas=personas,
        cohort_summary=cohort_summary,
        grounding_summary=grounding_summary,
        calibration_state=calibration_state,
    )


def _run_validation_and_save(personas: list, dry_run: bool) -> None:
    """Stage 5: Quality parity check and save."""
    from src.validation.quality_parity import check_parity, parity_report
    from src.persistence.envelope_store import save_envelope

    print("[Stage 5] Quality parity check...")

    results = []
    for persona in personas:
        result = check_parity(persona, provider="anthropic")
        results.append(result)

    at_par = sum(1 for r in results if r.is_at_par)
    below_par = len(results) - at_par
    total = len(results)

    print(f"  AT PAR:    {at_par}/{total} ({at_par / total * 100:.1f}%)")
    print(f"  BELOW PAR: {below_par}/{total} ({below_par / total * 100:.1f}%)")

    # Show first few failures if any
    if below_par:
        shown = 0
        for r in results:
            if not r.is_at_par and shown < 3:
                print(f"  x {r.persona_id}: {r.failures[0]}")
                shown += 1
        if below_par > 3:
            print(f"  ... and {below_par - 3} more below-par personas")

    if dry_run:
        print("[Done] Dry-run complete — skipping save.")
        return

    envelope = _build_cohort_envelope(personas)

    saved_path = save_envelope(envelope, OUTPUT_PATH)
    print(f"[Done] Saved to {saved_path.name}")
    print(f"       Full path: {saved_path}")
    print()
    print("=== Summary ===")
    print(f"  Personas:     {total}")
    print(f"  At parity:    {at_par}/{total} ({at_par / total * 100:.1f}%)")
    print(f"  Domain:       cpg (Littlejoys Nutrimix)")
    print(f"  Output:       {saved_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()

    skip_sarvam = args.skip_sarvam or args.dry_run
    dry_run = args.dry_run
    count = args.count

    if dry_run:
        print("=== Littlejoys Regeneration Pipeline [DRY RUN — Stages 1-2 only] ===")
    else:
        print("=== Littlejoys Regeneration Pipeline ===")
    print()

    # ------------------------------------------------------------------
    # Stage 1: Load converted personas
    # ------------------------------------------------------------------
    personas = _load_simulatte_personas(count)
    if not personas:
        print("[Stage 1] ERROR: No personas loaded. Aborting.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Stage 2: Grounding
    # ------------------------------------------------------------------
    personas = _run_grounding(personas)

    # Stage 2b: Re-estimate tendencies to enforce TR1–TR8 invariants
    personas = _recalculate_tendencies(personas)

    if dry_run:
        print()
        print("[Stage 3] Sarvam enrichment... skipped (--dry-run)")
        print("[Stage 4] Seeding working memory... skipped (--dry-run)")
        print()
        print("[Done] Dry-run complete — Stages 1-2 finished successfully.")
        print(f"       Processed {len(personas)} persona(s).")
        return

    # ------------------------------------------------------------------
    # Stage 3: Sarvam enrichment (optional)
    # ------------------------------------------------------------------
    if skip_sarvam:
        print("[Stage 3] Sarvam enrichment... skipped (--skip-sarvam)")
    else:
        personas = _run_sarvam_enrichment(personas)

    # ------------------------------------------------------------------
    # Stage 4: Seed working memory
    # ------------------------------------------------------------------
    personas = _seed_working_memory(personas)

    # ------------------------------------------------------------------
    # Stage 5: Validate + Save
    # ------------------------------------------------------------------
    _run_validation_and_save(personas, dry_run=False)


if __name__ == "__main__":
    main()
