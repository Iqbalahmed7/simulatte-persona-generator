# SPRINT 7 BRIEF — CURSOR
**Role:** Simulation Runner
**Sprint:** 7 — Temporal Simulation Modality
**Spec check:** Master Spec §1 (temporal simulation), §9 (full cognitive loop), §14A S18 (experiment isolation)
**Previous rating:** 19/20

---

## Your Job This Sprint

One file: `src/modalities/simulation.py`. The temporal simulation runner takes an `ExperimentSession` (with stimuli + optional decision scenarios), runs each stimulus through `run_loop()`, and returns a `SimulationResult` with per-turn log.

---

## File: `src/modalities/simulation.py`

### What It Does

Temporal simulation: core + working memory. Memory accumulates across turns. Each stimulus is processed through the full cognitive loop (perceive → remember → reflect → decide).

### Interface

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from src.schema.persona import PersonaRecord
from src.cognition.loop import LoopResult
from src.experiment.session import ExperimentSession

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
    ...
```

### Concurrency Model

```python
# For each turn (stimulus), run all personas in parallel:
for i, stimulus in enumerate(session.stimuli):
    scenario = session.decision_scenarios[i] if i < len(session.decision_scenarios) else None
    tasks = [_run_persona_turn(stimulus, scenario, persona_states[pid]) for pid in persona_ids]
    turn_results = await asyncio.gather(*tasks)
    # Update persona states for next turn
```

### Persona Source

```python
# Get starting personas from session
if session.persona:
    personas = [session.persona]
elif session.cohort:
    personas = session.cohort.personas
```

### TurnLog Population

```python
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
```

---

## Constraints

- Working memory accumulates across turns — do NOT reset between stimuli.
- Process stimuli sequentially within each persona (order matters for memory).
- Run personas concurrently per turn (independent personas).
- `session.cohort.personas` — access the persona list via this attribute.

---

## Outcome File

When done, write `sprints/outcome_cursor.md` with:
1. File created (line count)
2. Concurrency model — per-turn gather, sequential within persona
3. Memory handling — confirm no reset between turns
4. Known gaps
