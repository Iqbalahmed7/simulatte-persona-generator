"""pilots/the-mind/generate_exemplars.py

Phase 2 of The Mind (mind.simulatte.io) — generates 5 exemplar personas
on the provenance-instrumented pipeline and freezes them as exemplar_set_v1.

Run from the repo root:
  python3 pilots/the-mind/generate_exemplars.py

Outputs (in pilots/the-mind/exemplar_set_v1/):
  persona_priya.json
  persona_madison.json
  persona_linnea.json
  persona_arun.json
  persona_david.json
  manifest.json          <- version pin + generation metadata

Each persona JSON is a serialised PersonaRecord with full provenance on
every attribute. Do not edit these files after generation — re-run the
script with a new version tag if regeneration is required.

Version: exemplar_set_v1_2026_04
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── repo root on sys.path ──────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# ── load .env ──────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env", override=True)
except ImportError:
    pass

# ── output directory ───────────────────────────────────────────────────────
OUT_DIR = Path(__file__).parent / "exemplar_set_v1"
OUT_DIR.mkdir(exist_ok=True)


# ── ICP definitions ────────────────────────────────────────────────────────

def _make_demographics():
    """Return the 5 exemplar DemographicAnchor objects.

    All demographics are hard-coded to match the locked ICPs in the
    initiative doc. No sampler involved — exact control required.
    """
    from src.schema.persona import DemographicAnchor, Location, Household

    anchors = {
        "priya": DemographicAnchor(
            name="Priya Sharma",
            age=32,
            gender="female",
            location=Location(
                country="India",
                region="Maharashtra",
                city="Mumbai",
                urban_tier="metro",
            ),
            household=Household(
                structure="nuclear",
                size=4,
                income_bracket="upper-middle",
                dual_income=True,
            ),
            life_stage="young_parent",
            education="postgraduate",
            employment="full-time",
        ),

        "madison": DemographicAnchor(
            name="Madison Chen",
            age=36,
            gender="female",
            location=Location(
                country="United States",
                region="California",
                city="San Francisco",
                urban_tier="metro",
            ),
            household=Household(
                structure="couple-no-kids",
                size=2,
                income_bracket="upper",
                dual_income=True,
            ),
            life_stage="established_adult",
            education="postgraduate",
            employment="full-time",
        ),

        "linnea": DemographicAnchor(
            name="Linnea Bergström",
            age=28,
            gender="female",
            location=Location(
                country="Sweden",
                region="Stockholm County",
                city="Stockholm",
                urban_tier="metro",
            ),
            household=Household(
                structure="couple-no-kids",
                size=1,
                income_bracket="middle",
                dual_income=False,
            ),
            life_stage="early_career",
            education="postgraduate",
            employment="full-time",
        ),

        "arun": DemographicAnchor(
            name="Arun Verma",
            age=42,
            gender="male",
            location=Location(
                country="India",
                region="Madhya Pradesh",
                city="Indore",
                urban_tier="tier2",
            ),
            household=Household(
                structure="nuclear",
                size=4,
                income_bracket="middle",
                dual_income=False,
            ),
            life_stage="mid_career",
            education="undergraduate",
            employment="self-employed",
        ),

        "david": DemographicAnchor(
            name="David Kowalski",
            age=64,
            gender="male",
            location=Location(
                country="United States",
                region="Arizona",
                city="Phoenix",
                urban_tier="metro",
            ),
            household=Household(
                structure="couple-no-kids",
                size=2,
                income_bracket="middle",
                dual_income=False,
            ),
            life_stage="pre_retirement",
            education="undergraduate",
            employment="retired",
        ),
    }
    return anchors


# ── ICP specs (domain + mode per persona) ─────────────────────────────────

ICP_CONFIGS = {
    "priya": {
        "domain": "cpg",
        "mode": "deep",
        "prefix": "mind-priya",
        "index": 1,
        "description": "Indian metro mother, 32, Mumbai — marketing manager, health-conscious, premium-curious",
    },
    "madison": {
        "domain": "cpg",
        "mode": "deep",
        "prefix": "mind-madison",
        "index": 1,
        "description": "US premium wellness seeker, 36, San Francisco — SaaS PM, clinical-backing required",
    },
    "linnea": {
        "domain": "cpg",
        "mode": "deep",
        "prefix": "mind-linnea",
        "index": 1,
        "description": "European minimalist, 28, Stockholm — UX designer, climate-anxious, anti-maximalist",
    },
    "arun": {
        "domain": "cpg",
        "mode": "deep",
        "prefix": "mind-arun",
        "index": 1,
        "description": "Tier-2 Indian male, 42, Indore — small-business owner, value-seeker, YouTube-native",
    },
    "david": {
        "domain": "cpg",
        "mode": "deep",
        "prefix": "mind-david",
        "index": 1,
        "description": "US senior, 64, Phoenix — retired teacher, managing hypertension, skeptical of marketing",
    },
}


# ── generation ─────────────────────────────────────────────────────────────

async def generate_one(
    slug: str,
    demographic_anchor,
    config: dict,
    constructor,
) -> dict:
    from src.generation.identity_constructor import ICPSpec

    icp = ICPSpec(
        domain=config["domain"],
        mode=config["mode"],
        anchor_overrides={},
        persona_id_prefix=config["prefix"],
        persona_index=config["index"],
        domain_data=None,
        sarvam_enabled=False,
    )

    print(f"  [{slug}] Building {demographic_anchor.name}, {demographic_anchor.age}, "
          f"{demographic_anchor.location.city} ...", flush=True)

    persona = await constructor.build(
        demographic_anchor=demographic_anchor,
        icp_spec=icp,
    )

    out_path = OUT_DIR / f"persona_{slug}.json"
    persona_dict = persona.model_dump(mode="json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(persona_dict, f, indent=2, default=str)

    print(f"  [{slug}] ✓  {persona.persona_id}  "
          f"consistency={persona.derived_insights.consistency_score}  "
          f"→ {out_path.name}", flush=True)

    # Quick provenance spot-check
    total_attrs = sum(len(v) for v in persona.attributes.values())
    with_prov = sum(
        1
        for cat in persona.attributes.values()
        for attr in cat.values()
        if attr.provenance is not None
    )
    print(f"         provenance coverage: {with_prov}/{total_attrs} attributes", flush=True)

    return {"slug": slug, "persona_id": persona.persona_id, "path": str(out_path)}


async def main():
    import anthropic
    from src.generation.identity_constructor import IdentityConstructor

    print("\n═══ The Mind — Phase 2: Exemplar Generation ═══")
    print(f"Output dir : {OUT_DIR}")
    print(f"Version    : exemplar_set_v1_2026_04")
    print(f"Started    : {datetime.now(timezone.utc).isoformat()}\n")

    model = os.getenv("GENERATION_MODEL", "claude-sonnet-4-6")
    print(f"Model      : {model}\n")

    llm_client = anthropic.AsyncAnthropic()
    constructor = IdentityConstructor(llm_client, model=model)

    anchors = _make_demographics()
    results = []

    for slug, config in ICP_CONFIGS.items():
        try:
            result = await generate_one(
                slug=slug,
                demographic_anchor=anchors[slug],
                config=config,
                constructor=constructor,
            )
            results.append({**result, "status": "ok", "description": config["description"]})
        except Exception as e:
            print(f"  [{slug}] ✗  FAILED: {e}", flush=True)
            results.append({"slug": slug, "status": "failed", "error": str(e)})

    # Write manifest
    manifest = {
        "version": "exemplar_set_v1_2026_04",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "provenance_instrumented": True,
        "personas": results,
        "notes": (
            "Frozen exemplar set for The Mind (mind.simulatte.io) demo. "
            "Do not edit individual persona files. Re-run generate_exemplars.py "
            "with a new version tag if regeneration is required."
        ),
    }
    manifest_path = OUT_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n═══ Done ═══")
    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"Generated  : {ok}/{len(results)} personas")
    print(f"Manifest   : {manifest_path}")
    for r in results:
        status = "✓" if r["status"] == "ok" else "✗"
        print(f"  {status} {r['slug']:10s}  {r.get('persona_id', r.get('error', ''))}")


if __name__ == "__main__":
    asyncio.run(main())
