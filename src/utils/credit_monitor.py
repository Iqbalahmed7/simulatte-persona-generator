"""Credit balance monitoring and process-local halt signaling for Anthropic calls."""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class CreditExhaustedError(Exception):
    """Raised when Anthropic credit balance is too low to safely continue."""


@dataclass
class HaltSignal:
    requested: bool = False
    reason: str = ""
    balance_usd: float | None = None
    run_id: str | None = None
    last_completed_cluster: str | None = None
    last_completed_ensemble: str | None = None
    checkpoint_path: str | None = None
    requested_at: str | None = None


class CreditMonitor:
    """Tracks Anthropic credit state and emits a process-local halt signal."""

    def __init__(
        self,
        *,
        buffer_usd: float = 10.0,
        poll_every_calls: int = 200,
        usage_endpoint: str = "https://api.anthropic.com/v1/organizations/usage",
        api_key: str | None = None,
        ntfy_topic: str | None = None,
        ntfy_base_url: str = "https://ntfy.sh",
    ) -> None:
        self.buffer_usd = float(buffer_usd)
        self.poll_every_calls = max(1, int(poll_every_calls))
        self.usage_endpoint = usage_endpoint
        self.api_key = api_key
        self.ntfy_topic = ntfy_topic
        self.ntfy_base_url = ntfy_base_url.rstrip("/")

        self._halt = HaltSignal()
        self._api_calls = 0
        self._last_polled_calls = 0
        self._monitor_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    @classmethod
    def from_env(cls) -> "CreditMonitor":
        return cls(
            buffer_usd=float(os.getenv("SIMULATTE_CREDIT_BUFFER_USD", "10")),
            poll_every_calls=int(os.getenv("SIMULATTE_CREDIT_POLL_EVERY_CALLS", "200")),
            usage_endpoint=os.getenv(
                "SIMULATTE_ANTHROPIC_USAGE_ENDPOINT",
                "https://api.anthropic.com/v1/organizations/usage",
            ),
            api_key=(
                os.getenv("ANTHROPIC_ADMIN_API_KEY")
                or os.getenv("ANTHROPIC_API_KEY")
            ),
            ntfy_topic=os.getenv("SIMULATTE_NTFY_TOPIC"),
            ntfy_base_url=os.getenv("SIMULATTE_NTFY_BASE_URL", "https://ntfy.sh"),
        )

    def update_progress(
        self,
        *,
        run_id: str,
        cluster_id: str | None = None,
        ensemble_idx: int | None = None,
        ensemble_total: int | None = None,
        checkpoint_path: str | None = None,
    ) -> None:
        self._halt.run_id = run_id
        self._halt.last_completed_cluster = cluster_id
        if ensemble_idx is not None and ensemble_total is not None:
            self._halt.last_completed_ensemble = f"{ensemble_idx}/{ensemble_total}"
        if checkpoint_path:
            self._halt.checkpoint_path = checkpoint_path

    def note_api_call(self) -> None:
        self._api_calls += 1

    def is_halt_requested(self) -> bool:
        return bool(self._halt.requested)

    def halt_snapshot(self) -> dict[str, Any]:
        return {
            "requested": self._halt.requested,
            "reason": self._halt.reason,
            "balance_usd": self._halt.balance_usd,
            "run_id": self._halt.run_id,
            "last_completed_cluster": self._halt.last_completed_cluster,
            "last_completed_ensemble": self._halt.last_completed_ensemble,
            "checkpoint_path": self._halt.checkpoint_path,
            "requested_at": self._halt.requested_at,
        }

    def request_halt(
        self,
        *,
        reason: str,
        balance_usd: float | None = None,
    ) -> None:
        if self._halt.requested:
            return
        self._halt.requested = True
        self._halt.reason = reason
        self._halt.balance_usd = balance_usd
        self._halt.requested_at = datetime.now(timezone.utc).isoformat()
        logger.error("Credit halt requested: %s", reason)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._send_notification())
        except RuntimeError:
            pass

    async def preflight_check(self, *, run_id: str | None = None) -> float:
        if run_id:
            self._halt.run_id = run_id
        balance = await self.fetch_balance_usd()
        if balance < self.buffer_usd:
            self.request_halt(
                reason=(
                    f"Pre-flight credit check failed: balance ${balance:.2f} "
                    f"< buffer ${self.buffer_usd:.2f}"
                ),
                balance_usd=balance,
            )
            raise CreditExhaustedError(self._halt.reason)
        return balance

    async def start_background_monitor(self) -> None:
        if self._monitor_task and not self._monitor_task.done():
            return
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_background_monitor(self) -> None:
        if not self._monitor_task:
            return
        self._monitor_task.cancel()
        try:
            await self._monitor_task
        except asyncio.CancelledError:
            pass
        finally:
            self._monitor_task = None

    async def _monitor_loop(self) -> None:
        while not self._halt.requested:
            try:
                if (self._api_calls - self._last_polled_calls) >= self.poll_every_calls:
                    async with self._lock:
                        if (self._api_calls - self._last_polled_calls) >= self.poll_every_calls:
                            self._last_polled_calls = self._api_calls
                            balance = await self.fetch_balance_usd()
                            if balance < self.buffer_usd:
                                self.request_halt(
                                    reason=(
                                        f"In-flight credit check failed: balance ${balance:.2f} "
                                        f"< buffer ${self.buffer_usd:.2f}"
                                    ),
                                    balance_usd=balance,
                                )
                                return
                await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("credit monitor poll failed: %s", exc)
                await asyncio.sleep(1.0)

    async def fetch_balance_usd(self) -> float:
        if not self.api_key:
            raise RuntimeError(
                "Anthropic API key missing for credit monitor "
                "(set ANTHROPIC_ADMIN_API_KEY or ANTHROPIC_API_KEY)."
            )

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        timeout = httpx.Timeout(10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(self.usage_endpoint, headers=headers)
            response.raise_for_status()
            data = response.json()
        balance = _extract_balance_usd(data)
        if balance is None:
            raise RuntimeError("Unable to parse Anthropic balance from usage response")
        return float(balance)

    async def _send_notification(self) -> None:
        if not self.ntfy_topic:
            return
        snap = self.halt_snapshot()
        balance_txt = "unknown" if snap["balance_usd"] is None else f"${float(snap['balance_usd']):.2f}"
        msg = (
            "Simulatte run halted (credit low)\n"
            f"run_id={snap['run_id'] or 'unknown'}\n"
            f"balance={balance_txt}\n"
            f"last_cluster={snap['last_completed_cluster'] or 'unknown'}\n"
            f"last_ensemble={snap['last_completed_ensemble'] or 'unknown'}\n"
            f"checkpoint={snap['checkpoint_path'] or 'unknown'}\n"
            f"reason={snap['reason'] or 'credit halt'}"
        )
        url = f"{self.ntfy_base_url}/{self.ntfy_topic}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, content=msg.encode("utf-8"))
        except Exception as exc:
            logger.warning("Failed to send ntfy notification: %s", exc)


_MONITOR = CreditMonitor.from_env()


def get_credit_monitor() -> CreditMonitor:
    return _MONITOR


def reset_credit_monitor_for_tests() -> None:
    global _MONITOR
    _MONITOR = CreditMonitor.from_env()


def note_api_call() -> None:
    _MONITOR.note_api_call()


def is_halt_requested() -> bool:
    return _MONITOR.is_halt_requested()


def halt_snapshot() -> dict[str, Any]:
    return _MONITOR.halt_snapshot()


def request_halt(*, reason: str, balance_usd: float | None = None) -> None:
    _MONITOR.request_halt(reason=reason, balance_usd=balance_usd)


def is_credit_exhaustion_error(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status != 400:
        return False
    text = str(exc).lower()
    return "credit" in text and ("too low" in text or "balance" in text or "insufficient" in text)


def _extract_balance_usd(data: Any) -> float | None:
    """Best-effort balance extraction across possible Anthropic usage payload shapes."""
    if isinstance(data, (int, float)):
        return float(data)
    if not isinstance(data, dict):
        return None

    direct_keys = (
        "balance_usd",
        "available_credits_usd",
        "available_balance_usd",
        "remaining_balance_usd",
    )
    for key in direct_keys:
        value = data.get(key)
        if isinstance(value, (int, float)):
            return float(value)

    bal = data.get("balance")
    if isinstance(bal, dict):
        for key in ("usd", "available", "remaining", "amount"):
            value = bal.get(key)
            if isinstance(value, (int, float)):
                return float(value)

    for key in ("organization", "usage", "data"):
        nested = data.get(key)
        if isinstance(nested, dict):
            maybe = _extract_balance_usd(nested)
            if maybe is not None:
                return maybe
        elif isinstance(nested, list) and nested:
            for item in nested:
                maybe = _extract_balance_usd(item)
                if maybe is not None:
                    return maybe

    return None
