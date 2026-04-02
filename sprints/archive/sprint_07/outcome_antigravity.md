# SPRINT 7 OUTCOME — ANTIGRAVITY
**Engineer:** Antigravity
**Role:** Simulation Structural Gate Tests + BV1 Multi-Turn Extension
**Sprint:** 7 — Temporal Simulation Modality
**Date:** 2026-04-02
**Status:** COMPLETE

---

## 1. File Created

| File | Action | Lines |
|------|--------|-------|
| `tests/test_simulation_gates.py` | Created | 221 |

No source files were created or modified.

---

## 2. Test Results

```
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
asyncio: mode=strict
collected 3 items

tests/test_simulation_gates.py::test_run_loop_called_correct_number_of_times  PASSED
tests/test_simulation_gates.py::test_decision_scenarios_paired_to_correct_turns PASSED
tests/test_simulation_gates.py::test_bv1_mock_decision_consistency             PASSED

============================== 3 passed in 0.52s ===============================
```

**Summary: 3 passed, 0 failed, 0 skipped**

---

## 3. Decision Scenario Pairing Verification

Test 2 (`test_decision_scenarios_paired_to_correct_turns`) verifies turn-to-scenario alignment by:

1. Creating a session with 3 stimuli and only 2 decision_scenarios (`["Decide on S0?", "Decide on S1?"]`).
2. Replacing `run_loop` with a `capture` coroutine that appends the `decision_scenario` kwarg to a `call_scenarios` list on each invocation.
3. After `run_simulation` completes, asserting directly on the captured list:
   - `call_scenarios[0] == "Decide on S0?"` — turn 0 receives scenario 0
   - `call_scenarios[1] == "Decide on S1?"` — turn 1 receives scenario 1
   - `call_scenarios[2] is None` — turn 2 has no paired scenario (index beyond list length)

The alignment is governed by `run_simulation`'s index-based pairing logic:
`session.decision_scenarios[i] if i < len(session.decision_scenarios) else None`.

---

## 4. Known Gaps

**Gap 1: `_make_minimal_cohort` deviates from brief's sample field names.**
The brief's helper used field names that do not match the actual `CohortEnvelope` schema (e.g. `taxonomy_meta` vs `taxonomy_used`, `summary` vs `cohort_summary`, `calibration` vs `calibration_state`). The brief explicitly instructed to verify against `src/schema/cohort.py` before writing — corrected field names were used.

**Gap 2: capture() signature corrected from brief.**
The brief's `capture` side-effect used positional arg `persona_arg`. The actual `run_loop` call from `_run_persona_turn` passes all arguments as keyword args (`stimulus=`, `persona=`, `decision_scenario=`). The signature was corrected to keyword-only to match the real call site.

**Gap 3: No multi-persona scenario pairing test.**
Scenario pairing is verified only for a single-persona session. The cohort mode uses the same index-based logic (verified implicitly by Test 1 call-count), but a dedicated multi-persona pairing assertion is absent.

**Gap 4: Tests use the same synthetic persona for all 3 slots in Test 1.**
`make_synthetic_persona()` always returns the same Priya Mehta record (same `persona_id`). The 3 personas in Test 1 are identical objects. Sufficient for call-count verification; a `make_synthetic_persona(suffix=i)` variant would improve per-persona isolation.
