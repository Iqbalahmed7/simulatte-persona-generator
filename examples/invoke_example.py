"""
Standalone example — invoke the Simulatte Persona Generator from any project.

Run from the repo root:
    python examples/invoke_example.py

Or import from another project after adding the repo to sys.path:
    import sys
    sys.path.insert(0, "/path/to/Persona Generator")
    from examples.invoke_example import run_littlejoys_example
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running from outside the repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.orchestrator import invoke_persona_generator
from src.orchestrator.brief import PersonaGenerationBrief, RunIntent, SimulationScenario


async def run_littlejoys_example() -> None:
    """
    Minimal example: generate 5 SIGNAL-tier CPG personas for LittleJoys
    with a 3-stimulus simulation and automatic confirmation.
    """
    brief = PersonaGenerationBrief(
        client="LittleJoys",
        domain="cpg",
        business_problem="Why do Mumbai parents switch nutrition brands for under-5s?",
        count=5,
        run_intent=RunIntent.EXPLORE,       # SIGNAL tier — fast + cheap
        sarvam_enabled=True,
        anchor_overrides={
            "location": "Mumbai",
            "life_stage": "parent",
        },
        simulation=SimulationScenario(
            stimuli=[
                "Pediatrician-endorsed nutrition supplement for children aged 2-10",
                "Product packaging: Vitamin D + Iron, Indian pediatric certification logo",
                "Price: Rs 649/month — available on Flipkart",
            ],
            decision_scenario="Would you purchase a trial pack of this product today?",
        ),
        auto_confirm=True,          # skip interactive prompt
        emit_pipeline_doc=True,     # auto-generate pipeline documentation
        output_dir="./outputs/littlejoys",
    )

    result = await invoke_persona_generator(brief)

    # ── Print summary ─────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("RESULT SUMMARY")
    print("=" * 60)
    print(result.summary)
    print()
    print(f"Run ID:          {result.run_id}")
    print(f"Cohort ID:       {result.cohort_id}")
    print(f"Tier:            {result.tier_used.upper()}")
    print(f"Personas:        {result.count_delivered}")
    print(f"Total cost:      ${result.cost_actual.total:.2f}")
    print(f"Per persona:     ${result.cost_per_persona:.3f}")
    print(f"Gates passed:    {', '.join(result.quality_report.gates_passed)}")
    if result.quality_report.gates_failed:
        print(f"Gates FAILED:    {', '.join(result.quality_report.gates_failed)}")
    print(f"Cohort file:     {result.cohort_file_path}")
    print(f"Pipeline doc:    {result.pipeline_doc_path}")
    print()

    # ── Print persona names ───────────────────────────────────────────────
    print("PERSONAS GENERATED:")
    for p in result.personas:
        da = p.get("demographic_anchor", {})
        di = p.get("derived_insights", {})
        print(
            f"  {p.get('persona_id'):<12}  "
            f"{da.get('name',''):<18}  "
            f"Age {da.get('age','')}  "
            f"{da.get('location','')}  "
            f"[{di.get('decision_style','')}]"
        )
    print()

    # ── Print simulation decisions ────────────────────────────────────────
    if result.simulation_results:
        print("SIMULATION DECISIONS:")
        for persona_result in result.simulation_results.get("results", []):
            name = persona_result.get("persona_name", persona_result.get("persona_id"))
            rounds = persona_result.get("rounds", [])
            last = rounds[-1] if rounds else {}
            decision  = last.get("decision") or "—"
            confidence = last.get("confidence")
            conf_str = f"  ({confidence:.0f}% confidence)" if confidence else ""
            print(f"  {name:<20}  {decision}{conf_str}")
    print()


async def run_custom_example(
    client: str,
    domain: str,
    business_problem: str,
    count: int = 10,
    deliver: bool = False,
    stimuli: list[str] | None = None,
    decision_scenario: str | None = None,
) -> None:
    """
    Parameterised entry point — call from another program with your own brief.
    """
    brief = PersonaGenerationBrief(
        client=client,
        domain=domain,
        business_problem=business_problem,
        count=count,
        run_intent=RunIntent.DELIVER if deliver else RunIntent.EXPLORE,
        auto_confirm=True,
        simulation=SimulationScenario(
            stimuli=stimuli or [],
            decision_scenario=decision_scenario,
        ) if stimuli else None,
    )

    result = await invoke_persona_generator(brief)
    print(result.summary)
    result.save(f"./outputs/{client.lower().replace(' ', '_')}-run.json")
    return result


if __name__ == "__main__":
    asyncio.run(run_littlejoys_example())
