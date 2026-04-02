# SPRINT 1 BRIEF — CURSOR
**Role:** Schema Architect
**Sprint:** 1 — Foundation: Schema + Taxonomy
**Spec check:** Master Spec §5 (Persona Record Structure), §14A S2 (tendencies are soft priors)
**Previous rating:** n/a (Sprint 1)

---

## Your Job This Sprint

You own the Pydantic schema for the entire persona system. Every other engineer's code will import from what you build. Get this right — nothing else can be tested until schema is solid.

Two files. Both are the source of truth for the data model.

---

## File 1: `src/schema/persona.py`

Pydantic v2 models for a single persona. Implement **exactly** the structure in Master Spec §5. No additions, no omissions.

### Top-level model: `PersonaRecord`

```python
class PersonaRecord(BaseModel):
    persona_id: str                          # format: pg-[prefix]-[001]
    generated_at: datetime
    generator_version: str
    domain: str
    mode: Literal["quick", "deep", "simulation-ready", "grounded"]
    demographic_anchor: DemographicAnchor
    life_stories: list[LifeStory]            # 2-3 items
    attributes: dict[str, dict[str, Attribute]]  # category → attr_name → Attribute
    derived_insights: DerivedInsights
    behavioural_tendencies: BehaviouralTendencies
    narrative: Narrative
    decision_bullets: list[str]
    memory: Memory
```

### Sub-models to implement:

**`DemographicAnchor`**
```
name, age (int), gender (Literal), location (Location), household (Household),
life_stage (str), education (Literal), employment (Literal)
```

**`Location`**
```
country, region, city, urban_tier (Literal["metro","tier2","tier3","rural"])
```

**`Household`**
```
structure (Literal["nuclear","joint","single-parent","couple-no-kids","other"]),
size (int), income_bracket (str), dual_income (bool)
```

**`LifeStory`**
```
title (str), when (str), event (str), lasting_impact (str)
```

**`Attribute`**
```
value: float | str
type: Literal["continuous", "categorical"]
label: str
source: Literal["sampled", "inferred", "anchored", "domain_data"]
```

**`DerivedInsights`**
```
decision_style: Literal["emotional","analytical","habitual","social"]
decision_style_score: float  # 0.0–1.0
trust_anchor: Literal["self","peer","authority","family"]
risk_appetite: Literal["low","medium","high"]
primary_value_orientation: Literal["price","quality","brand","convenience","features"]
coping_mechanism: CopingMechanism
consistency_score: int  # 0–100
consistency_band: Literal["low","medium","high"]
key_tensions: list[str]  # ≥ 1 required
```

**`CopingMechanism`**
```
type: Literal["routine_control","social_validation","research_deep_dive","denial","optimism_bias"]
description: str
```

**`BehaviouralTendencies`** — CRITICAL: these are soft priors, NOT numerical coefficients.
```
price_sensitivity: TendencyBand
trust_orientation: TrustOrientation
switching_propensity: TendencyBand
objection_profile: list[Objection]
reasoning_prompt: str   # the assembled natural-language paragraph for LLM context
```

**`TendencyBand`**
```
band: Literal["low","medium","high","extreme"]  # "extreme" only for price_sensitivity
description: str   # natural language — e.g. "You tend to be quite price-sensitive..."
source: Literal["grounded","proxy","estimated"]
```

**`TrustOrientation`**
```
weights: TrustWeights   # all floats 0.0–1.0
dominant: str           # name of highest-weight source
description: str        # natural language
source: Literal["grounded","proxy","estimated"]
```

**`TrustWeights`**
```
expert: float, peer: float, brand: float, ad: float, community: float, influencer: float
# all 0.0–1.0, validated
```

**`Objection`**
```
objection_type: Literal["price_vs_value","trust_deficit","need_more_information",
                         "social_proof_gap","switching_cost_concern","risk_aversion",
                         "budget_ceiling","feature_gap","timing_mismatch"]
likelihood: Literal["high","medium","low"]
severity: Literal["blocking","friction","minor"]
```

**`Narrative`**
```
first_person: str    # 100-150 words
third_person: str    # 150-200 words
display_name: str
```

**`Memory`**
```
core: CoreMemory
working: WorkingMemory
```

**`CoreMemory`**
```
identity_statement: str          # 25 words, first person
key_values: list[str]            # 3-5 items
life_defining_events: list[LifeDefiningEvent]
relationship_map: RelationshipMap
immutable_constraints: ImmutableConstraints
tendency_summary: str            # copy of reasoning_prompt, for context-window injection
```

**`LifeDefiningEvent`**
```
age_when: int, event: str, lasting_impact: str
```

**`RelationshipMap`**
```
primary_decision_partner: str
key_influencers: list[str]
trust_network: list[str]
```

**`ImmutableConstraints`**
```
budget_ceiling: str | None
non_negotiables: list[str]
absolute_avoidances: list[str]
```

**`WorkingMemory`**
```
observations: list[Observation]
reflections: list[Reflection]
plans: list[str]
brand_memories: dict[str, Any]
simulation_state: SimulationState
```

**`Observation`**
```
id: str, timestamp: datetime, type: Literal["observation"]
content: str, importance: int (1-10), emotional_valence: float (-1.0 to 1.0)
source_stimulus_id: str | None, last_accessed: datetime
```

**`Reflection`**
```
id: str, timestamp: datetime, type: Literal["reflection"]
content: str, importance: int
source_observation_ids: list[str]   # minimum 2 required — validated
last_accessed: datetime
```

**`SimulationState`**
```
current_turn: int, importance_accumulator: float, reflection_count: int
awareness_set: dict, consideration_set: list[str], last_decision: str | None
```

### Validators to add on PersonaRecord:
- `key_tensions` must have at least 1 item
- `life_stories` must have 2-3 items
- `key_values` must have 3-5 items
- `source_observation_ids` on Reflection must have ≥ 2 items
- All `TrustWeights` floats must be 0.0–1.0

---

## File 2: `src/schema/cohort.py`

**`CohortEnvelope`** model. Implement exactly Master Spec §5 (Cohort Envelope section).

```python
class CohortEnvelope(BaseModel):
    cohort_id: str
    generated_at: datetime
    domain: str
    business_problem: str
    mode: Literal["quick","deep","simulation-ready","grounded"]
    icp_spec_hash: str
    taxonomy_used: TaxonomyMeta
    personas: list[PersonaRecord]
    cohort_summary: CohortSummary
    grounding_summary: GroundingSummary
    calibration_state: CalibrationState
```

Sub-models:

**`TaxonomyMeta`**: `base_attributes: int`, `domain_extension_attributes: int`, `total_attributes: int`, `domain_data_used: bool`

**`CohortSummary`**: `decision_style_distribution: dict`, `trust_anchor_distribution: dict`, `risk_appetite_distribution: dict`, `consistency_scores: dict` (mean/min/max), `persona_type_distribution: dict`, `distinctiveness_score: float`, `coverage_assessment: str`, `dominant_tensions: list[str]`

**`GroundingSummary`**: `tendency_source_distribution: dict` (grounded/proxy/estimated as floats summing to 1.0), `domain_data_signals_extracted: int`, `clusters_derived: int`

**`CalibrationState`**: `status: Literal["uncalibrated","benchmark_calibrated","client_calibrated","calibration_failed"]`, `method_applied: str | None`, `last_calibrated: datetime | None`, `benchmark_source: str | None`, `notes: str | None`

---

## Constraints

- **Pydantic v2 only.** Use `model_validator`, `field_validator` as needed.
- **No domain-specific fields** in these models. They must work for any domain.
- **No numerical decision parameters** (no purchase_prob, no elasticity coefficients). If you see these anywhere, do not add them — it violates Master Spec §3 and Constitution P4.
- Import path: other engineers import from `src.schema.persona` and `src.schema.cohort`.

---

## Outcome File

When done, write `sprints/outcome_cursor.md` with:
1. Files created (with line counts)
2. Any schema decisions you made that weren't explicitly specified (flag these)
3. Anything that conflicted with the spec (flag and describe how you resolved it)
4. Import path example: `from src.schema.persona import PersonaRecord, CoreMemory`
5. Known gaps or assumptions
