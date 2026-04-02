# SPRINT 4 BRIEF — GOOSE
**Role:** Memory Integration inside Cognitive Loop
**Sprint:** 4 — Cognitive Loop
**Spec check:** Master Spec §8 (Memory Architecture — integration points), §9 (Cognitive Loop — REMEMBER step)
**Previous rating:** 20/20

---

## Your Job This Sprint

You own the memory integration layer that sits between the cognitive loop and the working memory system. Your job is to ensure `WorkingMemoryManager` is correctly usable by `loop.py`, and to deliver the missing `reflection_store.py` from Sprint 3.

This sprint you will:
1. Verify `WorkingMemoryManager` has everything `loop.py` needs — fill gaps if any
2. Write `src/memory/reflection_store.py` — the missing file from Sprint 3

---

## File 1: `src/memory/working_memory.py` (verify + extend if needed)

Review Cursor's `loop.py` brief (Sprint 4). The loop requires these operations on `WorkingMemoryManager`:

- `write_observation(working: WorkingMemory, obs: Observation) -> WorkingMemory`
- `write_reflection(working: WorkingMemory, ref: Reflection) -> WorkingMemory`
- `retrieve_top_k(working: WorkingMemory, query: str, k: int) -> list[Observation | Reflection]`
- `increment_accumulator(working: WorkingMemory, amount: float) -> WorkingMemory`
- `should_reflect(working: WorkingMemory) -> bool`

Verify all five exist and match these exact signatures. If any method currently mutates the `WorkingMemory` object in place rather than returning a new `WorkingMemory`, add a return value so the loop can use the immutable-update pattern via `model_copy`. The loop requires each operation to return the updated `WorkingMemory`.

If all five methods already exist with correct signatures and return types, document this in your outcome file and make no changes.

---

## File 2: `src/memory/reflection_store.py`

This file was in the Sprint 3 deliverables list but was not delivered. Antigravity's `test_promotion_guard` test is blocked, waiting for `can_promote` from this file.

### Interface

```python
from src.schema.persona import Reflection

def can_promote(
    importance: int,
    citation_count: int,
    no_contradiction: bool,
) -> bool:
    """
    Promotion gate: returns True only when ALL three conditions are met:
    1. importance >= 9        (just above seed memory default of 8)
    2. citation_count >= 3    (cited by >= 3 distinct reflections)
    3. no_contradiction       (no contradicting entry in memory)

    Demographics are never promoted — this gate is called only for
    observations and reflections, never for core memory fields.

    Rules settled at §14A S17.
    """
    return importance >= 9 and citation_count >= 3 and no_contradiction


def citation_count(
    observation_id: str,
    reflections: list[Reflection],
) -> int:
    """
    Count how many reflections cite a given observation_id.
    """
    return sum(
        1 for r in reflections
        if observation_id in r.source_observation_ids
    )
```

---

## Integration Contract

- **Antigravity's blocked test** (`test_promotion_guard`) imports `from src.memory.reflection_store import can_promote` — exact function name and module path.
- **WorkingMemoryManager** — Cursor's `loop.py` imports `from src.memory.working_memory import WorkingMemoryManager`. All five required methods must be present on the class.

---

## Constraints

- `can_promote` is a pure function — no state, no LLM calls, no side effects.
- `citation_count` is also pure — it does not modify any objects.
- Promotion threshold: importance **>= 9**, citation_count **>= 3**, no_contradiction **True** (all three required simultaneously).
- Do not change the `WorkingMemoryManager` public interface unless a method is missing or the signature is wrong.

---

## Outcome File

When done, write `sprints/outcome_goose.md` with:
1. Files created/modified
2. WorkingMemoryManager gap analysis — which methods were already correct, which needed changes
3. `can_promote` — confirm the exact rule triple
4. Known gaps
