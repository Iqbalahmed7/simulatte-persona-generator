"""tests/test_rate_governor.py — Tests for the rate governor."""
from __future__ import annotations

import asyncio

import pytest

from src.utils.rate_governor import RateGovernor, get_governor, reset_governor_for_tests


class TestAcquireBlocksWhenRpmAtTarget:
    """Test that acquire blocks when RPM reaches the target threshold."""

    @pytest.mark.asyncio
    async def test_acquire_blocks_when_rpm_at_target(self):
        """When 80% of RPM is used, next acquire should wait."""
        governor = RateGovernor(rpm_limit=100, tpm_limit=100000, target_pct=0.80)

        # Acquire 80 requests to hit the 80% threshold
        for _ in range(80):
            await governor.acquire(1)

        # Next acquire should block for a short time
        start = asyncio.get_event_loop().time()
        task = asyncio.create_task(governor.acquire(1))
        await asyncio.sleep(0.05)
        assert not task.done(), "acquire should be blocking"
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed >= 0.05, "acquire should have blocked"


class TestAcquireBlocksWhenTpmAtTarget:
    """Test that acquire blocks when TPM reaches the target threshold."""

    @pytest.mark.asyncio
    async def test_acquire_blocks_when_tpm_at_target(self):
        """When 80% of TPM is used, next acquire should wait."""
        governor = RateGovernor(rpm_limit=10000, tpm_limit=1000, target_pct=0.80)

        # Acquire tokens up to 80% of TPM threshold
        # tpm_threshold = 1000 * 0.80 = 800 tokens
        await governor.acquire(800)

        # Next acquire should block because we'd exceed the threshold
        start = asyncio.get_event_loop().time()
        task = asyncio.create_task(governor.acquire(100))
        await asyncio.sleep(0.05)
        assert not task.done(), "acquire should be blocking due to TPM"
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed >= 0.05, "acquire should have blocked"


class TestRecordResponseCreditsBackUnusedTokens:
    """Test that record_response reconciles estimated vs actual tokens."""

    @pytest.mark.asyncio
    async def test_record_response_credits_back_unused_tokens(self):
        """Over-estimated tokens should get credited back."""
        governor = RateGovernor(rpm_limit=100, tpm_limit=10000, target_pct=0.80)

        # Estimate 500 tokens
        await governor.acquire(500)
        state = governor.state()
        assert state.tpm_used == 500

        # But actual was only 100 tokens
        governor.record_response(100)
        state = governor.state()
        assert state.tpm_used == 100, "Over-estimated tokens should be credited back"


class Test429ResponseTriggersAdaptiveThrottle:
    """Test that hitting a 429 triggers adaptive throttle."""

    def test_429_response_triggers_adaptive_throttle(self):
        """When retry.py sees a 429, governor target should reduce."""
        governor = RateGovernor(rpm_limit=100, tpm_limit=100000, target_pct=0.80)

        initial_pct = governor._effective_target_pct
        assert initial_pct == 0.80

        # Simulate 429 hit
        governor.trigger_adaptive_throttle()

        # Effective target should be reduced by 0.10
        assert abs(governor._effective_target_pct - 0.70) < 0.0001
        assert governor._throttle_start is not None

    @pytest.mark.asyncio
    async def test_adaptive_throttle_expires_after_60_seconds(self):
        """Throttle should reset after 60s window expires."""
        import time

        governor = RateGovernor(rpm_limit=100, tpm_limit=100000, target_pct=0.80)

        # Mock the time by directly setting throttle_start to past
        governor._throttle_start = time.monotonic() - 61
        governor._effective_target_pct = 0.70

        # Next acquire should reset the throttle
        await governor.acquire(1)

        # Should be back to original target
        assert governor._effective_target_pct == 0.80
        assert governor._throttle_start is None


class TestStateReflectsCurrentUsage:
    """Test that state() returns accurate usage information."""

    @pytest.mark.asyncio
    async def test_state_reflects_current_usage(self):
        """state() should return sane values for current usage."""
        governor = RateGovernor(rpm_limit=100, tpm_limit=10000, target_pct=0.80)

        # Acquire some requests
        await governor.acquire(500)
        await governor.acquire(300)

        state = governor.state()
        assert state.rpm_used == 2, "Should have 2 requests in the window"
        assert state.tpm_used == 800, "Should have 800 tokens in the window"
        assert state.rpm_limit == 100
        assert state.tpm_limit == 10000
        assert state.target_pct == 0.80
        assert state.throttle_active is False

        # Trigger throttle
        governor.trigger_adaptive_throttle()
        state = governor.state()
        assert state.throttle_active is True
        assert abs(state.target_pct - 0.70) < 0.0001


class TestConcurrentAcquireSerializes:
    """Test that concurrent acquires don't race."""

    @pytest.mark.asyncio
    async def test_concurrent_acquire_serializes(self):
        """100 concurrent acquires should complete without race conditions."""
        governor = RateGovernor(rpm_limit=150, tpm_limit=100000, target_pct=0.80)

        # Create 100 concurrent acquire tasks
        tasks = [governor.acquire(100) for _ in range(100)]

        # Run them all
        await asyncio.gather(*tasks)

        # All 100 should be recorded
        state = governor.state()
        assert state.rpm_used == 100, "All 100 requests should be in window"
        assert state.tpm_used == 10000, "All 10000 tokens should be in window"


class TestSingletonGovernor:
    """Test the module-level singleton pattern."""

    def test_get_governor_returns_singleton(self):
        """get_governor() should return the same instance."""
        reset_governor_for_tests()
        gov1 = get_governor()
        gov2 = get_governor()
        assert gov1 is gov2, "Should return the same singleton"

    def test_get_governor_reads_env_vars(self, monkeypatch):
        """get_governor() should read limits from environment."""
        reset_governor_for_tests()
        monkeypatch.setenv("SIMULATTE_RPM_LIMIT", "5000")
        monkeypatch.setenv("SIMULATTE_TPM_LIMIT", "900000")
        monkeypatch.setenv("SIMULATTE_RATE_TARGET_PCT", "0.75")

        gov = get_governor()
        assert gov.rpm_limit == 5000
        assert gov.tpm_limit == 900000
        assert gov.target_pct == 0.75

    def test_reset_governor_for_tests(self):
        """reset_governor_for_tests() should clear the singleton."""
        get_governor()
        reset_governor_for_tests()
        # After reset, a new get_governor() call should create a fresh instance
        gov = get_governor()
        assert gov.rpm_limit == 4000  # default
        assert gov.tpm_limit == 800000  # default
