# Sprint 14 — Parallel Simulation: Outcome

## What was done

Refactored `_run_simulation()` in `src/cli.py` to run persona simulations concurrently using `asyncio.gather`. The sequential `for persona in envelope.personas` loop was replaced with a nested `_simulate_persona` coroutine dispatched in parallel. The inner rounds loop remains sequential inside each coroutine, preserving the per-persona state dependency across rounds.

The unused `import anthropic` line was replaced with `import asyncio`.

## Exact new `_run_simulation` function

```python
async def _run_simulation(cohort_path: str, scenario_data: dict, rounds: int) -> dict:
    import asyncio
    from src.persistence.envelope_store import load_envelope
    from src.cognition.loop import run_loop

    envelope = load_envelope(cohort_path)
    stimuli = scenario_data.get("stimuli", [])
    decision_scenario = scenario_data.get("decision_scenario", None)

    # Cycle stimuli across rounds
    all_stimuli = (stimuli * ((rounds * len(stimuli) // len(stimuli)) + 1))[:rounds * max(len(stimuli), 1)]
    if not stimuli:
        all_stimuli = ["Observe the current market environment."] * rounds

    click.echo(f"  Simulating {len(envelope.personas)} persona(s) × {rounds} round(s)...", err=True)

    async def _simulate_persona(persona):
        persona_results = {
            "persona_id": persona.persona_id,
            "persona_name": persona.demographic_anchor.name,
            "rounds": [],
        }
        current_persona = persona
        for round_num, stimulus in enumerate(all_stimuli[:rounds], 1):
            current_persona, loop_result = await run_loop(
                stimulus=stimulus,
                persona=current_persona,
                decision_scenario=decision_scenario if round_num == rounds else None,
            )
            round_data = {
                "round": round_num,
                "stimulus": stimulus,
                "observation_importance": loop_result.observation.importance,
                "reflected": loop_result.reflected,
                "decided": loop_result.decided,
            }
            if loop_result.decided and loop_result.decision:
                round_data["decision"] = loop_result.decision.decision
                round_data["confidence"] = loop_result.decision.confidence
                round_data["reasoning"] = loop_result.decision.reasoning_trace[:200]
            persona_results["rounds"].append(round_data)
        click.echo(f"    Done: {persona.persona_id}", err=True)
        return persona_results

    results = list(await asyncio.gather(*[_simulate_persona(p) for p in envelope.personas]))

    return {
        "simulation_id": f"sim-{__import__('uuid').uuid4().hex[:8]}",
        "cohort_id": envelope.cohort_id,
        "rounds": rounds,
        "decision_scenario": decision_scenario,
        "results": results,
    }
```

## Test results

```
233 passed, 10 skipped in 1.22s
```

Full suite passed with 233 tests passing and 10 skipped. No regressions.
