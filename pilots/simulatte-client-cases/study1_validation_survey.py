"""
Study 1 — Validation Survey
Runs ONE_TIME_SURVEY against all 3 cohorts using original study questions.
Compare distributions against handcrafted persona findings.

Requires the Simulatte survey API to be running:
    cd "/Users/admin/Documents/Simulatte Projects/Persona Generator"
    python main.py  (or however the API is started)

Usage:
    python pilots/simulatte-client-cases/study1_validation_survey.py
"""

import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, "/Users/admin/Documents/Simulatte Projects/Persona Generator")

OUTPUT_ROOT = Path("./outputs/study1_listing_title")

# Load cohort registry written by the full run script
REGISTRY_PATH = OUTPUT_ROOT / "cohort_registry.json"

# Original study questions — verbatim from the research brief
ORIGINAL_QUESTIONS = [
    "When browsing for bread or bakery products online, what do you look for first in a product title?",
    "Does seeing the word 'keto' in a product title make you more or less likely to click on it? Why?",
    "How important is protein content vs. carbohydrate content when choosing a bread product?",
    "Would you purchase a bread product labelled primarily as 'keto' even if you don't follow a keto diet?",
    "Which product description feels most relevant to your eating goals: (a) zero-carb keto bread, (b) high-protein low-carb bread, (c) 12g protein per slice bread, or (d) everyday healthy low-calorie bread?",
    "What would stop you from clicking on a health-food bread listing you see on Amazon?",
    "How much would you expect to pay for a 200g loaf of health-functional bread with 12g protein per slice?",
]


async def run_survey(cohort_id: str, cohort_name: str) -> dict:
    """
    Invoke the survey modality for a single cohort.
    Uses _run_survey from the CLI module if available.
    """
    try:
        from src.cli import _run_survey
        print(f"\nRunning survey for {cohort_name} (cohort_id: {cohort_id})...")
        result = await _run_survey(
            cohort_id=cohort_id,
            questions=ORIGINAL_QUESTIONS,
            survey_type="ONE_TIME",
        )
        return {"cohort_name": cohort_name, "cohort_id": cohort_id, "result": result}
    except ImportError:
        # Fallback: HTTP call to running API
        import aiohttp
        payload = {
            "cohort_id": cohort_id,
            "questions": ORIGINAL_QUESTIONS,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:8000/survey", json=payload) as resp:
                result = await resp.json()
        return {"cohort_name": cohort_name, "cohort_id": cohort_id, "result": result}


async def main() -> None:
    if not REGISTRY_PATH.exists():
        print(f"ERROR: Registry not found at {REGISTRY_PATH}")
        print("Run study1_listing_title_full.py first.")
        return

    registry = json.loads(REGISTRY_PATH.read_text())
    survey_results = []

    for entry in registry:
        result = await run_survey(entry["cohort_id"], entry["cohort_name"])
        survey_results.append(result)

    out_path = OUTPUT_ROOT / "validation_survey_results.json"
    out_path.write_text(json.dumps(survey_results, default=str, indent=2))
    print(f"\n✓ Validation survey results saved: {out_path}")

    print("\n--- VALIDATION CHECKLIST ---")
    print("Compare these distributions against handcrafted persona findings:")
    print("  □ % who find 'keto' label off-putting (Cohort C: expect 60%+)")
    print("  □ % who prefer protein-led framing over keto-led (Cohort A: expect majority)")
    print("  □ Cohort B: expect keto-led title to rank #1 (diet adherents)")
    print("  □ Price expectations: expect Rs 80–120 range for 200g loaf")
    print("  □ Decision divergence between stated and revealed (simulation) preference is expected — that's the signal")


if __name__ == "__main__":
    asyncio.run(main())
