# SPRINT 11 BRIEF — GOOSE
**Role:** Memory Promotion Executor
**Sprint:** 11 — Production Entry Point + Technical Debt Clearance
**Spec ref:** Master Spec §8 (Memory Architecture), §14A S17 (promotion rules settled)
**Previous rating:** 20/20

---

## Context

The promotion gate (`can_promote()`) exists in `src/memory/reflection_store.py` and is functional. The cognitive loop in `src/cognition/loop.py` runs perceive → reflect → decide but never checks whether any observations have crossed the promotion threshold. Your job: write the promotion executor and wire it into the loop.

**Spec §14A S17 (settled):**
- Importance ≥ 9 AND citation_count ≥ 3 AND no_contradiction → promote to core memory
- Demographics are NEVER promoted
- Promotion moves the observation's `lasting_impact` text into `PersonaRecord.memory.core.life_context`

---

## File: `src/memory/promotion_executor.py`

```python
"""Memory promotion executor.

Sprint 11 — Production Entry Point + Technical Debt Clearance.
Spec §14A S17: Observations that cross the promotion threshold are
promoted to core memory (life_context field).

Rules (settled at §14A S17):
- importance >= 9
- citation_count >= 3 (cited by >= 3 distinct reflections)
- no_contradiction (caller flag — loop passes True for now; future: contradiction checker)
- Demographics are NEVER promoted

Promotion writes the observation text into persona.memory.core.life_context
(appended as a new sentence, deduplicated).
"""
from __future__ import annotations

from src.schema.persona import Observation, Reflection, WorkingMemory, CoreMemory


def get_promotable_observations(
    working: WorkingMemory,
) -> list[Observation]:
    """Return all observations from working memory that meet the promotion threshold.

    Checks:
    1. importance >= 9
    2. citation_count(obs.id, working.reflections) >= 3
    3. no_contradiction = True (structural — always True in current impl)

    Returns list of Observation objects (may be empty).
    """
    from src.memory.reflection_store import can_promote, citation_count

    promotable = []
    for obs in working.observations:
        citations = citation_count(obs.observation_id, working.reflections)
        if can_promote(
            importance=obs.importance,
            citation_count=citations,
            no_contradiction=True,  # S17: contradiction check is future work
        ):
            promotable.append(obs)
    return promotable


def promote_to_core(
    core: CoreMemory,
    observation: Observation,
) -> CoreMemory:
    """Promote a single observation to core memory.

    Appends the observation's content to core.life_context (deduplicated).
    Returns a new CoreMemory (model_copy — never mutates).

    Demographic observations are silently skipped (return core unchanged).
    """
    _DEMOGRAPHIC_KEYWORDS = {
        "age", "gender", "city", "location", "income", "education",
        "household", "employment", "marital", "name",
    }
    # Demographic guard: skip if any demographic keyword appears in the content
    content_lower = observation.content.lower()
    if any(kw in content_lower for kw in _DEMOGRAPHIC_KEYWORDS):
        return core  # Never promote demographics

    # Deduplicate: don't add if already in life_context
    if observation.content in (core.life_context or ""):
        return core

    new_context = (core.life_context or "").strip()
    if new_context:
        new_context = new_context + " " + observation.content
    else:
        new_context = observation.content

    return core.model_copy(update={"life_context": new_context})


def run_promotion_pass(
    working: WorkingMemory,
    core: CoreMemory,
) -> tuple[CoreMemory, list[str]]:
    """Run a full promotion pass over working memory.

    Finds all promotable observations, promotes each to core memory,
    and returns the updated CoreMemory + list of promoted observation_ids.

    Returns:
        (updated_core, promoted_ids) — promoted_ids is [] if nothing promoted.
    """
    promotable = get_promotable_observations(working)
    promoted_ids: list[str] = []

    for obs in promotable:
        updated = promote_to_core(core, obs)
        if updated is not core:  # Only count if something actually changed
            core = updated
            promoted_ids.append(obs.observation_id)

    return core, promoted_ids
```

---

## Wire into `src/cognition/loop.py`

After the reflection step (Step 4) and before Step 5 (decide), add a promotion pass:

Find the section after reflections are written to working memory:

```python
        reflected = True

    # ------------------------------------------------------------------
    # Step 5: Conditional decision
```

Insert between them:

```python
        reflected = True

    # ------------------------------------------------------------------
    # Step 4b: Memory promotion pass
    # ------------------------------------------------------------------
    # After reflecting, check if any observations meet the promotion threshold.
    # Promotable observations (importance >= 9, >= 3 citations) are written
    # to core memory. This is a no-op if no observations qualify.
    # Settled at §14A S17.
    promoted_ids: list[str] = []
    if working.reflections:  # Only run if there are reflections (citations needed)
        from src.memory.promotion_executor import run_promotion_pass
        new_core, promoted_ids = run_promotion_pass(working, persona.memory.core)
        if promoted_ids:
            # Update persona core memory — model_copy, never mutate
            new_mem_with_core = persona.memory.model_copy(update={"core": new_core})
            persona = persona.model_copy(update={"memory": new_mem_with_core})
            working = persona.memory.working  # re-sync working ref

    # ------------------------------------------------------------------
    # Step 5: Conditional decision
```

**Important:** The `promoted_ids` list is also passed through to `LoopResult`. Update the `LoopResult` dataclass and return statement accordingly.

Find the `LoopResult` dataclass at the top of `loop.py` and add:

```python
@dataclass
class LoopResult:
    ...
    promoted_memory_ids: list[str] = field(default_factory=list)
    """Observation IDs promoted to core memory this turn. Usually empty."""
```

And at the return:

```python
return LoopResult(
    ...
    promoted_memory_ids=promoted_ids,
)
```

---

## File: `tests/test_memory_promotion.py`

### Test 1: get_promotable_observations — empty working memory

```python
def test_get_promotable_empty():
    from src.memory.promotion_executor import get_promotable_observations
    from src.schema.persona import WorkingMemory, SimulationState

    working = WorkingMemory(
        observations=[],
        reflections=[],
        simulation_state=SimulationState(),
    )
    result = get_promotable_observations(working)
    assert result == []
```

### Test 2: get_promotable_observations — importance too low

```python
def test_get_promotable_importance_too_low():
    from src.memory.promotion_executor import get_promotable_observations
    from src.schema.persona import WorkingMemory, Observation, SimulationState
    import uuid

    obs = Observation(
        observation_id=str(uuid.uuid4()),
        content="I tried a new brand and liked it.",
        importance=8,  # Below threshold of 9
        valence=0.7,
        type="observation",
        turn=1,
    )
    working = WorkingMemory(
        observations=[obs],
        reflections=[],
        simulation_state=SimulationState(),
    )
    result = get_promotable_observations(working)
    assert result == []
```

### Test 3: get_promotable_observations — high importance but not enough citations

```python
def test_get_promotable_not_enough_citations():
    from src.memory.promotion_executor import get_promotable_observations
    from src.schema.persona import WorkingMemory, Observation, Reflection, SimulationState
    import uuid

    obs_id = str(uuid.uuid4())
    obs = Observation(
        observation_id=obs_id,
        content="This brand changed my mind about value.",
        importance=9,
        valence=0.8,
        type="observation",
        turn=1,
    )
    # Only 2 reflections cite it (need >= 3)
    reflections = [
        Reflection(
            reflection_id=str(uuid.uuid4()),
            content="I value quality more than I thought.",
            source_observation_ids=[obs_id],
            importance=8,
            type="reflection",
            turn=2,
        ),
        Reflection(
            reflection_id=str(uuid.uuid4()),
            content="My brand preferences are shifting.",
            source_observation_ids=[obs_id],
            importance=7,
            type="reflection",
            turn=3,
        ),
    ]
    working = WorkingMemory(
        observations=[obs],
        reflections=reflections,
        simulation_state=SimulationState(),
    )
    result = get_promotable_observations(working)
    assert result == []
```

### Test 4: promote_to_core — demographic content is skipped

```python
def test_promote_to_core_skips_demographic():
    from src.memory.promotion_executor import promote_to_core
    from src.schema.persona import Observation
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    import uuid

    persona = make_synthetic_persona()
    core = persona.memory.core
    original_context = core.life_context

    obs = Observation(
        observation_id=str(uuid.uuid4()),
        content="My age is 34 and I live in Mumbai.",  # Contains demographic keywords
        importance=10,
        valence=0.5,
        type="observation",
        turn=1,
    )
    result = promote_to_core(core, obs)
    assert result is core or result.life_context == original_context
```

### Test 5: run_promotion_pass — full pass with eligible observation

```python
def test_run_promotion_pass_promotes_eligible():
    from src.memory.promotion_executor import run_promotion_pass
    from src.schema.persona import WorkingMemory, Observation, Reflection, SimulationState
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    import uuid

    persona = make_synthetic_persona()
    core = persona.memory.core

    obs_id = str(uuid.uuid4())
    obs = Observation(
        observation_id=obs_id,
        content="This product consistently delivers on its promise.",
        importance=9,
        valence=0.9,
        type="observation",
        turn=1,
    )
    # 3 reflections citing the observation
    reflections = [
        Reflection(
            reflection_id=str(uuid.uuid4()),
            content=f"Reflection {j}",
            source_observation_ids=[obs_id],
            importance=8,
            type="reflection",
            turn=j + 2,
        )
        for j in range(3)
    ]
    working = WorkingMemory(
        observations=[obs],
        reflections=reflections,
        simulation_state=SimulationState(),
    )
    updated_core, promoted_ids = run_promotion_pass(working, core)
    assert obs_id in promoted_ids
    assert obs.content in (updated_core.life_context or "")
```

### Test 6: LoopResult has promoted_memory_ids field

```python
def test_loop_result_has_promoted_ids_field():
    from src.cognition.loop import LoopResult
    result = LoopResult(persona=None, decision_output=None, reflected=False)
    assert hasattr(result, "promoted_memory_ids")
    assert isinstance(result.promoted_memory_ids, list)
```

---

## Constraints

- No LLM calls.
- The promotion pass is a no-op when there are no reflections (fast path).
- `promote_to_core()` never mutates — always returns model_copy().
- Demographic guard uses keyword matching (not schema lookup) — keep it simple.
- 6 tests, all pass without `--integration`.
- Full suite must remain 155+ passed.

---

## Outcome File

Write `sprints/outcome_goose.md` with:
1. Files created / modified (line counts)
2. Promotion executor approach
3. Loop wiring — where in the cycle promotion runs
4. Test results (6/6)
5. Full suite result
6. Known gaps
