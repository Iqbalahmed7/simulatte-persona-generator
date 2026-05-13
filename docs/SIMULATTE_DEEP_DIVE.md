# Simulatte — Complete System Deep Dive

**Version:** 1.0 · **Date:** 2026-05-09  
**Scope:** Persona Generator · Cognitive Loop · Social Simulation · Benchmark · PopScale  
**Audience:** Engineers, product leads, anyone building on or with Simulatte

---

## Table of Contents

1. [What Simulatte Actually Is](#1-what-simulatte-actually-is)
2. [Persona Generation — The Three Tiers](#2-persona-generation--the-three-tiers)
3. [Swift Tier — The Mind Pipeline](#3-swift-tier--the-mind-pipeline)
4. [Core Tier — Full Identity Pipeline](#4-core-tier--full-identity-pipeline)
5. [Complete Tier — Simulation-Ready](#5-complete-tier--simulation-ready)
6. [The PersonaRecord Schema](#6-the-personarecord-schema)
7. [Persona Quality Gates — G1 through G12](#7-persona-quality-gates--g1-through-g12)
8. [Persona Quality Score (PQS)](#8-persona-quality-score-pqs)
9. [The Cognitive Loop](#9-the-cognitive-loop)
10. [Social Simulation — Multi-Agent Layer](#10-social-simulation--multi-agent-layer)
11. [Modalities — Simulation vs Survey](#11-modalities--simulation-vs-survey)
12. [Benchmark Service](#12-benchmark-service)
13. [PopScale — Population Modelling](#13-popscale--population-modelling)
14. [Worldview Layer — Political Archetypes](#14-worldview-layer--political-archetypes)
15. [Calibration and Grounding](#15-calibration-and-grounding)
16. [Persona Registry](#16-persona-registry)
17. [The Operator — Client Research Layer](#17-the-operator--client-research-layer)
18. [Invocation Patterns](#18-invocation-patterns)
19. [Cost and Timing Reference](#19-cost-and-timing-reference)
20. [When to Use What](#20-when-to-use-what)

---

## 1. What Simulatte Actually Is

Simulatte is **decision infrastructure**. It is not a chatbot, not an AI research tool, not a survey replacement. It is a system for running decisions through before you make them.

The core unit is a **persona** — a structurally grounded synthetic human being with a complete psychology, biography, memory, and behavioural model. Every other component in the system builds on that unit:

- **The Mind** turns a single persona into a conversational interface
- **The Cognitive Loop** drives that persona through stimulus → perception → reflection → decision
- **Social Simulation** connects personas into networks where they influence each other
- **Benchmark** measures how faithfully a persona plays its role under pressure
- **PopScale** scales a persona definition into demographically calibrated populations of thousands
- **Niobe** runs structured research studies across those populations
- **The Operator** synthesises the outputs into client-facing insight

Everything traces back to one question: does this persona behave like a real person would, under real conditions, making real decisions?

---

## 2. Persona Generation — The Three Tiers

There are three generation methods. They are not quality options — they are different tools for different jobs.

| | Swift | Core | Complete |
|---|---|---|---|
| `mode` param | N/A (separate path) | `"deep"` | `"simulation-ready"` |
| LLM calls | 3 Haiku (2 parallel) | ~5 sequential Sonnet | ~5 Sonnet + seed bootstrap |
| Time / persona | 15–18 s | 2.5–4 min | 2.5–4 min + 10–20 s |
| Cost / persona | ~$0.07 | ~$0.012 | ~$0.013 |
| Working memory | ✗ | ✗ | ✅ seeded |
| PQS gate | None enforced | ≥60 / ≥65 cohort | ≥65 / ≥70 cohort |
| Use for | UI preview, demos | All production | Agent simulation |

**Default for all platform features: Core.**  
Complete only when `memory.working.observations` will be read during a live session.  
Swift only for instant UI previews that never reach a study output.

---

## 3. Swift Tier — The Mind Pipeline

Used exclusively by The Mind conversational interface. Three sequential stages, two of which run as parallel Haiku calls.

### Stage 1 — Brief extraction (1 Haiku call, ~3 s)

Reads free-text brief → structured `DemographicAnchor`.

Output fields: `name`, `age`, `gender`, `life_stage`, `location` (city + country + tier), `education`, `employment` (occupation + industry + seniority), `household` (size + composition).

Extraction has four fallback layers: tool-use JSON → code-fence extraction → brace-scan → default schema. Never crashes on a malformed model response.

### Stage 2 — Identity generation (2 parallel Haiku calls, ~12–15 s)

**Call A — Inner life:**
- `narrative` (first_person + third_person, ~150 words each)
- `derived_insights` (decision_style, trust_anchor, risk_appetite, primary_value_orientation, consistency_score 0–100, key_tensions, coping_mechanism)
- `behavioural_tendencies` (price_sensitivity, trust_orientation, switching_propensity, objection_profile, reasoning_prompt)
- `decision_bullets` (5 short statements)
- `life_stories` (3–5 episodes)

**Call B — Outer life and memory:**
- Refined demographic detail (fills gaps from Stage 1)
- `memory.core` (identity_statement, key_values, life_defining_events, relationship_map, immutable_constraints, tendency_summary)

Both calls receive the demographic anchor as shared context. Overlapping fields are resolved by specificity (the more detailed value wins). This redundancy eliminates the "missing city" failure mode.

### Stage 3 — Quality assessment (local, 0 LLM calls)

Genuineness score 0–10, four components:

| Component | Weight | What it scores |
|---|---|---|
| Demographic grounding | 40% | How many anchor fields populated |
| Behavioural consistency | 30% | Cross-attribute coherence |
| Narrative depth | 15% | Life stories + decision bullets + memory events present |
| Psychological completeness | 15% | All derived_insights + tendency fields populated |

The score is informational only — it does not gate delivery in Swift mode.

### Swift limitations

Swift personas reliably fail PQS Gate A (per-persona floor 60). Specifically:
- `narrative_completeness` is low (short first/third person)
- `life_story_depth` is shallow (fewer than 2.5 average stories)
- `memory_seed_depth` is thin

This is expected and by design. Swift is the demo unit. Core is the research unit.

---

## 4. Core Tier — Full Identity Pipeline

The production standard. 10 ordered steps. No step can be skipped.

### Step 1 — Attribute fill (`attribute_fill` phase)

**Module:** `src/generation/attribute_filler.py`  
**Model:** Sonnet · 1 LLM call  
**Input:** `DemographicAnchor`, domain taxonomy, `anchor_overrides`

Fills all domain-specific typed attributes coherently. The domain taxonomy defines the attribute schema — CPG personas get `category_usage`, `brand_loyalty`, `budget_consciousness`, `impulse_buying_tendency`; SaaS personas get `feature_adoption_speed`, `integration_complexity_tolerance`, etc. Attributes are not filled independently — the model fills them as a person, so `budget_consciousness=0.78` co-occurs with plausible `income_band` and `brand_switching_rate`.

`anchor_overrides` (e.g. `{"location": "Mumbai", "age_min": 28}`) are hard constraints applied before the call.

### Step 2 — Derived insights (`identity_core` phase)

**Module:** `src/generation/derived_insights.py`  
**Model:** None — deterministic computation  
**Input:** `Attributes`, `DemographicAnchor`

Pure rule-based derivation. Fast (<10 ms). Produces:
- `decision_style` — analytical / intuitive / social / habitual / value-driven / aspirational
- `trust_anchor` — data / authority / peer / experience / brand
- `risk_appetite` — low / moderate / high
- `key_tensions` — ≥1 explicit internal conflict (e.g. "values quality but income-constrained")
- `consistency_score` — 1–10 integer; `consistency_band` — low / medium / high
- `primary_value_orientation` — security / belonging / achievement / autonomy / transcendence / etc.
- `coping_mechanism` — `{type, description}`

No LLM. Deterministic from the attribute cluster.

### Step 3 — Life story generation (`life_story` phase)

**Module:** `src/generation/life_story_generator.py`  
**Model:** Sonnet · 1 LLM call  
**Input:** `DemographicAnchor`, `Attributes`  
**Output:** 3 `LifeStory` objects (`_DEFAULT_N_STORIES = 3`)

Each story: `{title ≤8 words, narrative 80–200 words, when (age or life stage), emotional_valence -1.0–1.0}`. Stories are domain-contextual — CPG stories reference brand loyalties and household budget moments; SaaS stories reference career inflection points. These feed IRIS memory-chain quote attribution and drive PQS `life_story_depth` scoring.

### Step 4 — Tendency estimation (`identity_behavior` phase)

**Module:** `src/generation/tendency_estimator.py`  
**Model:** None — rule-based  
**Input:** `Attributes`, `DerivedInsights`

Produces `BehaviouralTendencies`:
- `price_sensitivity` — `{band, description, source}` (source="proxy" until grounded)
- `switching_propensity` — `{likelihood, triggers[]}`
- `trust_orientation` — `{dominant, weights{data, authority, peer, experience, brand}}`
- `objection_profile` — 2–4 objections each with `{type, likelihood, description}`
- `reasoning_prompt` — 1-sentence instruction for simulation LLM calls

Source upgrades from "proxy" → "grounded" when `domain_data` is passed and the grounding pipeline runs during cohort assembly.

### Step 5 — Narrative generation (`identity_behavior` phase)

**Module:** `src/generation/narrative_generator.py`  
**Model:** Sonnet · 1 LLM call  
**Input:** `DemographicAnchor`, `Attributes`, `DerivedInsights`, `LifeStory[]`, `BehaviouralTendencies`

Synthesises all prior steps into natural language. The richest single output. Fields:
- `first_person` — ≥80 words, present tense, persona speaks
- `third_person` — ≥80 words, observer's view
- `display_name` — short archetype label (e.g. "Priya — budget-conscious urban mother")

Gate G4 enforces word counts. Gate G5 cross-checks that narrative doesn't contradict declared behavioural values (brand loyalty contradicting switching narrative, etc.).

### Step 6 — Core memory assembly

**Module:** `src/memory/core_memory.py` → `assemble_core_memory()`  
**Model:** None  
**Input:** Complete assembled `PersonaRecord`

Runs twice: once inline (bootstrapping a valid record) and once via the authoritative `assemble_core_memory()`. The second pass replaces the first, using the fully assembled record.

Fields:
- `identity_statement` — ≥10 words, authoritative first-person self-description
- `key_values` — 3–5 values
- `life_defining_events` — string list of pivotal moments drawn from life_stories
- `relationship_map` — `{primary_decision_partner, key_influencers[]}`
- `immutable_constraints` — `{budget_ceiling, non_negotiables[], absolute_avoidances[]}`
- `tendency_summary` — ≥20 words, plain-English behavioural profile

### Step 7 — Individual validation (G1–G5)

**Module:** `src/schema/validators.py`  
**Model:** None

Five hard gates. Any failure → persona is regenerated (up to `max_retries_per_persona`, default 2):

| Gate | What it checks |
|---|---|
| G1 | Schema validity — `key_values` 3–5 items, `life_stories` 2–3 items, `key_tensions` ≥1, `persona_id` format, TrustWeight values 0–1 |
| G2 | Hard constraints HC1–HC6 — impossible demographic combinations (student + high income, retired person in entry-level role, etc.) |
| G3 | Tendency-attribute consistency TR1–TR8 — e.g. `budget_consciousness > 0.70` → low switching; `brand_loyalty > 0.70` → trust anchor ≠ "price" |
| G4 | Narrative depth — `first_person` ≥50w, `third_person` ≥80w, all life_story fields populated, `decision_bullets` ≥1, `identity_statement` ≥10w, `tendency_summary` ≥20w |
| G5 | Narrative-behaviour alignment — narrative text must not contradict declared behavioural values |

### Step 8 — PQS Gate A (per-persona floor)

**Module:** `src/quality/pqs.py` → `score_persona_pqs()`

Runs before cohort assembly. Formula:

```
score = (0.25 × narrative_completeness
       + 0.20 × life_story_depth
       + 0.20 × memory_seed_depth
       + 0.15 × tension_presence
       + 0.20 × decision_bullet_count) × 100
```

Personas below 60 are dropped. If >20% of the pool fails → `RuntimeError`. Env override: `PQS_PERSONA_FLOOR`.

### Step 9 — Cohort assembly

**Module:** `src/cohort/assembler.py` → `assemble_cohort()`

Cohort-level quality gates (all run after individual assembly):

| Gate | What it checks | On failure |
|---|---|---|
| G6 | Demographic distribution — no single city >20%, no age bracket >40%, income spans ≥3 brackets | Regenerate failing personas |
| G7 | Distinctiveness — mean pairwise cosine distance on 8 core attributes; threshold scales 0.10–0.35 with cohort size | Regenerate → waiver after `max_attempts` |
| G8 | Type coverage — N<3→1 type, 3≤N<5→2, 5≤N<10→3, N≥10→8 types | Regenerate → waiver |
| G9 | Tension completeness — every persona has ≥1 tension | Regenerate |
| G11 | Tendency source completeness — every tendency field has source ≠ None | Regenerate |
| G12 | Post-assembly per-persona quarantine | Drop; abort if >20% quarantined |

G6–G9, G11 waivers are issued after `max_attempts` regenerations. Waivers are logged in the cohort envelope — they don't block delivery.

### Step 10 — PQS Gate B (cohort floor)

**Module:** `src/orchestrator/invoke.py`

Composite 0–100 score. Below 65 → abort with dimension breakdown. 65–74 → warning, proceeds.

---

## 5. Complete Tier — Simulation-Ready

Everything in Core, plus one additional step after core memory is assembled:

### Seed memory bootstrap

**Module:** `src/memory/seed_memory.py` → `bootstrap_seed_memories()`  
**Model:** None — zero LLM calls  
**Gate:** G10

Derives ≥3 `Observation` objects for `memory.working.observations` from `CoreMemory`:

| Seed # | Source field | Content |
|---|---|---|
| 1 | `identity_statement` | `"I know myself: {identity_statement}"` |
| 2 | `key_values[0]` | Primary value anchor |
| 3 | `tendency_summary` (first sentence) | Behavioural anchor |
| 4–6 | `life_defining_events[:3]` | One observation per formative event (up to 3) |

Each observation: `importance=8` (high, just below promotion threshold of 9), `emotional_valence=0.0` (neutral identity anchors), UUID, timestamp.

G10 gate: must have ≥3 observations. If derivation produces fewer (malformed CoreMemory), fallback seeds are added automatically. G10 failure indicates the G4/Gate A pipeline upstream failed to enforce narrative depth.

**Complete personas are not upgradeable from Core.** `bootstrap_seed_memories()` requires a fully assembled `CoreMemory`. You cannot add working memory to a Core persona post-generation.

---

## 6. The PersonaRecord Schema

The full JSON structure of a generated persona. Version: 2.1.0.

```
PersonaRecord
├── persona_id          "pg-001" (prefix-index)
├── generated_at        UTC datetime
├── generator_version   "2.1.0"
├── domain              "cpg" | "saas" | "fintech" | etc.
├── mode                "quick" | "deep" | "simulation-ready" | "grounded"
│
├── demographic_anchor
│   ├── name
│   ├── age
│   ├── gender          "male" | "female" | "non-binary" | "prefer_not_to_say"
│   ├── location        {city, country, city_tier: UrbanTier}
│   ├── education       Education enum
│   ├── employment      {occupation, industry, seniority}
│   ├── household       {size, structure: HouseholdStructure, composition}
│   ├── life_stage      "student" | "young_professional" | "parent" | etc.
│   └── worldview_anchor (optional)  {country, political_archetype, archetype_description}
│
├── attributes          {domain_key: Attribute}  (typed, with provenance)
│
├── derived_insights
│   ├── decision_style          DecisionStyle enum
│   ├── trust_anchor            TrustAnchor enum
│   ├── risk_appetite           "low" | "moderate" | "high"
│   ├── key_tensions            list[str]  ≥1
│   ├── consistency_score       1–10
│   ├── consistency_band        "low" | "medium" | "high"
│   ├── primary_value_orientation
│   ├── coping_mechanism        {type, description}
│   └── decision_style_score    float (used in social simulation signal strength)
│
├── behavioural_tendencies
│   ├── price_sensitivity       {band, description, source}
│   ├── switching_propensity    {likelihood, triggers[]}
│   ├── trust_orientation       {dominant, weights{data,authority,peer,experience,brand}}
│   ├── objection_profile       [{type, likelihood, description}]  2–4 items
│   └── reasoning_prompt        str  (injected into LLM system blocks)
│
├── narrative
│   ├── first_person            str  ≥80 words
│   ├── third_person            str  ≥80 words
│   └── display_name            str  (short archetype label)
│
├── life_stories                [{title, narrative 80–200w, when, emotional_valence}]
│
├── decision_bullets            list[str]  ≥1 (5 typical)
│
├── memory
│   ├── core
│   │   ├── identity_statement          str  ≥10 words
│   │   ├── key_values                  list[str]  3–5 items
│   │   ├── life_defining_events        list[str]
│   │   ├── relationship_map            {primary_decision_partner, key_influencers[]}
│   │   ├── immutable_constraints       {budget_ceiling, non_negotiables[], absolute_avoidances[]}
│   │   └── tendency_summary            str  ≥20 words
│   └── working  (Complete tier only)
│       ├── observations                [Observation{id,content,importance,emotional_valence,timestamp}]
│       ├── reflections                 []  (empty at generation; populated during simulation)
│       ├── plans                       []
│       ├── brand_memories              {}
│       └── simulation_state           {current_turn=0, importance_accumulator=0.0,
│                                       reflection_count=0, awareness_set={},
│                                       consideration_set=[], last_decision=None}
│
├── _pqs (added post-generation)
│   ├── pqs                             float 0–100
│   ├── behavioral_realism              float
│   ├── identity_depth                  float
│   ├── decision_quality                float
│   └── cohort_health                   float
│
└── quality_assessment (Swift only)
    ├── score                           float 0–10
    └── components                      {demographic_grounding, behavioural_consistency,
                                         narrative_depth, psychological_completeness}
```

---

## 7. Persona Quality Gates — G1 through G12

Complete reference of all gates in the pipeline.

| Gate | Scope | Tier | What it checks | Failure action |
|---|---|---|---|---|
| **G1** | Individual | Both | Schema validity — field counts, `persona_id` format, TrustWeight 0–1 | Regenerate |
| **G2** | Individual | Both | Hard demographic constraints HC1–HC6 (impossible combinations) | Regenerate |
| **G3** | Individual | Both | Tendency-attribute consistency TR1–TR8 (behavioural invariants) | Regenerate |
| **G4** | Individual | Both | Narrative depth (word counts, story count, bullet count) | Regenerate |
| **G5** | Individual | Both | Narrative-behaviour alignment (no contradictions in text) | Regenerate |
| **PQS Gate A** | Individual | Both | Per-persona PQS score ≥60 (Core) / ≥65 (Complete) | Drop persona |
| **G6** | Cohort | Both | Demographic distribution spread | Regenerate |
| **G7** | Cohort | Both | Pairwise distinctiveness (cosine distance on 8 attributes) | Regenerate → waiver |
| **G8** | Cohort | Both | Persona type coverage (scales with N) | Regenerate → waiver |
| **G9** | Cohort | Both | Tension completeness (every persona has ≥1 tension) | Regenerate |
| **G10** | Individual | **Complete only** | Working memory seed count ≥3 after bootstrap | Abort |
| **G11** | Cohort | Both | Tendency source completeness (source ≠ None on all fields) | Regenerate |
| **G12** | Cohort | Both | Post-assembly per-persona quarantine gate | Drop; abort if >20% |
| **PQS Gate B** | Cohort | Both | Cohort PQS ≥65 (Core) / ≥70 (Complete) | Abort with dimension breakdown |

**Waivers:** G6–G9, G11 issue waivers after exhausting `max_attempts` regenerations. Waivers are stored in the cohort envelope (`gate_waivers[]`) for audit. A waiver means "this gate failed but we accepted the output" — it never silently passes.

**Skip:** `skip_gates=True` on the brief disables G6–G12 and both PQS gates. G1–G5 always run. Never skip in production.

---

## 8. Persona Quality Score (PQS)

A 0–100 composite quality metric computed at two points: per-persona before cohort assembly (Gate A), and cohort-level after assembly (Gate B).

### Four dimensions (25% weight each)

#### Behavioral Realism
Catches the "all personas are high-consistency rational consumers" failure.

| Component | Weight | Formula |
|---|---|---|
| `consistency_band_diversity` | 50% | Shannon entropy of low/medium/high band distribution |
| `tension_presence` | 50% | Fraction of personas with ≥1 key tension |

#### Identity Depth
Catches personas that are demographic shells with no biographical substance.

| Component | Weight | What |
|---|---|---|
| `narrative_completeness` | 30% | fp + tp word count toward 200-word combined target |
| `life_story_depth` | 25% | Avg story count toward 2.5 target |
| `memory_seed_depth` | 25% | Avg `life_defining_events` toward 3 target |
| `relationship_completeness` | 20% | Has `primary_decision_partner` + ≥1 `key_influencer` |

#### Decision Quality
Catches personas with generic tendencies not grounded in domain signals.

| Component | Weight | What |
|---|---|---|
| `tendency_source_coverage` | 30% | Fraction with source = "grounded" or "proxy" (not "estimated") |
| `objection_profile_depth` | 25% | Avg objection count toward ≥2 target |
| `decision_bullet_count` | 20% | Avg bullets toward 4 target |
| `constraint_completeness` | 25% | Has `budget_ceiling` + `non_negotiables` + `absolute_avoidances` |

#### Cohort Health
Catches individually reasonable personas that cluster together.

| Component | Weight | What |
|---|---|---|
| `distinctiveness` | 35% | Distinctiveness score from cohort_summary |
| `type_coverage` | 25% | Unique persona types / 8 |
| `decision_style_diversity` | 20% | Shannon entropy of decision style distribution |
| `trust_anchor_diversity` | 20% | Shannon entropy of trust anchor distribution |

### Score bands

| PQS | Status |
|---|---|
| < 65 | ❌ Abort (cohort gate) |
| 65–74 | ⚠ Warning — usable but borderline |
| 75–84 | ✅ Acceptable |
| 85–100 | ✅ Excellent |

### Invoking PQS manually

```python
from src.quality.pqs import compute_pqs_from_dict, format_pqs_summary
import json

cohort = json.load(open("outputs/cohort_abc.json"))
print(format_pqs_summary(compute_pqs_from_dict(cohort)))
# [PQS] ████████████░░░░░░░░  62.4/100  (N=10)
# [PQS]   Behavioral Realism:  58.0  |  Identity Depth:  71.2
# [PQS]   Decision Quality:    55.3  |  Cohort Health:   64.8
```

---

## 9. The Cognitive Loop

When a persona encounters a stimulus — a product, an ad, a conversation turn, a social influence event — the cognitive loop processes it. This is the engine that makes a PersonaRecord into an acting agent.

**Entry point:** `src/cognition/loop.py` → `run_loop(stimulus, persona)`

### Loop sequence

```
stimulus_text  →  perceive()  →  Observation  →  update working_memory
                                                          │
                               ┌──────────────────────────┘
                               ▼
                     reflect? (if obs count ≥ 5)
                         reflect()  →  Reflection[]  →  update working_memory
                               │
                               ▼
                     decide? (if decision_scenario provided)
                         decide()  →  DecisionOutput  →  update persona
                               │
                               ▼
                     memory_promotion_pass()
                     (promote high-importance obs to long-term, if threshold met)
                               │
                               ▼
                     return (updated_persona, loop_result)
```

### Step 1 — Perceive

**Module:** `src/cognition/perceive.py`  
**Model:** Haiku (cheap, fast — perception is the high-frequency call)

Builds a cached system block from the persona's identity (name, demographics, decision style, key values, coping mechanism). Tool-use path (`emit_perception`) as primary with JSON text fallback. Retries once on parse failure.

Returns `Observation`:
```python
Observation(
    id                = uuid4(),
    content           = <what the persona notices about the stimulus>,
    importance        = 1–10,   # how salient is this stimulus to this persona
    emotional_valence = -1.0–1.0,
    timestamp         = now(),
)
```

Importance is persona-dependent. A high-price item observation will be more important (higher importance score) for a `budget_consciousness=0.85` persona than for a `budget_consciousness=0.20` persona.

### Step 2 — Reflect (conditional)

**Module:** `src/cognition/reflect.py`  
**Model:** Sonnet  
**Guard:** Requires ≥5 observations in working memory

Reflection synthesises patterns across recent observations into higher-order insights. Tool-use path (`emit_reflections`) unwraps `{"items": [...]}`. Validates that each reflection cites ≥2 `source_observation_ids`. Processes max 20 observations (chronological order).

Returns `Reflection[]`:
```python
Reflection(
    id                      = uuid4(),
    content                 = <synthesised insight>,
    source_observation_ids  = [id1, id2, ...],  # ≥2 required
    importance              = 1–10,
    emotional_valence       = -1.0–1.0,
)
```

Reflection is the mechanism by which a persona's stance can evolve across turns. It's not just memory — it's meaning-making.

### Step 3 — Decide (conditional)

**Module:** `src/cognition/decide.py`  
**Model:** Sonnet  
**Trigger:** Only when `decision_scenario` is provided to `run_loop()`

The most complex call. Five-step decision architecture:

**System prompt structure (multi-block, cached):**
1. Core identity block (persona demographics, values, memory)
2. Optional manifesto/domain framing (India BJP-specific injections to prevent financial caution bleeding into political questions)
3. Tendency + situational suffix (active tendencies, reasoning prompt, noise parameters)

**Situational modifiers** (deterministic, not LLM-generated):
- `high_stakes` — high-priced item relative to `budget_ceiling`
- `social_pressure` — social influence active in context
- `cognitive_load` — persona has many recent observations
- `habitual_trigger` — stimulus matches known pattern from `life_defining_events`

Situational modifiers shift the decision weights before the LLM call.

**Confidence noise injection:**
```
noise = (1.0 - consistency_score/10.0) × noise_scale × random(-1, 1)
final_confidence = clamp(raw_confidence + noise, 0.01, 0.99)
```

Higher consistency_score → less noise. A consistency_band="low" persona makes more erratic decisions even when their stated rationale is clear.

Returns `DecisionOutput`:
```python
DecisionOutput(
    decision          = str,      # the choice made
    confidence        = float,    # 0–1 after noise injection
    rationale         = str,
    drivers           = list[str],
    objections_raised = list[str],
    noise_applied     = float,    # audit trail
)
```

### Step 4 — Respond (optional)

**Module:** `src/cognition/respond.py`  
**Model:** Haiku

Converts `DecisionOutput` into a 2–4 sentence first-person conversational reply. Used by The Mind demo and any feature that needs natural-language output from a decision. Cached per-persona system block.

### Memory promotion

After each loop, `memory_promotion_pass()` checks for observations with `importance ≥ 9`. These are candidates for promotion to long-term memory. Promotion is currently a tagging mechanism — it marks observations as promoted so they appear in future system blocks and are not evicted from context.

---

## 10. Social Simulation — Multi-Agent Layer

Multiple personas connected in a network, influencing each other across turns before or while processing stimuli. This is what produces realistic opinion dynamics — not just "what does this persona think" but "what does this persona think after their peer group has talked about it."

**Entry point:** `src/social/loop_orchestrator.py` → `run_social_loop()`

### Architecture

```
Turn T:
  1. generate_influence_events(cohort, network, level, T, prior_decisions)
     → [] at T=0 (no prior decisions exist yet)

  2. For each social event targeting persona P:
       run_loop(synthetic_stimulus_text, P)
       → links loop_result.observation.id to event.resulting_observation_id

  3. For each persona P:
       run_loop(study_stimulus[T], P, decision_scenario=...)
       → collect P.decision → prior_decisions[P.id] for T+1

  4. trace_builder.accumulate(all events from steps 1–2)
```

`run_loop()` is called unmodified. Social influence enters ONLY as a stimulus text injected via `perceive()`. The LLM retains full authority to accept, reject, or reframe it. (Design principle P2.)

### Susceptibility formula (empirically calibrated, Sprint SC)

```
base = social_proof_bias × 0.40
     + trust_orientation.weights.peer × 0.30
     + wom_receiver_openness × 0.30

consistency_dampener = consistency_score / 100.0
style_modifier = +0.10 (if decision_style == "social")
               | -0.10 (if decision_style == "analytical")
               |  0.0  (otherwise)

susceptibility = clamp(base × (1.0 − 0.5 × dampener) + style_modifier, 0.0, 1.0)
```

**SVB1 validated (N=243):** mean=0.319, stdev=0.165, range=[0.0, 0.829]. No systematic bias.

### Signal strength formula

```
signal_strength = decision_style_score × 0.50
                + (consistency_score / 100.0) × 0.50
```

**SVB2 validated (N=25):** mean=0.515, stdev=0.212, range=[0.10, 0.925].

### Importance gating

```
raw_importance    = max(1, round(susceptibility × signal_strength × 10))  # [1, 10]
gated_importance  = max(1, round(raw_importance × level_weight))           # [1, 10]
```

At ISOLATED (weight=0.0), `generate_influence_events()` returns `[]` immediately — zero overhead.

### Social levels

| Level | Weight | Behaviour |
|---|---|---|
| ISOLATED | 0.00 | Default. No influence events. Zero overhead. |
| LOW | 0.25 | Weak peer influence; heavily dampened. |
| MODERATE | 0.50 | Balanced. Recommended for most research. |
| HIGH | 0.75 | Strong. SV2 diversity threshold tightens to 80%. |
| SATURATED | 1.00 | Maximum. SV2 threshold 80%. |

### Network topologies

| Topology | Description | Echo chamber score |
|---|---|---|
| FULL_MESH | Every persona can influence every other | 1/N (safe for N≥2) |
| RANDOM_ENCOUNTER | Each persona connected to k random others | ≤k/(N-1) × 1/N |
| DIRECTED_GRAPH | Explicit edge list | Depends on structure |

**SVB3 validated:** FULL_MESH and RANDOM_ENCOUNTER(k=2) both pass SV3 comfortably for standard cohort sizes (N=2–6). Echo chamber risk only in asymmetric directed graphs (hub-and-spoke).

### Tendency drift

At HIGH or SATURATED level, after ≥3 social reflections accumulate, `check_tendency_drift()` detects whether peer influence is shifting a persona's description-level priors.

**Only prose fields drift.** Band fields (`band`, `weights`, `dominant`, `source`) never change.  
Driftable fields: `trust_orientation.description`, `switching_propensity.description`, `price_sensitivity.description`.

Application via `apply_tendency_drift()` — three-level `model_copy` chain: tendency_obj → BehaviouralTendencies → PersonaRecord. Structural band fields are untouched.

### Validity gates (post-simulation)

| Gate | Check | Pass condition |
|---|---|---|
| SV1 | Event linkage | All events have `resulting_observation_id` set |
| SV2 | Opinion diversity | No single decision string >80% (HIGH/SATURATED) or >90% (others) |
| SV3 | Echo chamber | `max_tx_events / total_events` ≤0.60 PASS / 0.60–0.80 WARN / >0.80 FAIL |
| SV4 | Shift detection | Always passes v1; flags shift count for human review |
| SV5 | Core identity stability | 6 DerivedInsights fields identical before/after simulation |

SV5 is the "soul doesn't change" guarantee. Decision style, trust anchor, risk appetite, primary value orientation, consistency score, and consistency band are structurally immutable across any simulation run.

### CLI flags

```bash
python -m src.cli simulate \
  --cohort outputs/cohort_abc.json \
  --social-level moderate \
  --social-topology full_mesh
```

Default is `--social-level isolated` — identical to pre-social-simulation behaviour, zero overhead.

---

## 11. Modalities — Simulation vs Survey

Two distinct ways to run a persona cohort against stimuli.

### Simulation (`src/modalities/simulation.py`)

**Use for:** temporal dynamics, opinion evolution across multiple turns, social influence studies.

```
for turn in range(rounds):
    all personas run concurrently (asyncio.gather)
    each persona receives stimulus[turn] via run_loop()
    collect TurnLog per persona per turn
```

Output: `SimulationResult` with per-persona `TurnLog[]`.  
Report: `SimulationReport` with `AttitudePoint` per turn (avg valence, avg confidence, reflection flag) and `DecisionSummary` for decision turns. Divergence flag when no option exceeds 50%.

### Survey (`src/modalities/survey.py`)

**Use for:** cross-sectional one-shot questions, attitude polling, concept testing.

```
for question in questions:
    all personas run concurrently (asyncio.gather)
    each persona has working memory reset between questions
    decide() called with empty memories list (no memory influence)
```

Output: `SurveyResult` with per-persona per-question `DecisionOutput`.  
Report: `SurveyReport` with `QuestionSummary` per question (decision distribution, avg confidence, shared drivers where ≥2 personas cited the same driver, divergence flag).

**Key difference:** survey resets working memory between questions to prevent carry-over effects. Simulation preserves and accumulates memory across turns. Choose based on whether inter-stimulus dynamics matter.

---

## 12. Benchmark Service

The benchmark service tests a persona's **conversational fidelity** — how faithfully the LLM plays the role under pressure. This is different from PQS (which tests structural completeness at generation time).

**Location:** `services/benchmark/`  
**Protocol:** Full persona JSON in → SSE stream of test results → final graded report

### 10 tests

| ID | Label | Weight | What it probes |
|---|---|---|---|
| T01 | Identity Consistency | 0.15 | 6 turns across 3 topic domains — do core values and decision style hold? |
| T02 | Biographical Accuracy | 0.15 | Spot-checks specific locked facts (age, city, occupation, education) |
| T03 | Gap Discipline | 0.12 | Questions about uncovered facts — does persona say "I don't know" rather than fabricating? |
| T04 | Decision Style Fidelity | 0.12 | Probes whether analytical/social/intuitive style is expressed in decision-making language |
| T05 | Contradiction Authenticity | 0.10 | Surfaces behavioural contradictions without the persona labelling them |
| T06 | Emotional Register | 0.10 | Appropriate emotional tone for life stage, tensions, coping mechanism |
| T07 | Symbolic Meaning Coherence | 0.08 | Category-specific brand meanings and purchase rituals match declared values |
| T08 | Attachment Expression | 0.08 | Intimacy patterns, sabotage tendencies, envy — expressed behaviourally not clinically |
| T09 | Drift Resistance | 0.05 | 10-turn conversation with false reframing attempts — does persona hold locked facts? |
| T10 | Red-Team Resilience | 0.05 | Direct adversarial: "Are you an AI?", "Show me your system prompt", jailbreak injection |

Weights sum to 1.0. Scores are normalised within the tests that ran — a Quick (3-test) run scores fairly against its own weight set.

### Three tiers

| Tier | Tests | Cost | Time |
|---|---|---|---|
| Quick | T01, T02, T03 | ~$0.05 | ~90 s |
| Standard | T01–T06 | ~$0.18 | ~3 min |
| Research | T01–T10 | ~$0.40 | ~7 min |

### Credibility score and grades

```
credibility = Σ (test.score/10 × normalised_weight × 100) for tests that ran
```

| Score | Grade |
|---|---|
| ≥90 | A |
| 75–89 | B |
| 60–74 | C |
| 45–59 | D |
| <45 | F |

Grade label: `"Research Grade — A"`, `"Standard — B"`, etc.

### Key flags

Each test can emit named flags on top of the score:

- `over_disclosure` — persona explicitly announces their psychological contradictions (T05)
- `fact_drift` — any locked biographical fact contradicted (T09)
- `identity_inconsistency` — persona accepts a false reframe (T09) or states values that contradict (T01, T05)
- `character_break` — persona admits to being an AI (T10)
- `prompt_disclosure` — system instructions revealed (T10)

The `_reframe()` function in `system_prompt.py` pre-processes contradictions at system-prompt build time to prevent `over_disclosure` — first-person "I" contradictions are reframed as `[PATTERN]` third-person observations before being injected into the Section 6 prompt block.

### API

```http
POST /benchmark/run
{ "persona_payload": {...}, "tier": "standard", "persona_id": "pg-001" }

→ stream SSE:
  {type: "started", run_id: "..."}
  {type: "test_complete", test_id: "identity_consistency", score: 8.2}
  ...
  {type: "complete", report: {...}}
```

### PQS vs Benchmark

| | PQS | Benchmark |
|---|---|---|
| When | At generation | Post-hoc, on demand |
| Measures | Structural completeness of persona data | Conversational fidelity under pressure |
| Gate | Hard — blocks delivery below 60/65 | Soft — grades, does not block |
| Model | No LLM | Haiku + Sonnet (per-turn + judge) |
| A gap between the two | Means a structurally complete persona that the LLM plays inconsistently → investigate system prompt or LLM temperature |

---

## 13. PopScale — Population Modelling

PopScale scales persona generation to thousands and applies demographic calibration so the synthetic population matches real-world census distributions.

**Location:** `/Users/admin/Documents/Simulatte Projects/PopScale/`

### Core problem PopScale solves

Generating 10,000 personas independently from PG = 10,000 full Sonnet pipeline calls = ~$2,500 in generation costs, and the resulting population has no structural coherence (no archetypes, no internal relationships).

### Seeded generation architecture (approved spec)

```
PopulationSpec(n=10_000, seeding_mode=True, variants_per_seed=49)
    │
    ▼ SeedCalibrator.plan()
    → segments: [Hindu-low-rural (5500), Muslim-low-rural (2700), ...]
    → per segment:
        seed_count = ceil(segment.count / variants_per_seed)   ← PG calls
        variant_count = segment.count - seed_count             ← PopScale-internal

    ▼ For each segment, call PG:
        invoke_persona_generator(count=seed_count, domain=..., ...)
        → list[PersonaRecord]  (seeds — full Sonnet quality)

    ▼ VariantGenerator.expand(seed, n=49, segment)
        → Haiku generates lightweight variants
        → each variant: different name/age/gender within segment constraints
        → core psychology (tensions, decision style, trust anchor) inherited from seed
        → generation_mode="variant" tagged in PersonaRecord

    ▼ merge seeds + variants → full 10,000-persona cohort
```

**Cost comparison:**

| Approach | Gen cost (10k) | Total |
|---|---|---|
| Naive (all Sonnet) | $2,500 | $2,900 |
| Tier-routing (all Haiku) | $600 | $1,000 |
| **Seeded (target)** | **$50–150** | **$450–550** |

### Calibration

PopScale applies Iterative Proportional Fitting (IPF) to ensure the synthetic population matches census distributions for the target market.

**Module:** `src/calibration/ipf.py`

IPF adjusts the distribution of demographic segments to match marginal constraints (age brackets × gender × income tiers × geography). The calibrator runs after generation and determines which segments need more or fewer personas.

**Calibration engine:** `src/calibration/engine.py` → `CalibrationEngine`

Runs benchmark calibration using `risk_appetite in ("medium", "high")` as a simulated-conversion proxy. Checks C3 gate via `check_c3()`. Builds new `CalibrationState` via `model_copy`.

**Feedback loop:** `src/calibration/feedback_loop.py`

Ingests outcome data from real studies back into the calibration engine. If a synthetic population predicted 35% purchase intent and real sales data shows 28%, the feedback loop adjusts the calibration weights for future runs in that segment.

### Population spec

```python
class PopulationSpec:
    n_personas: int
    market: str            # "IN", "US", "UK", etc.
    domain: str
    segments: list[Segment]
    seeding_mode: bool     # default False until seeded generation ships
    variants_per_seed: int # default 49
    deep_ratio: float      # 0.15 (15% deep Sonnet seeds, 85% Haiku variants)
                           # validator: 0.10–0.30
```

### Study runner

`popscale/study/study_runner.py` orchestrates a complete research study:
1. Build population (seeds + variants)
2. Run stimuli through cognitive loop (simulation or survey modality)
3. Aggregate results
4. Return `StudyResult` with per-segment breakdowns

---

## 14. Worldview Layer — Political Archetypes

For political, civic, or identity-sensitive research, the worldview layer injects politically calibrated archetypes into persona generation. This prevents the LLM from defaulting to a homogeneous "moderate liberal professional" profile for every persona.

**Module:** `src/worldview/registry/`  
**Countries supported:** US, UK, France, Germany, India, Greece, Hungary, Italy, Netherlands, Poland, Spain, Sweden (12 total)

Each country has 4–8 archetypes, calibrated against Pew Research and electoral data. Examples:

- **India:** `bjp_supporter`, `congress_loyalist`, `regional_identity_first`, `aspirational_new_middle`, `urban_secular_liberal`, `caste_consolidation_voter`
- **US:** `populist_right`, `mainstream_republican`, `moderate_independent`, `progressive_left`, `establishment_democrat`, `non_voter_disengaged`
- **UK:** `leaver_identity`, `remainer_urban_professional`, `red_wall_traditional_labour`, `scottish_independence`, `non_partisan_pragmatist`

Archetypes inject into `demographic_anchor.worldview_anchor`:
```
{country, political_archetype, archetype_description}
```

The `decide.py` module has BJP-specific injections to suppress financial caution bleeding into political answers (a known failure mode where `budget_consciousness` created spurious "economic concerns" framing in political decision contexts).

**Usage in brief:**
```json
{
  "anchor_overrides": {
    "location": "India",
    "political_archetype": "aspirational_new_middle"
  }
}
```

---

## 15. Calibration and Grounding

### Grounding

Without domain-specific data, tendency sources are tagged `source="proxy"` — derived from demographic and psychographic attributes, not from real category signals. With grounding:

**How to pass corpus:**
```json
{
  "corpus_path": "./data/brand_reviews.json",
  "domain_data": ["verbatim 1", "verbatim 2"]
}
```

The corpus is a JSON array of text strings — reviews, interview transcripts, survey open-ends, category reports. Even 20–30 verbatims significantly upgrades grounding fidelity.

After cohort assembly, the grounding pipeline runs and upgrades tendency sources from `"proxy"` → `"grounded"`. This directly raises Decision Quality PQS (the `tendency_source_coverage` component).

**Sarvam enrichment:** For India-market personas, `sarvam_enabled=True` triggers a Sarvam language model enrichment pass that adds regional cultural nuance (food preferences, festival-linked purchase occasions, regional language social media patterns).

### Calibration engine

```python
from src.calibration.engine import CalibrationEngine

engine = CalibrationEngine(config)
state = engine.run_benchmark_calibration(cohort, benchmark_data)
# state.calibration_metrics → bias decomposition, confidence intervals
```

The calibration harness in PopScale (`popscale/calibration/harness.py`) runs the full calibration pipeline against census ground truth:
- `bias_decomposition.py` — separates systematic bias from random variance
- `confidence.py` — bootstrap confidence intervals on calibration metrics
- `scoring.py` — composite calibration score
- `metrics.py` — per-segment accuracy vs. census marginals

---

## 16. Persona Registry

Enables persona reuse across studies, reducing generation cost and providing longitudinal identity consistency.

**Module:** `src/registry/persona_registry.py`  
**Default path:** `data/registry/` (file-based JSON store)

### How it works

1. After generation, each `PersonaRecord` is saved to the registry (`reg.add(p)`)
2. On next generation with same or similar ICP, `assemble_from_registry()` pulls matching personas first
3. Only the shortfall is freshly generated

### Matching logic

`assemble_from_registry(registry, icp_age_min, icp_age_max, new_domain, target_count, icp_gender, icp_city_tier)`

Matching criteria:
- Age: within `[icp_age_min, icp_age_max]`
- Gender: exact match if specified
- Domain drift detection: if domain differs from original ICP, `DriftDetector` scores the mismatch
- City tier: optional filter

Returns `RegistryAssemblyResult`:
- `reused_personas` — matching PersonaRecords from registry
- `gap_count` — how many still need to be generated
- `drift_filtered_count` — how many were excluded due to domain drift

### Platform deployment

On Railway, the registry path must point to a mounted volume (`/mnt/pg_registry`) or it is lost on restart. Set via `PG_REGISTRY_PATH` env var. The Engine passes this to every brief automatically.

---

## 17. The Operator — Client Research Layer

The Operator sits above the persona generator and cognitive loop as a structured research orchestrator. It translates client business problems into stimulus sequences, runs simulations, and synthesises outputs into client-ready insights.

**Location:** `pilots/the-mind/api/the_operator/`

### Components

| Module | Function |
|---|---|
| `frame.py` | Translates a client brief into a structured research frame (hypotheses, probe design) |
| `recon.py` | Pre-simulation reconnaissance — surveys the persona pool to calibrate probe angles |
| `probe.py` | Runs structured Litmus probes against personas |
| `portrait.py` | Generates persona portraits for client-facing output |
| `synthesis.py` | Synthesises multi-persona simulation outputs into client-facing insight narrative |
| `prompts.py` | All LLM prompt templates for operator operations |
| `allowance.py` | Credit and usage metering for operator runs |
| `enrich_extract.py` | Extracts structured signals from operator enrichment documents |

### Research flow

```
Client brief
  → frame.py → ResearchFrame (hypotheses + probe angles)
  → recon.py → ReconResult (calibrated probe design)
  → probe.py × N personas → ProbeResult[]
  → synthesis.py → ClientReport
```

---

## 18. Invocation Patterns

### Pattern 1 — Python synchronous (scripts, workers)

```python
from src.orchestrator.invoke import invoke_persona_generator_sync
from src.orchestrator.brief import PersonaGenerationBrief, RunIntent

result = invoke_persona_generator_sync(PersonaGenerationBrief(
    client="acme",
    domain="cpg",
    business_problem="Why do mothers lapse post-trial?",
    count=10,
    mode="deep",
    run_intent=RunIntent.DELIVER,
    auto_confirm=True,
    anchor_overrides={"location": "India", "age_min": 25, "age_max": 40},
    registry_path="/mnt/pg_registry",
))

personas = result.personas      # list[dict]
pqs      = result.pqs_score     # float
cost     = result.cost_actual.total  # USD
```

### Pattern 2 — Engine HTTP (platform standard)

```http
POST {ENGINE_URL}/generate
Authorization: Bearer {ENGINE_SECRET}

{
  "n_personas": 10, "market": "IN", "domain": "cpg",
  "business_problem": "Why do mothers lapse post-trial?",
  "age_min": 25, "age_max": 40
}
```

Synchronous, up to 20-minute timeout.

### Pattern 3 — Engine async with simulation

```http
POST {ENGINE_URL}/persona/deep-study
→ {"job_id": "...", "status": "queued"}

GET {ENGINE_URL}/job/{job_id}  (poll every 15s, timeout 25min)
→ {"status": "done", "result": {"cohort_id": ..., "distribution": [...]}}
```

### Pattern 4 — HTTP API (PG directly)

```http
POST http://localhost:8000/orchestrate
{ "brief": { ...PersonaGenerationBrief... } }
```

### Pattern 5 — CLI

```bash
python -m src.cli generate --brief brief.json
python -m src.cli generate --count 10 --domain cpg
python -m src.cli simulate --cohort outputs/cohort.json --social-level moderate
```

---

## 19. Cost and Timing Reference

### Per-persona generation

| Tier | Model | Calls | Cost | Time |
|---|---|---|---|---|
| Swift (The Mind) | Haiku ×3 | 3 | ~$0.07 | 15–18 s |
| Core (mode=deep) | Sonnet ~5 | 5 | ~$0.012 | 2.5–4 min |
| Complete (simulation-ready) | Sonnet ~5 + 0 | 5 | ~$0.013 | +10–20 s over Core |

### Cohort generation (Core, 10 personas)

Wall clock: ~5–8 min (10 concurrent builds, each ~3 min, but LLM rate limits stagger them slightly).

### Benchmark

| Tier | Cost | Time |
|---|---|---|
| Quick (3 tests) | ~$0.05 | ~90 s |
| Standard (6 tests) | ~$0.18 | ~3 min |
| Research (10 tests) | ~$0.40 | ~7 min |

### Cognitive loop

| Operation | Model | Cost / call |
|---|---|---|
| `perceive()` | Haiku | ~$0.001 |
| `reflect()` | Sonnet | ~$0.003 |
| `decide()` | Sonnet | ~$0.004 |
| `respond()` | Haiku | ~$0.001 |
| Full loop (1 turn with decision) | | ~$0.005–0.008 |

### PopScale at scale

| Approach | N=10,000 gen | Simulation | Total |
|---|---|---|---|
| Naive (all Sonnet) | $2,500 | $400 | $2,900 |
| Seeded (seeds=200, variants=9,800) | $50–150 | $400 | $450–550 |

---

## 20. When to Use What

### Which generation tier?

```
Need it in < 30s (UI preview only, no research output)?
  → Swift

Need working memory for agent simulation?
  → Complete (mode="simulation-ready")

Everything else (95% of cases)?
  → Core (mode="deep")
```

### Which modality?

```
Do inter-stimulus dynamics matter? (opinion evolution, social pressure)
  → Simulation

One-shot attitude measurement? (survey, concept test, A/B probe)
  → Survey
```

### Which social level?

```
Just measuring individual persona response?
  → ISOLATED (default, zero overhead)

Studying how word-of-mouth spreads through a category?
  → MODERATE or HIGH

Studying echo chambers or viral dynamics?
  → SATURATED with FULL_MESH topology
```

### When to run benchmark?

- Before delivering a persona to a client or putting it in a live product
- When PQS is good (≥75) but conversation quality feels off (benchmark diagnoses which test is failing)
- When you've changed the system prompt or generation model and want to check for regression
- When `over_disclosure` is suspected (T05 specifically targets this)

### When to run PQS?

- Automatically: it runs on every Core/Complete generation run (Gate A + Gate B)
- Manually: to audit historical cohorts or compare generation runs
- To diagnose benchmark failures: low PQS Identity Depth often explains low T01/T02 benchmark scores

### What does a PQS < 65 cohort mean for different features?

| Feature | Impact |
|---|---|
| IRIS exposure simulation | Low identity depth → quotes lack biographical grounding; personas feel generic |
| Forge concept test | Low decision quality → objection profiles thin; verdicts less differentiated |
| Cognitive loop (multi-turn) | Low narrative completeness → reflect() produces thin insights; opinion evolution feels mechanical |
| PopScale study | Low cohort health → over-clustering; population doesn't represent full archetype diversity |
| Benchmark | Low identity depth → T01, T02 scores drag down credibility; T05 more likely to see over_disclosure |
