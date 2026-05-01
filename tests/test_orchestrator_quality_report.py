from __future__ import annotations

from src.orchestrator.invoke import _build_quality_report


def test_quality_report_does_not_auto_pass_persona_gates():
    envelope = {
        "cohort_summary": {
            "decision_style_distribution": {"analytical": 0.4, "emotional": 0.6},
            "distinctiveness_score": 0.4,
        },
        "calibration_state": {"status": "calibrated"},
        "personas": [{"attributes": {"values": {}}}],
        "grounding_summary": {"tendency_source_distribution": {"grounded": 0.0}},
    }
    report = _build_quality_report(envelope)
    assert "G1-AttributeCoherence" not in report.gates_passed
    assert "G2-NarrativeConsistency" not in report.gates_passed
    assert "G3-MemoryValidity" not in report.gates_passed


def test_quality_report_flags_missing_attributes_and_uses_non_g12_grounding_label():
    envelope = {
        "cohort_summary": {
            "decision_style_distribution": {"analytical": 0.4, "emotional": 0.4, "social": 0.2},
            "distinctiveness_score": 0.35,
        },
        "calibration_state": {"status": "calibrated"},
        "personas": [{"attributes": {}}, {"attributes": {"values": {}}}],
        "grounding_summary": {"tendency_source_distribution": {"grounded": 0.5}},
    }
    report = _build_quality_report(envelope)
    assert "Persona-AttributePresence" in report.gates_failed
    assert "Grounding-AnchoredTendencies" in report.gates_passed
    assert "G12-Grounding" not in report.gates_passed
