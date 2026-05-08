"""services/benchmark/runner.py — Orchestrate a benchmark run end-to-end.

Fetches the persona, resolves the test list, runs tests sequentially (to avoid
hammering the Anthropic API), emits progress via an async generator, and
persists the result to SQLite.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from models import (
    BenchmarkEvent,
    BenchmarkReport,
    BenchmarkTier,
    RunStatus,
    TIER_TESTS,
)
from report import make_empty_report, mark_complete, mark_error, mark_running
from scoring import finalize_report
from storage import upsert_run
from tests.registry import get_test_instance

MIND_API = os.environ.get("MIND_API_URL", "http://localhost:8001")


async def _fetch_persona(persona_id: str) -> Dict[str, Any]:
    """Fetch persona payload from The Mind API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{MIND_API}/generated/{persona_id}")
        resp.raise_for_status()
        return resp.json()


def _resolve_test_ids(tier: BenchmarkTier, custom_tests: List[str]) -> List[str]:
    if tier == BenchmarkTier.CUSTOM:
        if not custom_tests:
            raise ValueError("custom_tests must be non-empty for CUSTOM tier")
        return custom_tests
    return TIER_TESTS[tier]


async def run_benchmark(
    persona_id: str,
    tier: BenchmarkTier = BenchmarkTier.STANDARD,
    custom_tests: Optional[List[str]] = None,
    persona_payload: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[BenchmarkEvent, None]:
    """
    Async generator that yields BenchmarkEvents as tests complete.

    Yields:
        started         — immediately
        test_complete   — after each test finishes
        complete        — when all tests done
        error           — if a fatal error occurs before tests run
    """
    run_id = str(uuid.uuid4())
    custom_tests = custom_tests or []
    test_ids = _resolve_test_ids(tier, custom_tests)

    # ── Fetch persona ──────────────────────────────────────────────────────────
    persona: Dict[str, Any]
    if persona_payload:
        persona = persona_payload
    else:
        try:
            persona = await _fetch_persona(persona_id)
        except Exception as exc:
            report = make_empty_report(run_id, persona_id, "unknown", tier)
            report = mark_error(report, f"Failed to fetch persona: {exc}")
            await upsert_run(report)
            yield BenchmarkEvent(
                type="error",
                run_id=run_id,
                message=str(exc),
            )
            return

    demo = persona.get("demographic_anchor", {})
    persona_name = demo.get("name", persona_id)

    # ── Initialise report ──────────────────────────────────────────────────────
    report = make_empty_report(run_id, persona_id, persona_name, tier)
    report = mark_running(report)
    await upsert_run(report)

    yield BenchmarkEvent(
        type="started",
        run_id=run_id,
        message=f"Running {len(test_ids)} tests for {persona_name} [{tier.value}]",
    )

    # ── Run tests sequentially ─────────────────────────────────────────────────
    for test_id in test_ids:
        try:
            test = get_test_instance(test_id)
            result = await test.run(persona)
        except Exception as exc:
            # Shouldn't reach here — BaseTest.run catches exceptions — but safety net
            from models import TestResult, TestStatus, TEST_WEIGHTS
            result = TestResult(
                test_id=test_id,
                label=test_id,
                status=TestStatus.ERROR,
                score=0.0,
                weight=TEST_WEIGHTS.get(test_id, 0.0),
                weighted_contribution=0.0,
                rationale=f"Runner error: {exc}",
                flags=["runner_exception"],
            )

        report.tests.append(result)
        await upsert_run(report)

        yield BenchmarkEvent(
            type="test_complete",
            run_id=run_id,
            test_id=result.test_id,
            test_label=result.label,
            score=result.score,
            message=result.rationale[:120] if result.rationale else "",
        )

        # Brief pause between tests to avoid API rate limits
        await asyncio.sleep(0.5)

    # ── Finalise ───────────────────────────────────────────────────────────────
    report = finalize_report(report)
    report = mark_complete(report)
    await upsert_run(report)

    yield BenchmarkEvent(
        type="complete",
        run_id=run_id,
        credibility_score=report.credibility_score,
        grade=report.grade,
        message=report.grade_label,
        report=report,
    )
