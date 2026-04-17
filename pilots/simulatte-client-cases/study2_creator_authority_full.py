"""
Study 2 — Creator Purchase Authority Audit (FunctionalHealth)
Client: Lo! Foods
FULL RUN — 10 personas per cohort (40 total), RunIntent.DELIVER (DEEP tier)

Run ONLY after proof runs pass.
auto_confirm=False: review cost estimate before spending.

Usage:
    cd "/Users/admin/Documents/Simulatte Projects/Persona Generator"
    python pilots/simulatte-client-cases/study2_creator_authority_full.py
"""

import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, "/Users/admin/Documents/Simulatte Projects/Persona Generator")

from src.orchestrator import invoke_persona_generator
from src.orchestrator.brief import PersonaGenerationBrief, RunIntent, SimulationScenario

OUTPUT_ROOT = Path("./outputs/study2_creator_authority")

CREATOR_SIMULATION = SimulationScenario(
    stimuli=[
        (
            "Archetype 1 — Celebrity Reach (30M followers): Bollywood actor posts a paid partnership reel "
            "featuring Lo! Protein Bread. High production quality. No nutritional depth. Caption: "
            "'Loving my healthy swap with @lofoods — guilt-free and delicious!' #ad"
        ),
        (
            "Archetype 2 — Macro Fitness Creator (650K followers): Fitness YouTuber with dedicated "
            "health and gym audience. Paid collaboration. 8-minute review video with macro comparison, "
            "taste test, and workout integration. Discloses partnership clearly."
        ),
        (
            "Archetype 3 — Credentialed Micro (8K followers): Registered dietitian with 8,000 "
            "Instagram followers. Unpaid, organic post. Includes detailed nutritional breakdown, "
            "blood glucose response data, and clinical context. No brand relationship."
        ),
        (
            "Archetype 4 — Proof Creator (12K followers): Regular consumer with 12,000 followers "
            "who documents their own 6-month low-carb journey. Shares real before/after, weekly "
            "grocery hauls, and authentic product experiences including Lo! Bread. No paid relationship."
        ),
        (
            "Archetype 5 — Credentialed Macro (180K followers): Sports nutritionist with 180K followers, "
            "paid brand partnership. Posts detailed macro analysis, comparison with regular bread, "
            "and structured recommendation for specific fitness goals."
        ),
    ],
    decision_scenario=(
        "You see each of these five types of creator content about Lo! Protein Bread in your social media feed. "
        "Rate each archetype on two dimensions: "
        "(1) How much does this content increase your trust in the product? (1–5 scale) "
        "(2) How likely are you to purchase Lo! Bread within 7 days of seeing this content? (1–5 scale) "
        "Explain the reasoning behind your ratings."
    ),
    rounds=3,
)

BUSINESS_PROBLEM = (
    "Which creator archetype — differentiated by follower count, credential type, "
    "and brand relationship (paid vs unpaid) — generates the highest purchase authority "
    "for health-functional food products among Indian health-conscious consumers? "
    "Hypothesis: follower count is inversely related to purchase authority; "
    "credentialed micro-creators and proof creators outperform celebrity and macro creators."
)


async def run_cohort(cohort_name: str, brief: PersonaGenerationBrief) -> dict:
    print(f"\n{'='*60}")
    print(f"FULL RUN — {cohort_name}")
    print(f"{'='*60}")
    result = await invoke_persona_generator(brief)
    print(f"\n[{cohort_name}] cohort_id: {result.cohort_id}")
    print(result.summary)

    safe_name = cohort_name.lower().replace(" ", "_").replace("—", "").replace("-", "_").strip("_")
    out_path = OUTPUT_ROOT / f"full_{safe_name}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result_dict = result.model_dump(mode="json") if hasattr(result, "model_dump") else vars(result)
    out_path.write_text(json.dumps(result_dict, default=str, indent=2))
    print(f"  → Cohort saved: {out_path}")
    return {"cohort_name": cohort_name, "cohort_id": result.cohort_id, "file": str(out_path)}


async def main() -> None:
    cohort_a = PersonaGenerationBrief(
        client="Lo! Foods",
        domain="health_wellness",
        business_problem=BUSINESS_PROBLEM,
        count=10,
        run_intent=RunIntent.DELIVER,
        anchor_overrides={
            "location": "Metro India (Mumbai/Delhi/Bangalore)",
            "category_relationship": "active health-food buyer, familiar with protein bread category",
            "social_media_behavior": "follows health and nutrition creators, moderately engaged",
        },
        simulation=CREATOR_SIMULATION,
        auto_confirm=False,
        emit_pipeline_doc=True,
        output_dir=str(OUTPUT_ROOT / "cohort_a_metro_health"),
    )

    cohort_b = PersonaGenerationBrief(
        client="Lo! Foods",
        domain="health_wellness",
        business_problem=BUSINESS_PROBLEM,
        count=10,
        run_intent=RunIntent.DELIVER,
        anchor_overrides={
            "location": "Metro and Tier-1 India",
            "age_band": "38–65",
            "health_condition": "Type 2 diabetes (self-managed or under medical supervision)",
            "trust_orientation": "doctor and medical authority trust dominant",
            "category_relationship": "high information need, willing to pay premium for medical credibility",
        },
        simulation=CREATOR_SIMULATION,
        auto_confirm=False,
        emit_pipeline_doc=True,
        output_dir=str(OUTPUT_ROOT / "cohort_b_diabetic"),
    )

    cohort_c = PersonaGenerationBrief(
        client="Lo! Foods",
        domain="health_wellness",
        business_problem=BUSINESS_PROBLEM,
        count=10,
        run_intent=RunIntent.DELIVER,
        anchor_overrides={
            "location": "Metro India",
            "age_band": "22–38",
            "life_stage": "active gym-goer or fitness enthusiast",
            "social_media_behavior": "follows multiple fitness creators, high content engagement",
            "category_relationship": "tracks macros, reads protein content, open to functional food swaps",
        },
        simulation=CREATOR_SIMULATION,
        auto_confirm=False,
        emit_pipeline_doc=True,
        output_dir=str(OUTPUT_ROOT / "cohort_c_fitness"),
    )

    cohort_d = PersonaGenerationBrief(
        client="Lo! Foods",
        domain="health_wellness",
        business_problem=BUSINESS_PROBLEM,
        count=10,
        run_intent=RunIntent.DELIVER,
        anchor_overrides={
            "location": "Metro and Tier-1 India",
            "age_band": "28–50",
            "category_relationship": "general healthy eating interest, not embedded in fitness community",
            "social_media_behavior": "casual health content consumer, not active in fitness creator ecosystem",
        },
        simulation=CREATOR_SIMULATION,
        auto_confirm=False,
        emit_pipeline_doc=True,
        output_dir=str(OUTPUT_ROOT / "cohort_d_mainstream"),
    )

    registry: list[dict] = []
    registry.append(await run_cohort("Cohort A — Metro Health-Conscious", cohort_a))
    registry.append(await run_cohort("Cohort B — Diabetic Segment", cohort_b))
    registry.append(await run_cohort("Cohort C — Fitness Community", cohort_c))
    registry.append(await run_cohort("Cohort D — Mainstream Health-Seekers", cohort_d))

    registry_path = OUTPUT_ROOT / "cohort_registry.json"
    registry_path.write_text(json.dumps(registry, indent=2))

    print("\n" + "="*60)
    print("FULL RUN COMPLETE — Study 2: Creator Purchase Authority")
    print(f"Registry: {registry_path}")
    print("\nCohort IDs for validation survey:")
    for r in registry:
        print(f"  {r['cohort_name']}: {r['cohort_id']}")
    print("\nNext step: run study2_validation_survey.py")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
