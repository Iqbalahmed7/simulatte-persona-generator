"""PR1 parity test: _build_quality_report must match canonical validator output exactly.

Five fixture envelopes cover:
  1. All cohort gates pass.
  2. G7 (distinctiveness) fails.
  3. G6 (diversity) and G11 (tendency source) fail.
  4. Empty gate_results → no cohort gate labels inferred (no inferred passes).
  5. Persona with empty attributes is quarantined; G6/G7 pass from gate_results.
  6. Quick mode emits explicit not_run for deferred/not-applicable gates.
"""
from __future__ import annotations

from src.orchestrator.invoke import _build_quality_report

# ── Canonical label constants (must match _GATE_LABELS in _build_quality_report) ─────

G6  = "G6-Diversity"
G7  = "G7-Distinctiveness"
G8  = "G8-TypeCoverage"
G9  = "G9-TensionCompleteness"
G11 = "G11-TendencySource"


def _envelope(gate_results: list[dict], *, personas=None, grounded: float = 0.0) -> dict:
    """Build a minimal CohortEnvelope dict suitable for _build_quality_report."""
    return {
        "gate_results": gate_results,
        "cohort_summary": {"distinctiveness_score": 0.4},
        "calibration_state": {"status": "calibrated"},
        "personas": personas if personas is not None else [{"attributes": {"values": {}}}],
        "grounding_summary": {"tendency_source_distribution": {"grounded": grounded}},
    }


def _gr(gate: str, passed: bool, failures: list[str] | None = None) -> dict:
    """Shorthand for a ValidationResult.to_dict() entry."""
    return {"gate": gate, "passed": passed, "failures": failures or [], "warnings": []}


def _status_map(report) -> dict[str, dict]:
    return {s["gate_id"]: s for s in report.gate_statuses}


# ── Fixture 1: all cohort gates pass ─────────────────────────────────────────────────

def test_parity_fixture1_all_gates_pass():
    """All five cohort gates pass → all five labels in gates_passed, gates_failed empty."""
    gate_results = [
        _gr("G6",  True),
        _gr("G7",  True),
        _gr("G8",  True),
        _gr("G9",  True),
        _gr("G11", True),
    ]
    report = _build_quality_report(_envelope(gate_results))

    for label in (G6, G7, G8, G9, G11):
        assert label in report.gates_passed, f"{label} must be in gates_passed"
    assert not report.gates_failed, f"gates_failed must be empty; got {report.gates_failed}"
    sm = _status_map(report)
    assert sm["G6"]["status"] == "passed"
    assert sm["G7"]["status"] == "passed"
    assert sm["G8"]["status"] == "passed"
    assert sm["G9"]["status"] == "passed"
    assert sm["G11"]["status"] == "passed"


# ── Fixture 2: G7 fails ───────────────────────────────────────────────────────────────

def test_parity_fixture2_g7_fails():
    """G7 failure recorded in gate_results → G7-Distinctiveness in gates_failed, not in gates_passed."""
    gate_results = [
        _gr("G6",  True),
        _gr("G7",  False, ["mean pairwise distance 0.08 < threshold 0.20"]),
        _gr("G8",  True),
        _gr("G9",  True),
        _gr("G11", True),
    ]
    report = _build_quality_report(_envelope(gate_results))

    assert G7 in report.gates_failed,   f"{G7} must be in gates_failed"
    assert G7 not in report.gates_passed, f"{G7} must NOT be in gates_passed"
    assert G6 in report.gates_passed,   f"{G6} must still be in gates_passed"
    sm = _status_map(report)
    assert sm["G7"]["status"] == "failed"


# ── Fixture 3: G6 and G11 fail ───────────────────────────────────────────────────────

def test_parity_fixture3_g6_and_g11_fail():
    """G6 + G11 failures → both labels in gates_failed; G7 pass label in gates_passed."""
    gate_results = [
        _gr("G6",  False, ["city Mumbai >20%"]),
        _gr("G7",  True),
        _gr("G8",  True),
        _gr("G9",  True),
        _gr("G11", False, ["price_sensitivity.source is None"]),
    ]
    report = _build_quality_report(_envelope(gate_results))

    assert G6  in report.gates_failed,   f"{G6} must be in gates_failed"
    assert G11 in report.gates_failed,   f"{G11} must be in gates_failed"
    assert G7  in report.gates_passed,   f"{G7} must be in gates_passed"
    assert G6  not in report.gates_passed
    assert G11 not in report.gates_passed
    sm = _status_map(report)
    assert sm["G6"]["status"] == "failed"
    assert sm["G11"]["status"] == "failed"


# ── Fixture 4: empty gate_results → no inferred passes ───────────────────────────────

def test_parity_fixture4_empty_gate_results_no_inferred_passes():
    """
    When gate_results is empty (gates skipped / CohortGateRunner unavailable),
    _build_quality_report must NOT infer any cohort-gate pass or fail.
    Old heuristic would have inferred G6/G7/G11 from cohort_summary — that is
    forbidden by the 'no inferred passes' constraint.
    """
    envelope = {
        "gate_results": [],  # empty — no canonical evidence
        "cohort_summary": {
            # These values would have triggered heuristic passes in the old code
            "decision_style_distribution": {"analytical": 0.3, "social": 0.7},
            "distinctiveness_score": 0.5,
        },
        "calibration_state": {"status": "calibrated"},
        "personas": [{"attributes": {"values": {}}}],
        "grounding_summary": {"tendency_source_distribution": {"grounded": 0.0}},
    }
    report = _build_quality_report(envelope)

    # No cohort gate label must appear in either list
    for label in (G6, G7, G8, G9, G11):
        assert label not in report.gates_passed, (
            f"{label} must NOT be inferred when gate_results is empty"
        )
        assert label not in report.gates_failed, (
            f"{label} must NOT be inferred when gate_results is empty"
        )
    sm = _status_map(report)
    for gid in ("G6", "G7", "G8", "G9", "G11"):
        assert sm[gid]["status"] == "not_run"


# ── Fixture 5: persona attribute quarantine + mixed gate results ──────────────────────

def test_parity_fixture5_attribute_quarantine_with_gate_results():
    """
    Persona with empty attributes is quarantined; Persona-AttributePresence in gates_failed.
    Gate results still flow through correctly (G6/G7 pass).
    """
    gate_results = [
        _gr("G6", True),
        _gr("G7", True),
    ]
    personas = [
        {"attributes": {}},           # empty → quarantined
        {"attributes": {"values": {}}},  # non-empty → not quarantined
    ]
    report = _build_quality_report(_envelope(gate_results, personas=personas))

    assert "Persona-AttributePresence" in report.gates_failed, (
        "Persona-AttributePresence must be in gates_failed when any persona has empty attributes"
    )
    assert report.personas_quarantined == 1
    assert G6 in report.gates_passed
    assert G7 in report.gates_passed
    sm = _status_map(report)
    assert sm["G6"]["status"] == "passed"
    assert sm["G7"]["status"] == "passed"


def test_parity_fixture6_quick_mode_explicit_not_run_statuses():
    """
    Quick mode must emit explicit not_run statuses for deferred/not-applicable gates.
    Expected:
      passed: G6,G7,G8,G9,G11
      not_run: G1,G2,G3,G10,G12
      failed: none
    """
    gate_results = [
        _gr("G6", True),
        _gr("G7", True),
        _gr("G8", True),
        _gr("G9", True),
        _gr("G11", True),
    ]
    report = _build_quality_report(_envelope(gate_results))
    sm = _status_map(report)

    for gid in ("G6", "G7", "G8", "G9", "G11"):
        assert sm[gid]["status"] == "passed"

    for gid in ("G1", "G2", "G3"):
        assert sm[gid]["status"] == "not_run"
        assert sm[gid]["reason"] == "deferred_to_generation_stage"
        assert "personas_validated_count" in sm[gid]

    assert sm["G10"]["status"] == "not_run"
    assert sm["G10"]["reason"] == "not_applicable_mode_quick"

    assert sm["G12"]["status"] == "not_run"
    assert sm["G12"]["reason"] == "deferred_to_simulation_stage"

    assert not report.gates_failed
