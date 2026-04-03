"""tests/test_calibration_engine.py — Sprint 22 calibration engine tests.

Antigravity — Sprint 22
Tests CalibrationEngine.run_benchmark_calibration() and run_feedback_calibration().
No LLM calls. Uses real Pydantic schema objects.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.calibration.engine import CalibrationEngine
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

def _make_cohort(n_personas: int = 2, status: str = "uncalibrated") -> CohortEnvelope:
    """Return a minimal valid CohortEnvelope with n_personas personas."""
    personas = [make_synthetic_persona() for _ in range(n_personas)]

    # Give them distinct IDs to avoid collisions in feedback tests
    for i, p in enumerate(personas):
        object.__setattr__(p, "persona_id", f"pg-test-{i:03d}")

    return CohortEnvelope(
        cohort_id="cohort-test-001",
        generated_at=datetime.now(tz=timezone.utc),
        domain="cpg",
        business_problem="Test calibration",
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
        calibration_state=CalibrationState(
            status=status,
            method_applied=None,
            last_calibrated=None,
        ),
    )


_BENCHMARKS = {
    "conversion_rate": 0.30,
    "wtp_median": 500.0,
}


# ---------------------------------------------------------------------------
# run_benchmark_calibration
# ---------------------------------------------------------------------------

class TestRunBenchmarkCalibration:

    def test_valid_cohort_returns_benchmark_calibrated_status(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        result = engine.run_benchmark_calibration(cohort, _BENCHMARKS)
        assert result.calibration_state.status == "benchmark_calibrated"

    def test_valid_cohort_method_applied_is_benchmark_anchoring(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        result = engine.run_benchmark_calibration(cohort, _BENCHMARKS)
        assert result.calibration_state.method_applied == "benchmark_anchoring"

    def test_empty_cohort_returns_calibration_failed(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        # Force an empty personas list via model_copy
        empty_cohort = cohort.model_copy(update={"personas": []})
        result = engine.run_benchmark_calibration(empty_cohort, _BENCHMARKS)
        assert result.calibration_state.status == "calibration_failed"

    def test_empty_cohort_method_applied_still_set(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        empty_cohort = cohort.model_copy(update={"personas": []})
        result = engine.run_benchmark_calibration(empty_cohort, _BENCHMARKS)
        assert result.calibration_state.method_applied == "benchmark_anchoring"

    def test_does_not_mutate_original_cohort(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        original_status = cohort.calibration_state.status
        _ = engine.run_benchmark_calibration(cohort, _BENCHMARKS)
        # Original should be unchanged
        assert cohort.calibration_state.status == original_status

    def test_result_is_new_envelope_object(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        result = engine.run_benchmark_calibration(cohort, _BENCHMARKS)
        assert result is not cohort

    def test_last_calibrated_is_set(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        result = engine.run_benchmark_calibration(cohort, _BENCHMARKS)
        assert result.calibration_state.last_calibrated is not None

    def test_notes_contain_simulated_conversion(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        result = engine.run_benchmark_calibration(cohort, _BENCHMARKS)
        assert "Simulated conversion proxy" in result.calibration_state.notes

    def test_personas_list_unchanged_after_benchmark_calibration(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        result = engine.run_benchmark_calibration(cohort, _BENCHMARKS)
        assert len(result.personas) == len(cohort.personas)


# ---------------------------------------------------------------------------
# run_feedback_calibration
# ---------------------------------------------------------------------------

class TestRunFeedbackCalibration:

    def test_matched_persona_id_updates_tendency_description(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        pid = cohort.personas[0].persona_id
        outcomes = [
            {"persona_id": pid, "actual_outcome": "purchased", "channel": "word_of_mouth"},
        ]
        result = engine.run_feedback_calibration(cohort, outcomes)
        # Description should be updated (feedback note appended)
        original_desc = cohort.personas[0].behavioural_tendencies.trust_orientation.description
        new_desc = result.personas[0].behavioural_tendencies.trust_orientation.description
        assert new_desc != original_desc
        assert "[Feedback:" in new_desc

    def test_unmatched_persona_id_leaves_personas_unchanged(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        outcomes = [
            {"persona_id": "non-existent-id", "actual_outcome": "purchased", "channel": "organic"},
        ]
        result = engine.run_feedback_calibration(cohort, outcomes)
        # Personas should be equal (same content)
        for orig, updated in zip(cohort.personas, result.personas):
            assert orig.behavioural_tendencies == updated.behavioural_tendencies

    def test_status_is_client_calibrated_after_feedback(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        pid = cohort.personas[0].persona_id
        outcomes = [
            {"persona_id": pid, "actual_outcome": "purchased", "channel": "organic"},
        ]
        result = engine.run_feedback_calibration(cohort, outcomes)
        assert result.calibration_state.status == "client_calibrated"

    def test_status_client_calibrated_even_with_unmatched_id(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        outcomes = [
            {"persona_id": "nobody", "actual_outcome": "rejected", "channel": "price_promotion"},
        ]
        result = engine.run_feedback_calibration(cohort, outcomes)
        assert result.calibration_state.status == "client_calibrated"

    def test_does_not_mutate_original_cohort(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        pid = cohort.personas[0].persona_id
        original_desc = cohort.personas[0].behavioural_tendencies.trust_orientation.description
        outcomes = [
            {"persona_id": pid, "actual_outcome": "purchased", "channel": "word_of_mouth"},
        ]
        _ = engine.run_feedback_calibration(cohort, outcomes)
        # Original cohort persona descriptions must be unchanged
        assert cohort.personas[0].behavioural_tendencies.trust_orientation.description == original_desc

    def test_result_is_new_envelope_object(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        outcomes = []
        result = engine.run_feedback_calibration(cohort, outcomes)
        assert result is not cohort

    def test_method_applied_is_client_feedback_loop(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        outcomes = []
        result = engine.run_feedback_calibration(cohort, outcomes)
        assert result.calibration_state.method_applied == "client_feedback_loop"

    def test_notes_record_outcome_count(self):
        engine = CalibrationEngine()
        cohort = _make_cohort(n_personas=2)
        pid = cohort.personas[0].persona_id
        outcomes = [
            {"persona_id": pid, "actual_outcome": "purchased", "channel": "organic"},
        ]
        result = engine.run_feedback_calibration(cohort, outcomes)
        assert "1 outcome records processed" in result.calibration_state.notes
