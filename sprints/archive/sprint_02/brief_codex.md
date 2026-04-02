# SPRINT 2 BRIEF — CODEX
**Role:** Narrative + Life Story Engineer
**Sprint:** 2 — Identity Constructor
**Spec check:** Master Spec §5 (life_stories, narrative schemas), §6 (narrative constrained by attributes), §14A S14 (narrative constrained by attributes — settled)
**Previous rating:** 20/20 — Perfect taxonomy. All exports correct. KNOWN_CORRELATIONS_DICT patch applied cleanly.

---

## Your Job This Sprint

You own two LLM-calling components: the life story generator and the narrative generator. Both produce human-readable content that must be consistent with the filled attribute profile — not generic LLM output.

Two files.

---

## File 1: `src/generation/life_story_generator.py`

### What It Does

Given a `DemographicAnchor` and the filled `attributes` dict, generates 2–3 life story vignettes that are consistent with the persona's psychology, values, and life stage. These become `PersonaRecord.life_stories`.

### Interface

```python
from src.schema.persona import DemographicAnchor, LifeStory, Attribute

class LifeStoryGenerator:
    def __init__(self, llm_client, model: str = "claude-sonnet-4-6"):
        self.llm = llm_client
        self.model = model

    async def generate(
        self,
        demographic_anchor: DemographicAnchor,
        attributes: dict[str, dict[str, Attribute]],
        n_stories: int = 3,
    ) -> list[LifeStory]:
        """
        Generates n_stories (2 or 3) life story vignettes.
        Each story must be grounded in the persona's attribute profile.
        Returns list of LifeStory objects.
        """
        ...
```

### The LLM Prompt

Single call generating all stories at once (more coherent than per-story calls):

```
SYSTEM:
You are constructing life story vignettes for a synthetic persona.
Each story must emerge naturally from this specific person's psychology and values.
Do not invent generic life events — derive each story from the attribute profile provided.

USER:
Demographics:
- Age: [age], Gender: [gender], Location: [city], [urban_tier]
- Life stage: [life_stage], Education: [education], Employment: [employment]
- Household: [structure], size [size], income: [income_bracket]

Key attribute profile (decision-relevant):
- Personality type: [personality_type value]
- Risk tolerance: [value] ([label])
- Primary value driver: [primary_value_driver value]
- Economic constraint level: [economic_constraint_level value] ([label])
- Tension seed: [tension_seed value]
- [Top 10 highest-signal attributes by category, name: value (label)]

Generate exactly [n_stories] life story vignettes. Each story must:
1. Have a specific, named event (not "went through a difficult time" — something precise)
2. Occur at a realistic age for this person
3. Have a lasting impact that explains one of their current attribute values
4. Be 2–3 sentences maximum

Return JSON only:
[
  {"title": "...", "when": "age 24", "event": "...", "lasting_impact": "..."},
  ...
]
```

### Attribute Selection for Context

Do not dump all 150+ attributes into the prompt. Select the 10 highest-signal attributes for the prompt using this priority:
1. All 8 anchor attributes (always included)
2. The 2 non-anchor attributes with the most extreme values (furthest from 0.5)

### Validation

After parsing the LLM response, validate:
- Exactly 2–3 stories returned (if fewer, retry once; if still fewer, pad with a fallback)
- Each story has non-empty `title`, `when`, `event`, `lasting_impact`
- Parse `when` field: acceptable formats are "age NN", "at NN", "NN years old", or a year (YYYY)

---

## File 2: `src/generation/narrative_generator.py`

### What It Does

Given the full persona (attributes + derived insights + life stories + tendencies), generates the first-person and third-person narratives that become `PersonaRecord.narrative`.

### Interface

```python
from src.schema.persona import (
    DemographicAnchor, Attribute, DerivedInsights,
    BehaviouralTendencies, LifeStory, Narrative
)

class NarrativeGenerator:
    def __init__(self, llm_client, model: str = "claude-sonnet-4-6"):
        self.llm = llm_client
        self.model = model

    async def generate(
        self,
        demographic_anchor: DemographicAnchor,
        attributes: dict[str, dict[str, Attribute]],
        derived_insights: DerivedInsights,
        life_stories: list[LifeStory],
        behavioural_tendencies: BehaviouralTendencies,
    ) -> Narrative:
        """
        Generates first_person (100-150 words) and third_person (150-200 words) narratives.
        Also derives display_name from demographic_anchor.name.
        Returns a Narrative object.
        """
        ...
```

### The LLM Prompt

Two calls — one per narrative type. Keep them separate so each can be word-count controlled.

**First-person prompt:**
```
SYSTEM:
Write in first person as this persona. Be specific to their profile — avoid generic statements.
Capture their internal tension, their primary value driver, and one life story reference.
Target exactly 100-150 words.

USER:
Persona profile:
- [Demographics summary — 1 line]
- Decision style: [decision_style] ([decision_style_score:.2f})
- Primary value: [primary_value_orientation]
- Key tension: [key_tensions[0]]
- Trust anchor: [trust_anchor]
- Life story reference: "[life_stories[0].title] — [life_stories[0].lasting_impact]"
- Tendency summary: [behavioural_tendencies.reasoning_prompt]

Write the first-person narrative. Return plain text only, no JSON.
```

**Third-person prompt:**
```
SYSTEM:
Write in third person about this persona as a researcher describing them.
Be analytical — explain why they behave as they do, not just what they do.
Target exactly 150-200 words.

USER:
[Same profile as first-person prompt]
Name: [demographic_anchor.name]

Write the third-person narrative. Return plain text only, no JSON.
```

### Word Count Enforcement

After generation, count words. If outside bounds, retry once with the bounds explicitly stated. If still outside bounds, accept the output — do not truncate (truncation creates incoherent text).

### display_name

Derive from `demographic_anchor.name`:
- If name has multiple words (first + last), use first name only
- If single word, use as-is

---

## Integration Contract

- **Imports from Cursor:** `ICPSpec` is in `src.generation.identity_constructor`
- **Called by Cursor:** `LifeStoryGenerator.generate()` at Step 3, `NarrativeGenerator.generate()` at Step 5
- **Exports:** `LifeStoryGenerator`, `NarrativeGenerator`

---

## Constraints

- **Narrative must not contradict attributes.** Per §14A S14 (settled): if `brand_loyalty > 0.8`, the narrative must not describe the persona as "brand agnostic." If `switching_propensity.band == "low"`, narrative must not describe them as adventurous with brands.
- **Life stories must trace to attributes.** Each `lasting_impact` must explain why an attribute value is what it is.
- **No invented demographics.** Do not add age, location, income, or any demographic detail not present in `DemographicAnchor`.
- **No domain-specific content.** Life stories and narrative are domain-agnostic (they describe the person, not their relationship to a product category).

---

## Outcome File

When done, write `sprints/outcome_codex.md` (overwrite the Sprint 1 version) with:
1. Files created (line counts)
2. Attribute selection logic for life story prompts — list the 10 attributes selected and why
3. Word count enforcement: how you handled out-of-bounds cases
4. Any prompt design decisions not explicitly specified
5. Known gaps or failure modes
