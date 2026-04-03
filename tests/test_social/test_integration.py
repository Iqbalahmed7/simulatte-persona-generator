"""tests/test_social/test_integration.py — Sprint SB end-to-end integration tests.

Tests for run_social_loop() in src/social/loop_orchestrator.py.

run_loop is mocked to avoid LLM calls. The mock returns a plausible
(updated_persona, LoopResult) so the orchestrator can run end-to-end.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.cognition.decide import DecisionOutput
from src.cognition.loop import LoopResult
from src.schema.persona import (
    Attribute,
    BehaviouralTendencies,
    CopingMechanism,
    CoreMemory,
    DemographicAnchor,
    DerivedInsights,
    Household,
    ImmutableConstraints,
    LifeDefiningEvent,
    LifeStory,
    Location,
    Memory,
    Narrative,
    Objection,
    Observation,
    PersonaRecord,
    PriceSensitivityBand,
    RelationshipMap,
    SimulationState,
    TendencyBand,
    TrustOrientation,
    TrustWeights,
    WorkingMemory,
)
from src.social.loop_orchestrator import run_social_loop
from src.social.network_builder import build_full_mesh
from src.social.schema import (
    NetworkTopology,
    SocialNetwork,
    SocialNetworkEdge,
    SocialSimulationLevel,
    SocialSimulationTrace,
)


# ---------------------------------------------------------------------------
# Helpers — persona factory
# ---------------------------------------------------------------------------

def make_persona(
    persona_id: str,
    name: str = "Test Persona",
    decision_style: str = "analytical",
) -> PersonaRecord:
    return PersonaRecord(
        persona_id=persona_id,
        generated_at=datetime.now(timezone.utc),
        generator_version="test-1.0",
        domain="cpg",
        mode="quick",
        demographic_anchor=DemographicAnchor(
            name=name,
            age=30,
            gender="female",
            location=Location(country="India", region="MH", city="Mumbai", urban_tier="metro"),
            household=Household(
                structure="nuclear", size=3, income_bracket="middle", dual_income=True
            ),
            life_stage="adult",
            education="undergraduate",
            employment="full-time",
        ),
        life_stories=[
            LifeStory(title="A", when="2020", event="Event A", lasting_impact="Impact A"),
            LifeStory(title="B", when="2018", event="Event B", lasting_impact="Impact B"),
        ],
        attributes={
            "base": {
                "openness": Attribute(value=0.7, type="continuous", label="Openness", source="sampled")
            }
        },
        derived_insights=DerivedInsights(
            decision_style=decision_style,
            decision_style_score=0.7,
            trust_anchor="authority",
            risk_appetite="medium",
            primary_value_orientation="quality",
            coping_mechanism=CopingMechanism(
                type="research_deep_dive", description="Researches deeply"
            ),
            consistency_score=75,
            consistency_band="high",
            key_tensions=["price vs quality"],
        ),
        behavioural_tendencies=BehaviouralTendencies(
            price_sensitivity=PriceSensitivityBand(
                band="medium", description="moderate price sensitivity", source="grounded"
            ),
            trust_orientation=TrustOrientation(
                weights=TrustWeights(
                    expert=0.5, peer=0.2, brand=0.1, ad=0.05, community=0.1, influencer=0.05
                ),
                dominant="expert",
                description="trusts experts",
                source="grounded",
            ),
            switching_propensity=TendencyBand(
                band="low", description="brand loyal", source="grounded"
            ),
            objection_profile=[
                Objection(
                    objection_type="price_vs_value", likelihood="medium", severity="friction"
                )
            ],
            reasoning_prompt="Think analytically.",
        ),
        narrative=Narrative(
            first_person="I am...", third_person="She is...", display_name=name
        ),
        decision_bullets=["Quality first"],
        memory=Memory(
            core=CoreMemory(
                identity_statement="A careful thinker",
                key_values=["quality", "trust", "value"],
                life_defining_events=[
                    LifeDefiningEvent(age_when=25, event="Career", lasting_impact="Ambition")
                ],
                relationship_map=RelationshipMap(
                    primary_decision_partner="spouse",
                    key_influencers=["doctor"],
                    trust_network=["family"],
                ),
                immutable_constraints=ImmutableConstraints(
                    budget_ceiling=None,
                    non_negotiables=["quality"],
                    absolute_avoidances=["fake"],
                ),
                tendency_summary="Careful",
            ),
            working=WorkingMemory(
                observations=[],
                reflections=[],
                plans=[],
                brand_memories={},
                simulation_state=SimulationState(
                    current_turn=0,
                    importance_accumulator=0.0,
                    reflection_count=0,
                    awareness_set={},
                    consideration_set=[],
                    last_decision=None,
                ),
            ),
        ),
    )


def make_mock_observation(obs_id: str | None = None) -> Observation:
    return Observation(
        id=obs_id or f"obs-{uuid4().hex[:8]}",
        timestamp=datetime.now(timezone.utc),
        type="observation",
        content="I processed the social stimulus.",
        importance=5,
        emotional_valence=0.0,
        last_accessed=datetime.now(timezone.utc),
    )


def make_mock_decision(decision_text: str = "I choose Brand X") -> DecisionOutput:
    return DecisionOutput(
        decision=decision_text,
        confidence=75,
        reasoning_trace="Step 1: gut. Step 2: check values.",
        gut_reaction="Brand X feels right.",
        key_drivers=["quality", "trust"],
        objections=["price"],
        what_would_change_mind="Better deal elsewhere",
    )


def make_mock_loop_result(
    persona: PersonaRecord,
    decision_text: str = "I choose Brand X",
    obs_id: str | None = None,
) -> tuple[PersonaRecord, LoopResult]:
    observation = make_mock_observation(obs_id)
    loop_result = LoopResult(
        observation=observation,
        decision=make_mock_decision(decision_text),
        reflected=False,
        decided=True,
    )
    return persona, loop_result


# ---------------------------------------------------------------------------
# run_loop mock — returns (persona_unchanged, LoopResult) every call
# ---------------------------------------------------------------------------

def make_run_loop_mock(personas: list[PersonaRecord]) -> AsyncMock:
    """
    Returns an AsyncMock for run_loop. Each call returns (persona, LoopResult)
    where the persona is looked up by the 'persona' kwarg/arg, and a fresh
    LoopResult is constructed with a unique observation id.
    """
    async def _mock_run_loop(stimulus, persona, **kwargs):
        obs_id = f"obs-{uuid4().hex[:8]}"
        loop_result = LoopResult(
            observation=make_mock_observation(obs_id),
            decision=make_mock_decision("I choose Brand X"),
            reflected=False,
            decided=True,
        )
        return persona, loop_result

    mock = AsyncMock(side_effect=_mock_run_loop)
    return mock


# ---------------------------------------------------------------------------
# 2-persona fixture
# ---------------------------------------------------------------------------

def two_personas() -> list[PersonaRecord]:
    return [
        make_persona("pg-int-001", name="Priya"),
        make_persona("pg-int-002", name="Ravi"),
    ]


def full_mesh_two() -> SocialNetwork:
    return build_full_mesh(["pg-int-001", "pg-int-002"])


# ---------------------------------------------------------------------------
# Integration tests — ISOLATED level
# ---------------------------------------------------------------------------

def test_isolated_level_zero_social_events():
    """ISOLATED level: no social events generated; total_influence_events=0."""
    personas = two_personas()
    network = full_mesh_two()
    mock_run_loop = make_run_loop_mock(personas)

    with patch("src.social.loop_orchestrator.run_loop", mock_run_loop):
        final_personas, trace = asyncio.run(
            run_social_loop(
                personas=personas,
                stimuli=["Which brand do you prefer?", "Would you switch brands?"],
                network=network,
                level=SocialSimulationLevel.ISOLATED,
                session_id="session-iso-001",
                cohort_id="cohort-iso-001",
            )
        )

    assert trace.total_influence_events == 0


def test_isolated_level_no_influence_vectors():
    """ISOLATED level: no events means no personas in influence_vectors."""
    personas = two_personas()
    network = full_mesh_two()
    mock_run_loop = make_run_loop_mock(personas)

    with patch("src.social.loop_orchestrator.run_loop", mock_run_loop):
        _, trace = asyncio.run(
            run_social_loop(
                personas=personas,
                stimuli=["Stimulus 1", "Stimulus 2"],
                network=network,
                level=SocialSimulationLevel.ISOLATED,
                session_id="session-iso-002",
                cohort_id="cohort-iso-002",
            )
        )

    assert trace.influence_vectors == {}


def test_single_turn_no_social_events():
    """With only 1 turn (turn 0), social events are never generated."""
    personas = two_personas()
    network = full_mesh_two()
    mock_run_loop = make_run_loop_mock(personas)

    with patch("src.social.loop_orchestrator.run_loop", mock_run_loop):
        _, trace = asyncio.run(
            run_social_loop(
                personas=personas,
                stimuli=["Single turn stimulus"],
                network=network,
                level=SocialSimulationLevel.MODERATE,
                session_id="session-single-001",
                cohort_id="cohort-single-001",
            )
        )

    assert trace.total_influence_events == 0


# ---------------------------------------------------------------------------
# Integration tests — MODERATE + FULL_MESH + 2 personas + 2 turns
# ---------------------------------------------------------------------------

def test_moderate_full_mesh_2personas_2turns_generates_social_events():
    """Social events generated on turn 2; trace has >0 total_influence_events."""
    personas = two_personas()
    network = full_mesh_two()
    mock_run_loop = make_run_loop_mock(personas)

    with patch("src.social.loop_orchestrator.run_loop", mock_run_loop):
        _, trace = asyncio.run(
            run_social_loop(
                personas=personas,
                stimuli=["Turn 0 stimulus", "Turn 1 stimulus"],
                network=network,
                level=SocialSimulationLevel.MODERATE,
                session_id="session-mod-001",
                cohort_id="cohort-mod-001",
            )
        )

    assert trace.total_influence_events > 0


def test_returns_correct_number_of_final_personas():
    personas = two_personas()
    network = full_mesh_two()
    mock_run_loop = make_run_loop_mock(personas)

    with patch("src.social.loop_orchestrator.run_loop", mock_run_loop):
        final_personas, _ = asyncio.run(
            run_social_loop(
                personas=personas,
                stimuli=["T0", "T1"],
                network=network,
                level=SocialSimulationLevel.MODERATE,
                session_id="session-mod-002",
                cohort_id="cohort-mod-002",
            )
        )

    assert len(final_personas) == 2


def test_trace_session_id_matches_input():
    personas = two_personas()
    network = full_mesh_two()
    mock_run_loop = make_run_loop_mock(personas)
    expected_session_id = "session-match-001"

    with patch("src.social.loop_orchestrator.run_loop", mock_run_loop):
        _, trace = asyncio.run(
            run_social_loop(
                personas=personas,
                stimuli=["T0", "T1"],
                network=network,
                level=SocialSimulationLevel.MODERATE,
                session_id=expected_session_id,
                cohort_id="cohort-match-001",
            )
        )

    assert trace.session_id == expected_session_id


def test_trace_cohort_id_matches_input():
    personas = two_personas()
    network = full_mesh_two()
    mock_run_loop = make_run_loop_mock(personas)
    expected_cohort_id = "cohort-match-002"

    with patch("src.social.loop_orchestrator.run_loop", mock_run_loop):
        _, trace = asyncio.run(
            run_social_loop(
                personas=personas,
                stimuli=["T0", "T1"],
                network=network,
                level=SocialSimulationLevel.MODERATE,
                session_id="session-match-002",
                cohort_id=expected_cohort_id,
            )
        )

    assert trace.cohort_id == expected_cohort_id


def test_trace_total_turns_matches_stimuli_length():
    personas = two_personas()
    network = full_mesh_two()
    mock_run_loop = make_run_loop_mock(personas)

    stimuli = ["T0", "T1", "T2", "T3"]

    with patch("src.social.loop_orchestrator.run_loop", mock_run_loop):
        _, trace = asyncio.run(
            run_social_loop(
                personas=personas,
                stimuli=stimuli,
                network=network,
                level=SocialSimulationLevel.MODERATE,
                session_id="session-turns-001",
                cohort_id="cohort-turns-001",
            )
        )

    assert trace.total_turns == len(stimuli)


def test_trace_social_simulation_level_matches_input():
    personas = two_personas()
    network = full_mesh_two()
    mock_run_loop = make_run_loop_mock(personas)

    with patch("src.social.loop_orchestrator.run_loop", mock_run_loop):
        _, trace = asyncio.run(
            run_social_loop(
                personas=personas,
                stimuli=["T0", "T1"],
                network=network,
                level=SocialSimulationLevel.MODERATE,
                session_id="session-level-001",
                cohort_id="cohort-level-001",
            )
        )

    assert trace.social_simulation_level == SocialSimulationLevel.MODERATE


def test_trace_validity_gate_results_contains_all_gates():
    """validity_gate_results must contain SV1, SV2, SV3, SV4, SV5 keys."""
    personas = two_personas()
    network = full_mesh_two()
    mock_run_loop = make_run_loop_mock(personas)

    with patch("src.social.loop_orchestrator.run_loop", mock_run_loop):
        _, trace = asyncio.run(
            run_social_loop(
                personas=personas,
                stimuli=["T0", "T1"],
                network=network,
                level=SocialSimulationLevel.MODERATE,
                session_id="session-gates-001",
                cohort_id="cohort-gates-001",
            )
        )

    for gate in ("SV1", "SV2", "SV3", "SV4", "SV5"):
        assert gate in trace.validity_gate_results, f"Missing gate {gate}"


def test_sv1_gate_all_events_linked():
    """SV1: resulting_observation_id set from mock loop_result.observation.id → SV1 passes."""
    personas = two_personas()
    network = full_mesh_two()
    mock_run_loop = make_run_loop_mock(personas)

    with patch("src.social.loop_orchestrator.run_loop", mock_run_loop):
        _, trace = asyncio.run(
            run_social_loop(
                personas=personas,
                stimuli=["T0", "T1"],
                network=network,
                level=SocialSimulationLevel.MODERATE,
                session_id="session-sv1-001",
                cohort_id="cohort-sv1-001",
            )
        )

    sv1 = trace.validity_gate_results["SV1"]
    assert sv1["passed"] is True


def test_sv5_gate_derived_insights_unchanged():
    """SV5: mocked run_loop returns the same persona → derived_insights unchanged → SV5 passes."""
    personas = two_personas()
    network = full_mesh_two()
    mock_run_loop = make_run_loop_mock(personas)

    with patch("src.social.loop_orchestrator.run_loop", mock_run_loop):
        _, trace = asyncio.run(
            run_social_loop(
                personas=personas,
                stimuli=["T0", "T1"],
                network=network,
                level=SocialSimulationLevel.MODERATE,
                session_id="session-sv5-001",
                cohort_id="cohort-sv5-001",
            )
        )

    sv5 = trace.validity_gate_results["SV5"]
    assert sv5["passed"] is True


def test_trace_is_social_simulation_trace_instance():
    personas = two_personas()
    network = full_mesh_two()
    mock_run_loop = make_run_loop_mock(personas)

    with patch("src.social.loop_orchestrator.run_loop", mock_run_loop):
        _, trace = asyncio.run(
            run_social_loop(
                personas=personas,
                stimuli=["T0", "T1"],
                network=network,
                level=SocialSimulationLevel.MODERATE,
                session_id="session-type-001",
                cohort_id="cohort-type-001",
            )
        )

    assert isinstance(trace, SocialSimulationTrace)


def test_trace_total_turns_single_stimulus():
    personas = two_personas()
    network = full_mesh_two()
    mock_run_loop = make_run_loop_mock(personas)

    with patch("src.social.loop_orchestrator.run_loop", mock_run_loop):
        _, trace = asyncio.run(
            run_social_loop(
                personas=personas,
                stimuli=["Only stimulus"],
                network=network,
                level=SocialSimulationLevel.MODERATE,
                session_id="session-single-002",
                cohort_id="cohort-single-002",
            )
        )

    assert trace.total_turns == 1
