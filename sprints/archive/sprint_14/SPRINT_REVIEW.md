# Sprint 14 Review — Performance + Production Hardening

**Sprint:** 14
**Theme:** Simulation Quality + Production Hardening
**Status:** COMPLETE ✅
**Date:** 2026-04-02
**Test Suite:** 249 passed, 15 skipped (up from 233 passed, 10 skipped)

---

## Deliverables

### Cursor — Parallel Simulation
- `src/cli.py` — `_run_simulation()` refactored with nested `_simulate_persona(persona)` coroutine + `asyncio.gather()`
- Rounds loop stays sequential inside each persona (state-dependent); persona-level parallelism via gather
- Removed unused `import anthropic`; added `import asyncio`
- **Result:** Multiple personas now simulate concurrently

### Codex — API Retry Wrapper
- `src/utils/__init__.py` — new package marker
- `src/utils/retry.py` — `api_call_with_retry(coro_fn, *args, delays=(1,2,4), **kwargs)` with exponential backoff on 429/529; non-retryable exceptions re-raise immediately
- `src/generation/attribute_filler.py` — replaced bare `for attempt in range(2)` loop with `api_call_with_retry`
- **Remaining callers for Sprint 15:** life_story_generator.py, narrative_generator.py, decide.py, perceive.py, reflect.py

### Goose — Calibration State
- `src/cohort/calibrator.py` — `compute_calibration_state()` + `apply_calibration()`; logic: ≥50% decided → benchmark_calibrated, <50% → calibration_failed, empty → uncalibrated
- `src/cli.py` — `_run_simulation()` now returns `"calibration_state"` key with status, method, score, N
- `tests/test_calibration.py` — 5 tests
- **Result:** Every simulation run produces a populated calibration_state

### OpenCode — Live E2E Test Suite
- `tests/test_live_e2e.py` — 5 tests (CPG generate, SaaS generate, simulate, survey, full pipeline); skipped by default, activated with `RUN_LIVE_TESTS=1`
- `tests/conftest.py` — created with `live` marker registration
- **Result:** 5 skipped (not failed) in normal test runs

### Antigravity — Sprint 14 Gate Tests
- `tests/test_sprint14_gates.py` — 11 tests (parallel sim ×3, retry wrapper ×4, calibration ×4)
- All 11 passed immediately
- **Result:** Full coverage of all Sprint 14 deliverables

---

## Engineer Ratings

| Engineer | Task | Quality | Notes |
|----------|------|---------|-------|
| Cursor | Parallel simulation | 10/10 | Clean nested coroutine, removed unused import |
| Codex | Retry wrapper | 10/10 | Clean utility module, complete caller inventory for Sprint 15 |
| Goose | Calibration state | 9/10 | Good boundary logic, 50% threshold well-reasoned |
| OpenCode | Live E2E suite | 9/10 | Proper skip mechanism, conftest.py created cleanly |
| Antigravity | Gate tests | 10/10 | All 11 passed immediately, good retry status_code mock |

---

## Live CLI Commands

```bash
# All previous commands unchanged

# Simulate (now parallel across personas)
python -m src.cli simulate --cohort cohort.json --scenario examples/scenario_cpg.json \
  --rounds 3 --output sim_results.json
# sim_results.json now includes calibration_state

# Run live E2E tests (requires API key)
RUN_LIVE_TESTS=1 python3 -m pytest tests/test_live_e2e.py -v
```

---

## Pending for Sprint 15 (suggestions)
- Apply `api_call_with_retry` to remaining 5 LLM callers (life_story, narrative, decide, perceive, reflect)
- Run live E2E tests and fix any issues found
- Simulation output: surface `promoted_memory_ids` in round results
- CLI `--version` flag
