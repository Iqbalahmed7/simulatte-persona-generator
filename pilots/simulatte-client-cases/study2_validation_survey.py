"""
Study 2 — Validation Survey
Runs ONE_TIME_SURVEY against all 4 cohorts using original study questions.
Compare distributions against handcrafted persona findings.

Requires the Simulatte survey API to be running:
    cd "/Users/admin/Documents/Simulatte Projects/Persona Generator"
    python main.py  (or however the API is started)

Usage:
    python pilots/simulatte-client-cases/study2_validation_survey.py
"""

import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, "/Users/admin/Documents/Simulatte Projects/Persona Generator")

OUTPUT_ROOT = Path("./outputs/study2_creator_authority")

REGISTRY_PATH = OUTPUT_ROOT / "cohort_registry.json"

# Original study questions — verbatim from the research brief
ORIGINAL_QUESTIONS = [
    "When you see a health or nutrition product recommended by someone online, what makes you trust that recommendation?",
    "Does the number of followers a creator has affect how much you trust their product recommendations? Why or why not?",
    "How do you feel about a creator recommending a product when it's a paid partnership vs. when they post about it organically?",
    "If a registered dietitian with a small following recommended a product, would you trust it more than a celebrity with millions of followers? Why?",
    "Have you ever purchased a health food product specifically because of a social media creator's recommendation? What type of creator was it?",
    "Which type of person would you most trust to recommend a bread product that helps manage blood sugar or support fitness goals?",
    "On a scale of 1–5, how likely are you to purchase a product within one week of seeing a creator recommend it?",
    "What signals in a creator's content make you feel a product recommendation is authentic vs. just a paid promotion?",
]


async def run_survey(cohort_id: str, cohort_name: str) -> dict:
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
        print("Run study2_creator_authority_full.py first.")
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
    print("  □ Trust in credentialed micro vs. celebrity: expect micro wins across Cohorts A, B, D")
    print("  □ Cohort C (fitness): expect macro fitness creator to score higher than other cohorts")
    print("  □ Cohort B (diabetic): expect highest trust in credentialed content regardless of follower count")
    print("  □ Paid disclosure impact: expect 30–50% trust reduction on paid posts vs. organic")
    print("  □ Proof creator (Archetype 4): expect high purchase intent in Cohorts A and D despite small following")
    print("  □ Hypothesis check: follower count inversely related to purchase authority — confirm or deny")


if __name__ == "__main__":
    asyncio.run(main())
