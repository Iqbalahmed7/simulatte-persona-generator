"""services/benchmark/report.py — Assemble and format a BenchmarkReport."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from models import BenchmarkReport, BenchmarkTier, RunStatus, TestResult, TestStatus


def make_empty_report(
    run_id: str,
    persona_id: str,
    persona_name: str,
    tier: BenchmarkTier,
) -> BenchmarkReport:
    """Return a fresh QUEUED report."""
    return BenchmarkReport(
        run_id=run_id,
        persona_id=persona_id,
        persona_name=persona_name,
        tier=tier,
        status=RunStatus.QUEUED,
        credibility_score=0.0,
        started_at=datetime.now(timezone.utc),
    )


def mark_running(report: BenchmarkReport) -> BenchmarkReport:
    report.status = RunStatus.RUNNING
    report.started_at = datetime.now(timezone.utc)
    return report


def mark_complete(report: BenchmarkReport) -> BenchmarkReport:
    report.status = RunStatus.COMPLETE
    report.completed_at = datetime.now(timezone.utc)
    return report


def mark_error(report: BenchmarkReport, message: str) -> BenchmarkReport:
    report.status = RunStatus.ERROR
    report.error = message
    report.completed_at = datetime.now(timezone.utc)
    return report


def summary_dict(report: BenchmarkReport) -> Dict[str, Any]:
    """Return a compact summary suitable for list endpoints."""
    return {
        "run_id": report.run_id,
        "persona_id": report.persona_id,
        "persona_name": report.persona_name,
        "tier": report.tier.value,
        "status": report.status.value,
        "credibility_score": report.credibility_score,
        "grade": report.grade,
        "grade_label": report.grade_label,
        "total_cost_usd": report.total_cost_usd,
        "total_duration_s": report.total_duration_s,
        "started_at": report.started_at.isoformat() if report.started_at else None,
        "completed_at": report.completed_at.isoformat() if report.completed_at else None,
    }
