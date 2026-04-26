"""src/utils/rate_governor.py — Token-bucket rate governor for Anthropic API limits."""
from __future__ import annotations

import asyncio
import os
import time
from collections import deque
from dataclasses import dataclass


@dataclass
class RateGovernorState:
    """Current state of the rate governor for observability."""

    rpm_used: int
    rpm_limit: int
    tpm_used: int
    tpm_limit: int
    target_pct: float
    throttle_active: bool


class GovernorTimeout(RuntimeError):
    """Raised when RateGovernor.acquire() cannot obtain budget within wait_budget_seconds."""


class RateGovernor:
    """Token-bucket governor that tracks RPM and TPM over sliding 60s windows.

    Stays at target_pct of declared limits. On 429, adaptively reduces target_pct
    for 60 seconds. Uses time.monotonic() for wall-clock-independent timing.
    """

    WINDOW_SECONDS = 60

    def __init__(self, rpm_limit: int, tpm_limit: int, target_pct: float = 0.80):
        """Initialize the governor.

        Args:
            rpm_limit: Requests per minute limit (default 4000)
            tpm_limit: Tokens per minute limit (default 800000)
            target_pct: Stay at this fraction of declared limits (default 0.80)
        """
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.target_pct = target_pct
        self._effective_target_pct = target_pct

        # Sliding window: deque of (timestamp, count/tokens) tuples
        self._rpm_window: deque[tuple[float, int]] = deque()
        self._tpm_window: deque[tuple[float, int]] = deque()

        # Throttle state: when was it activated?
        self._throttle_start: float | None = None

        # Lock for concurrent safety
        self._lock = asyncio.Lock()

    async def acquire(
        self,
        estimated_tokens: int,
        wait_budget_seconds: float | None = None,
    ) -> None:
        """Block until budget is available for estimated_tokens.

        Whichever is more constrained (RPM or TPM) gates the acquire.

        Args:
            estimated_tokens: token cost of the upcoming call.
            wait_budget_seconds: if provided, raise GovernorTimeout after this
                many seconds of queue blocking. If None, blocks indefinitely
                (existing behavior — backward compatible).

        Raises:
            GovernorTimeout: budget couldn't be acquired within wait_budget_seconds.
        """
        deadline = (
            time.monotonic() + wait_budget_seconds
            if wait_budget_seconds is not None
            else None
        )

        async def _acquire_body() -> None:
            while True:
                async with self._lock:
                    now = time.monotonic()

                    # Check if throttle period (60s) has expired
                    if self._throttle_start is not None:
                        if now - self._throttle_start >= self.WINDOW_SECONDS:
                            self._throttle_start = None
                            self._effective_target_pct = self.target_pct

                    # Evict stale entries
                    self._evict_old_entries(now)

                    # Calculate current usage
                    rpm_used = len(self._rpm_window)
                    tpm_used = sum(tokens for _, tokens in self._tpm_window)

                    # Calculate thresholds
                    rpm_threshold = int(self.rpm_limit * self._effective_target_pct)
                    tpm_threshold = int(self.tpm_limit * self._effective_target_pct)

                    # Check if we can proceed
                    if rpm_used < rpm_threshold and tpm_used + estimated_tokens <= tpm_threshold:
                        # Record this request (estimate)
                        self._rpm_window.append((now, 1))
                        self._tpm_window.append((now, estimated_tokens))
                        return

                # Release lock and wait before retrying
                await asyncio.sleep(0.01)  # 10ms wait before retry

        if deadline is None:
            await _acquire_body()
        else:
            remaining = deadline - time.monotonic()
            try:
                await asyncio.wait_for(_acquire_body(), timeout=max(0.0, remaining))
            except asyncio.TimeoutError:
                raise GovernorTimeout(
                    f"RateGovernor could not acquire {estimated_tokens} tokens "
                    f"within {wait_budget_seconds:.1f}s budget"
                )

    def record_response(self, actual_tokens: int) -> None:
        """Reconcile estimated vs actual tokens after the API call.

        If we over-estimated, adjust the trailing entry in the window.
        If we under-estimated, the overage is recorded (token count increased).
        """
        if self._tpm_window:
            ts, estimated = self._tpm_window[-1]
            # Update to actual (could be higher or lower)
            self._tpm_window[-1] = (ts, actual_tokens)

    def trigger_adaptive_throttle(self) -> None:
        """Called when a 429 is hit: reduce target_pct by 10% for 60 seconds."""
        now = time.monotonic()
        self._throttle_start = now
        self._effective_target_pct = max(0.1, self.target_pct - 0.10)

    def state(self) -> RateGovernorState:
        """Return current governor state for observability."""
        now = time.monotonic()
        self._evict_old_entries(now)

        rpm_used = len(self._rpm_window)
        tpm_used = sum(tokens for _, tokens in self._tpm_window)
        throttle_active = (
            self._throttle_start is not None
            and now - self._throttle_start < self.WINDOW_SECONDS
        )

        return RateGovernorState(
            rpm_used=rpm_used,
            rpm_limit=self.rpm_limit,
            tpm_used=tpm_used,
            tpm_limit=self.tpm_limit,
            target_pct=self._effective_target_pct,
            throttle_active=throttle_active,
        )

    def _evict_old_entries(self, now: float) -> None:
        """Remove entries older than WINDOW_SECONDS from both windows."""
        cutoff = now - self.WINDOW_SECONDS
        while self._rpm_window and self._rpm_window[0][0] < cutoff:
            self._rpm_window.popleft()
        while self._tpm_window and self._tpm_window[0][0] < cutoff:
            self._tpm_window.popleft()


# Module-level singleton
_governor: RateGovernor | None = None
_governor_lock = asyncio.Lock()


def get_governor() -> RateGovernor:
    """Get or create the singleton rate governor.

    Reads limits from environment:
    - SIMULATTE_RPM_LIMIT (default 4000)
    - SIMULATTE_TPM_LIMIT (default 800000)
    - SIMULATTE_RATE_TARGET_PCT (default 0.80)
    """
    global _governor
    if _governor is None:
        rpm_limit = int(os.getenv("SIMULATTE_RPM_LIMIT", "4000"))
        tpm_limit = int(os.getenv("SIMULATTE_TPM_LIMIT", "800000"))
        target_pct = float(os.getenv("SIMULATTE_RATE_TARGET_PCT", "0.80"))
        _governor = RateGovernor(rpm_limit, tpm_limit, target_pct)
    return _governor


def reset_governor_for_tests() -> None:
    """Reset the singleton for test isolation."""
    global _governor
    _governor = None
