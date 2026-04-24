from __future__ import annotations

from unittest.mock import MagicMock

from src.schema.validators import ValidationResult
from tests.fixtures.synthetic_persona import make_synthetic_persona


def test_assemble_cohort_emits_waiver_on_gate_failure(monkeypatch):
    from src.cohort import assembler as assembler_mod

    failing = ValidationResult(
        passed=False,
        gate="G6",
        failures=["city concentration too high"],
    )
    runner = MagicMock()
    runner.run_all.return_value = [failing]

    monkeypatch.setattr(assembler_mod, "CohortGateRunner", lambda: runner)
    monkeypatch.setattr(assembler_mod, "MAX_GATE_RETRIES", 3)

    envelope = assembler_mod.assemble_cohort(
        personas=[make_synthetic_persona()],
        domain="cpg",
        skip_gates=False,
    )

    assert envelope.gate_waivers
    assert envelope.gate_waivers[0]["gate_id"] == "G6"
    assert envelope.gate_waivers[0]["attempts_made"] == 3
    assert envelope.confidence_penalty == 0.1
    assert runner.run_all.call_count == 3


def test_assemble_cohort_bounded_retries_with_regenerator(monkeypatch):
    from src.cohort import assembler as assembler_mod

    failing = ValidationResult(
        passed=False,
        gate="G7",
        failures=["distinctiveness below threshold"],
    )
    runner = MagicMock()
    runner.run_all.side_effect = [
        [failing],
        [failing],
    ]

    regenerate_calls: list[int] = []

    def regenerate_failing(personas, failures, attempt):
        regenerate_calls.append(attempt)
        return personas

    monkeypatch.setattr(assembler_mod, "CohortGateRunner", lambda: runner)
    monkeypatch.setattr(assembler_mod, "MAX_GATE_RETRIES", 2)

    envelope = assembler_mod.assemble_cohort(
        personas=[make_synthetic_persona()],
        domain="cpg",
        regenerate_failing=regenerate_failing,
    )

    assert regenerate_calls == [1]
    assert envelope.gate_waivers[0]["gate_id"] == "G7"
    assert envelope.gate_waivers[0]["attempts_made"] == 2
    assert envelope.confidence_penalty == 0.1
