# Sprint 4 Outcome — Cursor (Cognitive Loop Orchestration)

## 1. Files Created

| File | Lines |
|------|-------|
| `src/cognition/loop.py` | 156 |

---

## 2. Loop Sequence — Exact Order of Operations

Each `run_loop()` call proceeds in this order:

1. **Perceive** — `await perceive(stimulus, persona, stimulus_id=stimulus_id)` returns an `Observation` with content, importance (1–10), emotional_valence (-1.0–1.0), and source_stimulus_id.

2. **Write observation** — `manager.write_observation(working, content, importance, emotional_valence, source_stimulus_id)` appends the observation to `working.observations` (with auto-eviction if > 1000 entries). Returns an updated `WorkingMemory` and the persisted `Observation` (the returned `Observation` is discarded here; the one from `perceive()` is kept for the `LoopResult`).

3. **Increment accumulator** — `manager.increment_accumulator(working, observation.importance)` adds `observation.importance` to `simulation_state.importance_accumulator`. Runs on every perceive call, regardless of whether reflection fires.

4. **Conditional reflection** — `manager.should_reflect(working)` is checked. If `True`:
   - `manager.retrieve_top_k(working, query="", k=20)` fetches the top-20 entries by recency + importance + relevance.
   - Only `Observation` entries are passed to `reflect()` (reflections are filtered out).
   - `await reflect(obs_for_reflect, persona)` returns 2–3 `Reflection` objects.
   - Each reflection is written via `manager.write_reflection(working, ...)`, which appends it to `working.reflections`, increments `reflection_count`, and resets `importance_accumulator` to 0.0.

5. **Conditional decision** — if `decision_scenario` is not `None`:
   - `all_memories = [*working.observations, *working.reflections]` — combines both types.
   - `retrieve_top_k(all_memories, query=decision_scenario, k=10)` — calls the module-level function from `src.memory.retrieval` directly (not the manager method) to handle mixed types, as specified.
   - `await decide(decision_scenario, top_10, persona)` returns a `DecisionOutput`.

6. **Increment current_turn** — `simulation_state.current_turn` is incremented by 1 via `model_copy`.

7. **Return** — `(updated_persona, LoopResult)` where `updated_persona` is a new `PersonaRecord` with the final working memory state.

---

## 3. State Management — How `model_copy` Produces the Updated PersonaRecord

The input `PersonaRecord` is never mutated. Immutability is maintained throughout via a chain of `model_copy(update={...})` calls:

```
working = manager.write_observation(working, ...)      # returns new WorkingMemory
working = manager.increment_accumulator(working, ...)  # returns new WorkingMemory
# (if reflect fires)
working, _ = manager.write_reflection(working, ...)    # returns new WorkingMemory
# (end of run)
new_state = working.simulation_state.model_copy(
    update={"current_turn": working.simulation_state.current_turn + 1}
)
working = working.model_copy(update={"simulation_state": new_state})
new_memory = persona.memory.model_copy(update={"working": working})
updated_persona = persona.model_copy(update={"memory": new_memory})
```

Each `model_copy` produces a structurally independent copy. The `working` variable is reassigned at each step; no reference to the original working memory object survives into the return value.

---

## 4. Reflect Trigger — Confirms `should_reflect()` Threshold Exactly

Reflection fires when `manager.should_reflect(working)` returns `True`. The `WorkingMemoryManager.should_reflect()` method (in `src/memory/working_memory.py`) checks:

```python
return memory.simulation_state.importance_accumulator > threshold  # default threshold=50.0
```

`loop.py` calls this with no override — it uses the default threshold of 50.0 exactly as specified. The accumulator is incremented on every perceive call; when the cumulative importance exceeds 50.0, reflection fires. After reflection, `write_reflection()` resets the accumulator to 0.0 automatically.

---

## 5. Known Gaps

**Gap 1: perceive.py, reflect.py, decide.py do not yet exist.** `loop.py` imports from `src.cognition.perceive`, `src.cognition.reflect`, and `src.cognition.decide`. These are Codex's deliverables for this sprint. Until they are present, `loop.py` cannot be executed end-to-end. The import structure and call signatures match the integration contract exactly.

**Gap 2: obs_for_reflect may have fewer than 5 entries.** `reflect()` raises `ReflectError` if fewer than 5 observations are provided (per Codex's brief). `loop.py` does not pre-check this count before calling reflect. If the accumulator threshold is hit very early (e.g. a single stimulus with importance=10 raising accumulator to 10 and re-threshold at 50 never fires — but edge cases exist), the reflect call would raise. A guard could be added but would deviate from the spec's accumulator-only trigger logic.

**Gap 3: The Observation returned from write_observation is discarded.** `write_observation()` returns `(updated_memory, new_observation)`. The new observation is a freshly created Pydantic object with its own UUID and timestamp — not the same object returned by `perceive()`. `loop.py` uses the `perceive()` observation in the `LoopResult`. This is consistent with the brief's data flow but means the `LoopResult.observation` is the pre-write object, not the persisted copy. In practice they are identical in content.

**Gap 4: No timeout or circuit-breaker on LLM calls.** The three awaited LLM calls (perceive, reflect, decide) have no timeout wrapper in `loop.py`. Long-running stimuli batches could block indefinitely if the Anthropic API is slow. Production use should wrap each await in `asyncio.wait_for()` with an appropriate timeout.
