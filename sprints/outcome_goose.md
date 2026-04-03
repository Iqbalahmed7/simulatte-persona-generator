# Sprint 22 Outcome — Goose

**Deliverable:** `src/calibration/feedback_loop.py`
**Date:** 2026-04-03

---

## What was built

Full replacement of the Sprint 22 stub in `src/calibration/feedback_loop.py`.

### Module-level constant

```python
CHANNEL_TENDENCY_MAP: dict[str, str] = {
    "doctor_referral": "trust_orientation",
    "social_media": "trust_orientation",
    "price_promotion": "price_sensitivity",
    "word_of_mouth": "trust_orientation",
    "organic": "switching_propensity",
}
```

### `adjust_tendency_from_outcome(persona: PersonaRecord, outcome: dict) -> PersonaRecord`

1. Reads `actual_outcome` and `channel` from the outcome dict.
2. Looks up the primary tendency via `CHANNEL_TENDENCY_MAP`; unknown channels fall back to `switching_propensity` with a `logger.warning`.
3. Calls `_is_mismatch()` to determine whether the outcome contradicts the tendency:
   - `price_sensitivity=high` + `purchased` → mismatch (underestimated propensity)
   - `trust_orientation.weights.expert >= 0.65` + `purchased` → match (expected)
   - `price_sensitivity=low` + `rejected` → mismatch (unexpected driver)
   - Default: `purchased`/`researched` = match; `rejected` = mismatch; `deferred` = match
4. Calls `_build_feedback_note()` to produce the annotation string.
5. Applies nested `model_copy` updates — only the `description` field of the affected tendency is changed; bands and weights are untouched.
6. If the tendency field is missing (schema error), logs a warning and returns persona unchanged.

### `summarise_outcomes(outcomes: list[dict]) -> dict`

Counts occurrences per `actual_outcome` label, returns a plain `dict[str, int]`.

### Private helpers

- `_is_mismatch(tendency_name, actual_outcome, persona) -> bool` — deterministic mismatch logic
- `_build_feedback_note(tendency_name, actual_outcome, channel, is_mismatch) -> str` — note formatter

---

## Verification

```
Import check:
python3 -c "from src.calibration.feedback_loop import adjust_tendency_from_outcome, summarise_outcomes; print('Import OK')"
→ Import OK

Full test suite:
python3 -m pytest tests/ -q --tb=short 2>&1 | tail -5
→ 545 passed, 15 skipped in 2.24s
```

No regressions. 15 skipped are pre-existing and unrelated to this sprint.

---

## Assumptions / deviations

- **Description-only updates:** The sprint spec says "only description strings are updated, not bands or weights." This is implemented exactly. The Sprint 22 sprint plan acceptance criterion ("Feedback loop: updates `tendency.band` for the correct persona when outcome data provided") appears to be in tension with the spec brief's explicit constraint — the brief takes precedence, so bands are not modified.
- **Stub replacement:** The pre-existing stub used a `brand_affinity` field (not in the current schema) and a different outcome→direction logic. It was a placeholder. The full implementation overwrites it entirely per the brief.
- **`summarise_outcomes` scope:** The spec says "Group outcomes by actual_outcome and channel" but the return type shown is `{"purchased": count, ...}` keyed by `actual_outcome` only. Implemented as outcome-keyed counts (matching the return type in the docstring). Channel breakdown is not included in the return value; it can be derived by the caller if needed.
- No LLM calls anywhere — fully deterministic as required.

---

# Sprint 21 Outcome — Goose

**Deliverable:** `src/validation/simulation_gates.py`
**Date:** 2026-04-03

---

## What was built

Five public symbols in `src/validation/simulation_gates.py`:

### `GateResult` dataclass
Fields: `gate`, `passed`, `threshold`, `actual`, `action_required`, `warning`.
`warning=True` means the gate warns but does not block.

### `check_s1(personas, sample_size=5) -> GateResult`
- Checks that `len(personas) >= sample_size` and every persona has a valid `memory.working.simulation_state` (not None, not an error-marker string).
- Accepts both attribute-access (PersonaRecord) and dict-style objects via a two-path fallback.
- Fails if fewer than `sample_size` personas were loaded OR any persona carries an error-state marker.
- Action on fail: "Debug pipeline before running full population"

### `check_s2(decisions) -> GateResult`
- Counts decision frequencies and computes `max_pct = max_count / total * 100`.
- Passes cleanly when `max_pct <= 80%`, warns (pass + `warning=True`) when `80 < max_pct <= 90%`, fails hard when `max_pct > 90%`.
- Threshold: "No single option > 90%"
- Action on fail/warn: "Review stimulus design; may indicate broken persona or prompt issue"

### `check_s3(key_drivers, domain_keywords) -> GateResult`
- Auto-passes with `warning=True` if `domain_keywords` is empty or `key_drivers` is empty.
- For non-empty inputs, computes what fraction of non-empty driver lists contain at least one domain keyword (case-insensitive substring match).
- Passes if `>= 70%` of driver lists contain a match.
- Action on fail: "Review stimulus prompts; check tendency-attribute assignment"

### `check_s4(wtp_values, ask_price) -> GateResult`
- Filters out `None` and `0.0` values, then computes median.
- Auto-passes with `warning=True` if no valid WTP data.
- Passes cleanly when deviation `<= 20%`, warns when `20% < deviation <= 30%`, fails when `deviation > 30%`.
- Threshold formatted with rupee symbol: `₹{ask_price:.0f}`
- Action on fail/warn: "Check tendency-attribute proxy formulas; may need recalibration"

### `run_all_gates(personas, decisions, key_drivers, wtp_values, ask_price, domain_keywords=None) -> list[GateResult]`
- Convenience wrapper that calls all four checks in order and returns `[S1, S2, S3, S4]`.

---

## Verification

```
Import check:
python3 -c "from src.validation.simulation_gates import GateResult, check_s1, check_s2, check_s3, check_s4, run_all_gates; print('Import OK')"
→ Import OK

Full test suite:
python3 -m pytest tests/ -q --tb=short 2>&1 | tail -5
→ 436 passed, 15 skipped in 1.92s
```

No regressions. Net change: +0 tests (module is new; no test file was authored this sprint — existing `test_simulation_gates.py` covers Sprint 7 simulation structural tests and was already passing).

---

## Assumptions / deviations

- **`simulation_state` attribute path:** The brief specifies `memory.working.simulation_state`. No `WorkingMemory.simulation_state` field exists in the current schema; the gate reads it defensively (catches `AttributeError`) so it won't crash on current personas. An absent or `None` state is treated as an error condition per the S1 spec intent.
- **S2 warning boundary:** The brief says "Warning (not fail) if 80 < max_pct <= 90". Implemented exactly that band. Below 80% is a clean pass with no warning.
- **S3 match logic:** "Contains at least one domain keyword" is implemented as a case-insensitive substring match (`kw in driver.lower()`), which handles multi-word drivers gracefully.
- **S4 warning boundary:** "Warning (not fail) if 0.20 < deviation <= 0.30". Below 0.20 is clean pass. Above 0.30 is hard fail.
- All functions are fully deterministic — no LLM calls anywhere in the module.

---

# Sprint 20 Outcome — Goose

**Deliverable:** `src/taxonomy/domain_merger.py`
**Date:** 2026-04-03

---

## What was built

Three functions in `src/taxonomy/domain_merger.py`:

### `detect_conflicts(base, domain_attrs) -> list[str]`
- Collects all attribute names from the 6 base category dicts (`psychology`, `values`, `social`, `lifestyle`, `identity`, `decision_making`).
- Checks each incoming domain attribute name against that set.
- Logs each conflict individually as `logging.warning(...)` — does not raise.
- Returns the list of conflicting names (empty if none).

### `merge_taxonomy(base, domain_attrs) -> dict`
- Starts with `copy.deepcopy(base)` — input never mutated.
- Calls `detect_conflicts()` internally for warning coverage.
- Handles both `DomainAttribute` (direct) and `RankedAttribute` (via `hasattr(item, 'attr')` check).
- Replaces any pre-existing `"domain_specific"` key entirely.
- Each entry in `"domain_specific"` carries: `description`, `valid_range`, `example_values`, `signal_count`, `extraction_source`, and mandatory `"layer": 2` (spec P10 traceability).
- Empty `domain_attrs` produces `"domain_specific": {}`.

### `get_domain_attribute_names(merged_taxonomy) -> set[str]`
- One-liner: `set(merged_taxonomy.get("domain_specific", {}).keys())`.

---

## Verification

```
Import check:
python3 -c "from src.taxonomy.domain_merger import merge_taxonomy, detect_conflicts, get_domain_attribute_names; print('Import OK')"
→ Import OK

Full test suite:
python3 -m pytest tests/ -q --tb=short
→ 400 passed, 15 skipped in 4.93s
```

No regressions.

---

## Assumptions / deviations

- **`RankedAttribute` shape:** No `RankedAttribute` dataclass exists in the codebase yet (Codex has not shipped it). The brief specifies handling it via `hasattr(item, 'attr')`. Implemented exactly as specified — when `attr` attribute is present, unwrap it; otherwise treat item as a direct `DomainAttribute`.
- **`base` dict format:** The `base` parameter is a dict-of-dicts (category key → dict of attribute definitions), consistent with the brief's output contract. `TAXONOMY_BY_CATEGORY` in `base_taxonomy.py` uses lists; converting to dict-of-dicts before calling `merge_taxonomy` is the caller's responsibility.
- **Conflict check scope:** Only keys from the 6 `_BASE_CATEGORIES` are inspected. Any pre-existing `"domain_specific"` key is excluded from conflict checking (it gets replaced, not conflicted with).
- No LLM calls anywhere in the module — fully deterministic as required.

---

# Sprint 15 Outcome — Goose

## Status: COMPLETE

All 4 new simulation-ready tests pass. Full suite: **253 passed, 15 skipped**.

---

## Files Created / Modified

- **Modified:** `src/generation/identity_constructor.py` — added Step 7b (seed memory bootstrap for simulation-ready mode)
- **Modified:** `src/cli.py` — updated `--mode` default to `quick` and clarified help text
- **Created:** `tests/test_simulation_ready.py` — 4 tests covering seed memory bootstrapping and G10 gate

---

## Code Added to `identity_constructor.py`

Step 7b inserted after Step 7 (validate) and before Step 8 (return):

```python
# ---------------------------------------------------------------
# Step 7b — Bootstrap seed memories (simulation-ready mode only)
# ---------------------------------------------------------------
if icp_spec.mode == "simulation-ready":
    from src.memory.seed_memory import bootstrap_seed_memories
    seeded_working = bootstrap_seed_memories(
        core_memory=persona.memory.core,
        persona_name=persona.demographic_anchor.name,
    )
    persona = persona.model_copy(
        update={"memory": Memory(core=persona.memory.core, working=seeded_working)}
    )
```

Note: the sprint brief showed `persona=persona` as the second argument, but the actual signature of `bootstrap_seed_memories` (verified in `src/memory/seed_memory.py`) is `persona_name: str`. The correct call uses `persona_name=persona.demographic_anchor.name`.

---

## CLI Change (`src/cli.py`)

```python
# Before:
@click.option("--mode", default="simulation-ready", help="Mode: quick | simulation-ready (default: simulation-ready).")

# After:
@click.option("--mode", default="quick", help="Mode: quick (fast, no seed memories) | simulation-ready (seeds working memory for cognitive loop). Default: quick.")
```

---

## Test Results

### `tests/test_simulation_ready.py`

```
test_simulation_ready_mode_seeds_working_memory  PASSED
test_quick_mode_has_empty_working_memory         PASSED
test_seed_memories_reference_core_values         PASSED
test_simulation_ready_passes_g10                 PASSED

4 passed in 0.13s
```

### Full Suite

```
253 passed, 15 skipped in 2.81s
```

Previous count: 249 passed, 15 skipped. Net gain: +4 tests.

---

## Implementation Notes

- `make_synthetic_persona()` fixture already calls `bootstrap_seed_memories` internally (mode="simulation-ready"), so `test_quick_mode_has_empty_working_memory` constructs an explicitly empty `WorkingMemory` via `model_copy` to correctly represent the quick-mode contract.
- G10 gate: `bootstrap_seed_memories` always produces >= 3 observations (identity anchor + primary value + core tension + optional life events), with fallback seeds if needed.

---

# Sprint 14 Outcome — Goose

## Status: COMPLETE

All 5 new calibration tests pass. Full suite: **238 passed, 10 skipped**.

---

## Files Created / Modified

- **Created:** `src/cohort/calibrator.py` — `compute_calibration_state` and `apply_calibration` functions
- **Modified:** `src/cli.py` — `_run_simulation` now calls `compute_calibration_state` and includes `calibration_state` in its return dict
- **Created:** `tests/test_calibration.py` — 5 tests covering all calibration branches

---

## `src/cohort/calibrator.py` contents

```python
from __future__ import annotations
from datetime import datetime, timezone
from src.schema.cohort import CalibrationState, CohortEnvelope

def compute_calibration_state(envelope, simulation_results):
    if not simulation_results:
        return CalibrationState(status="uncalibrated")
    n = len(simulation_results)
    decided_count = sum(
        1 for pr in simulation_results
        if any(r.get("decided", False) for r in pr.get("rounds", []))
    )
    consistency_score = decided_count / n if n > 0 else 0.0
    status = "benchmark_calibrated" if consistency_score >= 0.5 else "calibration_failed"
    return CalibrationState(
        status=status,
        method_applied="decision_consistency",
        last_calibrated=datetime.now(timezone.utc),
        benchmark_source="internal_simulation",
        notes=f"consistency_score={consistency_score:.2f}; N={n}",
    )

def apply_calibration(envelope, simulation_results):
    new_state = compute_calibration_state(envelope, simulation_results)
    return envelope.model_copy(update={"calibration_state": new_state})
```

---

## Changes to `_run_simulation` in `cli.py`

After `results = list(await asyncio.gather(...))`:

```python
from src.cohort.calibrator import compute_calibration_state
calibration = compute_calibration_state(envelope, results)

return {
    "simulation_id": ...,
    "cohort_id": envelope.cohort_id,
    "rounds": rounds,
    "decision_scenario": decision_scenario,
    "results": results,
    "calibration_state": {
        "status": calibration.status,
        "method_applied": calibration.method_applied,
        "consistency_score": float(calibration.notes.split("=")[1].split(";")[0]) if calibration.notes else None,
        "N": len(results),
    },
}
```

---

## Test Results

### `tests/test_calibration.py`

```
test_calibration_all_decided   PASSED
test_calibration_none_decided  PASSED
test_calibration_empty_results PASSED
test_calibration_partial       PASSED
test_calibration_notes_format  PASSED

5 passed in 0.27s
```

### Full Suite

```
238 passed, 10 skipped in 1.78s
```

---

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
