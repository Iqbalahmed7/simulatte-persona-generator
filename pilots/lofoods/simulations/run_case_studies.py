"""run_case_studies.py — Master runner for Lo! Foods case study simulations.

Runs all available case studies based on which cohort files exist.
Each case study: merge required cohorts → run simulation → save results.

Usage:
    # Run all available case studies (SIGNAL tier — for prep/iteration)
    python3 run_case_studies.py

    # Run specific case studies
    python3 run_case_studies.py --studies CS1 CS2 CS3

    # Final deliverable run (DEEP tier — use only when output goes into a deck/demo)
    python3 run_case_studies.py --studies CS1 CS2 --deliver

    # Dry run (show what would run, no execution)
    python3 run_case_studies.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
PERSONAS_DIR = BASE.parent / "personas"
SCENARIOS_DIR = BASE / "scenarios"
RESULTS_DIR = BASE / "results"
MERGED_DIR = BASE / "merged_cohorts"
PG_ROOT = BASE.parent.parent.parent  # Persona Generator root

# ---------------------------------------------------------------------------
# Case study definitions
# ---------------------------------------------------------------------------
CASE_STUDIES = {
    "CS1": {
        "title": "Brand Architecture",
        "cohorts": ["C1", "C2", "C3"],
        "scenario": SCENARIOS_DIR / "scenario_CS1_brand_architecture.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "isolated",
        "social_topology": None,
    },
    "CS2": {
        "title": "Keto to Protein Pivot",
        "cohorts": ["C2", "C3"],
        "scenario": SCENARIOS_DIR / "scenario_CS2_keto_protein_pivot.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "moderate",
        "social_topology": "full_mesh",
    },
    "CS3": {
        "title": "Price Sensitivity",
        "cohorts": ["C3", "C4"],
        "scenario": SCENARIOS_DIR / "scenario_CS3_price_sensitivity.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "isolated",
        "social_topology": None,
    },
    "CS11": {
        "title": "Competitive Defense vs Big FMCG",
        "cohorts": ["C1", "C2", "C3"],
        "scenario": SCENARIOS_DIR / "scenario_CS11_competitive_defense.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "moderate",
        "social_topology": "full_mesh",
    },
    "CS16": {
        "title": "Packaging and Shelf Life",
        "cohorts": ["C1", "C3", "C5"],
        "scenario": SCENARIOS_DIR / "scenario_CS16_packaging_shelf_life.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "isolated",
        "social_topology": None,
    },
    "CS4": {
        "title": "Quick Commerce Discoverability",
        "cohorts": ["C5", "C12"],
        "scenario": SCENARIOS_DIR / "scenario_CS4_quick_commerce.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "isolated",
        "social_topology": None,
    },
    "CS6": {
        "title": "DiabeSmart Trust and Medical Credibility",
        "cohorts": ["C7", "C8"],
        "scenario": SCENARIOS_DIR / "scenario_CS6_diabesmart_trust.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "isolated",
        "social_topology": None,
    },
    "CS7": {
        "title": "Tier 2-3 City Expansion",
        "cohorts": ["C1", "C9"],
        "scenario": SCENARIOS_DIR / "scenario_CS7_tier2_expansion.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "low",
        "social_topology": None,
    },
    "CS9": {
        "title": "Protein Bread Category Creation",
        "cohorts": ["C3", "C4", "C6"],
        "scenario": SCENARIOS_DIR / "scenario_CS9_protein_category.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "isolated",
        "social_topology": None,
    },
    "CS14": {
        "title": "Influencer and Content Strategy",
        "cohorts": ["C1", "C2", "C3", "C12"],
        "scenario": SCENARIOS_DIR / "scenario_CS14_influencer_strategy.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "moderate",
        "social_topology": "full_mesh",
    },
    "CS15": {
        "title": "Gluten Smart Real Demand or Trend",
        "cohorts": ["C10", "C11", "C1"],
        "scenario": SCENARIOS_DIR / "scenario_CS15_gluten_smart.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "isolated",
        "social_topology": None,
    },
    "CS5": {
        "title": "Cloud Kitchen vs Packaged Cannibalization",
        "cohorts": ["C1", "C2", "C15"],
        "scenario": SCENARIOS_DIR / "scenario_CS5_cloud_kitchen_vs_packaged.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "isolated",
        "social_topology": None,
    },
    "CS8": {
        "title": "Subscription Model Viability",
        "cohorts": ["C1", "C5", "C15"],
        "scenario": SCENARIOS_DIR / "scenario_CS8_subscription_model.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "isolated",
        "social_topology": None,
    },
    "CS10": {
        "title": "Amazon Listing Optimisation",
        "cohorts": ["C1", "C2", "C13"],
        "scenario": SCENARIOS_DIR / "scenario_CS10_amazon_listing.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "isolated",
        "social_topology": None,
    },
    "CS12": {
        "title": "Offline Retail Entry Strategy",
        "cohorts": ["C1", "C3", "C4", "C13"],
        "scenario": SCENARIOS_DIR / "scenario_CS12_offline_retail.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "isolated",
        "social_topology": None,
    },
    "CS13": {
        "title": "Fresh vs Packaged Which Channel Scales",
        "cohorts": ["C1", "C5", "C15"],
        "scenario": SCENARIOS_DIR / "scenario_CS13_fresh_vs_packaged_scale.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "isolated",
        "social_topology": None,
    },
    "CS17": {
        "title": "B2B Channel Hospitals and Corporates",
        "cohorts": ["P1", "P2", "P4"],
        "scenario": SCENARIOS_DIR / "scenario_CS17_b2b_channel.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "isolated",
        "social_topology": None,
    },
    "CS18": {
        "title": "Customer Retention and Repeat Purchase",
        "cohorts": ["C1", "C3", "C14"],
        "scenario": SCENARIOS_DIR / "scenario_CS18_customer_retention.json",
        "rounds": 3,
        "tier": "signal",
        "social_level": "isolated",
        "social_topology": None,
    },
}


def cohort_available(archetype: str) -> bool:
    path = PERSONAS_DIR / f"cohort_{archetype}.json"
    if not path.exists():
        return False
    # Quick validity check
    try:
        with open(path) as f:
            data = json.load(f)
        return len(data["envelope"]["personas"]) > 0
    except Exception:
        return False


def check_availability() -> dict[str, dict]:
    """Return availability status for all case studies."""
    status = {}
    for cs_id, cs in CASE_STUDIES.items():
        missing = [c for c in cs["cohorts"] if not cohort_available(c)]
        scenario_ready = cs["scenario"] is not None and cs["scenario"].exists()
        status[cs_id] = {
            "title": cs["title"],
            "cohorts": cs["cohorts"],
            "missing_cohorts": missing,
            "scenario_ready": scenario_ready,
            "runnable": len(missing) == 0 and scenario_ready,
        }
    return status


def _rekey_persona(persona: dict, archetype: str, seen_ids: set) -> dict:
    """Return a copy of persona with a unique ID, re-keyed if the original collides."""
    pid = persona.get("persona_id", "")
    if pid not in seen_ids:
        seen_ids.add(pid)
        return persona
    new_pid = f"{archetype.lower()}-{pid}"
    candidate = new_pid
    counter = 2
    while candidate in seen_ids:
        candidate = f"{new_pid}-{counter}"
        counter += 1
    seen_ids.add(candidate)
    p = dict(persona)
    p["persona_id"] = candidate
    return p


def merge_cohorts(archetypes: list[str]) -> Path:
    """Merge cohort files and return path to merged file. Re-keys colliding IDs."""
    MERGED_DIR.mkdir(exist_ok=True)
    slug = "_".join(archetypes)
    output_path = MERGED_DIR / f"merged_{slug}.json"

    merged_personas = []
    seen_ids: set = set()
    base_envelope = None

    for archetype in archetypes:
        cohort_path = PERSONAS_DIR / f"cohort_{archetype}.json"
        with open(cohort_path) as f:
            data = json.load(f)
        personas = data["envelope"]["personas"]
        rekeyed = [_rekey_persona(p, archetype, seen_ids) for p in personas]
        merged_personas.extend(rekeyed)
        if base_envelope is None:
            base_envelope = data.copy()

    merged = base_envelope.copy()
    merged["envelope"] = base_envelope["envelope"].copy()
    merged["envelope"]["personas"] = merged_personas
    merged["envelope"]["cohort_id"] = f"merged-{slug}"
    merged["envelope"]["business_problem"] = f"Lo! Foods multi-archetype: {slug}"

    with open(output_path, "w") as f:
        json.dump(merged, f, indent=2)

    return output_path


def run_simulation(cs_id: str, cs: dict, dry_run: bool = False) -> dict:
    """Run a single case study simulation."""
    RESULTS_DIR.mkdir(exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  {cs_id}: {cs['title']}")
    print(f"  Cohorts: {' + '.join(cs['cohorts'])} ({sum(1 for c in cs['cohorts'] if cohort_available(c))*10} personas)")
    print(f"  Social: {cs['social_level']}" + (f" / {cs['social_topology']}" if cs['social_topology'] else ""))
    print(f"  Rounds: {cs['rounds']} | Tier: {cs['tier']}")

    # Merge cohorts
    if len(cs["cohorts"]) == 1:
        cohort_path = PERSONAS_DIR / f"cohort_{cs['cohorts'][0]}.json"
    else:
        print(f"  Merging cohorts...")
        cohort_path = merge_cohorts(cs["cohorts"])

    output_path = RESULTS_DIR / f"sim_{cs_id}.json"

    cmd = [
        sys.executable, "-m", "src.cli", "simulate",
        "--cohort", str(cohort_path),
        "--scenario", str(cs["scenario"]),
        "--rounds", str(cs["rounds"]),
        "--tier", cs["tier"],
        "--social-level", cs["social_level"],
        "--output", str(output_path),
    ]
    if cs.get("social_topology"):
        cmd += ["--social-topology", cs["social_topology"]]

    print(f"  Output: {output_path.name}")

    if dry_run:
        print(f"  [DRY RUN] Would execute: {' '.join(cmd)}")
        return {"cs_id": cs_id, "status": "dry_run"}

    start = time.time()
    result = subprocess.run(cmd, cwd=str(PG_ROOT), capture_output=True, text=True)
    elapsed = time.time() - start

    if result.returncode == 0:
        # Verify output
        try:
            with open(output_path) as f:
                sim_data = json.load(f)
            n_personas = len(sim_data.get("results", []))
            print(f"  ✅ Done in {elapsed:.0f}s — {n_personas} persona results")
            return {"cs_id": cs_id, "status": "success", "elapsed": elapsed, "output": str(output_path)}
        except Exception as e:
            print(f"  ⚠️  Output parse error: {e}")
            return {"cs_id": cs_id, "status": "output_error", "error": str(e)}
    else:
        error_snippet = (result.stderr or result.stdout or "")[-500:]
        print(f"  ❌ Failed in {elapsed:.0f}s")
        print(f"  Error: {error_snippet}")
        return {"cs_id": cs_id, "status": "failed", "error": error_snippet}


def main():
    parser = argparse.ArgumentParser(description="Run Lo! Foods case study simulations")
    parser.add_argument("--studies", nargs="*", default=None,
                        help="Case study IDs to run (default: all available)")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")
    parser.add_argument("--status", action="store_true", help="Show availability status and exit")
    parser.add_argument(
        "--deliver",
        action="store_true",
        help="Use DEEP tier (Sonnet reflect). Only for final outputs going into a deck or demo. "
             "Default is SIGNAL tier (Haiku reflect, ~47%% cheaper) for prep/iteration runs.",
    )
    args = parser.parse_args()

    availability = check_availability()

    if args.status:
        print("\n=== Lo! Foods Case Study Availability ===\n")
        for cs_id, info in availability.items():
            icon = "✅" if info["runnable"] else ("⏳" if not info["missing_cohorts"] else "❌")
            missing = f" [missing: {', '.join(info['missing_cohorts'])}]" if info["missing_cohorts"] else ""
            scenario = "" if info["scenario_ready"] else " [no scenario]"
            print(f"  {icon} {cs_id}: {info['title']}{missing}{scenario}")
        return

    # Determine which studies to run
    if args.studies:
        to_run = args.studies
    else:
        to_run = [cs_id for cs_id, info in availability.items() if info["runnable"]]

    runnable = [cs_id for cs_id in to_run if availability[cs_id]["runnable"]]
    skipped = [cs_id for cs_id in to_run if not availability[cs_id]["runnable"]]

    tier_override = "deep" if args.deliver else None

    print(f"\n=== Lo! Foods Simulation Runner ===")
    print(f"  Mode: {'DELIVER (DEEP tier)' if args.deliver else 'EXPLORE (SIGNAL tier — prep/iteration)'}")
    print(f"  Runnable: {runnable}")
    if skipped:
        print(f"  Skipped (not ready): {skipped}")

    if not runnable:
        print("\nNo runnable case studies found. Run with --status to diagnose.")
        return

    results = []
    for cs_id in runnable:
        cs = dict(CASE_STUDIES[cs_id])
        if tier_override:
            cs["tier"] = tier_override
        r = run_simulation(cs_id, cs, dry_run=args.dry_run)
        results.append(r)

    # Summary
    print(f"\n{'='*60}")
    print(f"=== Run Complete ===")
    success = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]
    print(f"  Completed: {len(success)}/{len(results)}")
    if failed:
        print(f"  Failed: {[r['cs_id'] for r in failed]}")
    print(f"\nResults in: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
