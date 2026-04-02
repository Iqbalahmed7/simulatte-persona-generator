# SPRINT 4 BRIEF — CURSOR
**Role:** Cognitive Loop — Orchestration
**Sprint:** 4 — Cognitive Loop
**Spec check:** Master Spec §9 (Cognitive Loop — all subsections)
**Previous rating:** 20/20

---

## Your Job This Sprint

You own `loop.py` — the orchestration layer that ties together perceive → remember → reflect → decide. This is the entry point for running a persona through any stimulus. It must manage the importance accumulator, handle conditional reflection, and write all outputs back to working memory.

One file.

---

## File: `src/cognition/loop.py`

### What It Does

Accepts a stimulus and a PersonaRecord. Runs the full cognitive cycle:
1. **Perceive** — LLM call via Codex's `perceive()`
2. **Remember** — write observation to working memory via Goose's `WorkingMemoryManager`
3. **Reflect (conditional)** — if accumulator > threshold, call Codex's `reflect()` with top-20 observations
4. **Decide (conditional)** — if this is a decision point, call Codex's `decide()` with top-10 relevant memories

Returns a `LoopResult` containing all outputs.

### Interface

```python
from dataclasses import dataclass, field
from src.schema.persona import PersonaRecord, Observation, Reflection
from src.cognition.decide import DecisionOutput

@dataclass
class LoopResult:
    observation: Observation                    # always present
    reflections: list[Reflection] = field(default_factory=list)   # present if reflect fired
    decision: DecisionOutput | None = None      # present if decide was called
    reflected: bool = False                     # True if reflection cycle ran
    decided: bool = False                       # True if decision cycle ran

async def run_loop(
    stimulus: str,
    persona: PersonaRecord,
    stimulus_id: str | None = None,
    decision_scenario: str | None = None,
) -> tuple[PersonaRecord, LoopResult]:
    """
    Run one full cognitive cycle for a persona encountering a stimulus.

    Steps:
    1. perceive(stimulus, persona) → Observation
    2. WorkingMemoryManager.write_observation(persona.memory.working, observation)
    3. WorkingMemoryManager.increment_accumulator(persona.memory.working, observation.importance)
    4. If WorkingMemoryManager.should_reflect(persona.memory.working):
       a. Retrieve top-20 observations
       b. reflect(observations, persona) → list[Reflection]
       c. WorkingMemoryManager.write_reflection(persona.memory.working, each reflection)
    5. If decision_scenario is provided:
       a. Retrieve top-10 memories relevant to decision_scenario
       b. decide(decision_scenario, memories, persona) → DecisionOutput
    6. Return (updated_persona, LoopResult)

    Returns a new PersonaRecord (immutable update via model_copy) with the
    updated working memory state.
    """
    ...
```

### Memory State Management

The `PersonaRecord` passed in must not be mutated in place. Use `model_copy(update={"memory": ...})` to return an updated copy with the new working memory state.

Working memory state changes in a single loop run:
1. One new `Observation` added to `working.observations`
2. `working.simulation_state.importance_accumulator` incremented by `observation.importance`
3. If reflection fires: 2-3 `Reflection` objects added to `working.reflections`; accumulator reset to 0.0
4. `working.simulation_state.reflection_count` incremented if reflection fired
5. `working.simulation_state.current_turn` incremented by 1

### Retrieval for Reflect

```python
# Top-20 observations for reflect (no relevance query — pass empty string or observation content)
top_20 = manager.retrieve_top_k(persona.memory.working, query="", k=20)
```

Pass the raw `persona.memory.working.observations` list (all of them) to `retrieve_top_k` with k=20. This uses recency + importance + relevance to select the most relevant recent ones.

### Retrieval for Decide

```python
# Top-10 memories relevant to the decision scenario
all_memories = [*persona.memory.working.observations, *persona.memory.working.reflections]
top_10 = retrieve_top_k(all_memories, query=decision_scenario, k=10)
```

Call `retrieve_top_k` from `src.memory.retrieval` directly (not the manager method) since we're passing mixed observations + reflections.

### Accumulator Logic

```
After perceive():
  manager.increment_accumulator(working, observation.importance)

After increment:
  if manager.should_reflect(working):
      → run reflection cycle
      → write_reflection() resets accumulator to 0 automatically
```

### Simulation State Update

```python
# At end of each run_loop call, increment current_turn
new_state = working.simulation_state.model_copy(
    update={"current_turn": working.simulation_state.current_turn + 1}
)
```

---

## Integration Contract

- **Imports from Codex:** `from src.cognition.perceive import perceive`, `from src.cognition.reflect import reflect`, `from src.cognition.decide import decide, DecisionOutput`
- **Imports from Goose (memory):** `from src.memory.working_memory import WorkingMemoryManager`
- **Imports from retrieval:** `from src.memory.retrieval import retrieve_top_k`
- **Imports from schema:** `from src.schema.persona import PersonaRecord, Observation, Reflection, Memory, WorkingMemory`

---

## Constraints

- `run_loop` is async — all LLM calls inside are awaited.
- Never mutate the PersonaRecord passed in — always return a new one.
- The accumulator is incremented on EVERY perceive call (even when reflect does not fire).
- Reflect fires when `should_reflect()` returns True; after reflection, accumulator is reset.
- `decision_scenario` is optional — most loop runs are stimulus-only (no decision).
- The loop does not validate the persona (that happens in identity_constructor.py). Trust the input.

---

## Outcome File

When done, write `sprints/outcome_cursor.md` with:
1. Files created (line counts)
2. Loop sequence — describe the exact order of operations
3. State management — how model_copy is used to produce the updated PersonaRecord
4. Reflect trigger — confirm it uses should_reflect() threshold exactly
5. Known gaps
