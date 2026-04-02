"""src/modalities/simulation_report.py — Simulation report formatter.

Sprint 7 — OpenCode (Simulation Report + S1/S2 Quality Gates)

Spec: §12 (Simulation Quality Gates S1–S4)

Pure-computation report generation — no LLM calls.
Produces attitude arc, decision summaries, and per-persona logs from a SimulationResult.

Attitude arc: one AttitudePoint per turn, aggregated across all personas.
Decision summaries: one DecisionSummary per turn where at least one persona decided,
  with normalized decision distribution across personas.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from src.modalities.simulation import SimulationResult, TurnLog, PersonaSimulationResult


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AttitudePoint:
    turn: int
    avg_confidence: float      # mean confidence across all personas at this turn (None turns excluded)
    avg_valence: float         # mean observation emotional_valence at this turn
    reflection_fired: bool     # True if any persona reflected at this turn


@dataclass
class DecisionSummary:
    turn: int
    stimulus: str
    decision_distribution: dict[str, int]   # normalized decision → count
    avg_confidence: float
    divergence_flag: bool                   # True if no decision > 50% of deciding personas


@dataclass
class SimulationReport:
    simulation_id: str
    cohort_size: int
    total_turns: int
    attitude_arc: list[AttitudePoint]          # one per turn
    decision_summaries: list[DecisionSummary]  # only turns where decisions were made
    per_persona_logs: dict[str, list[TurnLog]] # persona_id → turn logs


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_decision(text: str) -> str:
    """Normalise a decision string to a short canonical key.

    yes/no prefix matching; otherwise first 40 chars of lowercased text.
    """
    t = text.lower().strip()
    if t.startswith("yes"):
        return "yes"
    if t.startswith("no"):
        return "no"
    return t[:40]


def _build_attitude_point(
    turn_index: int,
    logs_at_turn: list[TurnLog],
) -> AttitudePoint:
    """Compute AttitudePoint for a single turn across all personas.

    avg_valence: mean of observation_valence for all personas at this turn.
    avg_confidence: mean of confidence for personas where decided=True.
                    0.0 when no persona made a decision this turn.
    reflection_fired: True if any persona reflected at this turn.
    """
    # Average valence across all personas (always present)
    if logs_at_turn:
        avg_valence = sum(log.observation_valence for log in logs_at_turn) / len(logs_at_turn)
    else:
        avg_valence = 0.0

    # Average confidence — only from turns where decided=True
    decided_logs = [log for log in logs_at_turn if log.decided and log.confidence is not None]
    if decided_logs:
        avg_confidence = sum(log.confidence for log in decided_logs) / len(decided_logs)  # type: ignore[arg-type]
    else:
        avg_confidence = 0.0

    # Reflection fired if any persona reflected this turn
    reflection_fired = any(log.reflected for log in logs_at_turn)

    return AttitudePoint(
        turn=turn_index,
        avg_confidence=avg_confidence,
        avg_valence=avg_valence,
        reflection_fired=reflection_fired,
    )


def _build_decision_summary(
    turn_index: int,
    stimulus: str,
    logs_at_turn: list[TurnLog],
) -> DecisionSummary | None:
    """Compute DecisionSummary for a turn where at least one persona decided.

    Returns None if no persona made a decision this turn.
    """
    decided_logs = [log for log in logs_at_turn if log.decided and log.decision is not None]
    if not decided_logs:
        return None

    # Decision distribution — normalize decision strings
    decision_distribution: dict[str, int] = Counter(
        _normalize_decision(log.decision) for log in decided_logs  # type: ignore[arg-type]
    )

    # Average confidence across deciding personas
    confidences = [log.confidence for log in decided_logs if log.confidence is not None]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    # Divergence flag: True if no single normalized decision accounts for > 50%
    total = len(decided_logs)
    max_count = max(decision_distribution.values(), default=0)
    divergence_flag = (max_count / total) <= 0.5 if total > 0 else False

    return DecisionSummary(
        turn=turn_index,
        stimulus=stimulus,
        decision_distribution=dict(decision_distribution),
        avg_confidence=avg_confidence,
        divergence_flag=divergence_flag,
    )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def generate_simulation_report(result: SimulationResult) -> SimulationReport:
    """Compute SimulationReport from SimulationResult.

    All computation is deterministic — no LLM calls.

    Steps:
    1. Build per_persona_logs index (persona_id → list[TurnLog]).
    2. For each turn index, collect logs from all personas at that turn.
    3. Build AttitudePoint for each turn (avg_valence, avg_confidence, reflection_fired).
    4. Build DecisionSummary for turns where at least one persona decided.
    5. Return SimulationReport.
    """
    # Build per_persona_logs index
    per_persona_logs: dict[str, list[TurnLog]] = {}
    for persona_result in result.personas:
        per_persona_logs[persona_result.persona_id] = list(persona_result.turn_logs)

    cohort_size = len(result.personas)
    total_turns = result.total_turns

    # Build a turn-indexed view: turn_index → list of TurnLog across all personas
    # TurnLog.turn is the 0-based turn index
    logs_by_turn: dict[int, list[TurnLog]] = defaultdict(list)
    for persona_result in result.personas:
        for log in persona_result.turn_logs:
            logs_by_turn[log.turn].append(log)

    # Build stimulus lookup from first persona (all personas see same stimuli)
    stimulus_by_turn: dict[int, str] = {}
    if result.personas:
        for log in result.personas[0].turn_logs:
            stimulus_by_turn[log.turn] = log.stimulus

    # Build attitude arc — one AttitudePoint per turn
    attitude_arc: list[AttitudePoint] = []
    for turn_index in range(total_turns):
        logs_at_turn = logs_by_turn.get(turn_index, [])
        attitude_point = _build_attitude_point(turn_index, logs_at_turn)
        attitude_arc.append(attitude_point)

    # Build decision summaries — only for turns with at least one decision
    decision_summaries: list[DecisionSummary] = []
    for turn_index in range(total_turns):
        logs_at_turn = logs_by_turn.get(turn_index, [])
        stimulus = stimulus_by_turn.get(turn_index, "")
        summary = _build_decision_summary(turn_index, stimulus, logs_at_turn)
        if summary is not None:
            decision_summaries.append(summary)

    return SimulationReport(
        simulation_id=result.simulation_id,
        cohort_size=cohort_size,
        total_turns=total_turns,
        attitude_arc=attitude_arc,
        decision_summaries=decision_summaries,
        per_persona_logs=per_persona_logs,
    )
