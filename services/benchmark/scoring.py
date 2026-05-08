"""services/benchmark/scoring.py — Weighted composite credibility score.

Credibility score = sum(test.score/10 * test.weight * 100) for all tests run.
Weights are normalised to the subset of tests that actually ran, so a Quick
(3-test) run is scored fairly against its own weight set.
"""
from __future__ import annotations

from typing import List

from models import BenchmarkReport, BenchmarkTier, TEST_WEIGHTS, TestResult, TestStatus


def compute_credibility(tests: List[TestResult]) -> float:
    """Return a 0–100 credibility score from a list of completed test results."""
    run_weights: dict[str, float] = {}
    for t in tests:
        if t.status in (TestStatus.PASSED, TestStatus.FAILED):
            run_weights[t.test_id] = TEST_WEIGHTS.get(t.test_id, 0.0)

    total_weight = sum(run_weights.values())
    if total_weight == 0:
        return 0.0

    score = 0.0
    for t in tests:
        if t.test_id in run_weights:
            normalised_weight = run_weights[t.test_id] / total_weight
            contribution = (t.score / 10.0) * normalised_weight * 100.0
            score += contribution

    return round(score, 1)


def annotate_contributions(tests: List[TestResult]) -> List[TestResult]:
    """Fill in the weighted_contribution field on each test."""
    run_weights: dict[str, float] = {}
    for t in tests:
        if t.status in (TestStatus.PASSED, TestStatus.FAILED):
            run_weights[t.test_id] = TEST_WEIGHTS.get(t.test_id, 0.0)

    total_weight = sum(run_weights.values()) or 1.0

    for t in tests:
        if t.test_id in run_weights:
            normalised_weight = run_weights[t.test_id] / total_weight
            t.weighted_contribution = round((t.score / 10.0) * normalised_weight * 100.0, 2)

    return tests


def finalize_report(report: BenchmarkReport) -> BenchmarkReport:
    """Compute credibility score, grade, and grade_label on the report."""
    report.tests = annotate_contributions(report.tests)
    report.credibility_score = compute_credibility(report.tests)
    report.grade = BenchmarkReport.grade_from_score(report.credibility_score)
    report.grade_label = BenchmarkReport.grade_label_from(report.tier, report.grade)
    report.total_cost_usd = round(sum(t.cost_usd for t in report.tests), 5)
    report.total_duration_s = round(sum(t.duration_s for t in report.tests), 2)
    return report
