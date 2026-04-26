from __future__ import annotations

import asyncio

import httpx
import pytest

from src.utils.credit_monitor import CreditExhaustedError, CreditMonitor, is_credit_exhaustion_error
from src.utils import credit_monitor as credit_monitor_mod
from src.utils.retry import api_call_with_retry


def test_preflight_rejects_when_balance_below_buffer(monkeypatch):
    monitor = CreditMonitor(buffer_usd=10.0, poll_every_calls=200, api_key="test")

    async def _fake_balance() -> float:
        return 5.0

    monkeypatch.setattr(monitor, "fetch_balance_usd", _fake_balance)

    with pytest.raises(CreditExhaustedError):
        asyncio.run(monitor.preflight_check(run_id="run-preflight"))

    snap = monitor.halt_snapshot()
    assert snap["requested"] is True
    assert snap["balance_usd"] == 5.0
    assert snap["run_id"] == "run-preflight"


def test_mid_run_monitor_trips_halt_on_poll_threshold(monkeypatch):
    monitor = CreditMonitor(buffer_usd=10.0, poll_every_calls=2, api_key="test")
    balances = iter([9.0])

    async def _fake_balance() -> float:
        return next(balances)

    monkeypatch.setattr(monitor, "fetch_balance_usd", _fake_balance)

    async def _exercise() -> None:
        await monitor.start_background_monitor()
        monitor.note_api_call()
        monitor.note_api_call()
        await asyncio.sleep(0.35)
        assert monitor.is_halt_requested() is True
        await monitor.stop_background_monitor()

    asyncio.run(_exercise())


def test_credit_400_is_detected_and_not_retried(monkeypatch):
    credit_monitor_mod.reset_credit_monitor_for_tests()

    monitor = credit_monitor_mod.get_credit_monitor()
    calls = {"n": 0}

    async def _fail_credit():
        calls["n"] += 1
        err = Exception("BadRequestError: 400 - credit balance too low")
        err.status_code = 400
        raise err

    with pytest.raises(CreditExhaustedError):
        asyncio.run(api_call_with_retry(_fail_credit, delays=(0, 0, 0)))

    assert calls["n"] == 1
    assert monitor.is_halt_requested() is True


def test_halt_signal_snapshot_includes_progress_metadata():
    monitor = CreditMonitor(buffer_usd=10.0, poll_every_calls=2, api_key="test")
    monitor.update_progress(
        run_id="run-xyz",
        cluster_id="presidency_suburbs",
        ensemble_idx=1,
        ensemble_total=3,
        checkpoint_path="/tmp/wb_reruns/run-xyz.partial.json",
    )
    monitor.request_halt(reason="manual test halt", balance_usd=7.25)

    snap = monitor.halt_snapshot()
    assert snap["requested"] is True
    assert snap["run_id"] == "run-xyz"
    assert snap["last_completed_cluster"] == "presidency_suburbs"
    assert snap["last_completed_ensemble"] == "1/3"
    assert snap["checkpoint_path"] == "/tmp/wb_reruns/run-xyz.partial.json"


def test_credit_detection_helper():
    err = Exception("400 credit balance too low")
    err.status_code = 400
    assert is_credit_exhaustion_error(err) is True

    non_credit = Exception("400 bad request: invalid schema")
    non_credit.status_code = 400
    assert is_credit_exhaustion_error(non_credit) is False


def test_degrades_gracefully_when_no_api_key(caplog):
    monitor = CreditMonitor(buffer_usd=10.0, poll_every_calls=5, api_key=None)

    with caplog.at_level("WARNING"):
        balance = asyncio.run(monitor.preflight_check(run_id="run-no-key"))

    assert balance == 10.0
    assert monitor.proactive_monitoring_active is False
    assert monitor.is_halt_requested() is False
    assert "balance polling unavailable (no API key in env)" in caplog.text
    assert "relying on 400-credit-retry detection only" in caplog.text


def test_degrades_gracefully_on_403_from_balance_endpoint(monkeypatch, caplog):
    monitor = CreditMonitor(buffer_usd=10.0, poll_every_calls=5, api_key="regular-key")

    class _FakeResponse:
        status_code = 403

        def raise_for_status(self) -> None:
            raise httpx.HTTPStatusError("forbidden", request=None, response=None)

    class _FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            _ = args
            _ = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            _ = exc_type
            _ = exc
            _ = tb

        async def get(self, *args, **kwargs):
            _ = args
            _ = kwargs
            return _FakeResponse()

    monkeypatch.setattr(credit_monitor_mod.httpx, "AsyncClient", _FakeClient)

    with caplog.at_level("WARNING"):
        balance = asyncio.run(monitor.preflight_check(run_id="run-403"))

    assert balance == 10.0
    assert monitor.proactive_monitoring_active is False
    assert monitor.is_halt_requested() is False
    assert "balance polling unavailable (403 from balance endpoint — admin key required)" in caplog.text


def test_force_credit_low_env_triggers_halt(monkeypatch, caplog):
    monkeypatch.setenv("SIMULATTE_TEST_FORCE_CREDIT_LOW", "true")
    monitor = CreditMonitor(buffer_usd=10.0, poll_every_calls=5, api_key="test")

    with caplog.at_level("INFO"):
        with pytest.raises(CreditExhaustedError):
            asyncio.run(monitor.preflight_check(run_id="run-force-low"))

    snap = monitor.halt_snapshot()
    assert snap["requested"] is True
    assert snap["balance_usd"] == 0.0
    assert "test_force_credit_low active — credit-low path simulated for testing" in caplog.text
