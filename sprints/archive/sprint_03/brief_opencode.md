# SPRINT 3 BRIEF — OPENCODE
**Role:** Core Memory + Seed Memory Engineer
**Sprint:** 3 — Memory Architecture
**Spec check:** Master Spec §8 (Memory Architecture), §5 (CoreMemory schema), §14A S3 (core/working split), S17 (promotion rules settled)
**Previous rating:** 16/20 — Good domain templates. Missing __init__.py patched. Zero base taxonomy overlap.

---

## Your Job This Sprint

You own core memory assembly and seed memory bootstrap. Core memory is the immutable identity layer — assembled once during persona creation and never modified during simulation. Seed memories are the first working memory observations bootstrapped from core memory at the start of any simulation.

Two files.

---

## File 1: `src/memory/core_memory.py`

### What It Does

Takes a completed `PersonaRecord` and returns a fully assembled `CoreMemory`. This is the definitive assembly logic — `identity_constructor.py` (Cursor Sprint 2) has a simpler stub; this file is the authoritative version.

### Interface

```python
from src.schema.persona import PersonaRecord, CoreMemory

def assemble_core_memory(persona: PersonaRecord) -> CoreMemory:
    """
    Assembles CoreMemory from a validated PersonaRecord.
    All fields are derived deterministically — no LLM calls.

    Called once during persona creation. The result is stored in
    PersonaRecord.memory.core and is immutable thereafter.
    """
    ...
```

### Field Assembly Rules

**`identity_statement`** — str (25 words, first person)

Take the first 25 words of `persona.narrative.first_person`. If fewer than 25 words, use the full text. Strip trailing punctuation and ensure it ends with a period.

**`key_values`** — list[str] (3–5 items)

Derive from attributes:
1. Always include: human-readable label of `primary_value_driver` anchor (e.g., "Quality over price")
2. Map `tension_seed` to a value statement (e.g., "aspiration_vs_constraint" → "Driven by aspiration despite real constraints")
3. Add 1–3 more from the top-scoring values category attributes (highest absolute deviation from 0.5)
4. Clamp to 5 maximum.

**`life_defining_events`** — list[LifeDefiningEvent]

Convert each `LifeStory` in `persona.life_stories` to a `LifeDefiningEvent`:
- `age_when`: parse from `life_story.when` field (e.g., "age 24" → 24; "at 30" → 30; YYYY → YYYY - demographic_anchor.age + current_age_approx; fallback: 0)
- `event`: copy from `life_story.event`
- `lasting_impact`: copy from `life_story.lasting_impact`

**`relationship_map`** — RelationshipMap

```python
RelationshipMap(
    primary_decision_partner = _derive_decision_partner(persona),
    key_influencers          = _derive_key_influencers(persona),
    trust_network            = _derive_trust_network(persona),
)
```

Derivation rules:
- `primary_decision_partner`: based on `household.structure` + `trust_orientation_primary`:
  - joint/nuclear + family trust → "Spouse/partner"
  - single-parent → "Children / close family"
  - couple-no-kids → "Partner"
  - self trust → "Self"
  - peer trust → "Close friends"
  - authority trust → "Trusted expert/advisor"
- `key_influencers`: 2–3 entries derived from trust orientation weights (top 2 non-self sources by weight, named generically: "Expert reviews", "Peer recommendations", "Social community", etc.)
- `trust_network`: 2–3 entries derived from social attributes (peer_influence_strength, online_community_trust)

**`immutable_constraints`** — ImmutableConstraints

```python
ImmutableConstraints(
    budget_ceiling      = _derive_budget_ceiling(persona),
    non_negotiables     = _derive_non_negotiables(persona),
    absolute_avoidances = _derive_absolute_avoidances(persona),
)
```

Derivation rules:
- `budget_ceiling`: if `economic_constraint_level > 0.7` → `f"Tight budget — {income_bracket} income"`, else None
- `non_negotiables`: items from `key_tensions` that represent hard limits (look for "vs_budget", "vs_constraint" patterns); always include at least 1 if key_tensions is non-empty
- `absolute_avoidances`: derive from `absolute_avoidances` in existing immutable_constraints if present, else empty list (this field is populated from narrative context in deeper modes)

**`tendency_summary`** — str

Copy directly from `persona.behavioural_tendencies.reasoning_prompt`. This is the natural-language paragraph injected into every LLM reasoning call.

---

## File 2: `src/memory/seed_memory.py`

### What It Does

Bootstraps the initial working memory observations from core memory. Every persona starts simulation with ≥ 3 seed memories (G10 gate). These represent core identity beliefs that are "always present" in the persona's working memory.

### Interface

```python
from src.schema.persona import WorkingMemory, CoreMemory, Observation
from src.memory.working_memory import WorkingMemoryManager

def bootstrap_seed_memories(
    core_memory: CoreMemory,
    persona_name: str,
) -> WorkingMemory:
    """
    Creates a fresh WorkingMemory pre-populated with ≥ 3 seed observations
    derived from core memory.

    Seed observations represent:
    1. Identity anchor — derived from identity_statement
    2. Primary value — derived from key_values[0]
    3. Key tension — derived from core_memory (via tendency_summary or key_tensions)
    4+ Optional: one per life_defining_event (up to 3 additional)

    Returns a WorkingMemory ready for simulation.
    G10 gate: must have ≥ 3 observations after bootstrap.
    """
    ...

def _make_seed_observation(
    content: str,
    importance: int = 8,      # seed memories are high importance
    emotional_valence: float = 0.0,
) -> Observation:
    """
    Creates a seed Observation with fixed attributes:
    - id: uuid4
    - timestamp: now (UTC)
    - type: "observation"
    - source_stimulus_id: None (seed memories have no stimulus)
    - last_accessed: now (UTC)
    """
    ...
```

### Seed Memory Content Templates

```python
# Seed 1 — Identity anchor
f"I know myself: {core_memory.identity_statement}"

# Seed 2 — Primary value
f"What matters most to me: {core_memory.key_values[0]}"

# Seed 3 — Core tension
# Extract from tendency_summary or key_tensions — take first sentence of tendency_summary
f"Something I always navigate: {first_sentence_of_tendency_summary}"

# Seeds 4+ — Life events (one per life_defining_event, up to 3)
f"A defining moment in my life: {event.event} — {event.lasting_impact}"
```

All seed observations get `importance=8` (high importance, just below promotion threshold of 9).

---

## Integration Contract

- **`assemble_core_memory`** replaces `_assemble_core_memory()` in `identity_constructor.py`. Cursor's stub should be updated to call `from src.memory.core_memory import assemble_core_memory` at Step 6.
- **`bootstrap_seed_memories`** is called at simulation start (Sprint 6/7 modality layer), not during persona creation.
- **Exports:** `assemble_core_memory` from `src.memory.core_memory`, `bootstrap_seed_memories` from `src.memory.seed_memory`
- **No LLM calls** in either file.
- Create `src/memory/__init__.py` (empty).

---

## Constraints

- Core memory is assembled once and never modified. These files only assemble — they never update an existing CoreMemory.
- `bootstrap_seed_memories` creates a fresh `WorkingMemory` — it never modifies an existing one.
- G10 gate must pass: ≥ 3 observations after bootstrap. If derivation produces fewer, add fallback seeds until count ≥ 3.
- Seed memories are `type="observation"` (not reflection). Reflections require ≥ 2 source_observation_ids.

---

## Outcome File

When done, write `sprints/outcome_opencode.md` with:
1. Files created (line counts)
2. `key_values` derivation — show the mapping logic for all `primary_value_driver` options
3. `relationship_map` — show derivation rules applied
4. Seed memory count — confirm G10 is always satisfied (show minimum case)
5. Any derivation rules you were uncertain about
6. Known gaps
