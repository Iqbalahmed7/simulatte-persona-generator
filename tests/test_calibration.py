"""Tests for src/cohort/calibrator.py — Persona response consistency calibration."""
from __future__ import annotations

import pytest

from src.cohort.calibrator import compute_calibration_state
from src.schema.cohort import CalibrationState


def _make_envelope():
    """Return a minimal CohortEnvelope stub (not needed by compute_calibration_state
    for logic, but the signature requires it)."""
    # Use a simple object since the function only uses it for context
    from unittest.mock import MagicMock
    return MagicMock()


def test_calibration_all_decided():
    """All personas decided → benchmark_calibrated."""
    results = [
        {"persona_id": "p1", "rounds": [{"decided": True}]},
        {"persona_id": "p2", "rounds": [{"decided": True}]},
        {"persona_id": "p3", "rounds": [{"decided": True}]},
    ]
    state = compute_calibration_state(_make_envelope(), results)
    assert state.status == "benchmark_calibrated"
    assert state.method_applied == "decision_consistency"
    assert state.benchmark_source == "internal_simulation"


def test_calibration_none_decided():
    """No personas decided → calibration_failed."""
    results = [
        {"persona_id": "p1", "rounds": [{"decided": False}]},
        {"persona_id": "p2", "rounds": [{"decided": False}]},
        {"persona_id": "p3", "rounds": [{"decided": False}]},
    ]
    state = compute_calibration_state(_make_envelope(), results)
    assert state.status == "calibration_failed"


def test_calibration_empty_results():
    """Empty results → uncalibrated."""
    state = compute_calibration_state(_make_envelope(), [])
    assert state.status == "uncalibrated"
    assert state.method_applied is None
    assert state.notes is None


def test_calibration_partial():
    """50% decided → benchmark_calibrated (>= 0.5 threshold)."""
    results = [
        {"persona_id": "p1", "rounds": [{"decided": True}]},
        {"persona_id": "p2", "rounds": [{"decided": False}]},
    ]
    state = compute_calibration_state(_make_envelope(), results)
    # 1/2 = 0.5, which meets the >= 0.5 threshold
    assert state.status == "benchmark_calibrated"


def test_calibration_notes_format():
    """notes field contains consistency_score and N."""
    results = [
        {"persona_id": "p1", "rounds": [{"decided": True}]},
        {"persona_id": "p2", "rounds": [{"decided": True}]},
        {"persona_id": "p3", "rounds": [{"decided": False}]},
        {"persona_id": "p4", "rounds": [{"decided": False}]},
        {"persona_id": "p5", "rounds": [{"decided": True}]},
    ]
    state = compute_calibration_state(_make_envelope(), results)
    assert state.notes is not None
    assert "consistency_score=" in state.notes
    assert "N=5" in state.notes
    # Extract and validate the score value
    score_str = state.notes.split("consistency_score=")[1].split(";")[0]
    score = float(score_str)
    assert 0.0 <= score <= 1.0
    # 3/5 = 0.60
    assert abs(score - 0.60) < 1e-6
