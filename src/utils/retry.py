"""src/utils/retry.py — Async exponential backoff retry for Anthropic API calls."""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from src.utils.credit_monitor import (
    CreditExhaustedError,
    is_credit_exhaustion_error,
    note_api_call,
    request_halt,
)

_RETRYABLE_STATUS = {429, 529}
_DEFAULT_DELAYS = (1.0, 2.0, 4.0)  # seconds between retries


async def api_call_with_retry(
    coro_fn: Callable,
    *args: Any,
    delays: tuple[float, ...] = _DEFAULT_DELAYS,
    **kwargs: Any,
) -> Any:
    """Call an async API function with exponential backoff on 429/529 errors.

    Args:
        coro_fn: Async callable (e.g. client.messages.create)
        *args: Positional args to pass to coro_fn
        delays: Sequence of wait times between retries (default: 1s, 2s, 4s)
        **kwargs: Keyword args to pass to coro_fn

    Returns:
        The result of coro_fn(*args, **kwargs)

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exc: Exception | None = None
    for _attempt, delay in enumerate(((0.0,) + delays)):
        if delay > 0:
            await asyncio.sleep(delay)
        try:
            note_api_call()
            return await coro_fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if is_credit_exhaustion_error(exc):
                request_halt(reason=f"Anthropic credit exhausted (HTTP 400): {exc}")
                raise CreditExhaustedError(str(exc)) from exc

            status = getattr(exc, "status_code", None)
            if status not in _RETRYABLE_STATUS:
                raise  # non-retryable — re-raise immediately
            # retryable — continue to next attempt
    raise last_exc  # type: ignore[misc]
