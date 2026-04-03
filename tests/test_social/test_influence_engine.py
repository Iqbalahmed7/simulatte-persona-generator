"""tests/test_social/test_influence_engine.py — Sprint SA influence engine tests.

Tests for src/social/influence_engine.py: susceptibility, signal strength,
gated importance, stimulus formatting, event generation, and tendency drift.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

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
    PersonaRecord,
    PriceSensitivityBand,
    Reflection,
    RelationshipMap,
    SimulationState,
    TendencyBand,
    TrustOrientation,
    TrustWeights,
    WorkingMemory,
)
from src.social.influence_engine import (
    check_tendency_drift,
    compute_gated_importance,
    compute_signal_strength,
    compute_susceptibility,
    format_as_stimulus,
    generate_influence_events,
)
from src.social.schema import (
    NetworkTopology,
    SocialNetwork,
    SocialNetworkEdge,
    SocialSimulationLevel,
)


# ---------------------------------------------------------------------------
# Helper: make_minimal_persona
# ---------------------------------------------------------------------------

def make_minimal_persona(
    persona_id: str = "pg-test-001",
    domain: str = "cpg",
    age: int = 30,
    gender: str = "female",
    city_tier: str = "metro",
    decision_style: str = "analytical",
    consistency_score: int = 80,
    decision_style_score: float = 0.7,
    peer_weight: float = 0.2,
    name: str = "Test Persona",
) -> PersonaRecord:
    return PersonaRecord(
        persona_id=persona_id,
        generated_at=datetime.now(timezone.utc),
        generator_version="test-1.0",
        domain=domain,
        mode="quick",
        demographic_anchor=DemographicAnchor(
            name=name,
            age=age,
            gender=gender,
            location=Location(country="India", region="MH", city="Mumbai", urban_tier=city_tier),
            household=Household(structure="nuclear", size=4, income_bracket="middle", dual_income=True),
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
            decision_style_score=decision_style_score,
            trust_anchor="authority",
            risk_appetite="medium",
            primary_value_orientation="quality",
            coping_mechanism=CopingMechanism(type="research_deep_dive", description="Researches"),
            consistency_score=consistency_score,
            consistency_band="high",
            key_tensions=["price vs quality"],
        ),
        behavioural_tendencies=BehaviouralTendencies(
            price_sensitivity=PriceSensitivityBand(band="medium", description="moderate", source="grounded"),
            trust_orientation=TrustOrientation(
                weights=TrustWeights(
                    expert=0.5,
                    peer=peer_weight,
                    brand=0.1,
                    ad=0.05,
                    community=max(0.0, 0.3 - peer_weight),
                    influencer=0.05,
                ),
                dominant="expert",
                description="trusts experts",
                source="grounded",
            ),
            switching_propensity=TendencyBand(band="low", description="loyal", source="grounded"),
            objection_profile=[
                Objection(objection_type="price_vs_value", likelihood="medium", severity="friction")
            ],
            reasoning_prompt="Think analytically.",
        ),
        narrative=Narrative(first_person="I am...", third_person="She is...", display_name="Test"),
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


def make_reflection(rid: str) -> Reflection:
    now = datetime.now(timezone.utc)
    return Reflection(
        id=rid,
        timestamp=now,
        type="reflection",
        content="A social reflection",
        importance=5,
        source_observation_ids=["obs-1", "obs-2"],
        last_accessed=now,
    )


def make_network_pair(pid_a: str, pid_b: str) -> SocialNetwork:
    """Minimal 2-node full-mesh network."""
    return SocialNetwork(
        topology=NetworkTopology.FULL_MESH,
        edges=[
            SocialNetworkEdge(source_id=pid_a, target_id=pid_b),
            SocialNetworkEdge(source_id=pid_b, target_id=pid_a),
        ],
    )


# ---------------------------------------------------------------------------
# compute_susceptibility
# ---------------------------------------------------------------------------

def test_susceptibility_returns_float():
    p = make_minimal_persona()
    result = compute_susceptibility(p)
    assert isinstance(result, float)


def test_susceptibility_in_range():
    p = make_minimal_persona()
    result = compute_susceptibility(p)
    assert 0.0 <= result <= 1.0


def test_susceptibility_analytical_lower_than_social():
    """Analytical decision_style should yield lower susceptibility than social."""
    p_analytical = make_minimal_persona(decision_style="analytical", consistency_score=50)
    p_social = make_minimal_persona(decision_style="social", consistency_score=50)
    assert compute_susceptibility(p_analytical) < compute_susceptibility(p_social)


def test_susceptibility_missing_social_attributes_fallback():
    """Persona with no 'social' attributes category should fall back gracefully."""
    p = make_minimal_persona()
    # attributes dict only has 'base' — no 'social' key
    assert "social" not in p.attributes
    result = compute_susceptibility(p)
    # Should return a valid float with fallback values (0.5 each)
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0


# ---------------------------------------------------------------------------
# compute_signal_strength
# ---------------------------------------------------------------------------

def test_signal_strength_returns_float():
    p = make_minimal_persona()
    result = compute_signal_strength(p)
    assert isinstance(result, float)


def test_signal_strength_in_range():
    p = make_minimal_persona()
    result = compute_signal_strength(p)
    assert 0.0 <= result <= 1.0


def test_signal_strength_higher_for_high_consistency():
    """Higher consistency_score and decision_style_score → higher signal."""
    p_high = make_minimal_persona(consistency_score=100, decision_style_score=1.0)
    p_low = make_minimal_persona(consistency_score=10, decision_style_score=0.1)
    assert compute_signal_strength(p_high) > compute_signal_strength(p_low)


def test_signal_strength_formula():
    """Verify formula: dss * 0.5 + cs/100 * 0.5."""
    p = make_minimal_persona(consistency_score=80, decision_style_score=0.6)
    expected = 0.6 * 0.5 + 0.8 * 0.5
    result = compute_signal_strength(p)
    assert abs(result - expected) < 1e-9


# ---------------------------------------------------------------------------
# compute_gated_importance
# ---------------------------------------------------------------------------

def test_gated_importance_returns_int():
    result = compute_gated_importance(0.5, 0.5, SocialSimulationLevel.MODERATE)
    assert isinstance(result, int)


def test_gated_importance_in_range():
    for level in SocialSimulationLevel:
        gi = compute_gated_importance(0.5, 0.5, level)
        assert 1 <= gi <= 10, f"gated_importance={gi} out of [1,10] at level={level}"


def test_gated_importance_isolated_returns_at_least_1():
    """At ISOLATED (weight=0.0): raw * 0.0 = 0 → max(1, 0) = 1."""
    result = compute_gated_importance(0.9, 0.9, SocialSimulationLevel.ISOLATED)
    assert result >= 1


def test_gated_importance_saturated_max():
    """At SATURATED (weight=1.0) with max inputs: result = 10."""
    result = compute_gated_importance(1.0, 1.0, SocialSimulationLevel.SATURATED)
    assert result == 10


# ---------------------------------------------------------------------------
# format_as_stimulus
# ---------------------------------------------------------------------------

def test_format_as_stimulus_contains_name():
    text = format_as_stimulus("Priya", "I chose Brand X")
    assert "Priya" in text


def test_format_as_stimulus_contains_position():
    text = format_as_stimulus("Priya", "I chose Brand X")
    assert "I chose Brand X" in text


def test_format_as_stimulus_pattern():
    """Verify the exact pattern from §1."""
    text = format_as_stimulus("Asha", "Bought premium")
    assert text == "Asha, someone you know, recently said: 'Bought premium'"


# ---------------------------------------------------------------------------
# generate_influence_events
# ---------------------------------------------------------------------------

def test_generate_events_isolated_returns_empty():
    p1 = make_minimal_persona("p-001")
    p2 = make_minimal_persona("p-002")
    net = make_network_pair("p-001", "p-002")
    events = generate_influence_events(
        cohort_personas=[p1, p2],
        network=net,
        level=SocialSimulationLevel.ISOLATED,
        turn=1,
        prior_decisions={"p-001": "I chose Brand X"},
    )
    assert events == []


def test_generate_events_no_prior_decisions_generates_observation_events():
    """When prior_decisions=None, edges are NOT skipped — source_output_type becomes 'observation'."""
    p1 = make_minimal_persona("p-001")
    p2 = make_minimal_persona("p-002")
    net = make_network_pair("p-001", "p-002")
    events = generate_influence_events(
        cohort_personas=[p1, p2],
        network=net,
        level=SocialSimulationLevel.HIGH,
        turn=1,
        prior_decisions=None,
    )
    # With no prior_decisions the skip guard is inactive; events are produced as "observation" type
    assert len(events) > 0
    for evt in events:
        assert evt.source_output_type == "observation"


def test_generate_events_with_prior_decisions_produces_events():
    p1 = make_minimal_persona("p-001")
    p2 = make_minimal_persona("p-002")
    net = make_network_pair("p-001", "p-002")
    events = generate_influence_events(
        cohort_personas=[p1, p2],
        network=net,
        level=SocialSimulationLevel.MODERATE,
        turn=2,
        prior_decisions={"p-001": "I chose Brand X", "p-002": "Brand Y is better"},
    )
    assert len(events) > 0


def test_generate_events_correct_transmitter_receiver():
    p1 = make_minimal_persona("p-001")
    p2 = make_minimal_persona("p-002")
    # One-directional network: only p-001 → p-002
    net = SocialNetwork(
        topology=NetworkTopology.DIRECTED_GRAPH,
        edges=[SocialNetworkEdge(source_id="p-001", target_id="p-002")],
    )
    events = generate_influence_events(
        cohort_personas=[p1, p2],
        network=net,
        level=SocialSimulationLevel.MODERATE,
        turn=1,
        prior_decisions={"p-001": "I chose Brand X"},
    )
    assert len(events) == 1
    assert events[0].transmitter_id == "p-001"
    assert events[0].receiver_id == "p-002"


def test_generate_events_gated_importance_in_range():
    p1 = make_minimal_persona("p-001")
    p2 = make_minimal_persona("p-002")
    net = make_network_pair("p-001", "p-002")
    events = generate_influence_events(
        cohort_personas=[p1, p2],
        network=net,
        level=SocialSimulationLevel.HIGH,
        turn=1,
        prior_decisions={"p-001": "Brand A", "p-002": "Brand B"},
    )
    for evt in events:
        assert 1 <= evt.gated_importance <= 10, f"gated_importance={evt.gated_importance} out of range"


# ---------------------------------------------------------------------------
# check_tendency_drift
# ---------------------------------------------------------------------------

def test_drift_isolated_returns_empty():
    p = make_minimal_persona()
    reflections = [make_reflection(f"r{i}") for i in range(5)]
    result = check_tendency_drift(p, reflections, SocialSimulationLevel.ISOLATED, "s-001", 3)
    assert result == []


def test_drift_low_returns_empty():
    p = make_minimal_persona()
    reflections = [make_reflection(f"r{i}") for i in range(5)]
    result = check_tendency_drift(p, reflections, SocialSimulationLevel.LOW, "s-001", 3)
    assert result == []


def test_drift_moderate_returns_empty():
    p = make_minimal_persona()
    reflections = [make_reflection(f"r{i}") for i in range(5)]
    result = check_tendency_drift(p, reflections, SocialSimulationLevel.MODERATE, "s-001", 3)
    assert result == []


def test_drift_fewer_than_3_reflections_returns_empty():
    p = make_minimal_persona()
    reflections = [make_reflection(f"r{i}") for i in range(2)]
    result = check_tendency_drift(p, reflections, SocialSimulationLevel.HIGH, "s-001", 3)
    assert result == []


def test_drift_high_with_3_reflections_returns_records():
    p = make_minimal_persona()
    reflections = [make_reflection(f"r{i}") for i in range(3)]
    result = check_tendency_drift(p, reflections, SocialSimulationLevel.HIGH, "s-001", 3)
    assert isinstance(result, list)
    assert len(result) > 0


def test_drift_returns_3_records():
    """Exactly 3 TendencyShiftRecords — one per driftable field."""
    p = make_minimal_persona()
    reflections = [make_reflection(f"r{i}") for i in range(4)]
    result = check_tendency_drift(p, reflections, SocialSimulationLevel.HIGH, "s-002", 5)
    assert len(result) == 3


def test_drift_records_cover_all_three_fields():
    p = make_minimal_persona()
    reflections = [make_reflection(f"r{i}") for i in range(3)]
    result = check_tendency_drift(p, reflections, SocialSimulationLevel.SATURATED, "s-003", 2)
    fields = {r.tendency_field for r in result}
    assert "trust_orientation.description" in fields
    assert "switching_propensity.description" in fields
    assert "price_sensitivity.description" in fields


def test_drift_description_after_format():
    """description_after should mention the reflection count."""
    p = make_minimal_persona()
    reflections = [make_reflection(f"r{i}") for i in range(5)]
    result = check_tendency_drift(p, reflections, SocialSimulationLevel.HIGH, "s-004", 7)
    for rec in result:
        assert "5" in rec.description_after
        assert "PENDING DRIFT REVIEW" in rec.description_after
