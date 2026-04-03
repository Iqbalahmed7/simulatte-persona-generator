"""src/social/validity.py — Social simulation validity gates SV1–SV5.

Architecture §9 gates for any run with SocialSimulationLevel != ISOLATED.

No LLM calls.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional

from src.schema.persona import PersonaRecord
from src.social.schema import SocialInfluenceEvent, SocialSimulationLevel, TendencyShiftRecord


@dataclass
class ValidityGateResult:
    gate_id: str        # "SV1" through "SV5"
    passed: bool
    detail: str
    value: float | None = None   # the measured value (echo_chamber_score, etc.)


def check_sv1(events: list[SocialInfluenceEvent]) -> ValidityGateResult:
    """SV1: Every SocialInfluenceEvent has a resulting_observation_id set.

    Threshold: 100% of events must have resulting_observation_id != None.
    If events is empty: passed=True (vacuously true).
    """
    if not events:
        return ValidityGateResult(gate_id="SV1", passed=True, detail="No events to check.", value=1.0)
    linked = sum(1 for e in events if e.resulting_observation_id is not None)
    rate = linked / len(events)
    passed = rate == 1.0
    return ValidityGateResult(gate_id="SV1", passed=passed,
        detail=f"{linked}/{len(events)} events have resulting_observation_id.", value=rate)


def check_sv2(decisions: list[str], level: SocialSimulationLevel) -> ValidityGateResult:
    """SV2: Decision diversity under social influence.

    At HIGH/SATURATED level: no single decision string > 80% of all decisions.
    At ISOLATED/LOW/MODERATE: threshold is 90% (softer, matching existing S2 gate).
    If decisions is empty: passed=True.

    Normalises decision strings: strip + lowercase before counting.
    """
    if not decisions:
        return ValidityGateResult(gate_id="SV2", passed=True, detail="No decisions to check.", value=0.0)
    normalised = [d.strip().lower() for d in decisions]
    counts = Counter(normalised)
    most_common, top_count = counts.most_common(1)[0]
    concentration = top_count / len(normalised)
    threshold = 0.80 if level.value in {"high", "saturated"} else 0.90
    passed = concentration <= threshold
    return ValidityGateResult(gate_id="SV2", passed=passed,
        detail=f"Most common decision '{most_common}': {concentration:.1%} (threshold {threshold:.0%}).",
        value=concentration)


def check_sv3(events: list[SocialInfluenceEvent]) -> ValidityGateResult:
    """SV3: Echo chamber detection.

    echo_chamber_score = max events from a single transmitter / total events

    > 0.80 → FAIL
    > 0.60 → WARN (passed=True, but detail flags warning)
    ≤ 0.60 → PASS

    If events is empty: passed=True, value=0.0.
    """
    if not events:
        return ValidityGateResult(gate_id="SV3", passed=True, detail="No events.", value=0.0)
    tx_counts = Counter(e.transmitter_id for e in events)
    max_count = max(tx_counts.values())
    score = max_count / len(events)
    if score > 0.80:
        return ValidityGateResult(gate_id="SV3", passed=False,
            detail=f"Echo chamber score {score:.2f} > 0.80. Reduce level or use DIRECTED_GRAPH.", value=score)
    elif score > 0.60:
        return ValidityGateResult(gate_id="SV3", passed=True,
            detail=f"Echo chamber WARNING: score {score:.2f} > 0.60. Monitor.", value=score)
    return ValidityGateResult(gate_id="SV3", passed=True,
        detail=f"Echo chamber score {score:.2f} within safe range.", value=score)


def check_sv4(shift_records: list[TendencyShiftRecord]) -> ValidityGateResult:
    """SV4: Tendency shift direction consistency.

    v1 implementation: always flags for manual review.
    passed=True (requires human review, not automated fail).
    detail describes what was found.
    """
    if not shift_records:
        return ValidityGateResult(
            gate_id="SV4",
            passed=True,
            detail="No tendency shifts recorded. No review required.",
            value=0.0,
        )
    return ValidityGateResult(
        gate_id="SV4",
        passed=True,
        detail=f"{len(shift_records)} tendency shift(s) recorded. Manual review required to verify direction consistency.",
        value=float(len(shift_records)),
    )


def check_sv5(
    personas_before: list[PersonaRecord],
    personas_after: list[PersonaRecord],
) -> ValidityGateResult:
    """SV5: derived_insights unchanged after simulation.

    Checks that derived_insights fields (decision_style, trust_anchor, risk_appetite,
    primary_value_orientation, consistency_score, consistency_band) are identical
    for all personas.

    Compares by persona_id. If a persona_id from before is not found in after, skip.
    passed=True if all matched personas have identical derived_insights key fields.
    """
    after_map = {p.persona_id: p for p in personas_after}
    mismatches = []
    for p_before in personas_before:
        p_after = after_map.get(p_before.persona_id)
        if p_after is None:
            continue
        di_b = p_before.derived_insights
        di_a = p_after.derived_insights
        for field in ("decision_style", "trust_anchor", "risk_appetite", "primary_value_orientation", "consistency_score", "consistency_band"):
            if getattr(di_b, field) != getattr(di_a, field):
                mismatches.append(f"{p_before.persona_id}.{field}")
    passed = len(mismatches) == 0
    detail = "All derived_insights unchanged." if passed else f"Mismatches: {', '.join(mismatches)}"
    return ValidityGateResult(gate_id="SV5", passed=passed, detail=detail, value=float(len(mismatches)))
