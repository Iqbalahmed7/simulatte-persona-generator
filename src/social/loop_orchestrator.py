"""src/social/loop_orchestrator.py — Multi-persona social simulation orchestrator.

Wraps run_loop() to run multi-turn, multi-persona simulations with peer influence.

Architecture (§6): social influence fires BETWEEN stimuli as a Step 0 before
perceive() on each turn. run_loop() is called unchanged.

No LLM calls in this file (LLM is called via run_loop → perceive/reflect/decide).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from src.cognition.loop import LoopResult, run_loop
from src.experiment.session import SimulationTier
from src.schema.persona import PersonaRecord
from src.social.influence_engine import generate_influence_events
from src.social.schema import (
    SocialInfluenceEvent,
    SocialNetwork,
    SocialSimulationLevel,
    SocialSimulationTrace,
)


@dataclass
class TurnResult:
    """Results from a single simulation turn across all personas."""
    turn: int
    persona_results: dict[str, LoopResult]     # persona_id → LoopResult
    social_events: list[SocialInfluenceEvent]  # events injected this turn
    decisions: dict[str, str]                  # persona_id → decision text (for next turn)


async def run_social_loop(
    personas: list[PersonaRecord],
    stimuli: list[str],
    network: SocialNetwork,
    level: SocialSimulationLevel,
    session_id: str,
    cohort_id: str,
    decision_scenarios: list[str] | None = None,
    llm_client: Any = None,
    tier: SimulationTier = SimulationTier.DEEP,
) -> tuple[list[PersonaRecord], SocialSimulationTrace]:
    """Run a multi-turn social simulation for a cohort of personas.

    For each turn T:
      Step 0: Generate social influence events from prior turn's decisions
              (empty at turn 0 — no prior decisions exist yet)
      Step 1: For each social event targeting persona P:
              - run_loop(event.synthetic_stimulus_text, P) to inject social stimulus
              - link resulting observation_id back to the event
      Step 2: For each persona P:
              - run_loop(stimuli[T], P, decision_scenario=...) for primary stimulus
              - collect P's decision text for next turn
      Step 3: Accumulate all events into TraceBuilder

    After all turns:
      - Build SocialSimulationTrace
      - Run SV1-SV5 validity gates and store in trace.validity_gate_results

    Parameters
    ----------
    personas:           list of PersonaRecord (working memory should be reset before calling)
    stimuli:            one stimulus string per turn
    network:            SocialNetwork defining who influences whom
    level:              SocialSimulationLevel
    session_id:         experiment session ID
    cohort_id:          cohort ID
    decision_scenarios: optional list of one scenario per turn
    llm_client:         LLM client passed through to run_loop
    tier:               SimulationTier passed through to run_loop

    Returns
    -------
    (final_personas, SocialSimulationTrace)
    """
    from src.social.trace_builder import TraceBuilder
    from src.social.validity import check_sv1, check_sv2, check_sv3, check_sv4, check_sv5

    total_turns = len(stimuli)
    if decision_scenarios is None:
        decision_scenarios = [""] * total_turns

    # Build persona lookup
    persona_map: dict[str, PersonaRecord] = {p.persona_id: p for p in personas}

    # TraceBuilder accumulates events across all turns
    trace_builder = TraceBuilder(
        session_id=session_id,
        cohort_id=cohort_id,
        level=level,
        topology=network.topology,
    )

    # Track decisions from last turn for next turn's influence generation
    prior_decisions: dict[str, str] = {}
    all_decisions: list[str] = []
    personas_before = list(personas)  # snapshot for SV5

    for turn_idx in range(total_turns):
        stimulus = stimuli[turn_idx]
        scenario = decision_scenarios[turn_idx] if turn_idx < len(decision_scenarios) else ""
        current_personas = list(persona_map.values())

        # Step 0: Generate influence events (empty at turn 0)
        social_events: list[SocialInfluenceEvent] = []
        if turn_idx > 0 and prior_decisions:
            social_events = generate_influence_events(
                current_personas, network, level, turn_idx, prior_decisions
            )

        # Step 1: Inject social stimuli
        for event in social_events:
            receiver = persona_map.get(event.receiver_id)
            if receiver is None:
                continue
            updated_receiver, loop_result = await run_loop(
                stimulus=event.synthetic_stimulus_text,
                persona=receiver,
                stimulus_id=f"social-{event.event_id}",
                llm_client=llm_client,
                tier=tier,
            )
            # Link observation_id back to event
            event_with_obs = event.model_copy(update={
                "resulting_observation_id": loop_result.observation.id
            })
            trace_builder.accumulate(event_with_obs)
            persona_map[event.receiver_id] = updated_receiver

        # Step 2: Primary stimulus for all personas
        prior_decisions = {}
        for pid, persona in list(persona_map.items()):
            updated_persona, loop_result = await run_loop(
                stimulus=stimulus,
                persona=persona,
                decision_scenario=scenario or None,
                llm_client=llm_client,
                tier=tier,
            )
            persona_map[pid] = updated_persona
            if loop_result.decision:
                decision_text = loop_result.decision.decision
                prior_decisions[pid] = decision_text
                all_decisions.append(decision_text)

    final_personas = list(persona_map.values())

    # Build trace
    trace = trace_builder.build(total_turns=total_turns)

    # Run validity gates
    all_events = trace_builder.all_events()
    validity_results = {
        "SV1": check_sv1(all_events).__dict__,
        "SV2": check_sv2(all_decisions, level).__dict__,
        "SV3": check_sv3(all_events).__dict__,
        "SV4": check_sv4([]).__dict__,  # no tendency shifts in SB scope
        "SV5": check_sv5(personas_before, final_personas).__dict__,
    }

    trace = trace.model_copy(update={"validity_gate_results": validity_results})
    return final_personas, trace
