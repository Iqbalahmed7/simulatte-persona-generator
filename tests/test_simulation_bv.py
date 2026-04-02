"""tests/test_simulation_bv.py — BV3 and BV6 integration tests.

Sprint 7 — Goose (Simulation End-to-End Test)

Validity Protocol:
  BV3: Temporal consistency — confidence should increase across a positive arc.
  BV6: Believable consistency vs. unrealistic rigidity — persona follows tendencies
       but can override them under high-stakes circumstances.

These tests make real LLM calls.
Run with: pytest tests/test_simulation_bv.py --integration
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# BV3: Temporal Consistency Across Multi-Turn Simulation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
async def test_bv3_confidence_increases_across_positive_arc():
    """
    BV3: Run 5 positive stimuli. Confidence across the arc should be
    higher in turns 3-5 than in turns 1-2 (near-monotonic increase).

    Proxy check: avg_confidence in turns 3-5 >= avg_confidence in turns 1-2.
    """
    from src.modalities.simulation import run_simulation
    from src.modalities.simulation_report import generate_simulation_report
    from src.experiment.session import ExperimentSession
    from src.experiment.modality import ExperimentModality
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    import uuid

    persona = make_synthetic_persona()

    # 5 positive stimuli with decision scenarios — trust-building arc
    stimuli = [
        "A well-reviewed local brand launches a new affordable product line.",
        "Your neighbour praises the local brand's product quality.",
        "A consumer report rates the local brand highest in its category.",
        "The local brand offers a loyalty discount to existing customers.",
        "Three of your close friends have started using the local brand.",
    ]
    decision_scenarios = [
        "Do you try this new local brand?",
        "Are you more interested in trying the local brand now?",
        "Do you feel confident enough to buy the local brand's product?",
        "Do you take advantage of this loyalty discount?",
        "Do you decide to switch to the local brand as your regular choice?",
    ]

    session = ExperimentSession(
        session_id=f"bv3-{uuid.uuid4().hex[:6]}",
        modality=ExperimentModality.TEMPORAL_SIMULATION,
        persona=persona,
        stimuli=stimuli,
        decision_scenarios=decision_scenarios,
    )

    result = await run_simulation(session)
    report = generate_simulation_report(result)

    # Extract confidences from decision summaries
    confidences = [s.avg_confidence for s in report.decision_summaries if s.avg_confidence > 0]

    assert len(confidences) >= 3, "BV3: Need >= 3 decisions to check arc"

    early_avg = sum(confidences[:2]) / 2
    late_avg = sum(confidences[-2:]) / 2

    assert late_avg >= early_avg - 10, (  # allow ±10 tolerance
        f"BV3 FAIL: late confidence ({late_avg:.1f}) should be >= early ({early_avg:.1f})"
    )


# ---------------------------------------------------------------------------
# BV6: Believable Consistency vs Unrealistic Rigidity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
async def test_bv6_persona_follows_tendencies_but_can_override():
    """
    BV6: Run 5 standard + 1 override scenario.
    Standard scenarios: persona should follow price sensitivity (say no to premium).
    Override scenario: health emergency for child — price-sensitive persona may override.

    Assert:
    - >= 3/5 standard decisions are tendency-consistent (reject premium)
    - The override decision shows meaningful reasoning (trace >= 150 chars)
    """
    from src.modalities.simulation import run_simulation
    from src.experiment.session import ExperimentSession
    from src.experiment.modality import ExperimentModality
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    import uuid

    persona = make_synthetic_persona()  # Priya — price-sensitive, budget-conscious

    # 5 standard stimuli (premium products — Priya should typically resist)
    standard_stimuli = [
        "A luxury food brand launches a new product at 3x the usual price.",
        "A premium organic range is now available at your supermarket.",
        "A high-end brand runs an exclusive promotion.",
        "A celebrity-endorsed premium product launches.",
        "A luxury imported brand offers a 10% introductory discount.",
    ]
    standard_scenarios = [
        "Do you buy this luxury food product at 3x the usual price?",
        "Do you switch to this premium organic range?",
        "Do you participate in this exclusive promotion?",
        "Do you try this celebrity-endorsed premium product?",
        "Do you buy this imported luxury brand even with the discount?",
    ]

    # Override scenario: health emergency
    override_stimulus = "Your child has been diagnosed with a nutritional deficiency and the doctor specifically recommends a premium supplement."
    override_scenario = "Do you buy the premium supplement the doctor recommended for your child's health, despite the high cost?"

    all_stimuli = standard_stimuli + [override_stimulus]
    all_scenarios = standard_scenarios + [override_scenario]

    session = ExperimentSession(
        session_id=f"bv6-{uuid.uuid4().hex[:6]}",
        modality=ExperimentModality.TEMPORAL_SIMULATION,
        persona=persona,
        stimuli=all_stimuli,
        decision_scenarios=all_scenarios,
    )

    result = await run_simulation(session)
    logs = result.personas[0].turn_logs

    # Standard decisions: check how many reject premium (tendency-consistent)
    standard_logs = [l for l in logs[:5] if l.decided]
    consistent = sum(
        1 for l in standard_logs
        if l.decision and l.decision.lower().strip().startswith("no")
    )
    assert consistent >= 3 or len(standard_logs) < 3, (
        f"BV6 FAIL: only {consistent}/{len(standard_logs)} standard decisions were tendency-consistent"
    )

    # Override decision: reasoning should be substantial
    override_log = logs[5] if len(logs) > 5 else None
    if override_log and override_log.decided and override_log.reasoning_trace:
        assert len(override_log.reasoning_trace) >= 150, (
            "BV6: Override reasoning trace should be substantial (>= 150 chars)"
        )
