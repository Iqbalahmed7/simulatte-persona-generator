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
| **S8–S17** | *(archived — grounding, Sarvam, validation, CLI, persistence, quality gates)* | 2 | All 5 | See sprints/archive/ |
| **S18** | LittleJoys Full Regen + Sarvam | Pilot | Tech Lead | 200/200 personas regenerated, 97% parity |
| **S19** | Four Engine Improvements | Engine | Tech Lead | Noise injection, cache, aging, tiered simulation; deployed to LJ pipeline |
| **S20** | MiroFish Domain Taxonomy Extraction | 2 | Cursor, Codex, Goose, OpenCode, Antigravity | Auto domain taxonomy from ICP spec + domain data |
| **S21** | Simulation Quality Gates (BV3/BV6) | 2 | Cursor, Codex, Goose, OpenCode, Antigravity | BV3 temporal consistency, BV6 override scenarios, wired into pipeline |
| **S22** | Calibration Engine | 3 | Cursor, Codex, Goose, OpenCode, Antigravity | Benchmark anchoring, client feedback loop, C1–C5 gates |
| **S23** | LittleJoys App Integration | Pilot | Cursor, Codex, Goose, OpenCode, Antigravity | LJ Streamlit app connected to Simulatte engine; UI updates |

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

---

## Sprint 20 — MiroFish Domain Taxonomy Extraction

**Status:** CURRENT SPRINT
**Spec sections governing this sprint:**
- Master Spec §6 (Taxonomy Strategy — Layer 2 Domain Extension, MiroFish adoption decision)
- Master Spec §6B (Filling Order — domain-specific attributes filled last)
- Master Spec §4 (System Architecture — Grounded Mode pipeline)
- Constitution P8 (domain-agnostic core — domain attributes must stay in Layer 2)

**Context:**
Currently, domain taxonomy extension (Layer 2) is only available via hand-authored static templates (CPG, SaaS, etc.). The master spec explicitly adopts the MiroFish principle: when domain data is provided, the domain attribute set should be extracted automatically from that data. This is the last in-scope v1 gap.

**Problem it solves:** Without this, every new client domain requires a human to write a new template. With it, the system reads the domain data (reviews, ICP spec, transcripts) and derives the relevant attributes automatically — enabling true Grounded Mode automation.

**Deliverables:**
```
src/
  taxonomy/
    domain_extractor.py      ← (Cursor) ICP spec parser + LLM extraction of domain attributes
    attribute_ranker.py      ← (Codex) Score/rank extracted attributes by relevance + discriminative power
    domain_merger.py         ← (Goose) Merge extracted domain layer with base taxonomy; handle conflicts
    icp_spec_parser.py       ← (OpenCode) Parse ICP spec documents (markdown/JSON) → structured ICPSpec object
  schema/
    icp_spec.py              ← (OpenCode) Pydantic model for ICP spec
tests/
  test_domain_extractor.py   ← (Antigravity) Extraction, ranking, merging tests
```

**Engineer assignments:**
- **Cursor** → `src/taxonomy/domain_extractor.py` — takes raw domain text corpus (reviews, forum posts, transcripts) + optional ICPSpec; calls Sonnet to extract candidate domain attributes (name, description, valid range, example values); returns list of `DomainAttribute` objects
- **Codex** → `src/taxonomy/attribute_ranker.py` — scores each `DomainAttribute` by: (a) decision-relevance (does it affect buy/no-buy?), (b) discriminative power (does it differentiate personas?), (c) data coverage (what % of signal corpus mentions it?); returns ranked list, top 30–60 selected
- **Goose** → `src/taxonomy/domain_merger.py` — merges ranked domain attributes with base taxonomy; detects conflicts (e.g. a domain attribute that duplicates a base attribute); outputs final combined taxonomy as the structure `attribute_filler.py` expects
- **OpenCode** → `src/schema/icp_spec.py` + `src/taxonomy/icp_spec_parser.py` — define the `ICPSpec` Pydantic model (domain, business_problem, target_segment, anchor_traits, data_sources); parse both markdown-format and JSON-format ICP specs into the model
- **Antigravity** → `tests/test_domain_extractor.py` — test extraction on a synthetic 20-review corpus; test ranker output ordering; test merger conflict resolution; test that base taxonomy is never mutated; test ICPSpec parser on both formats

**Interface contracts:**

```python
# domain_extractor.py
@dataclass
class DomainAttribute:
    name: str                   # snake_case, e.g. "pediatrician_trust"
    description: str            # 1-2 sentences
    valid_range: str            # "0.0–1.0" or "low|medium|high" or list of options
    example_values: list[str]   # 3 examples from the corpus
    signal_count: int           # how many signals mention this attribute
    extraction_source: str      # "corpus" | "icp_anchor" | "template_fallback"

def extract_domain_attributes(
    corpus: list[str],          # raw signal texts
    icp_spec: ICPSpec | None = None,
    llm_client=None,
    max_attributes: int = 80,
) -> list[DomainAttribute]: ...

# attribute_ranker.py
def rank_attributes(
    attributes: list[DomainAttribute],
    base_taxonomy_names: set[str],   # to detect duplicates
    top_n: int = 50,
) -> list[DomainAttribute]: ...      # sorted by composite score, top_n returned

# domain_merger.py
def merge_taxonomy(
    base: dict,                      # base taxonomy (existing structure)
    domain_attrs: list[DomainAttribute],
) -> dict: ...                       # combined taxonomy dict, domain_specific key added

# icp_spec_parser.py
def parse_icp_spec(source: str | Path | dict) -> ICPSpec: ...
```

**Acceptance criteria:**
- Extractor: given 20+ synthetic reviews about a child nutrition product, extracts ≥ 8 domain attributes including at minimum: `pediatrician_trust`, `clean_label_preference`, `child_acceptance_concern`
- Ranker: correctly deprioritises attributes with < 3 signal mentions; correctly detects and skips duplicates of base taxonomy attributes
- Merger: combined taxonomy contains both `base` categories and `domain_specific` key; no base attribute mutated
- ICPSpec parser: parses both markdown ICP spec (with headers like `## Target Segment`) and JSON ICP spec without error
- All 15+ tests pass
- No LLM calls in ranker, merger, or parser (deterministic only — LLM is in extractor only)

**End-of-sprint spec checks:**
- [ ] Domain attributes are in `domain_specific` key — NOT merged into base taxonomy categories (P8)
- [ ] Extraction uses Sonnet (§4 component table: "Taxonomy Engine — Sonnet, one-time per domain")
- [ ] `extraction_source` field populated for all attributes (P10 — traceability)
- [ ] Extractor gracefully falls back to template when corpus < 200 signals (§7 Minimum Viable Data Set)

---

## Sprint 21 — Simulation Quality Gates (BV3 + BV6)

**Status:** QUEUED (starts after Sprint 20 complete)
**Spec sections governing this sprint:**
- Validity Protocol Module 2 — BV3 (temporal consistency), BV6 (believable consistency vs rigidity)
- Validity Protocol Module 3 — S1–S4 simulation gates
- Master Spec §9 (Cognitive Loop — temporal property requirements)

**Context:**
BV3 and BV6 are the only two behavioural validity tests not yet automated and wired into the pipeline. BV3 verifies that memory actually accumulates and influences decisions across a multi-turn simulation. BV6 verifies that personas are not robotically consistent — they should override tendencies when given a sufficiently compelling override scenario.

**Deliverables:**
```
src/
  validation/
    bv3_temporal.py       ← (Cursor) BV3 test runner: runs 10-stimulus arc, checks confidence trend
    bv6_override.py       ← (Codex) BV6 test runner: generates override scenarios, checks departure rate
    simulation_gates.py   ← (Goose) S1–S4 gate checks as callable functions (wraps existing logic)
    gate_report.py        ← (OpenCode) Structured report object + CLI output formatter
tests/
  test_bv3.py             ← (Antigravity) BV3 test fixtures (mock LLM, arc verification)
  test_bv6.py             ← (Antigravity) BV6 test fixtures (override scenario, departure detection)
```

**Engineer assignments:**
- **Cursor** → `bv3_temporal.py` — builds a 10-stimulus arc (5 positive, 5 mixed); runs through `run_loop` with mock LLM; checks: (a) confidence monotonically increases across stimuli 1–5, (b) at least 1 reflection after stimulus 5 references accumulating trend, (c) final decision cites both positive and mixed experiences
- **Codex** → `bv6_override.py` — generates 10 test scenarios for a given persona including 2 "override scenarios" (health emergency for price-sensitive persona; clear product failure for brand-loyal persona); runs each through `run_loop`; checks: 70–90% tendency-consistency across 8 normal scenarios, ≥ 1 departure in 2 override scenarios
- **Goose** → `simulation_gates.py` — wraps S1 (5-persona trial first), S2 (no decision option > 90%), S3 (driver coherence check), S4 (WTP plausibility) as `check_s1()` through `check_s4()` functions that return `GateResult` objects; wire these into `regenerate_pipeline.py` Stage 5
- **OpenCode** → `gate_report.py` — `GateReport` dataclass with gate name, pass/fail, threshold, actual value, action_required; `format_gate_report(report: GateReport) -> str` for CLI output; update `--simulate` Stage 6 output to include BV3/BV6 summary
- **Antigravity** → `test_bv3.py`, `test_bv6.py` — use `unittest.mock` to mock `run_loop` returning controlled sequences; test that BV3 correctly flags a flat-confidence run as a failure; test BV6 correctly flags 100%-consistent runs as failures and < 60%-consistent as failures

**Acceptance criteria:**
- BV3: correctly PASSES a monotonically-increasing confidence arc; correctly FAILS a flat-confidence arc
- BV6: correctly PASSES 80% consistent + 1 override departure; correctly FAILS 100% consistent
- S1–S4 gates: all 4 callable independently and return `GateResult` objects
- Pipeline: Stage 5 now runs S1–S4 gates and reports pass/fail; Stage 6 (`--simulate`) adds BV3/BV6 summary
- All 20+ tests pass

---

## Sprint 22 — Calibration Engine

**Status:** QUEUED (starts after Sprint 21 complete)
**Spec sections governing this sprint:**
- Master Spec §7 (Grounding Strategy — calibration relationship)
- Validity Protocol Module 4 — C1–C5 calibration gates
- Master Spec §4 (Mode Hierarchy — Grounded and Deep modes require calibration support)

**Context:**
The LittleJoys cohort is currently `status="uncalibrated"`. The spec defines two calibration methods: benchmark anchoring (compare population-level simulation outputs against known domain benchmarks) and client feedback loop (adjust when client provides real outcome data). This sprint builds both.

**Deliverables:**
```
src/
  calibration/
    __init__.py
    engine.py             ← (Cursor) Orchestrates both calibration methods; updates CohortEnvelope
    benchmark_anchor.py   ← (Codex) Benchmark anchoring: compare sim outputs vs domain benchmarks
    feedback_loop.py      ← (Goose) Client feedback: adjust population tendencies from outcome data
    population_validator.py ← (OpenCode) C1–C5 gate checks; staleness detection (> 6 months)
tests/
  test_calibration.py     ← (Antigravity)
```

**Engineer assignments:**
- **Cursor** → `engine.py` — `CalibrationEngine` class with `run_benchmark_calibration(cohort, benchmarks)` and `run_feedback_calibration(cohort, outcomes)` methods; both update `cohort.calibration_state` and return updated `CohortEnvelope`; add `--calibrate` flag to CLI `simulate` command
- **Codex** → `benchmark_anchor.py` — compare simulation output distribution (buy rate, WTP distribution, decision style distribution) against provided benchmarks (e.g., LittleJoys: 82.6% reorder, WTP ₹649 median); compute divergence score; flag if simulated conversion is outside 0.5x–2x of benchmark (C3 gate); output calibration adjustment recommendations (which tendency bands to shift and by how much)
- **Goose** → `feedback_loop.py` — accepts real outcome data (e.g., `{persona_id: "pg-lj-001", actual_outcome: "purchased", channel: "doctor_referral"}`); finds the corresponding persona; computes which tendency was the primary predictor; adjusts tendency description + band; updates `calibration_state.status` to `"client_calibrated"`
- **OpenCode** → `population_validator.py` — C1 (status not null), C2 (benchmark applied at least once), C3 (conversion plausibility), C4 (client feedback trigger check), C5 (staleness > 6 months flag); return `CalibrationGateReport`; expose as `validate_calibration(cohort) -> CalibrationGateReport`
- **Antigravity** → `test_calibration.py` — test benchmark anchoring sets status to `benchmark_calibrated`; test feedback loop updates correct persona tendency; test C3 gate fires when simulated conversion is 3x benchmark; test C5 staleness with mocked timestamp

**LittleJoys application of Sprint 22:**
After Sprint 22, run:
```bash
python3 pilots/littlejoys/regenerate_pipeline.py --tier signal --calibrate \
  --benchmark-conversion 0.826 --benchmark-wtp-median 649
```
This moves the LittleJoys cohort from `uncalibrated` → `benchmark_calibrated`.

**Acceptance criteria:**
- Benchmark anchoring: given LJ benchmarks (82.6% reorder, ₹649 WTP), produces `benchmark_calibrated` status
- C3 gate: correctly fires WARN when simulated buy rate is < 0.5x or > 2x benchmark
- C5 gate: correctly flags cohort as stale when `last_calibrated` > 6 months ago
- Feedback loop: updates `tendency.band` for the correct persona when outcome data provided
- All 20+ tests pass

---

## Sprint 23 — LittleJoys App Integration

**Status:** QUEUED (starts after Sprint 22 complete)
**Spec sections governing this sprint:**
- Master Spec §4 (Product Modalities: survey, temporal simulation, deep interview)
- Architecture COGNITIVE_ARCHITECTURE.md — simulation tier model

**Context:**
The LittleJoys Streamlit app (`/Users/admin/Documents/Simulatte Projects/1. LittleJoys/app/`) currently runs on the old legacy engine (`src.simulation.batch_runner`). It loads `personas_generated.json` (old format) and uses old `Persona` schema objects. It has no access to the Simulatte cognitive loop, tiers, noise injection, memory state, or calibration data.

This sprint replaces the old engine connection with the Simulatte engine and adds UI for Sprint 19–22 features.

**Deliverables:**
```
pilots/littlejoys/
  app_adapter.py              ← (Cursor) CohortEnvelope → LJ app data format adapter
  simulatte_batch_runner.py   ← (Codex) Wrapper: LJ JourneyConfig → run_loop calls with tier support

In LittleJoys app at /Users/admin/Documents/Simulatte Projects/1. LittleJoys/app/:
  streamlit_app.py            ← (Goose) Replace batch_runner import; add tier selector; update persona loading
  components/
    confidence_display.py     ← (OpenCode) Confidence + noise_applied display component
    memory_state_viewer.py    ← (OpenCode) Observations/reflections count + last reflection snippet
    calibration_badge.py      ← (OpenCode) Calibration status badge (uncalibrated/calibrated/stale)

tests/
  test_app_adapter.py         ← (Antigravity) Adapter round-trip tests
```

**Engineer assignments:**
- **Cursor** → `app_adapter.py` — `load_simulatte_cohort(path) -> list[PersonaRecord]`; `persona_to_display_dict(p: PersonaRecord) -> dict` that maps all fields the LJ app currently displays (name, age, city, decision_style, trust_anchor, WTP, etc.) from the new schema; handles missing fields gracefully
- **Codex** → `simulatte_batch_runner.py` — `run_simulatte_batch(personas, journey_config, tier)` that maps `JourneyConfig.stimuli` → `run_loop` calls; collects `DecisionOutput` from each persona; returns the same result schema the LJ app's existing Results tab expects; passes `tier=SimulationTier(tier_str)` through
- **Goose** → `streamlit_app.py` updates — (1) replace `load_all_personas()` to load from `simulatte_cohort_final.json` via `app_adapter.load_simulatte_cohort()`; (2) add tier radio button (DEEP / SIGNAL / VOLUME) to the "Run Scenario" page with cost tooltip; (3) pass tier to `run_simulatte_batch`; (4) add calibration status banner to sidebar
- **OpenCode** → three UI components: (a) `confidence_display.py` — shows `{confidence}` with `±{|noise_applied|}` noise indicator and color coding (green ≥ 70, amber 50–69, red < 50); (b) `memory_state_viewer.py` — compact panel showing observation count, reflection count, last reflection snippet; (c) `calibration_badge.py` — colored badge: green=calibrated, amber=uncalibrated, red=stale
- **Antigravity** → `test_app_adapter.py` — test that `persona_to_display_dict` produces all required keys; test that a missing optional field doesn't raise; test that `load_simulatte_cohort` raises `FileNotFoundError` with a useful message when the cohort file doesn't exist

**UI/UX changes — see `pilots/littlejoys/LJ_UI_CHANGES.md` for full spec (written separately)**

**Acceptance criteria:**
- LJ app loads `simulatte_cohort_final.json` without error
- Tier selector is visible and functional on the Run Scenario page
- Decision results display `confidence ± noise` for each persona
- Memory state panel shows observation/reflection counts after a simulation run
- Calibration badge shows in sidebar
- All 10+ adapter tests pass
- No changes to the LJ app's existing Results tab structure or export format
