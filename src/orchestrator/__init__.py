"""
Simulatte Persona Generator — Orchestration Layer
==================================================

Single public API for invoking persona generation from any external caller.

Quick start::

    from src.orchestrator import invoke_persona_generator, invoke_persona_generator_sync
    from src.orchestrator.brief import PersonaGenerationBrief, RunIntent, SimulationScenario

    # Build the brief
    brief = PersonaGenerationBrief(
        client="YourClient",
        domain="cpg",               # cpg | saas | ecommerce | healthcare | ...
        business_problem="What drives purchase decisions for X?",
        count=30,
        run_intent=RunIntent.DELIVER,    # explore | calibrate | deliver | volume
        auto_confirm=True,               # skip the cost prompt for automation
    )

    # Async usage (preferred)
    import asyncio
    result = asyncio.run(invoke_persona_generator(brief))

    # Sync usage (convenience wrapper)
    result = invoke_persona_generator_sync(brief)

    # Access results
    print(result.summary)
    print(f"Cost: ${result.cost_actual.total:.2f}")
    result.save("./output/run.json")

See src/orchestrator/README.md for the full integration guide.
"""

from src.orchestrator.brief import PersonaGenerationBrief, RunIntent, SimulationScenario
from src.orchestrator.invoke import invoke_persona_generator, invoke_persona_generator_sync
from src.orchestrator.result import PersonaGenerationResult

__all__ = [
    "PersonaGenerationBrief",
    "RunIntent",
    "SimulationScenario",
    "invoke_persona_generator",
    "invoke_persona_generator_sync",
    "PersonaGenerationResult",
]
