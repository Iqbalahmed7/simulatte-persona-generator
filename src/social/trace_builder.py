"""src/social/trace_builder.py — Accumulates SocialInfluenceEvents into a SocialSimulationTrace.

No LLM calls.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from src.social.schema import (
    InfluenceVector,
    NetworkTopology,
    SocialInfluenceEvent,
    SocialSimulationLevel,
    SocialSimulationTrace,
)


class TraceBuilder:
    """Accumulates SocialInfluenceEvents across turns, then builds a SocialSimulationTrace."""

    def __init__(
        self,
        session_id: str,
        cohort_id: str,
        level: SocialSimulationLevel,
        topology: NetworkTopology,
    ) -> None:
        self._session_id = session_id
        self._cohort_id = cohort_id
        self._level = level
        self._topology = topology
        self._events: list[SocialInfluenceEvent] = []

    def accumulate(self, event: SocialInfluenceEvent) -> None:
        """Add a SocialInfluenceEvent to the trace."""
        self._events.append(event)

    def all_events(self) -> list[SocialInfluenceEvent]:
        """Return all accumulated events (read-only copy)."""
        return list(self._events)

    def build(self, total_turns: int) -> SocialSimulationTrace:
        """Build the final SocialSimulationTrace.

        Computes per-persona InfluenceVector:
        - total_events_transmitted: how many events this persona transmitted
        - total_events_received: how many events targeted this persona
        - mean_gated_importance_transmitted: mean gated_importance of events transmitted
        - mean_gated_importance_received: mean gated_importance of events received
        """
        # 1. Collect all unique persona IDs from transmitters and receivers
        persona_ids: set[str] = set()
        for e in self._events:
            persona_ids.add(e.transmitter_id)
            persona_ids.add(e.receiver_id)

        # 2. Compute InfluenceVector for each persona
        vectors: dict[str, InfluenceVector] = {}
        for pid in persona_ids:
            transmitted = [e for e in self._events if e.transmitter_id == pid]
            received = [e for e in self._events if e.receiver_id == pid]

            mean_gi_tx = (
                sum(e.gated_importance for e in transmitted) / len(transmitted)
                if transmitted
                else 0.0
            )
            mean_gi_rx = (
                sum(e.gated_importance for e in received) / len(received)
                if received
                else 0.0
            )

            vectors[pid] = InfluenceVector(
                persona_id=pid,
                total_events_transmitted=len(transmitted),
                total_events_received=len(received),
                mean_gated_importance_transmitted=mean_gi_tx,
                mean_gated_importance_received=mean_gi_rx,
            )

        # 3. Build and return the trace
        return SocialSimulationTrace(
            trace_id=f"trace-{uuid4().hex[:8]}",
            session_id=self._session_id,
            cohort_id=self._cohort_id,
            social_simulation_level=self._level,
            network_topology=self._topology,
            total_turns=total_turns,
            total_influence_events=len(self._events),
            influence_vectors=vectors,
            tendency_shift_log=[],
            validity_gate_results={},
        )
