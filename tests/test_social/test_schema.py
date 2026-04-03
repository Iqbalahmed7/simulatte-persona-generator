"""tests/test_social/test_schema.py — Sprint SA schema unit tests.

Tests for src/social/schema.py data structures and the ExperimentSession
new social fields added in Sprint SA.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.social.schema import (
    LEVEL_WEIGHTS,
    InfluenceVector,
    NetworkTopology,
    SocialInfluenceEvent,
    SocialNetwork,
    SocialNetworkEdge,
    SocialSimulationLevel,
    SocialSimulationTrace,
    TendencyShiftRecord,
)


# ---------------------------------------------------------------------------
# SocialSimulationLevel enum
# ---------------------------------------------------------------------------

def test_level_isolated_value():
    assert SocialSimulationLevel.ISOLATED.value == "isolated"


def test_level_low_value():
    assert SocialSimulationLevel.LOW.value == "low"


def test_level_moderate_value():
    assert SocialSimulationLevel.MODERATE.value == "moderate"


def test_level_high_value():
    assert SocialSimulationLevel.HIGH.value == "high"


def test_level_saturated_value():
    assert SocialSimulationLevel.SATURATED.value == "saturated"


def test_level_enum_has_five_members():
    assert len(SocialSimulationLevel) == 5


# ---------------------------------------------------------------------------
# LEVEL_WEIGHTS mapping
# ---------------------------------------------------------------------------

def test_level_weight_isolated():
    assert LEVEL_WEIGHTS["isolated"] == 0.0


def test_level_weight_low():
    assert LEVEL_WEIGHTS["low"] == 0.25


def test_level_weight_moderate():
    assert LEVEL_WEIGHTS["moderate"] == 0.50


def test_level_weight_high():
    assert LEVEL_WEIGHTS["high"] == 0.75


def test_level_weight_saturated():
    assert LEVEL_WEIGHTS["saturated"] == 1.0


# ---------------------------------------------------------------------------
# NetworkTopology enum
# ---------------------------------------------------------------------------

def test_topology_full_mesh_value():
    assert NetworkTopology.FULL_MESH.value == "full_mesh"


def test_topology_random_encounter_value():
    assert NetworkTopology.RANDOM_ENCOUNTER.value == "random_encounter"


def test_topology_directed_graph_value():
    assert NetworkTopology.DIRECTED_GRAPH.value == "directed_graph"


# ---------------------------------------------------------------------------
# SocialNetworkEdge defaults
# ---------------------------------------------------------------------------

def test_edge_default_edge_type():
    edge = SocialNetworkEdge(source_id="p-001", target_id="p-002")
    assert edge.edge_type == "peer"


def test_edge_default_weight():
    edge = SocialNetworkEdge(source_id="p-001", target_id="p-002")
    assert edge.weight == 1.0


def test_edge_custom_fields():
    edge = SocialNetworkEdge(
        source_id="p-001", target_id="p-002",
        edge_type="authority", weight=2.5,
    )
    assert edge.edge_type == "authority"
    assert edge.weight == 2.5


# ---------------------------------------------------------------------------
# SocialNetwork construction
# ---------------------------------------------------------------------------

def test_social_network_construction():
    edges = [
        SocialNetworkEdge(source_id="p-001", target_id="p-002"),
        SocialNetworkEdge(source_id="p-002", target_id="p-001"),
    ]
    net = SocialNetwork(topology=NetworkTopology.FULL_MESH, edges=edges)
    assert net.topology == NetworkTopology.FULL_MESH
    assert len(net.edges) == 2


def test_social_network_empty_edges():
    net = SocialNetwork(topology=NetworkTopology.RANDOM_ENCOUNTER, edges=[])
    assert net.edges == []


# ---------------------------------------------------------------------------
# SocialInfluenceEvent construction
# ---------------------------------------------------------------------------

def test_influence_event_construction():
    evt = SocialInfluenceEvent(
        event_id="evt-abc12345",
        turn=1,
        transmitter_id="p-001",
        receiver_id="p-002",
        edge_type="peer",
        expressed_position="I chose Brand X",
        source_output_type="decision",
        raw_importance=5,
        gated_importance=4,
        level_weight_applied=0.75,
        susceptibility_score=0.45,
        signal_strength=0.60,
        synthetic_stimulus_text="Someone said: 'I chose Brand X'",
    )
    assert evt.transmitter_id == "p-001"
    assert evt.receiver_id == "p-002"
    assert evt.gated_importance == 4
    assert evt.resulting_observation_id is None  # default
    assert isinstance(evt.timestamp, datetime)


# ---------------------------------------------------------------------------
# TendencyShiftRecord construction
# ---------------------------------------------------------------------------

def test_tendency_shift_record_construction():
    record = TendencyShiftRecord(
        record_id="drift-00000001",
        persona_id="pg-test-001",
        session_id="session-abc",
        turn_triggered=3,
        tendency_field="trust_orientation.description",
        description_before="trusts experts",
        description_after="[PENDING DRIFT REVIEW — 3 social reflections]",
        source_social_reflection_ids=["r1", "r2", "r3"],
        social_simulation_level=SocialSimulationLevel.HIGH,
    )
    assert record.persona_id == "pg-test-001"
    assert record.tendency_field == "trust_orientation.description"
    assert record.social_simulation_level == SocialSimulationLevel.HIGH
    assert isinstance(record.timestamp, datetime)


# ---------------------------------------------------------------------------
# SocialSimulationTrace construction
# ---------------------------------------------------------------------------

def test_simulation_trace_construction():
    iv = InfluenceVector(persona_id="p-001")
    trace = SocialSimulationTrace(
        trace_id="trace-001",
        session_id="session-001",
        cohort_id="cohort-001",
        social_simulation_level=SocialSimulationLevel.MODERATE,
        network_topology=NetworkTopology.FULL_MESH,
        total_turns=5,
        total_influence_events=12,
        influence_vectors={"p-001": iv},
        tendency_shift_log=[],
        validity_gate_results={},
    )
    assert trace.trace_id == "trace-001"
    assert trace.total_turns == 5
    assert trace.total_influence_events == 12
    assert "p-001" in trace.influence_vectors
    assert isinstance(trace.generated_at, datetime)


# ---------------------------------------------------------------------------
# ExperimentSession social fields
# ---------------------------------------------------------------------------

def test_experiment_session_social_simulation_level_default():
    """ExperimentSession.social_simulation_level defaults to ISOLATED."""
    from src.experiment.session import ExperimentSession
    from src.experiment.modality import ExperimentModality
    from datetime import datetime, timezone
    from src.schema.persona import (
        PersonaRecord, DemographicAnchor, Location, Household, LifeStory,
        Attribute, DerivedInsights, CopingMechanism, BehaviouralTendencies,
        PriceSensitivityBand, TrustOrientation, TrustWeights, TendencyBand,
        Objection, Narrative, Memory, CoreMemory, WorkingMemory, SimulationState,
        LifeDefiningEvent, RelationshipMap, ImmutableConstraints,
    )
    persona = PersonaRecord(
        persona_id="pg-test-session",
        generated_at=datetime.now(timezone.utc),
        generator_version="test-1.0",
        domain="cpg", mode="quick",
        demographic_anchor=DemographicAnchor(
            name="Session Test", age=35, gender="male",
            location=Location(country="India", region="MH", city="Mumbai", urban_tier="metro"),
            household=Household(structure="nuclear", size=3, income_bracket="middle", dual_income=False),
            life_stage="adult", education="undergraduate", employment="full-time",
        ),
        life_stories=[
            LifeStory(title="A", when="2020", event="Event A", lasting_impact="Impact A"),
            LifeStory(title="B", when="2018", event="Event B", lasting_impact="Impact B"),
        ],
        attributes={"base": {"openness": Attribute(value=0.6, type="continuous", label="Openness", source="sampled")}},
        derived_insights=DerivedInsights(
            decision_style="analytical", decision_style_score=0.6,
            trust_anchor="authority", risk_appetite="low",
            primary_value_orientation="quality",
            coping_mechanism=CopingMechanism(type="research_deep_dive", description="Researches"),
            consistency_score=70, consistency_band="high", key_tensions=["price vs quality"],
        ),
        behavioural_tendencies=BehaviouralTendencies(
            price_sensitivity=PriceSensitivityBand(band="medium", description="moderate", source="grounded"),
            trust_orientation=TrustOrientation(
                weights=TrustWeights(expert=0.5, peer=0.2, brand=0.1, ad=0.05, community=0.1, influencer=0.05),
                dominant="expert", description="trusts experts", source="grounded",
            ),
            switching_propensity=TendencyBand(band="low", description="loyal", source="grounded"),
            objection_profile=[Objection(objection_type="price_vs_value", likelihood="medium", severity="friction")],
            reasoning_prompt="Think carefully.",
        ),
        narrative=Narrative(first_person="I am...", third_person="He is...", display_name="Session"),
        decision_bullets=["Quality first"],
        memory=Memory(
            core=CoreMemory(
                identity_statement="A careful thinker",
                key_values=["quality", "trust", "value"],
                life_defining_events=[LifeDefiningEvent(age_when=28, event="Career", lasting_impact="Ambition")],
                relationship_map=RelationshipMap(primary_decision_partner="spouse", key_influencers=["doctor"], trust_network=["family"]),
                immutable_constraints=ImmutableConstraints(budget_ceiling=None, non_negotiables=["quality"], absolute_avoidances=["fake"]),
                tendency_summary="Careful",
            ),
            working=WorkingMemory(
                observations=[], reflections=[], plans=[], brand_memories={},
                simulation_state=SimulationState(current_turn=0, importance_accumulator=0.0, reflection_count=0, awareness_set={}, consideration_set=[], last_decision=None),
            ),
        ),
    )
    session = ExperimentSession(
        session_id="test-session-001",
        modality=ExperimentModality.ONE_TIME_SURVEY,
        persona=persona,
    )
    assert session.social_simulation_level == SocialSimulationLevel.ISOLATED


def test_experiment_session_social_network_default_none():
    """ExperimentSession.social_network defaults to None."""
    from src.experiment.session import ExperimentSession
    from src.experiment.modality import ExperimentModality
    from datetime import datetime, timezone
    from src.schema.persona import (
        PersonaRecord, DemographicAnchor, Location, Household, LifeStory,
        Attribute, DerivedInsights, CopingMechanism, BehaviouralTendencies,
        PriceSensitivityBand, TrustOrientation, TrustWeights, TendencyBand,
        Objection, Narrative, Memory, CoreMemory, WorkingMemory, SimulationState,
        LifeDefiningEvent, RelationshipMap, ImmutableConstraints,
    )
    persona = PersonaRecord(
        persona_id="pg-test-session-2",
        generated_at=datetime.now(timezone.utc),
        generator_version="test-1.0",
        domain="cpg", mode="quick",
        demographic_anchor=DemographicAnchor(
            name="Session Test 2", age=40, gender="female",
            location=Location(country="India", region="MH", city="Mumbai", urban_tier="metro"),
            household=Household(structure="nuclear", size=4, income_bracket="upper-middle", dual_income=True),
            life_stage="adult", education="postgraduate", employment="full-time",
        ),
        life_stories=[
            LifeStory(title="A", when="2019", event="Event A", lasting_impact="Impact A"),
            LifeStory(title="B", when="2015", event="Event B", lasting_impact="Impact B"),
        ],
        attributes={"base": {"openness": Attribute(value=0.8, type="continuous", label="Openness", source="sampled")}},
        derived_insights=DerivedInsights(
            decision_style="social", decision_style_score=0.8,
            trust_anchor="peer", risk_appetite="medium",
            primary_value_orientation="convenience",
            coping_mechanism=CopingMechanism(type="research_deep_dive", description="Asks friends"),
            consistency_score=65, consistency_band="medium", key_tensions=["convenience vs quality"],
        ),
        behavioural_tendencies=BehaviouralTendencies(
            price_sensitivity=PriceSensitivityBand(band="high", description="very price sensitive", source="grounded"),
            trust_orientation=TrustOrientation(
                weights=TrustWeights(expert=0.2, peer=0.5, brand=0.1, ad=0.05, community=0.1, influencer=0.05),
                dominant="peer", description="trusts peers", source="grounded",
            ),
            switching_propensity=TendencyBand(band="high", description="switches often", source="grounded"),
            objection_profile=[Objection(objection_type="price_vs_value", likelihood="high", severity="friction")],
            reasoning_prompt="Ask friends.",
        ),
        narrative=Narrative(first_person="I ask...", third_person="She asks...", display_name="Session2"),
        decision_bullets=["Peer approval first"],
        memory=Memory(
            core=CoreMemory(
                identity_statement="A social thinker",
                key_values=["community", "peers", "convenience"],
                life_defining_events=[LifeDefiningEvent(age_when=22, event="College", lasting_impact="Social bonds")],
                relationship_map=RelationshipMap(primary_decision_partner="friend", key_influencers=["peer"], trust_network=["friends"]),
                immutable_constraints=ImmutableConstraints(budget_ceiling=None, non_negotiables=["peer approval"], absolute_avoidances=["isolation"]),
                tendency_summary="Social",
            ),
            working=WorkingMemory(
                observations=[], reflections=[], plans=[], brand_memories={},
                simulation_state=SimulationState(current_turn=0, importance_accumulator=0.0, reflection_count=0, awareness_set={}, consideration_set=[], last_decision=None),
            ),
        ),
    )
    session = ExperimentSession(
        session_id="test-session-002",
        modality=ExperimentModality.ONE_TIME_SURVEY,
        persona=persona,
    )
    assert session.social_network is None
