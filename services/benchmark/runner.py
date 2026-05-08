"""services/benchmark/runner.py — Orchestrate a benchmark run end-to-end.

The benchmark service is product-agnostic. It does not know about The Mind,
White Rabbit, or any other Simulatte service. The caller always provides the
full persona JSON — no service-to-service fetching happens here.

Flow: persona_payload → resolve test list → run tests sequentially →
      emit SSE events → persist result to SQLite.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

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


def _resolve_test_ids(tier: BenchmarkTier, custom_tests: List[str]) -> List[str]:
    if tier == BenchmarkTier.CUSTOM:
        if not custom_tests:
            raise ValueError("custom_tests must be non-empty for CUSTOM tier")
        return custom_tests
    return TIER_TESTS[tier]


async def run_benchmark(
    persona_payload: Dict[str, Any],
    tier: BenchmarkTier = BenchmarkTier.STANDARD,
    custom_tests: Optional[List[str]] = None,
    persona_id: Optional[str] = None,      # optional tracking label only
) -> AsyncGenerator[BenchmarkEvent, None]:
    """
    Async generator that yields BenchmarkEvents as tests complete.

    Args:
        persona_payload: the full persona JSON — required, always provided by caller.
        tier: which test suite to run.
        custom_tests: test IDs to run when tier=CUSTOM.
        persona_id: optional identifier for storage/reporting (e.g. a database ID
                    from the calling service). Has no effect on test execution.

    Yields:
        started         — immediately after validation
        test_complete   — after each test finishes
        complete        — when all tests done (includes full report)
        error           — if a fatal error occurs before tests start
    """
    run_id = str(uuid.uuid4())
    custom_tests = custom_tests or []
    test_ids = _resolve_test_ids(tier, custom_tests)

    demo = persona_payload.get("demographic_anchor", {})
    persona_name = demo.get("name", persona_id or "unknown")
    tracking_id = persona_id or persona_name

    # ── Initialise report ──────────────────────────────────────────────────────
    report = make_empty_report(run_id, tracking_id, persona_name, tier)
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
            result = await test.run(persona_payload)
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
