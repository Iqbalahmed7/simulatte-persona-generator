"""tests/test_calibration_card_audit.py — Calibration Card audit gate (Spec 02).

Verifies:
1. Audit gate: every PersonaGenerationResult ships with a non-None calibration_card.
2. Schema version locked to CALIBRATION_CARD_SCHEMA_VERSION.
3. Uncalibrated path emits the card with honest reason, not None.
4. Coverage map round-trip (segments serialise and deserialise correctly).
5. Calibrated path emits score and benchmark_sources.
6. Bad Iris inputs (invalid status, non-numeric score) gracefully degrade.

No LLM calls — build_calibration_card is deterministic from its inputs.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

import pytest

from src.schema.calibration_card import (
    CALIBRATION_CARD_SCHEMA_VERSION,
    BenchmarkSource,
    CalibrationCard,
    CoverageSegment,
)
from src.calibration.card_builder import build_calibration_card


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_envelope(domain: str = "cpg") -> dict:
    """Minimal cohort_envelope dict that the builder can work with."""
    return {
        "cohort_id": "test-cohort-001",
        "domain": domain,
        "anchor_overrides": {"age_group": "25-34", "location": "Mumbai"},
        "cohort_summary": {
            "decision_style_distribution": {"analytical": 0.6, "emotional": 0.4},
            "risk_appetite_distribution": {"low": 0.3, "medium": 0.5, "high": 0.2},
        },
        "personas": [],
    }


def _calibrated_iris_outputs() -> dict:
    return {
        "iris_run_id": "iris-run-abc123",
        "calibration_score": 0.07,
        "calibration_status": "calibrated",
        "benchmark_sources": [
            {
                "name": "US Census 2020 ACS",
                "type": "census",
                "citation": "US Census Bureau, ACS 5-Year Estimates 2020",
                "reference_url": "https://data.census.gov/",
            },
            {
                "name": "GWI Core Q4 2024",
                "type": "gwi",
                "citation": "GlobalWebIndex Core Survey, Q4 2024",
                "reference_url": None,
            },
        ],
        "known_limitations": [
            "Regulated claims excluded from calibration scope.",
        ],
    }


# ---------------------------------------------------------------------------
# 1. Audit gate — result always has a calibration_card
# ---------------------------------------------------------------------------

def test_result_carries_calibration_card():
    """PersonaGenerationResult must have a non-None calibration_card field.

    We test this at the build_calibration_card level (not the full
    invoke_persona_generator pipeline, which requires LLMs) — the audit
    contract is that build_calibration_card never returns None.
    """
    card = build_calibration_card(
        study_id="pg-test-001",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=None,
    )
    assert card is not None, "build_calibration_card must never return None"
    assert isinstance(card, CalibrationCard)


def test_result_to_dict_includes_calibration_card():
    """PersonaGenerationResult.to_dict() must include 'calibration_card' key."""
    from src.orchestrator.result import (
        CostActual, PersonaGenerationResult, QualityReport
    )

    card = build_calibration_card(
        study_id="pg-test-002",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=None,
    )

    result = PersonaGenerationResult(
        run_id="pg-test-002",
        cohort_id="cohort-001",
        client="TestCo",
        domain="cpg",
        tier_used="deep",
        count_requested=10,
        count_delivered=10,
        cost_actual=CostActual(),
        quality_report=QualityReport(),
        personas=[],
        cohort_envelope={},
        calibration_card=card,
    )

    d = result.to_dict()
    assert "calibration_card" in d, "to_dict() must include 'calibration_card'"
    assert d["calibration_card"] is not None


def test_result_calibration_card_none_is_detectable():
    """A result with calibration_card=None should be flagged — this is the bug case."""
    from src.orchestrator.result import (
        CostActual, PersonaGenerationResult, QualityReport
    )

    result = PersonaGenerationResult(
        run_id="pg-test-bug",
        cohort_id="cohort-bug",
        client="TestCo",
        domain="cpg",
        tier_used="deep",
        count_requested=10,
        count_delivered=10,
        cost_actual=CostActual(),
        quality_report=QualityReport(),
        personas=[],
        cohort_envelope={},
        calibration_card=None,  # intentionally missing to prove the audit catches it
    )

    # The audit contract: calibration_card is None IFF something went wrong.
    # This test documents that None is detectable (not silently ignored).
    assert result.calibration_card is None  # we can see it
    d = result.to_dict()
    assert d["calibration_card"] is None  # it surfaces in the output, not hidden


# ---------------------------------------------------------------------------
# 2. Schema version locked
# ---------------------------------------------------------------------------

def test_schema_version_locked():
    """CalibrationCard.schema_version must equal CALIBRATION_CARD_SCHEMA_VERSION."""
    card = build_calibration_card(
        study_id="pg-test-ver",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=None,
    )
    assert card.schema_version == CALIBRATION_CARD_SCHEMA_VERSION
    assert card.schema_version == "2026-05-01"


def test_schema_version_matches_receipt_version():
    """CalibrationCard and ResponseReceipt must share the same schema version."""
    from src.schema.receipt import RECEIPT_SCHEMA_VERSION
    assert CALIBRATION_CARD_SCHEMA_VERSION == RECEIPT_SCHEMA_VERSION, (
        "Calibration Card and ResponseReceipt schema versions must stay in sync "
        f"(card={CALIBRATION_CARD_SCHEMA_VERSION!r}, receipt={RECEIPT_SCHEMA_VERSION!r})"
    )


# ---------------------------------------------------------------------------
# 3. Uncalibrated path
# ---------------------------------------------------------------------------

def test_uncalibrated_path_emits_card_not_none():
    """When iris_outputs=None the card must still be emitted, not None."""
    card = build_calibration_card(
        study_id="pg-unca-001",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=None,
    )
    assert card is not None
    assert card.calibration_status == "uncalibrated"


def test_uncalibrated_score_is_none():
    """Uncalibrated card must have calibration_score=None (never fake a number)."""
    card = build_calibration_card(
        study_id="pg-unca-002",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=None,
    )
    assert card.calibration_score is None, (
        "calibration_score must be None when uncalibrated — never fabricate a number"
    )


def test_uncalibrated_has_honest_reason():
    """Uncalibrated card must carry a non-empty honest_disclaimer."""
    card = build_calibration_card(
        study_id="pg-unca-003",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=None,
    )
    assert card.honest_disclaimer, "honest_disclaimer must not be empty"
    assert len(card.honest_disclaimer) > 20


def test_uncalibrated_known_limitations_not_empty():
    """Uncalibrated card must have at least one known_limitations entry."""
    card = build_calibration_card(
        study_id="pg-unca-004",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=None,
    )
    assert len(card.known_limitations) >= 1, (
        "known_limitations must explain why calibration_score is None"
    )


def test_uncalibrated_iris_run_id_is_none():
    """Uncalibrated card must have iris_run_id=None."""
    card = build_calibration_card(
        study_id="pg-unca-005",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=None,
    )
    assert card.iris_run_id is None


# ---------------------------------------------------------------------------
# 4. Coverage map round-trip
# ---------------------------------------------------------------------------

def test_coverage_map_populated():
    """Coverage map must contain at least one segment for a non-empty envelope."""
    card = build_calibration_card(
        study_id="pg-cov-001",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=None,
    )
    assert len(card.coverage_map) >= 1, "coverage_map must have at least one segment"


def test_coverage_map_segment_fields():
    """Each CoverageSegment must have segment_name and calibration_status."""
    card = build_calibration_card(
        study_id="pg-cov-002",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=None,
    )
    for seg in card.coverage_map:
        assert seg.segment_name, "segment_name must not be empty"
        assert seg.calibration_status in ("calibrated", "extrapolated", "novel"), (
            f"Unknown calibration_status: {seg.calibration_status!r}"
        )


def test_coverage_map_round_trips_via_asdict():
    """Coverage map must survive a dataclass asdict round-trip."""
    card = build_calibration_card(
        study_id="pg-cov-003",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=None,
    )
    d = asdict(card)
    cmap = d["coverage_map"]
    assert isinstance(cmap, list)
    for item in cmap:
        assert "segment_name" in item
        assert "calibration_status" in item
        assert "confidence_delta" in item


def test_coverage_map_from_iris_outputs():
    """When Iris supplies a coverage_map, builder must use it verbatim."""
    iris = _calibrated_iris_outputs()
    iris["coverage_map"] = [
        {"segment_name": "age_group", "calibration_status": "calibrated", "confidence_delta": 0.03},
        {"segment_name": "novel_segment", "calibration_status": "novel", "confidence_delta": None},
    ]
    card = build_calibration_card(
        study_id="pg-cov-004",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=iris,
    )
    names = [s.segment_name for s in card.coverage_map]
    assert "age_group" in names
    assert "novel_segment" in names
    novel = next(s for s in card.coverage_map if s.segment_name == "novel_segment")
    assert novel.calibration_status == "novel"
    assert novel.confidence_delta is None


# ---------------------------------------------------------------------------
# 5. Calibrated path
# ---------------------------------------------------------------------------

def test_calibrated_path_score_populated():
    """Calibrated card must have a non-None calibration_score."""
    card = build_calibration_card(
        study_id="pg-cal-001",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=_calibrated_iris_outputs(),
    )
    assert card.calibration_status == "calibrated"
    assert card.calibration_score is not None
    assert card.calibration_score == pytest.approx(0.07)


def test_calibrated_path_benchmark_sources():
    """Calibrated card must carry the benchmark sources from Iris."""
    card = build_calibration_card(
        study_id="pg-cal-002",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=_calibrated_iris_outputs(),
    )
    assert len(card.benchmark_sources) == 2
    names = {s.name for s in card.benchmark_sources}
    assert "US Census 2020 ACS" in names
    assert "GWI Core Q4 2024" in names


def test_calibrated_path_iris_run_id():
    """Calibrated card must carry the iris_run_id from Iris outputs."""
    card = build_calibration_card(
        study_id="pg-cal-003",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=_calibrated_iris_outputs(),
    )
    assert card.iris_run_id == "iris-run-abc123"


def test_calibrated_metric_is_mae():
    """calibration_metric must always be 'mean_absolute_error'."""
    card = build_calibration_card(
        study_id="pg-cal-004",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=_calibrated_iris_outputs(),
    )
    assert card.calibration_metric == "mean_absolute_error"


# ---------------------------------------------------------------------------
# 6. Bad Iris inputs — graceful degradation
# ---------------------------------------------------------------------------

def test_bad_calibration_score_degrades_to_uncalibrated():
    """Non-numeric calibration_score from Iris must degrade to uncalibrated."""
    iris = _calibrated_iris_outputs()
    iris["calibration_score"] = "not-a-number"
    card = build_calibration_card(
        study_id="pg-bad-001",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=iris,
    )
    assert card.calibration_status == "uncalibrated"
    assert card.calibration_score is None


def test_unknown_calibration_status_degrades():
    """Unknown calibration_status from Iris must degrade to uncalibrated."""
    iris = _calibrated_iris_outputs()
    iris["calibration_status"] = "wizard_status"
    card = build_calibration_card(
        study_id="pg-bad-002",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=iris,
    )
    assert card.calibration_status == "uncalibrated"
    assert card.calibration_score is None


def test_unknown_benchmark_type_is_skipped():
    """Benchmark source with unknown type must be skipped, not crash."""
    iris = _calibrated_iris_outputs()
    iris["benchmark_sources"].append({
        "name": "Mystery Source",
        "type": "unknown_panel",
        "citation": "???",
        "reference_url": None,
    })
    card = build_calibration_card(
        study_id="pg-bad-003",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=iris,
    )
    # Original 2 sources present; mystery source skipped
    assert len(card.benchmark_sources) == 2
    names = {s.name for s in card.benchmark_sources}
    assert "Mystery Source" not in names


def test_novel_segments_appear_in_known_limitations():
    """Segments with calibration_status='novel' must be called out in known_limitations."""
    iris = _calibrated_iris_outputs()
    iris["coverage_map"] = [
        {"segment_name": "new_category_x", "calibration_status": "novel", "confidence_delta": None},
    ]
    card = build_calibration_card(
        study_id="pg-bad-004",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=iris,
    )
    limitations_text = " ".join(card.known_limitations)
    assert "new_category_x" in limitations_text, (
        "Novel segments must be surfaced in known_limitations"
    )


# ---------------------------------------------------------------------------
# 7. Foundation version threading
# ---------------------------------------------------------------------------

def test_foundation_version_threaded_from_envelope():
    """foundation_version in cohort_envelope must be passed through to the card."""
    envelope = _minimal_envelope()
    envelope["foundation_version"] = "popscale-v3.2.1"
    card = build_calibration_card(
        study_id="pg-fv-001",
        cohort_envelope=envelope,
        iris_outputs=None,
    )
    assert card.foundation_version == "popscale-v3.2.1"


def test_foundation_version_none_when_absent():
    """foundation_version must be None when not in the envelope."""
    card = build_calibration_card(
        study_id="pg-fv-002",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=None,
    )
    assert card.foundation_version is None


# ---------------------------------------------------------------------------
# 8. generated_at is always a timezone-aware datetime
# ---------------------------------------------------------------------------

def test_generated_at_is_utc_aware():
    """generated_at must be a UTC-aware datetime, not naive."""
    card = build_calibration_card(
        study_id="pg-ts-001",
        cohort_envelope=_minimal_envelope(),
        iris_outputs=None,
    )
    assert isinstance(card.generated_at, datetime)
    assert card.generated_at.tzinfo is not None, (
        "generated_at must be timezone-aware (UTC)"
    )
