# SPRINT 4 BRIEF — ANTIGRAVITY
**Role:** Cognitive Loop Quality Enforcer
**Sprint:** 4 — Cognitive Loop
**Spec check:** Master Spec §9 (Cognitive Loop), Validity Protocol BV1 (repeated-run stability), BV2 (memory-faithful recall)
**Previous rating:** 19/20

---

## Your Job This Sprint

You own the behavioural validation test harness for the cognitive loop. Two test files: BV1 (stability) and BV2 (memory fidelity). These are the first tests that run LLM calls — they are integration tests, not unit tests.

Two files.

---

## File 1: `tests/test_bv1_stability.py`

### BV1: Repeated-Run Stability

A valid cognitive persona should reach the same decision at least 2 out of 3 times when given the same stimulus and scenario under identical conditions.

```python
"""
BV1: Repeated-run stability test.

Runs the same decision scenario 3 times for the same persona.
Asserts: ≥ 2/3 runs produce the same final decision (normalized match).
"""
```

### Test Structure

```python
import pytest
import asyncio
from src.cognition.loop import run_loop, LoopResult
from src.cognition.decide import DecisionOutput
from tests.fixtures.synthetic_persona import make_synthetic_persona

@pytest.mark.asyncio
async def test_bv1_decision_stability():
    """
    Same persona, same stimulus, same decision scenario.
    Run 3 times. Assert >= 2/3 return the same decision (normalized).
    """
    persona = make_synthetic_persona()
    stimulus = "A new premium coffee brand is offering a free trial sample."
    scenario = "Do you sign up for the free trial?"

    decisions = []
    for _ in range(3):
        _, result = await run_loop(
            stimulus=stimulus,
            persona=persona,
            decision_scenario=scenario,
        )
        decisions.append(result.decision.decision.lower().strip())

    # Normalize: check if most common decision appears >= 2 times
    from collections import Counter
    most_common, count = Counter(decisions).most_common(1)[0]
    assert count >= 2, (
        f"BV1 FAIL: decisions were not stable. Got: {decisions}"
    )
```

### Decision Normalization

Two decisions are "the same" if:
- Exact string match (after lowercasing and stripping), OR
- Both start with "yes" or both start with "no"

Write a `_normalize_decision(text: str) -> str` helper:
- If text starts with "yes" → return "yes"
- If text starts with "no" → return "no"
- Else → return the first 30 characters of the text

Use `_normalize_decision` when comparing decisions in the stability check.

---

## File 2: `tests/test_bv2_memory_fidelity.py`

### BV2: Memory-Faithful Recall

A persona's decisions should reference its working memory. Specifically: a decision made after a persona has observed a relevant experience should cite or reflect that experience.

```python
"""
BV2: Memory-faithful recall test.

Seeds a persona's working memory with a high-importance observation.
Runs a decision scenario related to that observation.
Asserts: the reasoning trace mentions the seeded observation's content.
"""
```

### Test Structure

```python
import pytest
from src.cognition.loop import run_loop
from src.memory.working_memory import WorkingMemoryManager
from tests.fixtures.synthetic_persona import make_synthetic_persona
from tests.fixtures.synthetic_observation import make_synthetic_observation

@pytest.mark.asyncio
async def test_bv2_decision_references_memory():
    """
    Plant a high-importance observation in working memory.
    Run a decision relevant to that observation.
    Assert: reasoning_trace mentions a key word from the seeded observation.
    """
    persona = make_synthetic_persona()
    manager = WorkingMemoryManager()

    # Plant a relevant, high-importance observation
    seed_obs = make_synthetic_observation(
        content="I tried the premium brand last month and it was far too expensive for what it offered.",
        importance=9,
        emotional_valence=-0.6,
    )
    updated_working = manager.write_observation(persona.memory.working, seed_obs)
    from src.schema.persona import Memory
    persona = persona.model_copy(
        update={"memory": Memory(core=persona.memory.core, working=updated_working)}
    )

    # Run a related decision
    stimulus = "A premium coffee brand is offering a full-price subscription."
    scenario = "Do you subscribe to this premium coffee service?"

    _, result = await run_loop(
        stimulus=stimulus,
        persona=persona,
        decision_scenario=scenario,
    )

    # The reasoning trace should reference the seeded memory
    trace = result.decision.reasoning_trace.lower()
    assert any(
        word in trace
        for word in ["expensive", "last month", "premium", "offered"]
    ), (
        f"BV2 FAIL: reasoning_trace did not reference seeded memory.\n"
        f"Trace: {result.decision.reasoning_trace[:500]}"
    )
```

---

## File 3: `tests/fixtures/synthetic_persona.py`

Write a fixture module that creates a minimal but valid `PersonaRecord` for testing without LLM calls.

```python
from src.schema.persona import PersonaRecord, CoreMemory, WorkingMemory, Memory, SimulationState, ...

def make_synthetic_persona() -> PersonaRecord:
    """
    Returns a minimal but fully valid PersonaRecord for use in BV tests.
    Uses fixed values — not randomised — for test reproducibility.
    """
    ...
```

The persona should represent a specific, consistent character (e.g., "Priya Mehta, 34, Mumbai, budget-conscious, family-focused, peer trust dominant"). Enough detail that perceive/reflect/decide responses are plausible and consistent.

Use `WorkingMemory` with the seed observations from `bootstrap_seed_memories` if possible; otherwise construct manually with ≥ 3 observations.

---

## File 4: `tests/fixtures/synthetic_observation.py`

```python
from src.schema.persona import Observation
import uuid
from datetime import datetime, timezone

def make_synthetic_observation(
    content: str,
    importance: int = 5,
    emotional_valence: float = 0.0,
) -> Observation:
    now = datetime.now(timezone.utc)
    return Observation(
        id=str(uuid.uuid4()),
        timestamp=now,
        type="observation",
        content=content,
        importance=importance,
        emotional_valence=emotional_valence,
        source_stimulus_id=None,
        last_accessed=now,
    )
```

---

## Integration Contract

- **BV tests require a live Anthropic API key** in the environment. Add a pytest marker `@pytest.mark.integration` and a `pytest.ini` or `conftest.py` that skips integration tests unless `--integration` flag is passed.
- **Imports:** `from src.cognition.loop import run_loop`, `from src.cognition.decide import DecisionOutput`, `from src.memory.working_memory import WorkingMemoryManager`
- **Run command:** `python -m pytest tests/test_bv1_stability.py tests/test_bv2_memory_fidelity.py -v --integration`

---

## Constraints

- BV tests make real LLM calls — they are integration tests, not unit tests. Do not mock the LLM.
- Tests must be skippable without API key (use `pytest.mark.integration` + conftest skip).
- `make_synthetic_persona()` must produce a persona that passes G1–G3 (schema, hard constraints, tendency-attribute). Run `PersonaValidator().validate_all(persona)` inside the fixture and assert all pass.
- BV1 runs 3 iterations — this costs API calls. Keep stimulus/scenario short.
- BV2 asserts on a substring match — keep the seeded observation content concrete and specific.

---

## Outcome File

When done, write `sprints/outcome_antigravity.md` with:
1. Files created (line counts)
2. BV1 — describe the normalization strategy and threshold
3. BV2 — describe the seeded content and assertion strategy
4. Fixture — describe the synthetic persona used
5. Known gaps / test flakiness risks
