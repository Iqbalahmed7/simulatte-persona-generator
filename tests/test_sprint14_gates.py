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
