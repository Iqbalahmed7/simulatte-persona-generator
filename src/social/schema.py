"""src/social/schema.py — Social simulation data structures.

All types are immutable value objects. No LLM calls.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class SocialSimulationLevel(str, Enum):
    ISOLATED  = "isolated"    # 0.0 — no social influence; existing behaviour unchanged
    LOW       = "low"         # 0.25
    MODERATE  = "moderate"    # 0.50
    HIGH      = "high"        # 0.75 — tendency drift allowed
    SATURATED = "saturated"   # 1.0  — stress-test only

# Level → float weight (used for gated_importance computation)
LEVEL_WEIGHTS: dict[str, float] = {
    "isolated":  0.0,
    "low":       0.25,
    "moderate":  0.50,
    "high":      0.75,
    "saturated": 1.0,
}


class NetworkTopology(str, Enum):
    FULL_MESH         = "full_mesh"
    RANDOM_ENCOUNTER  = "random_encounter"
    DIRECTED_GRAPH    = "directed_graph"


class SocialNetworkEdge(BaseModel):
    source_id: str       # transmitter persona_id
    target_id: str       # receiver persona_id
    edge_type: Literal["peer", "authority", "family", "influencer"] = "peer"
    weight: float = 1.0  # influence weight multiplier (1.0 = standard)


class SocialNetwork(BaseModel):
    topology: NetworkTopology
    edges: list[SocialNetworkEdge]


class InfluenceVector(BaseModel):
    """Per-persona influence accounting for a simulation run."""
    persona_id: str
    total_events_transmitted: int = 0
    total_events_received: int = 0
    mean_gated_importance_transmitted: float = 0.0
    mean_gated_importance_received: float = 0.0


class SocialInfluenceEvent(BaseModel):
    event_id: str
    turn: int
    transmitter_id: str
    receiver_id: str
    edge_type: Literal["peer", "authority", "family", "influencer"]
    expressed_position: str           # what the transmitter said/decided
    source_output_type: Literal["decision", "observation"]
    raw_importance: int               # before level gate (1–10)
    gated_importance: int             # after level gate (1–10)
    level_weight_applied: float
    susceptibility_score: float       # receiver susceptibility [0.0, 1.0]
    signal_strength: float            # transmitter signal strength [0.0, 1.0]
    synthetic_stimulus_text: str      # the text injected into perceive()
    resulting_observation_id: str | None = None  # set by loop orchestrator after perceive()
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TendencyShiftRecord(BaseModel):
    """Audit trail for any tendency description drift at HIGH/SATURATED level."""
    record_id: str
    persona_id: str
    session_id: str
    turn_triggered: int
    tendency_field: str               # e.g. "trust_orientation.description"
    description_before: str
    description_after: str
    source_social_reflection_ids: list[str]   # >= 3 required
    social_simulation_level: SocialSimulationLevel
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SocialSimulationTrace(BaseModel):
    """Accumulated record of a full social simulation run."""
    trace_id: str
    session_id: str
    cohort_id: str
    social_simulation_level: SocialSimulationLevel
    network_topology: NetworkTopology
    total_turns: int
    total_influence_events: int
    influence_vectors: dict[str, InfluenceVector]   # persona_id → InfluenceVector
    tendency_shift_log: list[TendencyShiftRecord]
    validity_gate_results: dict[str, Any]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
