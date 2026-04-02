# SPRINT 4 BRIEF — CODEX
**Role:** Cognitive Loop — LLM Engines
**Sprint:** 4 — Cognitive Loop
**Spec check:** Master Spec §9 (Cognitive Loop — all subsections), §14A S1 (LLM is cognitive engine), Constitution P1, P2, P4
**Previous rating:** 19/20

---

## Your Job This Sprint

You own the three LLM-backed cognitive engines: `perceive.py`, `reflect.py`, and `decide.py`. These are the most important files in the whole system — the quality of `decide()` is the primary output of Simulatte.

Three files. All involve LLM calls.

---

## File 1: `src/cognition/perceive.py`

### What It Does

Takes a stimulus and a PersonaRecord. Returns an `Observation` by calling Haiku to score importance and valence through the persona's psychological lens.

### Interface

```python
from src.schema.persona import PersonaRecord, Observation

async def perceive(
    stimulus: str,
    persona: PersonaRecord,
    stimulus_id: str | None = None,
) -> Observation:
    """
    Process a stimulus through the persona's psychological lens.

    Makes one Haiku call. Returns an Observation with:
    - content: first-person description of what stood out
    - importance: int 1-10
    - emotional_valence: float -1.0 to 1.0
    - source_stimulus_id: stimulus_id if provided
    - type: "observation"
    - id: uuid4
    - timestamp: now (UTC)
    - last_accessed: now (UTC)
    """
    ...
```

### Prompt Structure (from §9)

```
System:
You are {persona.demographic_anchor.name}. {core_memory_block}

User:
You just encountered: {stimulus}

Given who you are, your values, and your past experiences:
1. What stands out to you about this?
2. How important is this to you? (1-10)
3. How does it make you feel? (-1.0 to 1.0, negative to positive)

Respond in first person, in character.
Reply in JSON: {"content": "...", "importance": N, "emotional_valence": F}
```

### Core Memory Block Format

```python
def _core_memory_block(persona: PersonaRecord) -> str:
    core = persona.memory.core
    return (
        f"You know yourself: {core.identity_statement} "
        f"What matters most to you: {', '.join(core.key_values[:3])}. "
        f"{core.tendency_summary}"
    )
```

### Model

`claude-haiku-4-5-20251001` — fast and cheap. This runs per stimulus × persona.

### Output Parsing

Parse JSON response. Clamp importance to [1, 10] (int). Clamp emotional_valence to [-1.0, 1.0]. On parse failure, retry once with a stricter prompt; on second failure raise `PerceiveError`.

### Critical Constraints

- Core memory MUST be in context (§14A S11). Never call without it.
- `tendency_summary` is injected as natural language only — never as numerical weights (P4).
- The persona does not passively receive stimuli — it amplifies signals that match its psychology.

---

## File 2: `src/cognition/reflect.py`

### What It Does

Takes a list of recent observations and a PersonaRecord. Returns 2-3 `Reflection` objects by calling Sonnet to synthesise higher-order insights.

### Interface

```python
from src.schema.persona import PersonaRecord, Reflection

async def reflect(
    observations: list[Observation],
    persona: PersonaRecord,
) -> list[Reflection]:
    """
    Synthesise 2-3 insights from recent observations.

    Makes one Sonnet call. Returns a list of Reflection objects.
    Each reflection MUST cite ≥ 2 source_observation_ids.
    Raises ReflectError if fewer than 5 observations provided (insufficient context).
    """
    ...
```

### Prompt Structure (from §9)

```
System:
You are {persona.demographic_anchor.name}. {core_memory_block}

User:
Here are your recent experiences:
{observations_block}

Step back and think about what patterns you're noticing.
What 2-3 insights or realizations are forming?
These should be about YOUR evolving views — not summaries of events.

For each insight, cite which specific experience IDs led to it.

Reply in JSON:
[
  {
    "content": "...",
    "importance": N,
    "emotional_valence": F,
    "source_observation_ids": ["id1", "id2"]
  },
  ...
]
```

### Observations Block Format

```python
def _observations_block(observations: list[Observation]) -> str:
    lines = []
    for obs in observations:
        lines.append(f"[{obs.id[:8]}] {obs.content} (importance: {obs.importance})")
    return "\n".join(lines)
```

Pass up to 20 observations, ordered chronologically (oldest first so the LLM sees the arc).

### Model

`claude-sonnet-4-6` — reflection needs depth.

### Output Parsing + Validation

Parse JSON list. For each item:
- `source_observation_ids` MUST have ≥ 2 entries — reject any with fewer (drop silently, log warning)
- `importance` clamped to [1, 10]
- `emotional_valence` clamped to [-1.0, 1.0]
- `content` must be non-empty string

Minimum return: 1 valid reflection. If all reflections fail validation, raise `ReflectError`.

### Critical Constraints

- Every reflection MUST cite ≥ 2 source_observation_ids (schema enforced + logic enforced).
- Core memory MUST be in context.
- Reflections must be about EVOLVING VIEWS, not summaries. The prompt enforces this but parse for it.

---

## File 3: `src/cognition/decide.py`

### What It Does

Takes a decision scenario, relevant memories, and a PersonaRecord. Returns a `DecisionOutput` (define this dataclass) by calling Sonnet with the 5-step reasoning chain.

### Interface

```python
from dataclasses import dataclass
from src.schema.persona import PersonaRecord, Observation, Reflection

@dataclass
class DecisionOutput:
    decision: str                    # The actual decision made
    confidence: int                  # 0-100
    reasoning_trace: str             # Full 5-step reasoning as text
    gut_reaction: str                # Step 1 extracted
    key_drivers: list[str]           # Top 2-3 factors
    objections: list[str]            # Hesitations / objections
    what_would_change_mind: str      # Override condition

async def decide(
    scenario: str,
    memories: list[Observation | Reflection],
    persona: PersonaRecord,
) -> DecisionOutput:
    """
    Run the 5-step reasoning chain for a decision.

    Makes one Sonnet call with max_tokens=2048.
    tendency_summary is ALWAYS in context.
    Core memory is ALWAYS in context.
    """
    ...
```

### Prompt Structure (from §9 — this is the most critical prompt in the system)

```
System:
You are {persona.demographic_anchor.name}. {core_memory_block}

{tendency_summary}

User:
You are now facing this decision:
{scenario}

Here are your relevant memories and experiences:
{memories_block}

Think through this decision step by step:

1. GUT REACTION: What is your immediate, instinctive response?
2. INFORMATION PROCESSING: What information matters most to you here? What are you paying attention to?
3. CONSTRAINT CHECK: Are there hard limits (budget, non-negotiables, absolute avoidances) that apply?
4. SOCIAL SIGNAL CHECK: What would the people you trust think? What would {primary_decision_partner} say?
5. FINAL DECISION: What do you actually decide to do, and why?

Also state:
- Your confidence in this decision (0-100)
- The top 2-3 factors that drove your decision
- Any objections or hesitations you have
- What would change your mind

Respond in first person, in character.

Reply in JSON:
{
  "gut_reaction": "...",
  "information_processing": "...",
  "constraint_check": "...",
  "social_signal_check": "...",
  "final_decision": "...",
  "confidence": N,
  "key_drivers": ["...", "..."],
  "objections": ["..."],
  "what_would_change_mind": "..."
}
```

### Memories Block Format

```python
def _memories_block(memories: list[Observation | Reflection]) -> str:
    lines = []
    for m in memories:
        tag = "Memory" if m.type == "observation" else "Insight"
        lines.append(f"- [{tag}] {m.content}")
    return "\n".join(lines)
```

Pass up to 10 memories, ordered by retrieval score (most relevant first).

### Core Memory Block for Decide

Richer than perceive — include immutable_constraints:

```python
def _decide_core_memory_block(persona: PersonaRecord) -> str:
    core = persona.memory.core
    constraints = core.immutable_constraints
    lines = [
        f"You know yourself: {core.identity_statement}",
        f"What matters most to you: {', '.join(core.key_values)}.",
    ]
    if constraints.budget_ceiling:
        lines.append(f"Budget reality: {constraints.budget_ceiling}.")
    if constraints.non_negotiables:
        lines.append(f"Non-negotiables: {'; '.join(constraints.non_negotiables)}.")
    if constraints.absolute_avoidances:
        lines.append(f"You never: {'; '.join(constraints.absolute_avoidances)}.")
    return " ".join(lines)
```

### Model

`claude-sonnet-4-6`, `max_tokens=2048` — the full reasoning chain needs space.

### Output Parsing

Parse JSON. Assemble `DecisionOutput`:
- `decision` = `final_decision` field
- `reasoning_trace` = all 5 steps joined as text
- `confidence` clamped to [0, 100] (int)
- `key_drivers` list — default to empty list if missing
- `objections` list — default to empty list if missing

On parse failure, retry once. On second failure raise `DecideError`.

### CRITICAL DRIFT CHECKS (apply in your own code review before submitting)

- [ ] `decide()` does NOT compute a probability before the LLM call (P4 violation if it does)
- [ ] `tendency_summary` is injected as natural language ONLY — never as numerical weights (P4)
- [ ] Core memory is in context for every LLM call
- [ ] The 5-step structure must always be in the prompt — never shortened or combined
- [ ] The primary_decision_partner is injected into step 4 from `core.relationship_map.primary_decision_partner`

---

## File 4: `src/cognition/__init__.py`

Create this file. Empty or minimal docstring. Required for the cognition package to be importable.

---

## Integration Contract

- **Imports Cursor's loop.py will use:** `from src.cognition.perceive import perceive`, `from src.cognition.reflect import reflect`, `from src.cognition.decide import decide, DecisionOutput`
- **Imports from schema:** `from src.schema.persona import PersonaRecord, Observation, Reflection`
- **Anthropic client:** Use `anthropic.AsyncAnthropic()` — same pattern as `life_story_generator.py` and `narrative_generator.py` from Sprint 2.
- **Model IDs:** Haiku = `"claude-haiku-4-5-20251001"`, Sonnet = `"claude-sonnet-4-6"`

---

## Error Classes

Define these in a `src/cognition/errors.py`:

```python
class PerceiveError(Exception): ...
class ReflectError(Exception): ...
class DecideError(Exception): ...
```

---

## Constraints

- All three prompts must include core memory in context. Non-negotiable.
- tendency_summary injected as-is (natural language paragraph) — no reformatting into scores.
- No pre-LLM probability computation.
- Retry logic: one retry on JSON parse failure, then raise.
- No mocking of LLM in the implementation (tests will mock — that's Antigravity's job).

---

## Outcome File

When done, write `sprints/outcome_codex.md` with:
1. Files created (line counts)
2. perceive() — show the exact prompt template used
3. reflect() — show the exact prompt template used
4. decide() — show the exact prompt template used
5. Drift checks — confirm all 3 critical checks pass
6. Known gaps
