# SPRINT 1 BRIEF — GOOSE
**Role:** Generation Engine
**Sprint:** 1 — Foundation: Schema + Taxonomy
**Spec check:** Master Spec §6 (Progressive Conditioning, Filling Order), §14A S4 (anchor-first), S6 (progressive filling)
**Previous rating:** n/a (Sprint 1)

---

## Your Job This Sprint

You build the attribute filler — the engine that turns a demographic anchor into a fully populated attribute profile. This is the progressive conditional filling mechanism from Master Spec §6.

One file. It imports from Cursor (schema) and Codex (taxonomy).

---

## File: `src/generation/attribute_filler.py`

### What It Does

Given a `DemographicAnchor` and a list of `AttributeDefinition` objects (from the taxonomy), it fills all attributes one by one, each conditioned on all previously assigned attributes. The result is a `dict[str, dict[str, Attribute]]` (the `attributes` field of `PersonaRecord`).

### The Filling Algorithm

```
Step 1: Fill 8 anchor attributes (in anchor_order 1–8)
Step 2: Fill user-specified anchor traits from ICP Spec (if any)
Step 3: Fill all remaining extended attributes (progressively, conditioned on all prior)
Step 4: Fill domain-specific attributes last (conditioned on full profile)
```

### Interface

```python
from src.schema.persona import DemographicAnchor, Attribute
from src.taxonomy.base_taxonomy import AttributeDefinition

class AttributeFiller:
    def __init__(self, llm_client, model: str = "claude-sonnet-4-6"):
        self.llm = llm_client
        self.model = model

    def fill(
        self,
        demographic_anchor: DemographicAnchor,
        taxonomy: list[AttributeDefinition],
        anchor_overrides: dict[str, any] | None = None,  # from ICP Spec
    ) -> dict[str, dict[str, Attribute]]:
        """
        Returns attributes dict: {category: {attr_name: Attribute}}
        """
        ...

    def _fill_single_attribute(
        self,
        attr_def: AttributeDefinition,
        profile_so_far: dict,          # all assigned attributes + demographics
        demographic_anchor: DemographicAnchor,
    ) -> Attribute:
        """
        LLM call: given what we know so far, assign this attribute.
        Returns an Attribute with value, type, label, source="sampled".
        """
        ...
```

### The LLM Call for Each Attribute

Each attribute is filled with a single LLM call. Keep prompts tight — this runs once per attribute per persona (~150 calls per persona, so efficiency matters).

```
SYSTEM:
You are assigning a single psychological or behavioural attribute for a persona.
Be realistic, specific, and consistent with everything already assigned.

USER:
Persona so far:
- Demographics: [age], [gender], [location.urban_tier], [income_bracket], [life_stage]
- Attributes assigned so far: [last 15 assigned attributes as name: value pairs]
  (Note: show only the last 15 to keep context tight)

Assign this attribute:
Name: [attr_def.name]
Category: [attr_def.category]
Description: [attr_def.description]
Type: [continuous (0.0-1.0) | categorical (options: [options])]
Population prior: [prior if available]

[For continuous]: Return a single float between 0.0 and 1.0.
[For categorical]: Return one of: [options]

Return JSON only: {"value": ..., "label": "..."}
The label should be a human-readable interpretation (e.g., "high", "moderate", or the category value itself).
```

### Handling Correlation Constraints

After each attribute is assigned, check `KNOWN_CORRELATIONS` from the taxonomy:

```python
def _apply_correlation_check(
    self,
    newly_assigned: str,
    newly_assigned_value: float,
    profile_so_far: dict,
) -> dict:
    """
    For any correlation pair involving newly_assigned attr,
    if the previously assigned end of the pair violates direction,
    flag it. Do not silently correct — flag with source="inferred"
    and document the override.
    """
    ...
```

This is a soft check. The attribute filler can note the tension but should not silently change already-assigned values. The constraint checker (Antigravity) handles hard violations separately.

### Filling Order Logic

```python
def _get_fill_order(
    self,
    taxonomy: list[AttributeDefinition],
    anchor_overrides: dict | None,
) -> list[AttributeDefinition]:
    """
    Returns ordered list:
    1. Anchors (anchor_order 1–8)
    2. User-specified overrides (if any, set source="anchored")
    3. All remaining attributes (randomised within category for now)
    """
    ...
```

### Source Assignment

| How assigned | Source value |
|-------------|-------------|
| Demographic anchor fills | `"sampled"` |
| Forced from ICP anchor_overrides | `"anchored"` |
| LLM-filled based on profile | `"sampled"` |
| Adjusted because of correlation | `"inferred"` |
| From domain data (later) | `"domain_data"` |

---

## Performance Requirement

~150 LLM calls per persona is expensive if run sequentially. Implement async parallel filling for non-anchor attributes:

```python
import asyncio

async def fill_async(
    self,
    demographic_anchor: DemographicAnchor,
    taxonomy: list[AttributeDefinition],
    anchor_overrides: dict | None = None,
) -> dict[str, dict[str, Attribute]]:
    # Fill anchors sequentially (each conditions on prior)
    # Fill extended attributes in batches of 10 (they condition on anchors but not each other)
    # Fill domain-specific attributes sequentially at the end
    ...
```

For batched filling, each call in the batch receives the same "profile so far" snapshot (taken after anchors are filled). This is a pragmatic approximation — the true progressive model would be fully sequential, but batching is necessary for reasonable latency.

---

## Integration Contract

- **Imports from Cursor:** `from src.schema.persona import Attribute, DemographicAnchor`
- **Imports from Codex:** `from src.taxonomy.base_taxonomy import AttributeDefinition, BASE_TAXONOMY, ANCHOR_ATTRIBUTES, TAXONOMY_BY_NAME, KNOWN_CORRELATIONS`
- **Output type:** `dict[str, dict[str, Attribute]]` — maps directly onto `PersonaRecord.attributes`

---

## Constraints

- Do NOT generate `derived_insights` here. Those are computed deterministically in Sprint 2 from the filled attributes.
- Do NOT generate `behavioural_tendencies` here. Those are assigned by the `TendencyEstimator` in Sprint 2.
- Do NOT generate `narrative` or `life_stories` here. Those are LLM calls in Sprint 2.
- If an attribute fails to fill (LLM returns invalid response), retry once, then fall back to the `population_prior` value from the taxonomy definition. Mark source as `"sampled"`.

---

## Outcome File

When done, write `sprints/outcome_goose.md` with:
1. File created (with key class and method names)
2. Average LLM calls per persona (measured on a 3-persona test)
3. Async batch size you settled on and why
4. Any attribute types that were difficult to handle
5. How you handled LLM failures / invalid responses
6. Known gaps or edge cases
