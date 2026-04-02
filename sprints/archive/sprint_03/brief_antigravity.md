# SPRINT 3 BRIEF — ANTIGRAVITY
**Role:** Memory Quality Enforcer
**Sprint:** 3 — Memory Architecture
**Spec check:** Master Spec §8 (eviction, promotion, isolation), §12 (G10 — seed memory count), §14A S17 (promotion rules settled), S18 (experiment isolation settled)
**Previous rating:** 19/20 — G4/G5 clean. G5 keyword limitation documented. Good backward-compatible update.

---

## Your Job This Sprint

You own three things: the G10 validator (seed memory count), the eviction logic verification test, and the promotion rules guard. Plus creating the memory package init.

One file (extended validator) + one test file + one init file.

---

## File 1: `src/schema/validators.py` (extend existing)

Add `g10_seed_memory_count` to `PersonaValidator`. Update `validate_all` to optionally include it.

```python
def g10_seed_memory_count(
    self,
    memory: WorkingMemory,
) -> ValidationResult:
    """
    G10: ≥ 3 seed memories per persona after bootstrap.

    Checks:
    - memory.observations has ≥ 3 entries
    - All entries have valid id (non-empty string)
    - All entries have importance 1–10
    - All entries have emotional_valence -1.0 to 1.0
    - No duplicate ids
    """
    ...
```

Update `validate_all`:
```python
def validate_all(
    self,
    persona: PersonaRecord,
    include_narrative: bool = False,
    include_memory: bool = False,
) -> list[ValidationResult]:
    """
    G1, G2, G3 always.
    G4, G5 when include_narrative=True.
    G10 when include_memory=True (pass persona.memory.working).
    """
    ...
```

---

## File 2: `tests/test_memory.py`

Write a test suite that verifies the memory system without requiring LLM calls. Use synthetic data only.

```python
"""
Tests for Sprint 3 memory components.
No LLM calls. All synthetic data.
"""

def test_write_observation():
    """Write one observation, verify fields are set correctly."""
    ...

def test_write_reflection_requires_two_sources():
    """Verify ValueError raised when source_observation_ids < 2."""
    ...

def test_eviction_at_cap():
    """
    Write 1001 observations with varying importance.
    Verify eviction fires and len(observations) ≤ 1000 after write.
    """
    ...

def test_eviction_order():
    """
    Write observations with known importance values.
    Trigger eviction. Verify highest-importance entries are retained.
    """
    ...

def test_reset_clears_working_memory():
    """
    Write observations and reflections.
    Call reset(). Verify all working fields are empty.
    Verify reset is idempotent (call twice, same result).
    """
    ...

def test_retrieval_top_k():
    """
    Write 10 observations with varied importance and content.
    Query with a relevant term. Verify top-K are returned.
    Verify order is descending by score.
    """
    ...

def test_importance_accumulator():
    """
    Verify increment_accumulator adds correctly.
    Verify should_reflect returns False below threshold, True above.
    Verify write_reflection resets accumulator to 0.
    """
    ...

def test_g10_seed_memory_gate():
    """
    bootstrap_seed_memories returns WorkingMemory with ≥ 3 observations.
    g10_seed_memory_count passes on that memory.
    g10_seed_memory_count fails on empty WorkingMemory.
    """
    ...

def test_promotion_guard():
    """
    Verify that no observation with importance < 9 can be promoted.
    Verify that a reflection with < 3 source_observation_ids cannot be promoted.
    (Promotion function lives in reflection_store.py — Sprint 3 OpenCode territory,
    but the guard logic test should be here.)
    """
    ...
```

For `test_promotion_guard`: import and test `can_promote` from `src.memory.reflection_store` if it exists, otherwise skip with a clear skip message.

---

## File 3: `src/memory/__init__.py`

Create this file. Empty or minimal docstring only. Required for the memory package to be importable.

---

## Integration Contract

- **Imports from Goose:** `from src.memory.working_memory import WorkingMemoryManager`
- **Imports from OpenCode:** `from src.memory.seed_memory import bootstrap_seed_memories`
- **Imports from schema:** `from src.schema.persona import WorkingMemory, Observation, Reflection`
- **Tests are runnable with:** `python -m pytest tests/test_memory.py` (no LLM client needed)

---

## Constraints

- Tests must pass without any LLM client. Use synthetic Observation/Reflection objects only.
- G10 takes `WorkingMemory` directly (not `PersonaRecord`) — the gate is called after bootstrap, not during full persona validation.
- Promotion guard: promotion fires when `importance ≥ 9 AND citation_count ≥ 3 AND no_contradiction`. Never promotes demographics. Document these rules in the test.

---

## Outcome File

When done, write `sprints/outcome_antigravity.md` with:
1. Files created/modified
2. G10 implementation — what exactly is checked
3. Test results — which tests pass, which are skipped and why
4. Promotion guard test — confirmed rules match §14A S17
5. Known gaps
