"""tests/test_social/test_trace_builder.py — Sprint SB TraceBuilder unit tests.

Tests for src/social/trace_builder.py: event accumulation, all_events copy
semantics, and SocialSimulationTrace construction via build().
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.social.schema import (
    InfluenceVector,
    NetworkTopology,
    SocialInfluenceEvent,
    SocialSimulationLevel,
    SocialSimulationTrace,
)
from src.social.trace_builder import TraceBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_event(
    event_id: str,
    transmitter_id: str,
    receiver_id: str,
    turn: int = 1,
    gated_importance: int = 5,
    resulting_observation_id: str | None = "obs-001",
) -> SocialInfluenceEvent:
    return SocialInfluenceEvent(
        event_id=event_id,
        turn=turn,
        transmitter_id=transmitter_id,
        receiver_id=receiver_id,
        edge_type="peer",
        expressed_position="I chose Brand X",
        source_output_type="decision",
        raw_importance=5,
        gated_importance=gated_importance,
        level_weight_applied=0.5,
        susceptibility_score=0.6,
        signal_strength=0.7,
        synthetic_stimulus_text="Someone said: 'I chose Brand X'",
        resulting_observation_id=resulting_observation_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def make_builder() -> TraceBuilder:
    return TraceBuilder(
        session_id="session-sb-001",
        cohort_id="cohort-sb-001",
        level=SocialSimulationLevel.MODERATE,
        topology=NetworkTopology.FULL_MESH,
    )


# ---------------------------------------------------------------------------
# accumulate
# ---------------------------------------------------------------------------

def test_accumulate_adds_single_event():
    tb = make_builder()
    evt = make_event("evt-001", "p-001", "p-002")
    tb.accumulate(evt)
    assert len(tb.all_events()) == 1


def test_accumulate_adds_multiple_events():
    tb = make_builder()
    tb.accumulate(make_event("evt-001", "p-001", "p-002"))
    tb.accumulate(make_event("evt-002", "p-002", "p-001"))
    tb.accumulate(make_event("evt-003", "p-001", "p-003"))
    assert len(tb.all_events()) == 3


def test_accumulate_preserves_event_identity():
    tb = make_builder()
    evt = make_event("evt-unique", "p-001", "p-002")
    tb.accumulate(evt)
    events = tb.all_events()
    assert events[0].event_id == "evt-unique"


def test_accumulate_empty_builder_has_no_events():
    tb = make_builder()
    assert len(tb.all_events()) == 0


# ---------------------------------------------------------------------------
# all_events — copy semantics
# ---------------------------------------------------------------------------

def test_all_events_returns_copy():
    tb = make_builder()
    tb.accumulate(make_event("evt-001", "p-001", "p-002"))
    events_a = tb.all_events()
    events_b = tb.all_events()
    assert events_a is not events_b


def test_all_events_mutation_does_not_affect_internal_state():
    tb = make_builder()
    tb.accumulate(make_event("evt-001", "p-001", "p-002"))
    events = tb.all_events()
    events.clear()
    assert len(tb.all_events()) == 1


def test_all_events_empty_returns_empty_list():
    tb = make_builder()
    assert tb.all_events() == []


# ---------------------------------------------------------------------------
# build — empty events
# ---------------------------------------------------------------------------

def test_build_with_no_events_total_influence_events_zero():
    tb = make_builder()
    trace = tb.build(total_turns=3)
    assert trace.total_influence_events == 0


def test_build_with_no_events_influence_vectors_empty():
    tb = make_builder()
    trace = tb.build(total_turns=3)
    assert trace.influence_vectors == {}


def test_build_with_no_events_returns_simulation_trace():
    tb = make_builder()
    trace = tb.build(total_turns=2)
    assert isinstance(trace, SocialSimulationTrace)


# ---------------------------------------------------------------------------
# build — trace metadata
# ---------------------------------------------------------------------------

def test_build_session_id_matches():
    tb = make_builder()
    trace = tb.build(total_turns=1)
    assert trace.session_id == "session-sb-001"


def test_build_cohort_id_matches():
    tb = make_builder()
    trace = tb.build(total_turns=1)
    assert trace.cohort_id == "cohort-sb-001"


def test_build_level_matches():
    tb = make_builder()
    trace = tb.build(total_turns=1)
    assert trace.social_simulation_level == SocialSimulationLevel.MODERATE


def test_build_topology_matches():
    tb = make_builder()
    trace = tb.build(total_turns=1)
    assert trace.network_topology == NetworkTopology.FULL_MESH


def test_build_total_turns_matches():
    tb = make_builder()
    trace = tb.build(total_turns=7)
    assert trace.total_turns == 7


def test_build_trace_id_is_string():
    tb = make_builder()
    trace = tb.build(total_turns=1)
    assert isinstance(trace.trace_id, str)
    assert len(trace.trace_id) > 0


# ---------------------------------------------------------------------------
# build — InfluenceVector counts
# ---------------------------------------------------------------------------

def test_build_single_event_correct_tx_count():
    tb = make_builder()
    tb.accumulate(make_event("evt-001", "p-001", "p-002"))
    trace = tb.build(total_turns=2)
    assert trace.influence_vectors["p-001"].total_events_transmitted == 1


def test_build_single_event_correct_rx_count():
    tb = make_builder()
    tb.accumulate(make_event("evt-001", "p-001", "p-002"))
    trace = tb.build(total_turns=2)
    assert trace.influence_vectors["p-002"].total_events_received == 1


def test_build_multiple_events_two_personas_each_direction():
    tb = make_builder()
    tb.accumulate(make_event("evt-001", "p-001", "p-002", gated_importance=4))
    tb.accumulate(make_event("evt-002", "p-002", "p-001", gated_importance=6))
    trace = tb.build(total_turns=2)
    assert trace.influence_vectors["p-001"].total_events_transmitted == 1
    assert trace.influence_vectors["p-001"].total_events_received == 1
    assert trace.influence_vectors["p-002"].total_events_transmitted == 1
    assert trace.influence_vectors["p-002"].total_events_received == 1


def test_build_total_influence_events_count():
    tb = make_builder()
    tb.accumulate(make_event("evt-001", "p-001", "p-002"))
    tb.accumulate(make_event("evt-002", "p-002", "p-001"))
    tb.accumulate(make_event("evt-003", "p-001", "p-003"))
    trace = tb.build(total_turns=3)
    assert trace.total_influence_events == 3


# ---------------------------------------------------------------------------
# build — mean_gated_importance
# ---------------------------------------------------------------------------

def test_build_mean_gated_importance_transmitted_correct():
    tb = make_builder()
    tb.accumulate(make_event("evt-001", "p-001", "p-002", gated_importance=4))
    tb.accumulate(make_event("evt-002", "p-001", "p-003", gated_importance=6))
    trace = tb.build(total_turns=2)
    # mean of [4, 6] = 5.0
    assert trace.influence_vectors["p-001"].mean_gated_importance_transmitted == 5.0


def test_build_mean_gated_importance_received_correct():
    tb = make_builder()
    tb.accumulate(make_event("evt-001", "p-001", "p-002", gated_importance=3))
    tb.accumulate(make_event("evt-002", "p-003", "p-002", gated_importance=7))
    trace = tb.build(total_turns=2)
    # mean of [3, 7] = 5.0
    assert trace.influence_vectors["p-002"].mean_gated_importance_received == 5.0


def test_build_persona_only_transmitted_rx_mean_is_zero():
    """Persona that only transmitted events → mean_gated_importance_received=0.0."""
    tb = make_builder()
    tb.accumulate(make_event("evt-001", "p-001", "p-002"))
    trace = tb.build(total_turns=1)
    # p-001 only appears as transmitter
    assert trace.influence_vectors["p-001"].mean_gated_importance_received == 0.0
    assert trace.influence_vectors["p-001"].total_events_received == 0


def test_build_persona_only_received_tx_mean_is_zero():
    """Persona that only received events → mean_gated_importance_transmitted=0.0."""
    tb = make_builder()
    tb.accumulate(make_event("evt-001", "p-001", "p-002"))
    trace = tb.build(total_turns=1)
    # p-002 only appears as receiver
    assert trace.influence_vectors["p-002"].mean_gated_importance_transmitted == 0.0
    assert trace.influence_vectors["p-002"].total_events_transmitted == 0


# ---------------------------------------------------------------------------
# build — multiple personas
# ---------------------------------------------------------------------------

def test_build_three_personas_all_have_vectors():
    tb = make_builder()
    tb.accumulate(make_event("evt-001", "p-001", "p-002"))
    tb.accumulate(make_event("evt-002", "p-002", "p-003"))
    tb.accumulate(make_event("evt-003", "p-003", "p-001"))
    trace = tb.build(total_turns=3)
    assert "p-001" in trace.influence_vectors
    assert "p-002" in trace.influence_vectors
    assert "p-003" in trace.influence_vectors


def test_build_influence_vectors_are_influvencevector_instances():
    tb = make_builder()
    tb.accumulate(make_event("evt-001", "p-001", "p-002"))
    trace = tb.build(total_turns=1)
    for pid, vec in trace.influence_vectors.items():
        assert isinstance(vec, InfluenceVector)
        assert vec.persona_id == pid
