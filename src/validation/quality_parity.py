"""Quality parity checker for Sarvam-generated personas.

Runs the same G1–G5 gate suite that the generator applies to Claude-generated
personas, and produces a ParityResult indicating whether the Sarvam persona
meets the same structural and behavioural quality standards.

Gate mapping (from src/schema/validators.py PersonaValidator):
    G1 — g1_schema_validity          : structural field/format checks
    G2 — g2_hard_constraints         : impossible combinations (HC1–HC6)
    G3 — g3_tendency_attribute_consistency : behavioural invariants (TR1–TR8)
    G4 — g4_narrative_completeness   : word-count / completeness checks
    G5 — g5_narrative_attribute_alignment : keyword contradiction checks

Usage:
    from src.validation.quality_parity import check_parity, ParityResult
    result = check_parity(persona, provider="sarvam")
    if not result.is_at_par:
        print(f"Parity failed: {result.failures}")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass  # avoid circular imports at module level


@dataclass
class ParityResult:
    """Result of a quality parity check on a single persona."""

    persona_id: str
    provider: str  # "sarvam" | "anthropic" | "unknown"
    gates_checked: int
    gates_passed: int
    gates_failed: int
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """Fraction of gates passed (0.0–1.0)."""
        if self.gates_checked == 0:
            return 1.0
        return self.gates_passed / self.gates_checked

    @property
    def is_at_par(self) -> bool:
        """True if all gates pass (no failures)."""
        return self.gates_failed == 0

    def summary(self) -> str:
        status = "AT PAR" if self.is_at_par else "BELOW PAR"
        return (
            f"[{status}] {self.persona_id} ({self.provider}): "
            f"{self.gates_passed}/{self.gates_checked} gates passed "
            f"({self.pass_rate:.0%})"
        )


# ---------------------------------------------------------------------------
# Gate runner helpers
# ---------------------------------------------------------------------------

def _run_gate(label: str, fn, *args) -> list[str]:
    """
    Call fn(*args), which returns a ValidationResult.
    Collect ValidationResult.failures and prefix them with the gate label.
    Returns a (possibly empty) list of failure strings.
    Wraps any unexpected exception so a crash in one gate never aborts the run.
    """
    try:
        result = fn(*args)
        # ValidationResult.failures is a list[str]; prefix each with gate label
        # if not already prefixed (defensive: some messages already include "Gn:")
        gate_failures = []
        for msg in result.failures:
            if msg.startswith(label + ":"):
                gate_failures.append(msg)
            else:
                gate_failures.append(f"{label}: {msg}")
        return gate_failures
    except Exception as exc:  # noqa: BLE001
        return [f"{label}: unexpected error — {exc}"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_parity(persona: Any, provider: str = "unknown") -> ParityResult:
    """Run G1–G5 gate checks on a persona and return a ParityResult.

    Runs the same per-persona validation logic that the generator applies,
    giving a comparable quality score regardless of which LLM produced the
    persona.

    Args:
        persona: A PersonaRecord instance (or dict — will be coerced via
                 PersonaRecord.model_validate).
        provider: Label for which LLM generated this persona.
                  Conventional values: "sarvam", "anthropic", "unknown".

    Returns:
        ParityResult with gate pass/fail details.
    """
    from src.schema.validators import PersonaValidator
    from src.schema.persona import PersonaRecord

    # Accept dict or PersonaRecord
    if isinstance(persona, dict):
        persona = PersonaRecord.model_validate(persona)

    validator = PersonaValidator()
    all_failures: list[str] = []

    # G1: structural schema validity (field counts, persona_id format, trust weights)
    all_failures.extend(_run_gate("G1", validator.g1_schema_validity, persona))

    # G2: hard demographic/attribute constraints (HC1–HC6)
    all_failures.extend(_run_gate("G2", validator.g2_hard_constraints, persona))

    # G3: tendency-attribute consistency rules (TR1–TR8)
    all_failures.extend(
        _run_gate("G3", validator.g3_tendency_attribute_consistency, persona)
    )

    # G4: narrative completeness (word counts, non-empty fields)
    all_failures.extend(_run_gate("G4", validator.g4_narrative_completeness, persona))

    # G5: narrative-attribute alignment (keyword contradiction scan)
    all_failures.extend(
        _run_gate("G5", validator.g5_narrative_attribute_alignment, persona)
    )

    gates_checked = 5
    gates_failed = len(all_failures)
    # Gates are pass/fail per gate, not per failure message — but the brief asks
    # for gates_failed == number of failure messages (consistent with "any failure
    # in a gate counts as that gate failing").  To give the most actionable count
    # we count *distinct gates* that produced at least one failure.
    failed_gate_labels = {f.split(":")[0].strip() for f in all_failures}
    gates_failed = len(failed_gate_labels)
    gates_passed = gates_checked - gates_failed

    return ParityResult(
        persona_id=persona.persona_id,
        provider=provider,
        gates_checked=gates_checked,
        gates_passed=gates_passed,
        gates_failed=gates_failed,
        failures=all_failures,
        warnings=[],
    )


def compare_parity(
    sarvam_result: ParityResult,
    baseline_result: ParityResult,
) -> bool:
    """Return True if Sarvam result is at parity with the baseline.

    Parity means: the Sarvam persona passes at least as many gates as the
    baseline Claude persona (pass_rate >= baseline pass_rate).

    Args:
        sarvam_result: ParityResult for the Sarvam-generated persona.
        baseline_result: ParityResult for the reference (Claude) persona.

    Returns:
        True if sarvam_result.pass_rate >= baseline_result.pass_rate.
    """
    return sarvam_result.pass_rate >= baseline_result.pass_rate


def parity_report(results: list[ParityResult]) -> str:
    """Format a multi-persona parity report as a human-readable string.

    Args:
        results: List of ParityResult objects (one per persona).

    Returns:
        Multi-line report string.
    """
    if not results:
        return "No parity results to report."

    lines = ["=== Quality Parity Report ==="]
    at_par = sum(1 for r in results if r.is_at_par)
    lines.append(
        f"Personas checked: {len(results)}  |  At parity: {at_par}/{len(results)}"
    )
    lines.append("")
    for r in results:
        lines.append(r.summary())
        if r.failures:
            for f in r.failures:
                lines.append(f"  x {f}")
    return "\n".join(lines)
