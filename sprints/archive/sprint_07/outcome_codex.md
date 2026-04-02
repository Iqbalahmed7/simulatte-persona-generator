# Sprint 7 Outcome — Codex

## 1. Files Created

| File | Lines |
|------|-------|
| `tests/test_simulation_structural.py` | 164 |
| `src/modalities/simulation_report.py` | 105 |

One existing file was modified:
- `src/modalities/simulation.py`: changed `run_loop` call from keyword args (`stimulus=`, `persona=`) to positional args so the test's `side_effect` mock with parameter `persona_arg` could intercept the call correctly.

---

## 2. Test Results

```
tests/test_simulation_structural.py::test_simulation_produces_correct_turn_logs   PASSED
tests/test_simulation_structural.py::test_simulation_accumulates_memory_across_turns  PASSED
tests/test_simulation_structural.py::test_simulation_report_attitude_arc          PASSED
```

All 3 structural tests pass. Full suite: 52 passed, 5 skipped (integration tests gated on `--integration`).

---

## 3. Memory Accumulation Test — Persona State Threading

The test verifies that `run_loop` receives an updated persona on each successive turn rather than a fresh copy of the original. The approach used:

- A `capture_run_loop` side-effect function records each `(stimulus, persona_arg)` call in `call_args_list`.
- On each call, it appends a new `Observation` to the persona's working memory via `WorkingMemoryManager.write_observation`, then returns the enriched persona as `updated_persona`.
- `run_simulation` threads the returned `updated_persona` as the input to the next turn's `run_loop` call (via `persona = updated_persona` in the stimulus loop).
- The assertion checks `call_args_list[1]` — the persona passed to turn 2 — and confirms it holds at least one observation from turn 1.

This validates the "no reset between turns" contract: working memory persists and accumulates across the full stimulus sequence.

---

## 4. Known Gaps

- `generate_simulation_report` flattens all personas' turn logs into a single `attitude_arc` list. For multi-persona simulations, consumers must filter by `persona_id` if per-persona arcs are needed.
- `DecisionSummary` includes `avg_confidence` (added by linter) which equals `confidence` for single-persona runs; multi-persona aggregation is not implemented.
- No serialisation helpers (JSON/dict export) on `SimulationResult` or `SimulationReport`.
- `run_simulation` does not support cohort mode in the current implementation (raises `ValueError`); cohort simulation would require extending to accept `session.cohort`.
