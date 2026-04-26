"""src/utils/retry.py — Async exponential backoff retry for Anthropic API calls."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Callable

from src.utils.credit_monitor import (
    CreditExhaustedError,
    is_credit_exhaustion_error,
    note_api_call,
    request_halt,
)
from src.utils.rate_governor import GovernorTimeout, get_governor

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {429, 503, 529}
_DEFAULT_DELAYS = (1.0, 2.0, 4.0)  # seconds between retries (exponential: 1s/2s/4s)

# Sentinel: read SIMULATTE_GOVERNOR_TIMEOUT_S env var as the default governor timeout.
# calibrated_generator sets this env var before invoking PG so the governor
# timeout propagates through the full call chain without threading the parameter.
# Set to "0" or "" to disable (blocks indefinitely — original behavior).
_ENV_GOVERNOR_TIMEOUT: float | None = None
_raw = os.getenv("SIMULATTE_GOVERNOR_TIMEOUT_S", "600")
if _raw:
    try:
        _v = float(_raw)
        if _v > 0:
            _ENV_GOVERNOR_TIMEOUT = _v
    except ValueError:
        pass


async def api_call_with_retry(
    coro_fn: Callable,
    *args: Any,
    delays: tuple[float, ...] = _DEFAULT_DELAYS,
    governor_timeout: float | None = _ENV_GOVERNOR_TIMEOUT,
    **kwargs: Any,
) -> Any:
    """Call an async API function with exponential backoff on 429/529 errors.

    Integrates with the rate governor: every call acquires token budget before
    executing, then records actual token usage after. On 429, triggers adaptive
    throttle to reduce effective rate limits for 60 seconds.

    Args:
        coro_fn: Async callable (e.g. client.messages.create)
        *args: Positional args to pass to coro_fn
        delays: Sequence of wait times between retries (default: 1s, 2s, 4s)
        governor_timeout: if provided, passed to RateGovernor.acquire() as
            wait_budget_seconds. Raises GovernorTimeout if budget can't be
            acquired in time. If None, blocks indefinitely (existing behavior).
        **kwargs: Keyword args to pass to coro_fn

    Returns:
        The result of coro_fn(*args, **kwargs)

    Raises:
        GovernorTimeout: if governor_timeout is set and budget can't be acquired.
        The last exception if all retries are exhausted.
    """
    governor = get_governor()
    estimated_tokens = _estimate_tokens_from_args(args, kwargs)

    last_exc: Exception | None = None
    for _attempt, delay in enumerate(((0.0,) + delays)):
        if delay > 0:
            await asyncio.sleep(delay)
        try:
            # Acquire budget from rate governor (raises GovernorTimeout if timed out)
            await governor.acquire(estimated_tokens, wait_budget_seconds=governor_timeout)

            note_api_call()
            response = await coro_fn(*args, **kwargs)

            # Reconcile actual vs estimated tokens
            actual_tokens = _get_token_usage(response)
            if actual_tokens is not None:
                governor.record_response(actual_tokens)

            return response
        except GovernorTimeout:
            raise  # Not a response error — propagate immediately, no record_response
        except Exception as exc:
            last_exc = exc
            if is_credit_exhaustion_error(exc):
                request_halt(reason=f"Anthropic credit exhausted (HTTP 400): {exc}")
                raise CreditExhaustedError(str(exc)) from exc

            status = getattr(exc, "status_code", None)
            if status not in _RETRYABLE_STATUS:
                raise  # non-retryable — re-raise immediately

            # Handle 429 with adaptive throttle
            if status == 429:
                governor.trigger_adaptive_throttle()
                logger.warning(
                    f"Rate limit 429 hit, reducing effective target_pct for 60s. "
                    f"Current state: {governor.state()}"
                )
                # Check for Retry-After header
                retry_after = getattr(exc, "headers", {}).get("retry-after")
                if retry_after:
                    try:
                        delay = float(retry_after)
                        # Respect Retry-After by updating delay for next iteration
                        if _attempt < len(delays):
                            delays_list = list(delays)
                            delays_list[_attempt] = max(delays_list[_attempt], delay)
                    except (ValueError, TypeError):
                        pass

            # Handle 503 (service unavailable) — transient infrastructure error
            elif status == 503:
                logger.warning(
                    "Service unavailable (503) — exponential backoff retry %d/%d.",
                    _attempt,
                    len(delays),
                )

            # Handle 529 (Anthropic overloaded) — distinct from rate-limit 429
            elif status == 529:
                logger.warning(
                    "Anthropic overloaded (529) — exponential backoff retry %d/%d.",
                    _attempt,
                    len(delays),
                )

            # retryable — continue to next attempt
    raise last_exc  # type: ignore[misc]


def _estimate_tokens_from_args(args: tuple[Any, ...], kwargs: dict[str, Any]) -> int:
    """Estimate tokens from messages and max_tokens arguments.

    Simple heuristic: len(text) // 4. For message lists, sum across all.
    """
    total = 0

    # Look for 'messages' kwarg (typical for Anthropic API)
    if "messages" in kwargs:
        messages = kwargs["messages"]
        if isinstance(messages, list):
            for msg in messages:
                if isinstance(msg, dict) and "content" in msg:
                    content = msg["content"]
                    if isinstance(content, str):
                        total += len(content) // 4
        elif isinstance(messages, str):
            total += len(messages) // 4

    # Look for 'max_tokens' kwarg
    if "max_tokens" in kwargs:
        total += kwargs["max_tokens"]

    # Positional args: check for messages-like first positional
    if args:
        # If first positional looks like messages, estimate it
        for arg in args:
            if isinstance(arg, str):
                total += len(arg) // 4
            elif isinstance(arg, list):
                for item in arg:
                    if isinstance(item, dict) and "content" in item:
                        content = item["content"]
                        if isinstance(content, str):
                            total += len(content) // 4

    return max(1, total)  # At least 1 token estimate


def _get_token_usage(response: Any) -> int | None:
    """Extract actual token usage from response.

    Looks for response.usage.input_tokens and output_tokens.
    """
    if response is None:
        return None

    usage = getattr(response, "usage", None)
    if usage is None:
        return None

    input_tokens = getattr(usage, "input_tokens", 0)
    output_tokens = getattr(usage, "output_tokens", 0)
    return input_tokens + output_tokens
