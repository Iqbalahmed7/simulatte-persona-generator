"""tests/test_retry_hardening.py — BRIEF-024 retry hardening tests for 503/529."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.utils.retry import api_call_with_retry


def _make_exc(status: int) -> Exception:
    exc = Exception(f"HTTP {status}")
    exc.status_code = status  # type: ignore[attr-defined]
    return exc


def _make_governor():
    gov = MagicMock()
    gov.acquire = AsyncMock()
    gov.record_response = MagicMock()
    gov.state = MagicMock(return_value={})
    gov.trigger_adaptive_throttle = MagicMock()
    return gov


@pytest.mark.asyncio
async def test_503_retries_with_exponential_backoff():
    """503 should retry up to 3 times (delays tuple has 3 entries) before raising."""
    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        raise _make_exc(503)

    gov = _make_governor()
    with (
        patch("src.utils.retry.get_governor", return_value=gov),
        patch("src.utils.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        with pytest.raises(Exception, match="HTTP 503"):
            await api_call_with_retry(flaky, delays=(0.0, 0.0, 0.0))

    # 1 initial attempt + 3 retries = 4 total calls
    assert call_count == 4
    # delays are 0.0 so sleep is never actually awaited (delay > 0 guard in retry loop)
    assert mock_sleep.call_count == 0


@pytest.mark.asyncio
async def test_529_retries_with_exponential_backoff():
    """529 (Anthropic overloaded) should retry up to 3 times before raising."""
    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        raise _make_exc(529)

    gov = _make_governor()
    with (
        patch("src.utils.retry.get_governor", return_value=gov),
        patch("src.utils.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        with pytest.raises(Exception, match="HTTP 529"):
            await api_call_with_retry(flaky, delays=(0.0, 0.0, 0.0))

    assert call_count == 4
    assert mock_sleep.call_count == 0  # delays=0.0, sleep is skipped by > 0 guard


@pytest.mark.asyncio
async def test_503_succeeds_on_second_attempt():
    """503 should retry and return successfully if the API recovers."""
    call_count = 0

    async def recovers():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise _make_exc(503)
        result = MagicMock()
        result.usage = None
        return result

    gov = _make_governor()
    with (
        patch("src.utils.retry.get_governor", return_value=gov),
        patch("src.utils.retry.asyncio.sleep", new_callable=AsyncMock),
        patch("src.utils.retry.note_api_call"),
    ):
        result = await api_call_with_retry(recovers, delays=(0.0, 0.0, 0.0))

    assert result is not None
    assert call_count == 2


@pytest.mark.asyncio
async def test_503_does_not_trigger_adaptive_throttle():
    """503 is a service error, not a rate limit — must NOT trigger adaptive throttle."""
    async def always_503():
        raise _make_exc(503)

    gov = _make_governor()
    with (
        patch("src.utils.retry.get_governor", return_value=gov),
        patch("src.utils.retry.asyncio.sleep", new_callable=AsyncMock),
    ):
        with pytest.raises(Exception):
            await api_call_with_retry(always_503, delays=(0.0, 0.0, 0.0))

    gov.trigger_adaptive_throttle.assert_not_called()


@pytest.mark.asyncio
async def test_non_retryable_500_raises_immediately():
    """HTTP 500 is not in _RETRYABLE_STATUS — should raise immediately, no retries."""
    call_count = 0

    async def server_error():
        nonlocal call_count
        call_count += 1
        raise _make_exc(500)

    gov = _make_governor()
    with (
        patch("src.utils.retry.get_governor", return_value=gov),
        patch("src.utils.retry.asyncio.sleep", new_callable=AsyncMock),
    ):
        with pytest.raises(Exception, match="HTTP 500"):
            await api_call_with_retry(server_error, delays=(0.0, 0.0, 0.0))

    assert call_count == 1
