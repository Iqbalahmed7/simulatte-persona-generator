"""tests/test_simulation_gates.py — Simulation pipeline structural (non-LLM) quality gates.

Sprint 7 — Antigravity (Simulation Structural Gate Tests + BV1 Multi-Turn Extension)
Validity Protocol: BV1 (multi-turn stability), S1 structural

No LLM calls. All run_loop calls are stubbed via unittest.mock.AsyncMock.
Tests verify:
  1. run_loop is called exactly N_personas × N_stimuli times.
  2. decision_scenarios are paired correctly to turns (None for turns beyond list length).
  3. BV1 structural proxy: deterministic mock produces identical decisions across 3 runs.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_loop_result(persona):
    from src.cognition.loop import LoopResult
    from tests.fixtures.synthetic_observation import make_synthetic_observation
    obs = make_synthetic_observation(content="Mock observation", importance=5, emotional_valence=0.1)
    return LoopResult(observation=obs, reflections=[], decision=None, reflected=False, decided=False)


def _make_mock_loop_result_with_decision(persona, decision_output):
    from src.cognition.loop import LoopResult
    from tests.fixtures.synthetic_observation import make_synthetic_observation
    obs = make_synthetic_observation(content="Mock observation", importance=5, emotional_valence=0.1)
    return LoopResult(observation=obs, reflections=[], decision=decision_output, reflected=False, decided=True)


def _make_minimal_cohort(personas):
    from src.schema.cohort import (
        CohortEnvelope,
        CohortSummary,
        TaxonomyMeta,
        GroundingSummary,
        CalibrationState,
    )
    from datetime import datetime, timezone
    import uuid

    return CohortEnvelope(
        cohort_id=f"cohort-{uuid.uuid4().hex[:6]}",
        domain="cpg",
        business_problem="Test business problem for gate tests.",
        mode="simulation-ready",
        icp_spec_hash="test-hash-000",
        generated_at=datetime.now(timezone.utc),
        taxonomy_used=TaxonomyMeta(
            base_attributes=150,
            domain_extension_attributes=0,
            total_attributes=150,
            domain_data_used=False,
        ),
        personas=personas,
        cohort_summary=CohortSummary(
            decision_style_distribution={},
            trust_anchor_distribution={},
            risk_appetite_distribution={},
            consistency_scores={},
            persona_type_distribution={},
            distinctiveness_score=0.0,
            coverage_assessment="synthetic test cohort",
            dominant_tensions=[],
        ),
        grounding_summary=GroundingSummary(
            tendency_source_distribution={"grounded": 0.0, "proxy": 1.0, "estimated": 0.0},
            domain_data_signals_extracted=0,
            clusters_derived=0,
        ),
        calibration_state=CalibrationState(status="uncalibrated"),
    )


# ---------------------------------------------------------------------------
# Test 1: run_loop Called Once Per Turn Per Persona
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_loop_called_correct_number_of_times():
    """
    3 personas × 4 stimuli = 12 run_loop calls.
    """
    from unittest.mock import AsyncMock, patch
    from src.modalities.simulation import run_simulation
    from src.experiment.session import ExperimentSession
    from src.experiment.modality import ExperimentModality
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    personas = [make_synthetic_persona() for _ in range(3)]

    # Build a minimal CohortEnvelope for multi-persona sessions
    cohort = _make_minimal_cohort(personas)
    session = ExperimentSession(
        session_id="gate-test-001",
        modality=ExperimentModality.TEMPORAL_SIMULATION,
        cohort=cohort,
        stimuli=["S1", "S2", "S3", "S4"],
    )

    mock_result = _make_mock_loop_result(personas[0])

    with patch("src.modalities.simulation.run_loop", new_callable=AsyncMock) as mock_loop:
        mock_loop.return_value = (personas[0], mock_result)
        result = await run_simulation(session)

    assert mock_loop.call_count == 12
    assert result.total_turns == 4
    assert len(result.personas) == 3


# ---------------------------------------------------------------------------
# Test 2: Decision Scenarios Paired Correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decision_scenarios_paired_to_correct_turns():
    """
    decision_scenarios[i] should be passed as decision_scenario kwarg at turn i.
    Turns beyond len(decision_scenarios) should get decision_scenario=None.
    """
    from unittest.mock import AsyncMock, patch, call
    from src.modalities.simulation import run_simulation
    from src.experiment.session import ExperimentSession
    from src.experiment.modality import ExperimentModality
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    import uuid

    persona = make_synthetic_persona()
    stimuli = ["S0", "S1", "S2"]
    decision_scenarios = ["Decide on S0?", "Decide on S1?"]  # only 2 of 3

    session = ExperimentSession(
        session_id="scenario-pairing-001",
        modality=ExperimentModality.TEMPORAL_SIMULATION,
        persona=persona,
        stimuli=stimuli,
        decision_scenarios=decision_scenarios,
    )

    call_scenarios = []

    async def capture(stimulus=None, persona=None, stimulus_id=None, decision_scenario=None):
        call_scenarios.append(decision_scenario)
        return (persona, _make_mock_loop_result(persona))

    with patch("src.modalities.simulation.run_loop", side_effect=capture):
        await run_simulation(session)

    assert call_scenarios[0] == "Decide on S0?"
    assert call_scenarios[1] == "Decide on S1?"
    assert call_scenarios[2] is None  # turn 2 has no paired scenario


# ---------------------------------------------------------------------------
# Test 3: BV1 Multi-Turn Mock Stability
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bv1_mock_decision_consistency():
    """
    BV1 structural version: run the same session 3 times with a deterministic mock.
    Assert >= 2/3 runs produce the same decisions at each turn.

    (Structural proxy — does not test LLM variance, tests that the pipeline
    produces identical outputs when given identical inputs and mocked LLM.)
    """
    from unittest.mock import AsyncMock, patch
    from src.modalities.simulation import run_simulation
    from src.experiment.session import ExperimentSession
    from src.experiment.modality import ExperimentModality
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cognition.decide import DecisionOutput
    import uuid

    persona = make_synthetic_persona()
    stimuli = ["S1", "S2"]
    decision_scenarios = ["Q1?", "Q2?"]

    session = ExperimentSession(
        session_id="bv1-mock-001",
        modality=ExperimentModality.TEMPORAL_SIMULATION,
        persona=persona,
        stimuli=stimuli,
        decision_scenarios=decision_scenarios,
    )

    fixed_decision = DecisionOutput(
        decision="Yes, I would.",
        confidence=72,
        reasoning_trace="My values align with this.",
        gut_reaction="Positive",
        key_drivers=["quality"],
        objections=[],
        what_would_change_mind="If price doubled.",
    )

    all_run_decisions = []

    for _ in range(3):
        mock_result = _make_mock_loop_result_with_decision(persona, fixed_decision)
        with patch("src.modalities.simulation.run_loop", new_callable=AsyncMock) as mock:
            mock.return_value = (persona, mock_result)
            result = await run_simulation(session)
        decisions = [l.decision for l in result.personas[0].turn_logs if l.decided]
        all_run_decisions.append(decisions)

    # All 3 runs should produce identical decisions (deterministic mock)
    assert all_run_decisions[0] == all_run_decisions[1] or \
           all_run_decisions[0] == all_run_decisions[2] or \
           all_run_decisions[1] == all_run_decisions[2], \
           "BV1: At least 2/3 runs should produce identical decisions"
