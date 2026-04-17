"""
Study 1 — E-Commerce Listing Title Optimisation (FunctionalBread)
Client: Lo! Foods
FULL RUN — 10 personas per cohort (30 total), RunIntent.DELIVER (DEEP tier)

Run ONLY after proof runs pass.
auto_confirm=False: review cost estimate before spending.

Usage:
    cd "/Users/admin/Documents/Simulatte Projects/Persona Generator"
    python pilots/simulatte-client-cases/study1_listing_title_full.py
"""

import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, "/Users/admin/Documents/Simulatte Projects/Persona Generator")

from src.orchestrator import invoke_persona_generator
from src.orchestrator.brief import PersonaGenerationBrief, RunIntent, SimulationScenario

OUTPUT_ROOT = Path("./outputs/study1_listing_title")

LISTING_SIMULATION = SimulationScenario(
    stimuli=[
        "Variant A — Keto-led: 'Lo! Keto Bread — Zero Carb, High Protein | Gluten Free | 200g'",
        "Variant B — Benefit-led: 'Lo! High Protein Bread — Low Carb, Guilt-Free | Gluten Free | 200g'",
        "Variant C — Protein-led: 'Lo! Protein Bread 12g per Slice — Low Carb | Gluten Free | 200g'",
        "Variant D — Outcome-led: 'Lo! Everyday Healthy Bread — Low Calorie, High Fibre | Gluten Free | 200g'",
    ],
    decision_scenario=(
        "You are browsing the bread/bakery category on Amazon India. "
        "Which of these four product titles would make you most likely to click through to the product page? "
        "Rank them 1–4 (1 = most likely to click, 4 = least likely) and explain your reasoning."
    ),
    rounds=3,
)

BUSINESS_PROBLEM = (
    "Does the presence of the 'keto' keyword in an Amazon listing title "
    "suppress click-through and conversion among mainstream health-conscious buyers "
    "who are not committed to a ketogenic diet protocol, relative to title framings "
    "that lead with protein content, benefit outcomes, or general health positioning?"
)


async def run_cohort(cohort_name: str, brief: PersonaGenerationBrief) -> dict:
    print(f"\n{'='*60}")
    print(f"FULL RUN — {cohort_name}")
    print(f"{'='*60}")
    result = await invoke_persona_generator(brief)
    print(f"\n[{cohort_name}] cohort_id: {result.cohort_id}")
    print(result.summary)

    out_path = OUTPUT_ROOT / f"full_{cohort_name.lower().replace(' ', '_').replace('—', '').replace('-', '_')}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result_dict = result.model_dump(mode="json") if hasattr(result, "model_dump") else vars(result)
    out_path.write_text(json.dumps(result_dict, default=str, indent=2))
    print(f"  → Cohort saved: {out_path}")
    return {"cohort_name": cohort_name, "cohort_id": result.cohort_id, "file": str(out_path)}


async def main() -> None:
    cohort_a = PersonaGenerationBrief(
        client="Lo! Foods",
        domain="lofoods_fmcg",
        business_problem=BUSINESS_PROBLEM,
        count=10,
        run_intent=RunIntent.DELIVER,
        anchor_overrides={
            "location": "Metro India (Mumbai/Delhi/Bangalore/Hyderabad)",
            "age_band": "26–42",
            "life_stage": "urban professional",
            "category_relationship": "health-conscious grocery buyer, not diet-protocol-committed",
        },
        simulation=LISTING_SIMULATION,
        auto_confirm=False,
        emit_pipeline_doc=True,
        output_dir=str(OUTPUT_ROOT / "cohort_a_metro_health"),
    )

    cohort_b = PersonaGenerationBrief(
        client="Lo! Foods",
        domain="lofoods_fmcg",
        business_problem=BUSINESS_PROBLEM,
        count=10,
        run_intent=RunIntent.DELIVER,
        anchor_overrides={
            "location": "Metro India",
            "diet_protocol": "keto or low-carb adherent",
            "protocol_adherence_score": "0.70 or above (self-reported)",
            "category_relationship": "active diet-protocol follower, reads macros and labels",
        },
        simulation=LISTING_SIMULATION,
        auto_confirm=False,
        emit_pipeline_doc=True,
        output_dir=str(OUTPUT_ROOT / "cohort_b_diet_adherents"),
    )

    cohort_c = PersonaGenerationBrief(
        client="Lo! Foods",
        domain="lofoods_fmcg",
        business_problem=BUSINESS_PROBLEM,
        count=10,
        run_intent=RunIntent.DELIVER,
        anchor_overrides={
            "location": "Metro and Tier-1 India",
            "age_band": "28–55",
            "category_relationship": "mainstream e-commerce grocery shopper, convenience and price primary drivers",
            "diet_protocol": "none — general healthy eating interest at most",
        },
        simulation=LISTING_SIMULATION,
        auto_confirm=False,
        emit_pipeline_doc=True,
        output_dir=str(OUTPUT_ROOT / "cohort_c_mainstream"),
    )

    registry: list[dict] = []
    registry.append(await run_cohort("Cohort A — Metro Health-Conscious", cohort_a))
    registry.append(await run_cohort("Cohort B — Diet Adherents", cohort_b))
    registry.append(await run_cohort("Cohort C — Mainstream Shoppers", cohort_c))

    # Write cohort registry summary
    registry_path = OUTPUT_ROOT / "cohort_registry.json"
    registry_path.write_text(json.dumps(registry, indent=2))

    print("\n" + "="*60)
    print("FULL RUN COMPLETE — Study 1: Listing Title Optimisation")
    print(f"Registry: {registry_path}")
    print("\nCohort IDs for validation survey:")
    for r in registry:
        print(f"  {r['cohort_name']}: {r['cohort_id']}")
    print("\nNext step: run study1_validation_survey.py")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
