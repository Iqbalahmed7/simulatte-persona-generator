# Persona Generation Method Specifications

**Version:** 1.0  
**Date:** 2026-05-09  
**Target audience:** Core Platform engineers  
**Status:** Ground truth — build against this

This document specifies the two production-grade persona generation methods
available to the Core Platform: **Core** and **Complete**. It covers the
exact pipeline, all quality gates, invocation contracts, output guarantees,
timing and cost profiles, and the decision guide for when to invoke each.

Swift (2-call Haiku) is intentionally excluded — it produces personas that
fail PQS Gate A and is not a valid input to any study or test output. It is
documented in `PERSONA_GENERATION_TIERS.md` for reference only.

---

## Method 1 — Core

### Summary
The full identity construction pipeline. Produces a research-grade persona
with complete psychology, biography, behavioural tendencies, and narrative.
**This is the default for all platform operations.**

| Property | Value |
|---|---|
| `mode` parameter | `"deep"` |
| Pipeline depth | 8 construction steps + cohort assembly |
| LLM calls per persona | ~5 sequential (Sonnet 4.5+) |
| Wall-clock time | 2.5–4 min / persona; 5–8 min for cohort of 10 |
| Cost / persona | ~$0.012 USD |
| PQS floor (per-persona) | 60 / 100 (Gate A) |
| PQS floor (cohort) | 65 / 100 (Gate B) |
| Requires OpenAI embeddings | No |
| Requires domain corpus | No (improves Decision Quality if provided) |
| Suitable for simulation | No — working memory not seeded |

---

### Pipeline — step by step

#### Step 1 — Attribute fill (`attribute_fill` phase)
**Module:** `src/generation/attribute_filler.py`  
**LLM:** Yes (1 call, Sonnet)  
**Input:** `DemographicAnchor`, domain taxonomy, `anchor_overrides`  
**Output:** All domain-specific attributes filled (category_usage, media_consumption, brand_landscape, income_band, psychographic_archetype, openness_to_novelty, etc.)

The domain taxonomy defines which attributes exist and what values are valid
for that domain (cpg, saas, fintech, etc.). The LLM fills attribute values
coherently — not independently. A `budget_consciousness=0.78` will co-occur
with plausible `income_band` and `brand_loyalty` values.

`anchor_overrides` (e.g. `{"location": "Mumbai", "age_min": 28}`) are applied
as hard constraints before the fill call.

---

#### Step 2 — Derived insights (`identity_core` phase)
**Module:** `src/generation/derived_insights.py`  
**LLM:** No (deterministic computation from Step 1 output)  
**Input:** `Attributes`, `DemographicAnchor`  
**Output:** `DerivedInsights`

Fields derived:
- `decision_style` — (analytical / intuitive / social / habitual / value-driven / aspirational)
- `trust_anchor` — primary trust signal (data / authority / peer / experience / brand)
- `risk_appetite` — (low / moderate / high) derived from attribute cluster
- `key_tensions` — ≥1 internal conflict (e.g. "values quality but income-constrained")
- `consistency_score` — 1–10; `consistency_band` — (low / medium / high)
- `primary_value_orientation` — (security / belonging / achievement / autonomy / etc.)
- `coping_mechanism` — `{type, description}` derived from psychographic profile

No LLM call. This step is fully deterministic and fast (<10 ms).

---

#### Step 3 — Life story generation (`life_story` phase)
**Module:** `src/generation/life_story_generator.py`  
**LLM:** Yes (1 call, Sonnet)  
**Input:** `DemographicAnchor`, `Attributes`  
**Output:** 3 `LifeStory` objects

Each story has:
```
title       — short anchor phrase (≤ 8 words)
narrative   — 80–200 word episode
when        — age or life stage when event occurred
emotional_valence — float -1.0 to 1.0
```

Stories are drawn from formative life episodes relevant to the persona's
category relationship. A CPG persona's stories will reference early brand
loyalties, household budget constraints, parental influences. A SaaS persona's
stories will reference career inflection points and tool adoption.

These stories directly feed Gate A PQS scoring (`life_story_depth`) and
drive IRIS memory-chain quote attribution.

---

#### Step 4 — Tendency estimation (`identity_behavior` phase)
**Module:** `src/generation/tendency_estimator.py`  
**LLM:** No (rule-based estimation from Steps 1–2)  
**Input:** `Attributes`, `DerivedInsights`  
**Output:** `BehaviouralTendencies`

Fields estimated:
- `price_sensitivity` — `{band, description, source}` — source will be `"proxy"` (upgraded to `"grounded"` if domain corpus is provided — see grounding note below)
- `switching_propensity` — `{likelihood, triggers[]}`
- `trust_orientation` — `{dominant, weights: {data, authority, peer, experience, brand}}`
- `objection_profile` — 2–4 objections each with `{type, likelihood, description}`
- `reasoning_prompt` — 1-sentence LLM instruction phrase for simulation

**Grounding upgrade:** if `domain_data` is passed to the pipeline, the
grounding module runs after cohort assembly and upgrades tendency sources
from `"proxy"` to `"grounded"`. This directly raises `Decision Quality` PQS
(the `tendency_source_coverage` component). For platform-generated pools:
pass a `business_problem` with category context — it signals the LLM to
produce tendencies closer to grounded state.

---

#### Step 5 — Narrative generation (`identity_behavior` phase)
**Module:** `src/generation/narrative_generator.py`  
**LLM:** Yes (1 call, Sonnet)  
**Input:** `DemographicAnchor`, `Attributes`, `DerivedInsights`, `LifeStory[]`, `BehaviouralTendencies`  
**Output:** `Narrative`

Fields generated:
```
first_person    — ≥ 80 words, persona speaks in present tense about their life
third_person    — ≥ 80 words, observer describes the persona
display_name    — short label (e.g. "Priya — budget-conscious urban mother")
```

The narrative synthesises all prior steps into coherent voice. This is the
richest single output — it carries the persona's tensions, decision style,
and key relationships in natural language. System prompt builders (`build_system_prompt`)
use `first_person` and `third_person` directly.

Gate G4 enforces minimum word counts on both fields and validates
`display_name` is present.  
Gate G5 cross-checks that narrative text is consistent with behavioural
values (e.g. if `brand_loyalty > 0.80`, narrative must not contain
switching language).

---

#### Step 6 — Core memory assembly
**Module:** `src/memory/core_memory.py` → `assemble_core_memory()`  
**LLM:** No  
**Input:** Complete `PersonaRecord` assembled from Steps 1–5  
**Output:** `CoreMemory`

Fields assembled:
```
identity_statement      — ≥ 10 words, authoritative self-description
key_values              — 3–5 values drawn from derived_insights + attributes
life_defining_events    — string list of pivotal moments (from life_stories)
relationship_map        — {primary_decision_partner, key_influencers[]}
immutable_constraints   — {budget_ceiling, non_negotiables[], absolute_avoidances[]}
tendency_summary        — ≥ 20 words, plain-English summary of behavioural profile
```

Step 6 runs twice: once inline (bootstrapping a valid `PersonaRecord`) and
once via the authoritative `assemble_core_memory()` which uses the full
assembled record. The second run replaces the first.

---

#### Step 7 — Individual persona validation (G1–G5)
**Module:** `src/schema/validators.py`  
**LLM:** No  
**Input:** Final `PersonaRecord`

| Gate | What it checks | Failure action |
|---|---|---|
| **G1** | Schema validity — `key_values` 3–5 items, `life_stories` 2–3 items, `key_tensions` ≥1, `persona_id` format, TrustWeight values 0–1 | Regenerate persona |
| **G2** | Hard constraints HC1–HC6 — impossible demographic combinations (e.g. student + high income) | Regenerate persona |
| **G3** | Tendency-attribute consistency TR1–TR8 — behavioural invariants (e.g. `budget_consciousness > 0.70` requires low `switching_propensity`, `brand_loyalty > 0.70` requires trust anchor ≠ "price") | Regenerate persona |
| **G4** | Narrative depth — `first_person` ≥ 50 words, `third_person` ≥ 80 words, `life_stories` all fields populated, `decision_bullets` ≥ 1, `identity_statement` ≥ 10 words, `tendency_summary` ≥ 20 words | Regenerate persona |
| **G5** | Narrative-behaviour alignment — narrative text must not contradict declared behavioural values (brand loyalty, switching, price sensitivity, trust, risk appetite) | Regenerate persona |

G1–G5 are hard failures. A persona that fails any of them is regenerated up
to `max_retries_per_persona` times (default 2). If it cannot pass after
retries, it is quarantined.

---

#### Step 8 — PQS Gate A (per-persona floor)
**Module:** `src/quality/pqs.py` → `score_persona_pqs()`  
**Input:** Individual `PersonaRecord`  
**Threshold:** 60 / 100 (env: `PQS_PERSONA_FLOOR`)

Scored on:
- Narrative completeness (25%) — word counts toward 200-word combined target
- Life story depth (20%) — story count toward 2.5 target
- Memory seed depth (20%) — `life_defining_events` toward 3 target
- Tension presence (15%) — `key_tensions` toward 1.5 target
- Decision bullet count (20%) — bullets toward 4 target

Personas below 60 are dropped before cohort assembly. If more than 20% of
the pool fails (`PQS_MAX_QUARANTINE_PCT`), the run aborts with an error
identifying which generator component is producing thin output.

---

#### Step 9 — Cohort assembly
**Module:** `src/cohort/assembler.py` → `assemble_cohort()`  
**LLM:** Optional (grounding upgrade if `domain_data` provided)  
**Input:** All passing `PersonaRecord[]`

Runs cohort-level quality gates:

| Gate | What it checks | Threshold | Failure action |
|---|---|---|---|
| **G6** | Demographic distribution — no single city >20%, no age bracket >40%, income spans ≥3 brackets | Per-cohort | Regenerate failing personas, up to `max_attempts` |
| **G7** | Distinctiveness — mean pairwise cosine distance on 8 core attributes; scaled threshold 0.10–0.35 by cohort size | Scales with N | Regenerate; waiver after `max_attempts` |
| **G8** | Type coverage — unique persona types: N<3→1, 3≤N<5→2, 5≤N<10→3, N≥10→8 | Scales with N | Regenerate; waiver after `max_attempts` |
| **G9** | Tension completeness — every persona has ≥1 explicit tension in `key_tensions` | 100% of cohort | Regenerate |
| **G11** | Tendency source — every tendency field has `source != None` | 100% of cohort | Regenerate |
| **G12** | Per-persona quarantine — any persona flagged by post-assembly checks | Max 20% quarantine rate | Drop quarantined; abort if >20% |

G6–G9, G11 waivers are issued after `max_attempts` regenerations (default 2).
Waivers are logged and stored in the cohort envelope for audit — they do not
block delivery.

---

#### Step 10 — PQS Gate B (cohort floor)
**Module:** `src/orchestrator/invoke.py`  
**Threshold:** 65 / 100 (env: `PQS_COHORT_FLOOR`)

Four-dimension composite scored after full assembly:
- Behavioral Realism (25%) — band diversity entropy + tension presence rate
- Identity Depth (25%) — narrative completeness, story depth, memory depth, relationship completeness
- Decision Quality (25%) — tendency source coverage, objection depth, bullet count, constraint completeness
- Cohort Health (25%) — distinctiveness score, type coverage, decision style diversity, trust anchor diversity

Below 65: run aborts with dimension breakdown.  
65–74: warning emitted, run proceeds.  
75+: clean pass.

---

### Core output — guaranteed fields

When `Core` completes without abort, the platform can depend on all of the
following fields being present and non-empty on every persona in the
`personas[]` array:

```
demographic_anchor.name
demographic_anchor.age
demographic_anchor.gender
demographic_anchor.location.{city, country}
demographic_anchor.employment.{occupation, industry, seniority}
demographic_anchor.education
demographic_anchor.life_stage
demographic_anchor.household.{size, composition}

derived_insights.decision_style
derived_insights.trust_anchor
derived_insights.risk_appetite
derived_insights.key_tensions[]          ≥ 1 item
derived_insights.consistency_score
derived_insights.consistency_band
derived_insights.primary_value_orientation
derived_insights.coping_mechanism.{type, description}

behavioural_tendencies.price_sensitivity.{band, description}
behavioural_tendencies.switching_propensity.{likelihood, triggers[]}
behavioural_tendencies.objection_profile[]   ≥ 2 items
behavioural_tendencies.trust_orientation.{dominant, weights{}}
behavioural_tendencies.reasoning_prompt

narrative.first_person     ≥ 50 words
narrative.third_person     ≥ 80 words
narrative.display_name

life_stories[]             2–3 items, each with {title, narrative, when}
decision_bullets[]         ≥ 1 item

memory.core.identity_statement        ≥ 10 words
memory.core.key_values[]              3–5 items
memory.core.life_defining_events[]    ≥ 1 item
memory.core.relationship_map.{primary_decision_partner, key_influencers[]}
memory.core.immutable_constraints.{budget_ceiling, non_negotiables[], absolute_avoidances[]}
memory.core.tendency_summary          ≥ 20 words

_pqs.pqs                   ≥ 65 (cohort-level)
_pqs.{behavioral_realism, identity_depth, decision_quality, cohort_health}
```

Fields NOT present in Core output:
```
memory.working.observations[]   — empty list (no seed memories)
memory.working.reflections[]    — empty list
```

---

### Core invocation

**Via Engine HTTP API (platform standard)**

```http
POST {ENGINE_URL}/generate
Authorization: Bearer {ENGINE_SECRET}
Content-Type: application/json

{
  "n_personas":       10,
  "market":           "IN",
  "domain":           "cpg",
  "business_problem": "Why do urban mothers lapse post-trial?",
  "age_min":          25,
  "age_max":          40
}
```

Response (200, synchronous, up to 20 min):
```json
{
  "cohort_id":       "cohort-abc123",
  "personas":        [...],
  "count_delivered": 9
}
```

**Direct Python invocation (for platform-internal workers)**

```python
from src.orchestrator.invoke import invoke_persona_generator_sync
from src.orchestrator.brief import PersonaGenerationBrief, RunIntent

brief = PersonaGenerationBrief(
    client="platform",
    domain="cpg",
    business_problem="Why do urban mothers lapse post-trial?",
    count=10,
    mode="deep",                    # Core
    run_intent=RunIntent.DELIVER,
    auto_confirm=True,
    anchor_overrides={
        "location": "India",
        "age_min": 25,
        "age_max": 40,
    },
    registry_path="/mnt/pg_registry",
)

result = invoke_persona_generator_sync(brief)
personas = result.personas          # list[dict] — full dossiers
pqs      = result.pqs_score         # float or None
cost     = result.cost_actual.total # float USD
```

**Env vars that affect Core generation:**

```
GENERATION_MODEL=claude-sonnet-4-6     # default; Haiku reduces quality
PG_REGISTRY_PATH=/mnt/pg_registry      # for persona reuse across pools
PQS_PERSONA_FLOOR=60                   # per-persona gate (default)
PQS_COHORT_FLOOR=65                    # cohort gate (default)
PQS_MAX_QUARANTINE_PCT=0.20            # abort threshold if too many fail
```

---

---

## Method 2 — Complete

### Summary
Core plus simulation bootstrapping. Produces everything Core produces, then
derives seed working memories from the persona's biography for immediate use
in agent-based simulation loops.

| Property | Value |
|---|---|
| `mode` parameter | `"simulation-ready"` |
| Pipeline depth | Core steps 1–10 + seed memory bootstrap |
| LLM calls per persona | ~5 sequential (same as Core) |
| Extra step | `bootstrap_seed_memories()` — zero LLM calls, pure derivation |
| Wall-clock time | ~10–20 s more than Core (seed step is fast) |
| Cost / persona | ~$0.013 USD (negligible increase over Core — seed step has no LLM cost) |
| PQS floor (per-persona) | 65 / 100 (higher — simulation requires richer identity) |
| PQS floor (cohort) | 70 / 100 |
| Requires OpenAI embeddings | No — seed memories are derived in-process |
| Suitable for simulation | Yes — `memory.working` is seeded and ready |

---

### Additional step — seed memory bootstrap (Complete only)

**Module:** `src/memory/seed_memory.py` → `bootstrap_seed_memories()`  
**LLM:** No — zero LLM calls  
**Runs after:** Core steps 1–10  
**Gate:** G10

Takes the assembled `CoreMemory` and derives ≥3 `Observation` objects for
`working_memory.observations`. These are the episodic memories the persona
"has in mind" at the start of a simulation.

**Four seed categories (in order):**

| Seed # | Source | Content pattern |
|---|---|---|
| 1 | `identity_statement` | `"I know myself: {identity_statement}"` |
| 2 | `key_values[0]` | Derived from primary value |
| 3 | `tendency_summary` (first sentence) | Key behavioural anchor |
| 4–6 | `life_defining_events[:3]` | One observation per formative event (up to 3 additional) |

Each seed observation carries:
```python
Observation(
    id                 = uuid4(),
    content            = <derived string>,
    importance         = 8,          # high — just below promotion threshold of 9
    emotional_valence  = 0.0,        # neutral — identity anchors have no valence bias
    timestamp          = datetime.now(utc),
)
```

**Gate G10:** after bootstrap, `working_memory.observations` must have ≥3
items. If derivation produces fewer (malformed `CoreMemory`), fallback seeds
are added automatically. Gate G10 failure aborts the run — it indicates a
structural problem in core memory assembly upstream.

---

### Complete — additional guaranteed fields

Everything in Core output, plus:

```
memory.working.observations[]     ≥ 3 seed items
  each: {id, content, importance=8, emotional_valence=0.0, timestamp}

memory.working.simulation_state   initialised at zero
  {current_turn=0, importance_accumulator=0.0, reflection_count=0,
   awareness_set={}, consideration_set=[], last_decision=null}
```

The `memory.working.reflections[]` list starts empty — reflections are
generated during simulation turns, not at generation time.

---

### Complete invocation

**Via Engine HTTP API**

Use `POST /persona/deep-study` (returns async job) when n_personas is large
or when bundling generation + simulation in one call:

```http
POST {ENGINE_URL}/persona/deep-study
Authorization: Bearer {ENGINE_SECRET}
Content-Type: application/json

{
  "study_name":        "LittleJoys Post-Trial Simulation",
  "region":            "India",
  "n_personas":        15,
  "domain":            "cpg",
  "research_question": "Why do mothers lapse after first month?",
  "scenario_question": "Would you repurchase LittleJoys Family Pack?",
  "scenario_context":  "You purchased last month. Your child enjoyed it but...",
  "scenario_options":  ["Yes — repurchase", "No — switching brand", "Undecided"],
  "age_min":           25,
  "age_max":           40,
  "icp_description":   "Urban mothers, children under 5, SEC B/B+"
}
```

Poll `GET /job/{job_id}` every 15 seconds. Timeout after 25 minutes.

**Direct Python invocation**

```python
brief = PersonaGenerationBrief(
    client="platform",
    domain="cpg",
    business_problem="Why do urban mothers lapse post-trial?",
    count=15,
    mode="simulation-ready",         # Complete
    run_intent=RunIntent.DELIVER,
    auto_confirm=True,
    anchor_overrides={
        "location": "India",
        "age_min": 25,
        "age_max": 40,
    },
    registry_path="/mnt/pg_registry",
)

result = invoke_persona_generator_sync(brief)
# result.personas[n]["memory"]["working"]["observations"] → seeded
```

**Higher PQS floors for Complete:**

```
PQS_PERSONA_FLOOR=65     # override from default 60
PQS_COHORT_FLOOR=70      # override from default 65
```

Set these on the platform at the pool creation layer when `pipeline_mode="complete"`
is requested. Do not change the global defaults — they apply to Core.

---

---

## Decision guide — Core vs Complete

### Rule 1: Default to Core

If you are uncertain, use Core. It covers every product feature except
live agent simulation. Running Complete when you don't need working memory
wastes 10–20 seconds per persona and produces output fields the feature
cannot use.

---

### Rule 2: Complete is required only when simulation is active

Use Complete when the platform feature will call `memory.working.observations`
during a live session. Concretely:

| Feature | Method | Reason |
|---|---|---|
| IRIS — pre-flight panel reveal | Core | Only needs dossier fields |
| IRIS — exposure simulation (1-turn verdict) | Core | Single turn, no memory retrieval needed |
| IRIS — multi-turn creative dialogue (future) | Complete | Persona recalls prior stimuli between turns |
| Forge — concept test run | Core | Single-turn verdict per persona |
| Forge — `POST /tests/{id}/ask` (any question) | Core | One-shot Q&A, not simulation |
| Forge — variant A/B comparison across sessions | Complete | Persona must remember prior concept reactions |
| PopScale — social topology simulation | Complete | Multi-round agent loop reads working memory |
| Morpheus — probe_mechanism() / probe_counterfactual() | Core | Niobe probes are single-turn |
| Niobe — population survey | Core | No simulation loop |
| The Mind — conversational persona (first load) | Core | Single session, no prior state |
| The Mind — returning user with prior chat history | Complete | Working memory enables persistent recall |

---

### Rule 3: Use the smallest method that satisfies the gate

Complete has a higher PQS floor (65/70 vs 60/65). This means a pool that
passes Core gates may fail Complete gates. Do not generate Complete pools
"just in case" — you will see higher abort rates for marginal personas that
would have passed Core.

**Escalation path:** generate Core first. If the feature requires simulation
and the pool was generated as Core, re-generate the specific personas that
will be used in the simulation loop as Complete. Don't regenerate the entire
pool.

---

### Rule 4: Complete cannot be downgraded post-generation

A Complete persona is structurally identical to a Core persona plus working
memory. You can ignore `memory.working` on a Complete persona (treat it as
Core), but you cannot add `memory.working` to a Core persona after the fact.
`bootstrap_seed_memories()` requires `CoreMemory` fields to be fully
assembled — it is not a post-hoc enrichment you can call on a stored dossier.

---

### Rule 5: Signal the platform pool service, not PG directly

The platform pool service sets `pipeline_mode` at pool creation time. Once
set, it is immutable for that pool. IRIS and Forge pass `pipeline_mode` in
the pool create request and do not need to know whether Core or Complete was
used — the dossier shape is identical except for `memory.working`.

```
POST /internal/pools/generate
{
  "pipeline_mode": "core" | "complete",   ← set here once, immutable
  ...
}
```

---

### Quick reference

```
Does the feature need personas to remember prior turns
  within the same session or across sessions?
  │
  ├── NO  → Core (mode="deep")
  │         PQS floor: 60 / 65
  │         Cost: ~$0.012/persona
  │         Time: 3–4 min/10 personas
  │
  └── YES → Complete (mode="simulation-ready")
            PQS floor: 65 / 70
            Cost: ~$0.013/persona
            Time: 3–5 min/10 personas
            Requires: pool_mode="complete" set at pool creation
```

---

## Error handling — both methods

### PQS Gate A abort (per-persona floor)

```
RuntimeError: PQS Gate A: 3/10 personas (30%) below floor 60 — exceeds
PQS_MAX_QUARANTINE_PCT=0.20. Check life_story_generator and narrative_generator output.
```

Cause: domain is too abstract (e.g. `domain="consumer"` with no business
problem), or the model generating life stories is producing thin output.  
Fix: provide a more specific `business_problem` string, or set `domain` to a
concrete domain key (`cpg`, `fintech`, `saas`, etc.).

### PQS Gate B abort (cohort floor)

```
RuntimeError: PQS cohort gate failed: 58.3 / 100 (floor=65).
Failing dimensions: {"Decision Quality": 41.2, "Cohort Health": 52.1}.
Add domain_data/corpus_path for grounding, increase cohort size,
or set PQS_COHORT_FLOOR=50 to bypass for dev runs.
```

Cause of low Decision Quality: no domain corpus provided (all tendencies
remain `source="proxy"`).  
Cause of low Cohort Health: n < 5 makes distinctiveness scoring volatile; or
all personas share same decision style.  
Fix: pass `domain_data` (list of product review strings) in the brief for
grounding, or increase `count`.

### G10 abort (Complete only)

```
ValueError: G10 gate failure: bootstrap_seed_memories produced only 1
observation(s); minimum is 3.
```

Cause: `CoreMemory` has empty `life_defining_events` and empty `key_values`.
This means upstream Steps 5 (narrative) and 6 (core memory assembly) produced
thin output.  
Fix: this should not reach G10 — G4 and Gate A would have caught it. If G10
fires, check that G4 and PQS Gate A are enabled (`skip_gates=False`).

### Timeout

Engine `/generate` has a 20-minute hard timeout set by `wr-populations`.
For large cohorts (n > 50), use `/persona/deep-study` (async) instead.
At 10 concurrent builds, 50 personas take approximately 6–10 minutes.

### Dev / debug bypass

To run without quality gates during development:

```python
brief = PersonaGenerationBrief(
    ...
    skip_gates=True,   # disables G6–G12 and both PQS gates
)
```

Or via env:
```
PQS_COHORT_FLOOR=0
PQS_PERSONA_FLOOR=0
```

Never set bypass flags in production environment variables.

---

## Gate summary — both methods

| Gate | Scope | Method | What it checks | On failure |
|---|---|---|---|---|
| G1 | Individual | Both | Schema validity | Regenerate |
| G2 | Individual | Both | Hard demographic constraints | Regenerate |
| G3 | Individual | Both | Tendency-attribute consistency (TR1–TR8) | Regenerate |
| G4 | Individual | Both | Narrative depth (word counts, story count) | Regenerate |
| G5 | Individual | Both | Narrative-behaviour alignment | Regenerate |
| PQS Gate A | Individual | Both | Per-persona score ≥ 60 (Core) / ≥ 65 (Complete) | Drop persona |
| G6 | Cohort | Both | Demographic distribution | Regenerate |
| G7 | Cohort | Both | Pairwise distinctiveness | Regenerate → waiver |
| G8 | Cohort | Both | Persona type coverage | Regenerate → waiver |
| G9 | Cohort | Both | Tension completeness | Regenerate |
| G11 | Cohort | Both | Tendency source completeness | Regenerate |
| G12 | Cohort | Both | Post-assembly per-persona quarantine | Drop → abort if >20% |
| PQS Gate B | Cohort | Both | Cohort score ≥ 65 (Core) / ≥ 70 (Complete) | Abort with breakdown |
| G10 | Individual | **Complete only** | Working memory seed count ≥ 3 | Abort |
