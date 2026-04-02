# SIMULATTE PERSONA GENERATOR — V1 SPRINT PLAN
**Tech Lead document. Owner: Claude (Tech Lead)**
**Date:** 2026-04-02
**Govering spec:** `SIMULATTE_PERSONA_GENERATOR_MASTER_SPEC.md` v1.2

---

## How This Plan Works

Each sprint has five engineer slots: Cursor, Codex, Goose, OpenCode, Antigravity.
Not all engineers are assigned every sprint — idle slots are noted.
Each sprint produces individual briefs: `sprints/current_brief_[engineer].md`
On completion each engineer writes: `sprints/outcome_[engineer].md`
Tech Lead (me) reviews outcomes, runs spec alignment check, issues ratings, archives, writes next briefs.

**The spec check is not optional.** At the start of every sprint brief I document which master spec sections govern that sprint's work. At the end of every outcome review I verify no settled decision was violated.

---

## V1 Scope — What We Are Building

From Master Spec Section 14C, v1 REQUIRED components are:

**Phase 1 — Identity + Memory (the product):**
- Base taxonomy (~150 attributes, 6 categories)
- Progressive conditional attribute filling, anchor-first ordering
- 5:3:2 stratification
- Hard + soft constraint checker
- Life story generation
- Narrative generation (first-person + third-person)
- Persona type system (8 types)
- Core memory structure
- Working memory (observations, reflections)
- Memory write, retrieve, evict operations
- Reflection trigger + generation
- Perceive engine
- Reflect engine
- Decide engine (5-step)
- Working memory reset (per experiment)

**Phase 1 product modalities (end-to-end):**
- One-time survey
- Temporal simulation

**Out of v1:**
- Grounding pipeline (domain data → clusters) — RECOMMENDED SOON AFTER v1
- Calibration — LATER-PHASE
- Multi-user, database, API — LATER-PHASE
- Social interaction, real-time feeds — OUT OF SCOPE

---

## Sprint Map

| Sprint | Name | Phase | Engineers | Primary Deliverable |
|--------|------|-------|-----------|---------------------|
| **S1** | Foundation: Schema + Taxonomy | 1 | Cursor, Codex, Goose, OpenCode, Antigravity | Pydantic schema, base taxonomy, attribute filler stub, domain templates, constraint checker |
| **S2** | Identity Constructor | 1 | Cursor, Codex, Goose | Progressive filling pipeline, life story generation, narrative generation |
| **S3** | Memory Architecture | 1 | Goose, OpenCode, Antigravity | Core/working split, write/retrieve/evict, seed memory bootstrap |
| **S4** | Cognitive Loop | 1 | Codex, Goose, Cursor | Perceive, reflect, decide engines with prompt templates |
| **S5** | Cohort Assembly + Experiment Modularity | 1 | Cursor, Codex, OpenCode, Antigravity | Cohort builder, distinctiveness check, working memory reset, type coverage |
| **S6** | One-Time Survey Modality | 1 | Codex, Goose, Antigravity | End-to-end survey runner with structural quality gates |
| **S7** | Temporal Simulation Modality | 1 | All 5 | End-to-end simulation runner with BV1–BV6 tests |

---

## Sprint 1 — Foundation: Schema + Taxonomy

**Spec sections governing this sprint:**
- Master Spec §5 (Persona Record Structure) — defines the schema
- Master Spec §6 (Taxonomy Strategy) — defines base taxonomy + filling order
- Master Spec §10 (Constraint System) — defines hard/soft constraints + tendency-attribute rules
- Master Spec §14A S3 (settled: anchor-first), S5 (settled: 5:3:2), S6 (settled: progressive filling)
- Validity Protocol Gates G1, G2, G3 (schema, hard constraint, tendency-attribute)

**Start-of-sprint spec check:**
Before any code is written, verify:
- [ ] Schema matches Master Spec §5 exactly — no additional fields, no missing fields
- [ ] Taxonomy categories match §6 Layer 1 — 6 categories, ~150 attributes total
- [ ] Anchor-first list matches §6 (8 defined core attributes)
- [ ] Hard constraints match §10 table exactly
- [ ] No domain-specific attributes in base taxonomy (P8 principle)

**Deliverables:**
```
src/
  schema/
    persona.py          ← Pydantic models for full persona record (Cursor)
    cohort.py           ← Pydantic models for cohort envelope (Cursor)
    validators.py       ← G1, G2, G3 automated validation (Antigravity)
  taxonomy/
    base_taxonomy.py    ← ~150 attributes across 6 categories (Codex)
    domain_templates/
      cpg.py            ← Consumer packaged goods template (OpenCode)
      saas.py           ← SaaS/B2B template (OpenCode)
      template_loader.py ← Template selection + extension merge (OpenCode)
  generation/
    attribute_filler.py ← Progressive filling, anchor-first logic (Goose)
    stratification.py   ← 5:3:2 cosine-distance stratification (Antigravity)
    constraint_checker.py ← Hard/soft constraint validation (Antigravity)
```

**Engineer assignments:**
- **Cursor** → `schema/persona.py`, `schema/cohort.py`
- **Codex** → `taxonomy/base_taxonomy.py`
- **Goose** → `generation/attribute_filler.py`
- **OpenCode** → `taxonomy/domain_templates/` + `template_loader.py`
- **Antigravity** → `schema/validators.py`, `generation/stratification.py`, `generation/constraint_checker.py`

**Acceptance criteria (from Validity Protocol):**
- G1: Every sample persona parses without Pydantic error
- G2: Hard constraint checker correctly rejects all 6 impossible combinations
- G3: Tendency-attribute consistency checker correctly flags all 8 rule violations
- Taxonomy: all 6 categories present, total attribute count 130–180
- Anchor-first: filling sequence starts with exactly the 8 defined core attributes
- Stratification: a cohort of 10 produces 5/3/2 distribution within ±1 tolerance
- Domain templates: CPG and SaaS templates each define 30–60 domain-specific attributes

**End-of-sprint spec check:**
- [ ] No coefficients in the schema (P4 — behavioural_tendencies are bands + descriptions, not floats)
- [ ] No domain-specific attributes in base_taxonomy.py (P8)
- [ ] All tendency fields carry a `source` field (P10)
- [ ] No settled decisions violated (review 14A)

---

## Sprint 2 — Identity Constructor

**Spec sections governing this sprint:**
- Master Spec §6 (progressive conditioning, filling order)
- Master Spec §5 (life_stories, narrative, derived_insights schemas)
- Master Spec §10 (narrative constraints)
- Master Spec §14A S4 (anchor-first), S6 (progressive filling), S14 (narrative constrained by attributes)

**Deliverables:**
```
src/
  generation/
    identity_constructor.py   ← Orchestrates full identity build sequence
    life_story_generator.py   ← LLM call: generate 2-3 life story vignettes
    derived_insights.py       ← Deterministic computation of decision_style, trust_anchor, etc.
    narrative_generator.py    ← LLM call: first-person + third-person narrative
    tendency_estimator.py     ← Proxy formula computation (source: "proxy")
```

**Engineer assignments:**
- **Cursor** → `identity_constructor.py` (orchestration, sequence control)
- **Codex** → `life_story_generator.py`, `narrative_generator.py` (LLM prompt templates)
- **Goose** → `derived_insights.py`, `tendency_estimator.py` (deterministic computation)
- **OpenCode** → idle (prepares domain template expansions for S3)
- **Antigravity** → G4, G5 validators (narrative completeness + alignment checks)

**Acceptance criteria:**
- G4: 100% narrative completeness on 10 sample personas
- G5: 0 narrative-attribute contradictions on 10 sample personas
- G9: 100% of personas have ≥ 1 documented tension
- Derived insights: decision_style, trust_anchor, risk_appetite computed deterministically from attributes (no LLM call)
- Tendency source: all tendencies marked `source: "proxy"` when no domain data provided

---

## Sprint 3 — Memory Architecture

**Spec sections governing this sprint:**
- Master Spec §8 (Memory Architecture — all subsections)
- Master Spec §5 (memory schema — core + working)
- Master Spec §14A S3 (core/working split settled), S17 (promotion rules settled), S18 (experiment isolation settled)

**Deliverables:**
```
src/
  memory/
    core_memory.py        ← Core memory assembly from persona record
    working_memory.py     ← Working memory CRUD (write, retrieve, evict, reset)
    retrieval.py          ← Retrieval formula: α·recency + β·importance + γ·relevance
    reflection_store.py   ← Reflection entry storage + citation validation
    seed_memory.py        ← Bootstrap ≥ 3 seed memories from core memory
```

**Engineer assignments:**
- **Goose** → `working_memory.py`, `retrieval.py` (core logic)
- **OpenCode** → `core_memory.py`, `seed_memory.py` (assembly + bootstrap)
- **Antigravity** → G10 validator (seed memory count), eviction logic, isolation test
- **Cursor** → idle (prepares S4 prompt templates)
- **Codex** → idle (prepares perceive prompt)

**Acceptance criteria:**
- G10: ≥ 3 seed memories per persona after bootstrap
- Retrieval: formula produces correct top-K ranking on synthetic test set
- Eviction: cap at 1,000 entries, evicts lowest 10% by importance × recency
- Isolation: `reset_working_memory()` clears all working fields; core untouched
- Promotion: only fires when importance ≥ 9, ≥ 3 citations, no contradiction; never promotes demographics

---

## Sprint 4 — Cognitive Loop

**Spec sections governing this sprint:**
- Master Spec §9 (Cognitive Loop — all subsections including prompt structures)
- Master Spec §14A S1 (LLM is cognitive engine — settled), P2 principle
- Constitution P1, P2, P4 — most critical sprint for drift prevention

**Deliverables:**
```
src/
  cognition/
    perceive.py     ← Haiku call: score importance + valence through persona's lens
    reflect.py      ← Sonnet call: synthesize 2-3 insights from top-20 observations
    decide.py       ← Sonnet call: 5-step reasoning chain → decision + confidence + trace
    loop.py         ← Orchestrates perceive → remember → reflect → decide cycle
```

**Engineer assignments:**
- **Cursor** → `loop.py` (orchestration, trigger logic, accumulator management)
- **Codex** → `perceive.py`, `reflect.py`, `decide.py` (all three prompt templates + LLM calls)
- **Goose** → integration with memory (retrieval calls, write calls inside loop)
- **OpenCode** → idle
- **Antigravity** → BV1 test harness (repeated-run stability), BV2 test (memory-faithful recall)

**Acceptance criteria:**
- BV1: ≥ 2/3 runs same decision on 3-persona test set
- BV2: 100% citation validity; ≥ 80% high-importance recall
- Reflect: every reflection carries ≥ 2 source_observation_ids (rejected otherwise)
- Decide: 5-step structure always present in output; tendency_summary always in context
- Loop: accumulator increments on every perceive(); reflection fires when > 50; resets after

**Critical drift check (end of sprint):**
- [ ] Verify: decide() does NOT compute a probability before the LLM call (P4 violation)
- [ ] Verify: tendency_summary is injected as natural language, not as numerical weights (P4)
- [ ] Verify: core memory is in context for every LLM call in perceive/reflect/decide (settled S11)

---

## Sprint 5 — Cohort Assembly + Experiment Modularity

**Spec sections governing this sprint:**
- Master Spec §11 (Distinctiveness Enforcement)
- Master Spec §14A S18 (experiment isolation settled)
- Validity Protocol G6, G7, G8, G9, G11

**Deliverables:**
```
src/
  cohort/
    assembler.py          ← Assembles N personas into a validated cohort envelope
    type_coverage.py      ← Enforces 8-type system + coverage rules per cohort size
    diversity_checker.py  ← G6 distribution checks (city, age, income)
    distinctiveness.py    ← G7 mean pairwise cosine distance on 8 core attributes
  experiment/
    modality.py           ← Experiment type enum + working memory reset logic
    session.py            ← Experiment session: ties persona + stimuli + modality
```

**Engineer assignments:**
- **Cursor** → `assembler.py`, `session.py`
- **Codex** → `type_coverage.py`
- **OpenCode** → `diversity_checker.py`, `distinctiveness.py`
- **Antigravity** → G6, G7, G8, G9, G11 automated gate runner
- **Goose** → idle (prepares S6 survey runner)

**Acceptance criteria:**
- G6: Distribution checker correctly flags city > 20%, age bracket > 40%
- G7: Distinctiveness > 0.35 enforced; resampling triggered when below
- G8: Type coverage rules enforced for N=3, 5, 10
- G9: Tension completeness check correctly flags personas without tensions
- Reset: `reset_working_memory()` verified idempotent; core memory unchanged after reset

---

## Sprint 6 — One-Time Survey Modality

**Spec sections governing this sprint:**
- Master Spec §1 (Four Product Modalities — survey)
- Validity Protocol G1–G9, G11, BV4 (interview realism), BV5 (adjacent distinction)

**Deliverables:**
```
src/
  modalities/
    survey.py           ← Survey runner: present questions → collect responses via decide()
    survey_report.py    ← Output formatting: per-persona responses + cohort summary
tests/
  test_survey_e2e.py    ← End-to-end test: ICP Spec → cohort → survey → report
```

**Acceptance criteria:**
- Full pipeline runs: ICP Spec → generate cohort (5 personas) → run 5-question survey → produce report
- G1–G9, G11 all pass on generated cohort
- BV4: ≥ 3/5 responses cite life story detail on at least 2 personas
- BV5: Two adjacent personas produce < 50% shared language in survey responses

---

## Sprint 7 — Temporal Simulation Modality

**Spec sections governing this sprint:**
- Master Spec §1 (temporal simulation modality)
- Master Spec §9 (full cognitive loop in simulation)
- Validity Protocol S1–S4, BV1–BV6

**Deliverables:**
```
src/
  modalities/
    simulation.py         ← Simulation runner: stimulus sequence → per-turn perceive/reflect/decide
    simulation_report.py  ← Per-turn decision log, attitude evolution, cohort summary
tests/
  test_simulation_e2e.py  ← 10-stimulus sequence, 5 personas, all BV tests
```

**Acceptance criteria:**
- S1: 5-persona trial run completes without error
- S2: No single decision > 90% of cohort
- BV1: Repeated-run stability on 3 sample personas
- BV2: Memory-faithful recall on 3 sample personas
- BV3: Temporal consistency across positive arc
- BV6: ≥ 1/2 override scenarios produce motivated departure

---

## Spec Alignment Check Template

Used at the start and end of every sprint.

```
SPEC ALIGNMENT CHECK — Sprint [N] [start/end]
=============================================
Date: [date]
Sprint: [name]

GOVERNING SECTIONS REVIEWED:
□ [section numbers]

SETTLED DECISIONS CHECKED (Master Spec 14A):
□ No coefficient parameters introduced (S2, P4)
□ LLM remains cognitive engine (S1, P2)
□ Memory not deferred (S3, P3)
□ Core memory immutable (S3, S17)
□ Domain-agnostic core (S9, P8)
□ Tendencies carry source labels (S13, P10)
□ Every persona has ≥ 1 tension (S10, P9)

ANTI-PATTERNS CHECKED (Constitution Part II):
□ No coefficient creep (A1)
□ Narrative not decorative (A2)
□ Memory not deferred (A3)
□ No domain leakage into base taxonomy (A4)
□ No validation theater — BV tests run (A5)

RESULT: [ ] ALIGNED  [ ] DRIFT DETECTED
If drift: [describe what drifted and corrective action]
```

---

## Engineer Rating Dimensions

After each sprint, each engineer is rated 1–5 on four dimensions:

| Dimension | What It Measures |
|-----------|-----------------|
| **Spec adherence** | Did the output match the brief without unsolicited deviations? |
| **Output completeness** | Were all deliverables produced and functional? |
| **Code quality** | Is the code readable, appropriately structured, and without obvious bugs? |
| **Acceptance criteria** | Did the output pass the tests and gates specified in the brief? |

Ratings are embedded in the next sprint's brief as context for calibration.

---

## Archive Structure

After each sprint:
```
sprints/
  archive/
    sprint_01/
      brief_cursor.md
      brief_codex.md
      brief_goose.md
      brief_opencode.md
      brief_antigravity.md
      outcome_cursor.md
      outcome_codex.md
      outcome_goose.md
      outcome_opencode.md
      outcome_antigravity.md
      SPRINT_REVIEW.md     ← Tech Lead's summary, ratings, spec alignment result
```
