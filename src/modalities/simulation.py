"""src/modalities/simulation.py — Temporal Simulation Modality Runner.

Sprint 7 — Cursor (Simulation Runner)

Spec: §1 (temporal simulation), §9 (full cognitive loop), §14A S18 (experiment isolation)

Temporal simulation: core + working memory. Memory accumulates across turns.
Each stimulus is processed through the full cognitive loop
(perceive → remember → reflect → decide).

Concurrency model:
- All personas run concurrently per turn (asyncio.gather per stimulus).
- Stimuli processed sequentially within each persona (memory must accumulate in order).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from src.schema.persona import PersonaRecord
from src.cognition.loop import LoopResult, run_loop
from src.experiment.session import ExperimentSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class TurnLog:
    turn: int
    stimulus: str
    persona_id: str
    observation_content: str
    observation_importance: int
    observation_valence: float
    reflected: bool
    decided: bool
    decision: str | None               # DecisionOutput.decision if decided
    confidence: int | None             # DecisionOutput.confidence if decided
    key_drivers: list[str] = field(default_factory=list)
    reasoning_trace: str | None = None


@dataclass
class PersonaSimulationResult:
    persona_id: str
    persona_name: str
    turn_logs: list[TurnLog]
    final_persona_state: PersonaRecord  # persona after all stimuli processed


@dataclass
class SimulationResult:
    simulation_id: str
    session_id: str
    personas: list[PersonaSimulationResult]
    total_turns: int
    stimuli: list[str]
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_turn_log(turn: int, stimulus: str, persona_id: str, result: LoopResult) -> TurnLog:
    return TurnLog(
        turn=turn,
        stimulus=stimulus,
        persona_id=persona_id,
        observation_content=result.observation.content,
        observation_importance=result.observation.importance,
        observation_valence=result.observation.emotional_valence,
        reflected=result.reflected,
        decided=result.decided,
        decision=result.decision.decision if result.decision else None,
        confidence=result.decision.confidence if result.decision else None,
        key_drivers=result.decision.key_drivers if result.decision else [],
        reasoning_trace=result.decision.reasoning_trace if result.decision else None,
    )


async def _run_persona_turn(
    turn: int,
    stimulus: str,
    scenario: str | None,
    persona: PersonaRecord,
) -> tuple[str, PersonaRecord, TurnLog]:
    """Run one stimulus turn for a single persona.

    Returns (persona_id, updated_persona, turn_log).
    """
    updated_persona, loop_result = await run_loop(
        stimulus,
        persona,
        decision_scenario=scenario,
    )
    log = _make_turn_log(turn, stimulus, persona.persona_id, loop_result)
    return persona.persona_id, updated_persona, log


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


async def run_simulation(session: ExperimentSession) -> SimulationResult:
    """
    Run temporal simulation for all personas in the session.

    For each persona:
    1. Start with session.persona (or each persona in session.cohort.personas)
    2. For each stimulus in session.stimuli:
       a. Check if this stimulus index has a paired decision scenario
          (session.decision_scenarios[i] if i < len(session.decision_scenarios))
       b. Call run_loop(stimulus, persona, decision_scenario=scenario_or_None)
       c. Log the TurnLog from LoopResult
       d. Update persona state for next turn

    Run all personas concurrently (asyncio.gather) for each stimulus turn.
    Process stimuli sequentially within each persona (memory must accumulate in order).

    simulation_id defaults to f"sim-{uuid4().hex[:8]}"
    """
    simulation_id = f"sim-{uuid4().hex[:8]}"

    # ------------------------------------------------------------------
    # Resolve starting personas from session
    # ------------------------------------------------------------------
    if session.persona is not None:
        starting_personas: list[PersonaRecord] = [session.persona]
    else:
        starting_personas = list(session.cohort.personas)  # type: ignore[union-attr]

    # Build mutable state map: persona_id → current PersonaRecord
    # Working memory carries forward turn-to-turn (no reset between stimuli).
    persona_states: dict[str, PersonaRecord] = {
        p.persona_id: p for p in starting_personas
    }

    # Accumulate turn logs per persona
    turn_logs_by_persona: dict[str, list[TurnLog]] = {
        p.persona_id: [] for p in starting_personas
    }

    persona_ids: list[str] = [p.persona_id for p in starting_personas]

    # ------------------------------------------------------------------
    # Process stimuli sequentially; run all personas concurrently per turn
    # ------------------------------------------------------------------
    for i, stimulus in enumerate(session.stimuli):
        scenario: str | None = (
            session.decision_scenarios[i]
            if i < len(session.decision_scenarios)
            else None
        )

        logger.debug(
            "run_simulation %s: turn %d/%d, %d persona(s), decision_scenario=%s",
            simulation_id,
            i,
            len(session.stimuli) - 1,
            len(persona_ids),
            bool(scenario),
        )

        tasks = [
            _run_persona_turn(
                turn=i,
                stimulus=stimulus,
                scenario=scenario,
                persona=persona_states[pid],
            )
            for pid in persona_ids
        ]

        turn_results: tuple[tuple[str, PersonaRecord, TurnLog], ...] = (
            await asyncio.gather(*tasks)
        )

        # Update persona states and collect logs for next turn
        for pid, updated_persona, turn_log in turn_results:
            persona_states[pid] = updated_persona
            turn_logs_by_persona[pid].append(turn_log)

    # ------------------------------------------------------------------
    # Assemble per-persona results
    # ------------------------------------------------------------------
    persona_results: list[PersonaSimulationResult] = [
        PersonaSimulationResult(
            persona_id=pid,
            persona_name=persona_states[pid].demographic_anchor.name,
            turn_logs=turn_logs_by_persona[pid],
            final_persona_state=persona_states[pid],
        )
        for pid in persona_ids
    ]

    return SimulationResult(
        simulation_id=simulation_id,
        session_id=session.session_id,
        personas=persona_results,
        total_turns=len(session.stimuli),
        stimuli=list(session.stimuli),
    )
