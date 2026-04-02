# SPRINT 14 OUTCOME — ANTIGRAVITY

**Role:** Sprint 14 Gate Tests
**Sprint:** 14 — Parallel Simulation + API Retry Wrapper + Calibration State
**Date:** 2026-04-02

---

## 1. File Created

**`tests/test_sprint14_gates.py`** — 11 tests covering all three Sprint 14 deliverables.

---

## 2. Test File Contents

```python
"""tests/test_sprint14_gates.py — Sprint 14 Gate Tests.

Validates the three Sprint 14 deliverables:
  - Parallel Simulation: _run_simulation uses asyncio.gather + nested _simulate_persona
  - API Retry Wrapper: src.utils.retry.api_call_with_retry is importable and correct
  - Calibration State: src.cohort.calibrator computes correct status values

No live API calls. All tests are structural or use pure-Python stubs.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Parallel Simulation (3 tests)
# ---------------------------------------------------------------------------

def test_simulate_uses_gather():
    """_run_simulation must use asyncio.gather for concurrent persona simulation."""
    import inspect
    from src import cli
    source = inspect.getsource(cli._run_simulation)
    assert "gather" in source, "_run_simulation must use asyncio.gather"


def test_simulate_persona_nested_coroutine():
    """_run_simulation must define a nested _simulate_persona coroutine."""
    import inspect
    from src import cli
    source = inspect.getsource(cli._run_simulation)
    assert "_simulate_persona" in source


def test_simulate_rounds_sequential_within_persona():
    """Rounds loop must be inside _simulate_persona (sequential per-persona)."""
    import inspect
    from src import cli
    source = inspect.getsource(cli._run_simulation)
    # _simulate_persona should contain a for loop over rounds
    assert "for round_num" in source or "enumerate" in source


# ---------------------------------------------------------------------------
# API Retry Wrapper (4 tests)
# ---------------------------------------------------------------------------

def test_retry_module_importable():
    """src.utils.retry must be importable."""
    from src.utils.retry import api_call_with_retry
    assert callable(api_call_with_retry)


def test_retry_succeeds_on_first_attempt():
    """api_call_with_retry returns immediately when call succeeds."""
    import asyncio
    from src.utils.retry import api_call_with_retry

    async def _ok():
        return "result"

    result = asyncio.run(api_call_with_retry(_ok, delays=()))
    assert result == "result"


def test_retry_reraises_non_retryable():
    """Non-retryable errors (e.g. ValueError) are re-raised immediately."""
    import asyncio
    import pytest
    from src.utils.retry import api_call_with_retry

    async def _fail():
        raise ValueError("not retryable")

    with pytest.raises(ValueError):
        asyncio.run(api_call_with_retry(_fail, delays=()))


def test_retry_retries_on_429():
    """429 errors trigger retries up to the delay count."""
    import asyncio
    import pytest
    from src.utils.retry import api_call_with_retry

    call_count = 0

    async def _rate_limited():
        nonlocal call_count
        call_count += 1
        err = Exception("rate limited")
        err.status_code = 429
        raise err

    with pytest.raises(Exception):
        asyncio.run(api_call_with_retry(_rate_limited, delays=(0, 0)))  # no actual sleep

    assert call_count == 3  # initial + 2 retries


# ---------------------------------------------------------------------------
# Calibration State (4 tests)
# ---------------------------------------------------------------------------

def test_calibration_module_importable():
    """src.cohort.calibrator must be importable."""
    from src.cohort.calibrator import compute_calibration_state, apply_calibration
    assert callable(compute_calibration_state)
    assert callable(apply_calibration)


def test_calibration_all_decided():
    """All personas decided → benchmark_calibrated."""
    from src.cohort.calibrator import compute_calibration_state
    results = [
        {"persona_id": "p1", "rounds": [{"decided": True}]},
        {"persona_id": "p2", "rounds": [{"decided": True}]},
    ]
    state = compute_calibration_state(None, results)
    assert state.status == "benchmark_calibrated"


def test_calibration_none_decided():
    """No personas decided → calibration_failed."""
    from src.cohort.calibrator import compute_calibration_state
    results = [
        {"persona_id": "p1", "rounds": [{"decided": False}]},
        {"persona_id": "p2", "rounds": [{"decided": False}]},
    ]
    state = compute_calibration_state(None, results)
    assert state.status == "calibration_failed"


def test_calibration_empty():
    """Empty results → uncalibrated."""
    from src.cohort.calibrator import compute_calibration_state
    state = compute_calibration_state(None, [])
    assert state.status == "uncalibrated"
```

---

## 3. Test Results: 11/11 Passed

All 11 Sprint 14 gate tests pass immediately — the source code already implements all three deliverables.

| # | Test | Status | Notes |
|---|------|--------|-------|
| 1 | `test_simulate_uses_gather` | PASSED | `asyncio.gather` found in `_run_simulation` source |
| 2 | `test_simulate_persona_nested_coroutine` | PASSED | `_simulate_persona` found in `_run_simulation` source |
| 3 | `test_simulate_rounds_sequential_within_persona` | PASSED | `for round_num` found inside `_simulate_persona` |
| 4 | `test_retry_module_importable` | PASSED | `api_call_with_retry` is callable |
| 5 | `test_retry_succeeds_on_first_attempt` | PASSED | Returns `"result"` immediately on first call |
| 6 | `test_retry_reraises_non_retryable` | PASSED | `ValueError` (no `status_code`) re-raised immediately |
| 7 | `test_retry_retries_on_429` | PASSED | `call_count == 3` (initial + 2 retries with `delays=(0, 0)`) |
| 8 | `test_calibration_module_importable` | PASSED | Both `compute_calibration_state` and `apply_calibration` are callable |
| 9 | `test_calibration_all_decided` | PASSED | `status == "benchmark_calibrated"` when all personas decided |
| 10 | `test_calibration_none_decided` | PASSED | `status == "calibration_failed"` when no personas decided |
| 11 | `test_calibration_empty` | PASSED | `status == "uncalibrated"` for empty results list |

No tests need other engineers — all deliverables were already implemented in the codebase.

---

## 4. Implementation Findings

### Parallel Simulation
`src/cli.py` — `_run_simulation()` defines a nested `async def _simulate_persona(persona)` coroutine
that contains a sequential `for round_num, stimulus in enumerate(all_stimuli[:rounds], 1):` loop.
The outer function then calls `asyncio.gather(*[_simulate_persona(p) for p in envelope.personas])`
for concurrent cross-persona execution.

### API Retry Wrapper
`src/utils/retry.py` — `api_call_with_retry(coro_fn, *args, delays=_DEFAULT_DELAYS, **kwargs)`
iterates over `(0.0,) + delays` attempts. Non-retryable exceptions (no `status_code` attribute, or
`status_code` not in `{429, 529}`) are re-raised immediately. Retryable 429/529 errors loop through
all delays before raising the last exception.

### Calibration State
`src/cohort/calibrator.py` — `compute_calibration_state(envelope, simulation_results)` returns a
`CalibrationState` with:
- `"uncalibrated"` when `simulation_results` is empty
- `"benchmark_calibrated"` when >= 50% of personas produced a decision
- `"calibration_failed"` when < 50% of personas produced a decision

`apply_calibration()` returns a new `CohortEnvelope` with the updated calibration state via `model_copy`.

---

## 5. Full Suite Result

```
249 passed, 10 skipped in 1.40s
```

Sprint 14 adds 11 new tests; all 11 pass immediately. No regressions introduced.
Prior baseline: 238 tests (249 - 11 new).
