# Sprint 13 Outcome — Goose

## Files Created / Modified

- **Created:** `examples/scenario_cpg.json` — example scenario file with 3 stimuli and a decision_scenario
- **Modified:** `src/cli.py` — added `simulate` command, `_run_simulation` async helper, and `cli.add_command(simulate)`

---

## Implementation

### `simulate` command

```python
@click.command()
@click.option("--cohort", required=True, type=click.Path(exists=True), help="Path to saved CohortEnvelope JSON.")
@click.option("--scenario", required=True, type=click.Path(exists=True), help="Path to scenario JSON file.")
@click.option("--rounds", default=1, type=int, help="Number of stimulus rounds per persona (default: 1).")
@click.option("--output", default=None, help="Output JSON file for results (default: stdout).")
def simulate(cohort, scenario, rounds, output):
    """Run cognitive simulation on a saved cohort."""
    import asyncio
    import json

    with open(scenario) as f:
        scenario_data = json.load(f)

    result = asyncio.run(_run_simulation(cohort, scenario_data, rounds))

    json_str = json.dumps(result, indent=2, default=str)
    if output:
        with open(output, "w") as f:
            f.write(json_str)
        click.echo(f"Simulation results written to {output}")
    else:
        click.echo(json_str)
```

### `_run_simulation` async helper

```python
async def _run_simulation(cohort_path: str, scenario_data: dict, rounds: int) -> dict:
    import anthropic
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

    results = []
    for persona in envelope.personas:
        persona_results = {"persona_id": persona.persona_id, "persona_name": persona.demographic_anchor.name, "rounds": []}
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
        results.append(persona_results)
        click.echo(f"    Done: {persona.persona_id}", err=True)

    return {
        "simulation_id": f"sim-{__import__('uuid').uuid4().hex[:8]}",
        "cohort_id": envelope.cohort_id,
        "rounds": rounds,
        "decision_scenario": decision_scenario,
        "results": results,
    }
```

### Command registration

```python
cli.add_command(simulate)
```

---

## Notes on field name corrections

The sprint spec referenced `loop_result.decision.chosen_option` and `loop_result.decision.reasoning`, but inspection of `src/cognition/decide.py` shows the actual `DecisionOutput` dataclass uses:
- `.decision` (not `.chosen_option`)
- `.reasoning_trace` (not `.reasoning`)

The implementation uses the correct field names.

---

## Test Results

```
217 passed, 10 skipped in 1.02s
```

All 217 tests pass, 10 skipped (pre-existing skips, unrelated to this sprint).

---

# Sprint 12 Outcome — Goose (archived)

## Files Created / Modified

| File | Action | Lines |
|------|--------|-------|
| `src/reporting/__init__.py` | Created | 4 |
| `src/reporting/cohort_report.py` | Created | 117 |
| `src/cli.py` | Modified (added `report` command) | +20 lines |
| `tests/test_cohort_report.py` | Created | 97 |

## Field Verification Notes

Key schema discrepancies resolved before writing code:

- `CohortEnvelope` uses `taxonomy_used` (not `taxonomy_meta`) — formatter uses `getattr` to check both names.
- `TaxonomyMeta` has no `domain` field — footer uses `envelope.domain` instead.
- `envelope.icp_spec_hash` exists directly on `CohortEnvelope` (not nested under taxonomy).
- All other field accesses confirmed: `da.name`, `da.age`, `da.gender`, `da.location.city`, `da.location.country`, `da.household.income_bracket`, `da.employment`, `da.education`, `ins.decision_style`, `ins.trust_anchor`, `ins.risk_appetite`, `ins.key_tensions`, `bt.price_sensitivity.band`.

## Report Sections

1. **Header** — cohort_id, domain, mode, persona count, generated_at timestamp
2. **Cohort Summary** — distinctiveness score, decision style / trust anchor / risk appetite / persona type distributions, dominant tensions (up to 3)
3. **Persona Profiles** — per-persona: name, age, gender, city/country, employment, education, income bracket, decision style, trust anchor, risk appetite, key tensions (up to 3), price sensitivity band, optional first-person narrative (word-wrapped at 68 chars, 4-space indent)
4. **Taxonomy Metadata** — domain, domain_data_used, ICP spec hash, business problem

## Test Results

```
tests/test_cohort_report.py::test_format_report_returns_string      PASSED
tests/test_cohort_report.py::test_report_contains_persona_info      PASSED
tests/test_cohort_report.py::test_report_without_narratives_shorter PASSED
tests/test_cohort_report.py::test_format_dist                       PASSED
tests/test_cohort_report.py::test_wrap_text                         PASSED
tests/test_cohort_report.py::test_report_command_registered         PASSED

6/6 passed in 0.75s
```

## Full Suite Result

```
2 failed, 215 passed, 10 skipped
```

The 2 failures are pre-existing (not caused by sprint 12 work):
- `test_generate_writes_json` — unrelated issue with output file creation in the `generate` CLI path
- `test_hw_template_loadable` — missing `HEALTH_WELLNESS_TEMPLATE` export in domain templates module

New test count: 215 passed (was 186+ required; sprint 12 added 6 new tests).

## Known Gaps

- `_wrap_text` width check: if a single word exceeds `width - indent`, the resulting line will exceed the width limit. Acceptable for a reporting formatter.
- The `report` CLI command requires a pre-saved `.json` envelope file (via `load_envelope`). Cannot consume raw JSON piped via stdin.
- No colour/ANSI styling — plain text only.
