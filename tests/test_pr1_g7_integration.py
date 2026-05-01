"""PR1 integration test: G7-failing cohort auto-regenerates and passes without waiver.

Scenario
--------
A 2-persona cohort starts with G7 (distinctiveness) failing.
The assemble_cohort retry loop calls `regenerate_failing`, which returns new
personas.  On the second gate check the mock runner returns all-pass.
The resulting envelope must have:
  - no gate_waivers
  - confidence_penalty == 0.0
  - gate_results reflecting the final all-pass state
"""
from __future__ import annotations

from unittest.mock import MagicMock

from src.schema.validators import ValidationResult
from tests.fixtures.synthetic_persona import make_synthetic_persona


def _make_distinct_persona(suffix: str):
    """Return a valid persona with a unique persona_id."""
    p = make_synthetic_persona()
    return p.model_copy(update={"persona_id": f"pg-priya-{suffix}"})


def test_g7_failing_cohort_regenerates_and_passes_without_waiver(monkeypatch):
    """
    Verifies the full regeneration path:
    1. First gate run → G7 fails.
    2. regenerate_failing is called exactly once.
    3. Second gate run → all pass.
    4. No waiver is emitted; confidence_penalty stays 0.0.
    5. gate_results in envelope reflect the final all-pass state.
    """
    from src.cohort import assembler as assembler_mod

    call_count = [0]

    def _mock_run_all(personas):
        call_count[0] += 1
        if call_count[0] == 1:
            # First attempt: G7 fails; everything else passes
            return [
                ValidationResult(passed=True,  gate="G6"),
                ValidationResult(passed=False, gate="G7",
                                 failures=["mean pairwise distance 0.05 < threshold 0.20"]),
                ValidationResult(passed=True,  gate="G8"),
                ValidationResult(passed=True,  gate="G9"),
                ValidationResult(passed=True,  gate="G11"),
            ]
        # After regeneration: all pass
        return [
            ValidationResult(passed=True, gate="G6"),
            ValidationResult(passed=True, gate="G7"),
            ValidationResult(passed=True, gate="G8"),
            ValidationResult(passed=True, gate="G9"),
            ValidationResult(passed=True, gate="G11"),
        ]

    runner = MagicMock()
    runner.run_all.side_effect = _mock_run_all
    monkeypatch.setattr(assembler_mod, "CohortGateRunner", lambda: runner)

    p1 = _make_distinct_persona("001")
    p2 = _make_distinct_persona("002")

    regenerated_flag = [False]

    def regenerate_failing(personas, failing_results, attempt):
        regenerated_flag[0] = True
        assert any(r.gate == "G7" for r in failing_results), (
            "G7 must be among the failing results passed to regenerate_failing"
        )
        assert attempt == 1, f"Expected attempt=1, got {attempt}"
        # Return personas unchanged; mock runner decides pass/fail independently
        return list(personas)

    envelope = assembler_mod.assemble_cohort(
        personas=[p1, p2],
        domain="cpg",
        regenerate_failing=regenerate_failing,
        max_attempts=2,
    )

    assert regenerated_flag[0], "regenerate_failing was never called"
    assert runner.run_all.call_count == 2, (
        f"Expected exactly 2 gate checks, got {runner.run_all.call_count}"
    )
    assert not envelope.gate_waivers, (
        f"No waivers should be issued when regeneration succeeds; got {envelope.gate_waivers}"
    )
    assert envelope.confidence_penalty == 0.0, (
        f"confidence_penalty must be 0.0 when no waivers issued; got {envelope.confidence_penalty}"
    )

    # gate_results must reflect the final (passing) run
    assert envelope.gate_results, "gate_results must not be empty after gate checks"
    g7_result = next((r for r in envelope.gate_results if r["gate"] == "G7"), None)
    assert g7_result is not None, "G7 gate result must be present"
    assert g7_result["passed"] is True, (
        f"G7 must be passing in final gate_results; got {g7_result}"
    )
