"""tests/test_population_validator.py — Sprint 22 population validator tests.

Antigravity — Sprint 22
Tests validate_calibration() and check_c3() from population_validator.py.
No LLM calls. Uses real Pydantic schema objects.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.calibration.population_validator import (
    C3Result,
    CalibrationGateReport,
    check_c3 as pv_check_c3,
    validate_calibration,
)
from src.schema.cohort import (
    CalibrationState,
    CohortEnvelope,
    CohortSummary,
    GroundingSummary,
    TaxonomyMeta,
)
from tests.fixtures.synthetic_persona import make_synthetic_persona


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_cohort(
    status: str | None = "benchmark_calibrated",
    method_applied: str | None = "benchmark_anchoring",
    last_calibrated: datetime | None = None,
    has_calibration_state: bool = True,
) -> CohortEnvelope:
    """Return a minimal valid CohortEnvelope with configurable calibration_state."""
    personas = [make_synthetic_persona()]

    if last_calibrated is None:
        last_calibrated = datetime.now(tz=timezone.utc)

    if has_calibration_state:
        cal_state = CalibrationState(
            status=status,
            method_applied=method_applied,
            last_calibrated=last_calibrated,
        )
    else:
        # CalibrationState is required by CohortEnvelope — set to uncalibrated with None method
        cal_state = CalibrationState(
            status="uncalibrated",
            method_applied=None,
            last_calibrated=None,
        )

    cohort = CohortEnvelope(
        cohort_id="cohort-pv-test",
        generated_at=datetime.now(tz=timezone.utc),
        domain="cpg",
        business_problem="Validator test",
        mode="simulation-ready",
        icp_spec_hash="abc123",
        taxonomy_used=TaxonomyMeta(
            base_attributes=10,
            domain_extension_attributes=5,
            total_attributes=15,
            domain_data_used=False,
            business_problem="Test",
            icp_spec_hash="abc123",
        ),
        personas=personas,
        cohort_summary=CohortSummary(
            decision_style_distribution={"social": 1.0},
            trust_anchor_distribution={"peer": 1.0},
            risk_appetite_distribution={"low": 1.0},
            consistency_scores={"mean": 74.0, "min": 60, "max": 88},
            persona_type_distribution={"standard": 1.0},
            distinctiveness_score=0.8,
            coverage_assessment="good",
            dominant_tensions=["price-vs-quality"],
        ),
        grounding_summary=GroundingSummary(
            tendency_source_distribution={"grounded": 0.0, "proxy": 1.0, "estimated": 0.0},
            domain_data_signals_extracted=0,
            clusters_derived=1,
        ),
        calibration_state=cal_state,
    )

    return cohort


# ---------------------------------------------------------------------------
# C1 gate — status not null
# ---------------------------------------------------------------------------

class TestC1Gate:

    def test_benchmark_calibrated_status_c1_passes(self):
        cohort = _make_cohort(status="benchmark_calibrated")
        report = validate_calibration(cohort)
        assert report.c1_passed is True

    def test_client_calibrated_status_c1_passes(self):
        cohort = _make_cohort(status="client_calibrated", method_applied="client_feedback_loop")
        report = validate_calibration(cohort)
        assert report.c1_passed is True

    def test_none_status_c1_fails(self):
        """Simulate a cohort whose calibration_state.status is effectively None/missing."""
        cohort = _make_cohort(status="benchmark_calibrated")
        # Patch calibration_state to have None status via a simple mock
        from unittest.mock import MagicMock
        bad_state = MagicMock()
        bad_state.status = None
        bad_state.method_applied = None
        bad_state.last_calibrated = None
        object.__setattr__(cohort, "calibration_state", bad_state)
        report = validate_calibration(cohort)
        assert report.c1_passed is False

    def test_none_calibration_state_c1_fails(self):
        """cohort.calibration_state is None → C1 fails."""
        cohort = _make_cohort(status="benchmark_calibrated")
        object.__setattr__(cohort, "calibration_state", None)
        report = validate_calibration(cohort)
        assert report.c1_passed is False


# ---------------------------------------------------------------------------
# C2 gate — method_applied not None
# ---------------------------------------------------------------------------

class TestC2Gate:

    def test_method_applied_set_c2_passes(self):
        cohort = _make_cohort(
            status="benchmark_calibrated",
            method_applied="benchmark_anchoring",
        )
        report = validate_calibration(cohort)
        assert report.c2_passed is True

    def test_method_applied_none_c2_fails(self):
        cohort = _make_cohort(
            status="benchmark_calibrated",
            method_applied=None,
        )
        report = validate_calibration(cohort)
        assert report.c2_passed is False

    def test_c2_fail_noted_in_notes(self):
        cohort = _make_cohort(
            status="benchmark_calibrated",
            method_applied=None,
        )
        report = validate_calibration(cohort)
        combined_notes = " ".join(report.notes).lower()
        assert "c2" in combined_notes


# ---------------------------------------------------------------------------
# C3 gate — conversion plausibility
# ---------------------------------------------------------------------------

class TestC3Gate:

    def test_c3_passes_when_ratio_within_range(self):
        cohort = _make_cohort()
        # 0.30 / 0.30 = 1.0 → within 0.5–2.0
        report = validate_calibration(
            cohort,
            simulated_conversion=0.30,
            benchmark_conversion=0.30,
        )
        assert report.c3_passed is True

    def test_c3_fails_when_ratio_outside_range(self):
        cohort = _make_cohort()
        # 0.10 / 0.30 = 0.33 → outside 0.5–2.0
        report = validate_calibration(
            cohort,
            simulated_conversion=0.10,
            benchmark_conversion=0.30,
        )
        assert report.c3_passed is False

    def test_c3_auto_passes_when_no_conversion_args_provided(self):
        cohort = _make_cohort()
        report = validate_calibration(cohort)
        assert report.c3_passed is True

    def test_c3_auto_passes_noted_in_notes(self):
        cohort = _make_cohort()
        report = validate_calibration(cohort)
        combined_notes = " ".join(report.notes).lower()
        assert "c3" in combined_notes

    def test_c3_auto_passes_when_benchmark_conversion_zero(self):
        cohort = _make_cohort()
        report = validate_calibration(
            cohort,
            simulated_conversion=0.30,
            benchmark_conversion=0.0,
        )
        assert report.c3_passed is True

    def test_c3_boundary_at_2x(self):
        cohort = _make_cohort()
        report = validate_calibration(
            cohort,
            simulated_conversion=0.60,
            benchmark_conversion=0.30,
        )
        assert report.c3_passed is True

    def test_c3_just_above_2x_fails(self):
        cohort = _make_cohort()
        report = validate_calibration(
            cohort,
            simulated_conversion=0.63,
            benchmark_conversion=0.30,
        )
        assert report.c3_passed is False

    def test_c3_boundary_at_0_5x(self):
        cohort = _make_cohort()
        report = validate_calibration(
            cohort,
            simulated_conversion=0.15,
            benchmark_conversion=0.30,
        )
        assert report.c3_passed is True

    def test_c3_just_below_0_5x_fails(self):
        cohort = _make_cohort()
        # 0.14 / 0.30 = 0.467 → below 0.5
        report = validate_calibration(
            cohort,
            simulated_conversion=0.14,
            benchmark_conversion=0.30,
        )
        assert report.c3_passed is False


# ---------------------------------------------------------------------------
# C4 gate — client feedback trigger
# ---------------------------------------------------------------------------

class TestC4Gate:

    def test_client_calibrated_c4_passes(self):
        cohort = _make_cohort(
            status="client_calibrated",
            method_applied="client_feedback_loop",
        )
        report = validate_calibration(cohort)
        assert report.c4_passed is True

    def test_benchmark_calibrated_c4_passes_with_note(self):
        cohort = _make_cohort(
            status="benchmark_calibrated",
            method_applied="benchmark_anchoring",
        )
        report = validate_calibration(cohort)
        assert report.c4_passed is True
        # A note about client feedback not yet applied should appear
        combined_notes = " ".join(report.notes).lower()
        assert "client" in combined_notes or "c4" in combined_notes


# ---------------------------------------------------------------------------
# C5 gate — staleness warning
# ---------------------------------------------------------------------------

class TestC5Gate:

    def test_recent_calibration_no_c5_warning(self):
        cohort = _make_cohort(
            last_calibrated=datetime.now(tz=timezone.utc) - timedelta(days=10)
        )
        report = validate_calibration(cohort)
        assert report.c5_warning is False

    def test_stale_calibration_triggers_c5_warning(self):
        cohort = _make_cohort(
            last_calibrated=datetime.now(tz=timezone.utc) - timedelta(days=200)
        )
        report = validate_calibration(cohort)
        assert report.c5_warning is True

    def test_c5_warning_at_boundary_184_days(self):
        """184 days > 183 day threshold → warning."""
        cohort = _make_cohort(
            last_calibrated=datetime.now(tz=timezone.utc) - timedelta(days=184)
        )
        report = validate_calibration(cohort)
        assert report.c5_warning is True

    def test_c5_no_warning_at_180_days(self):
        """180 days < 183 day threshold → no warning."""
        cohort = _make_cohort(
            last_calibrated=datetime.now(tz=timezone.utc) - timedelta(days=180)
        )
        report = validate_calibration(cohort)
        assert report.c5_warning is False

    def test_c5_does_not_affect_all_passed(self):
        """C5 is warning-only; all_passed stays True even when c5_warning is True."""
        cohort = _make_cohort(
            status="benchmark_calibrated",
            method_applied="benchmark_anchoring",
            last_calibrated=datetime.now(tz=timezone.utc) - timedelta(days=200),
        )
        report = validate_calibration(cohort)
        assert report.c5_warning is True
        assert report.all_passed is True


# ---------------------------------------------------------------------------
# CalibrationGateReport.all_passed
# ---------------------------------------------------------------------------

class TestAllPassed:

    def test_all_passed_true_when_all_gates_pass(self):
        cohort = _make_cohort(
            status="benchmark_calibrated",
            method_applied="benchmark_anchoring",
            last_calibrated=datetime.now(tz=timezone.utc),
        )
        report = validate_calibration(cohort)
        assert report.all_passed is True

    def test_all_passed_false_when_c1_fails(self):
        cohort = _make_cohort(status="benchmark_calibrated")
        object.__setattr__(cohort, "calibration_state", None)
        report = validate_calibration(cohort)
        assert report.all_passed is False

    def test_all_passed_false_when_c2_fails(self):
        cohort = _make_cohort(
            status="benchmark_calibrated",
            method_applied=None,
        )
        report = validate_calibration(cohort)
        assert report.all_passed is False

    def test_all_passed_false_when_c3_fails(self):
        cohort = _make_cohort(
            status="benchmark_calibrated",
            method_applied="benchmark_anchoring",
        )
        # Force C3 to fail
        report = validate_calibration(
            cohort,
            simulated_conversion=0.05,
            benchmark_conversion=0.40,
        )
        assert report.all_passed is False


# ---------------------------------------------------------------------------
# check_c3 from population_validator (returns C3Result)
# ---------------------------------------------------------------------------

class TestPopulationValidatorCheckC3:

    def test_ratio_within_range_passes(self):
        result = pv_check_c3(0.30, 0.30)
        assert isinstance(result, C3Result)
        assert result.passed is True

    def test_ratio_at_2x_passes(self):
        result = pv_check_c3(0.60, 0.30)
        assert result.passed is True

    def test_ratio_above_2x_fails(self):
        result = pv_check_c3(0.63, 0.30)
        assert result.passed is False

    def test_ratio_at_0_5x_passes(self):
        result = pv_check_c3(0.15, 0.30)
        assert result.passed is True

    def test_ratio_below_0_5x_fails(self):
        result = pv_check_c3(0.10, 0.30)
        assert result.passed is False

    def test_message_field_present(self):
        result = pv_check_c3(0.30, 0.30)
        assert hasattr(result, "message")
        assert isinstance(result.message, str)
        assert len(result.message) > 0

    def test_passed_message_contains_pass(self):
        result = pv_check_c3(0.30, 0.30)
        assert "PASS" in result.message

    def test_failed_message_contains_warn_or_fail(self):
        result = pv_check_c3(0.10, 0.30)
        assert "WARN" in result.message or "FAIL" in result.message

    def test_benchmark_conversion_zero_auto_passes(self):
        """benchmark_conversion <= 0 → auto-pass guard clause."""
        result = pv_check_c3(0.30, 0.0)
        assert result.passed is True

    def test_benchmark_conversion_zero_message_contains_skip(self):
        result = pv_check_c3(0.30, 0.0)
        assert "SKIP" in result.message

    def test_ratio_field_computed_correctly(self):
        result = pv_check_c3(0.60, 0.30)
        assert result.ratio == pytest.approx(2.0)

    def test_simulated_and_benchmark_fields_stored(self):
        result = pv_check_c3(0.45, 0.30)
        assert result.simulated == pytest.approx(0.45)
        assert result.benchmark == pytest.approx(0.30)
