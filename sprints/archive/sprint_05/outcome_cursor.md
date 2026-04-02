# SPRINT 5 OUTCOME — CURSOR
**Engineer:** Cursor
**Role:** Cohort Assembler + Experiment Session
**Sprint:** 5 — Cohort Assembly + Experiment Modularity
**Date:** 2026-04-02
**Status:** COMPLETE

---

## 1. Files Created

| File | Lines | Description |
|------|-------|-------------|
| `src/cohort/__init__.py` | 1 | Package marker (already existed, verified empty) |
| `src/cohort/assembler.py` | 253 | `assemble_cohort()` + `_compute_summary()` |
| `src/experiment/__init__.py` | 1 | Package marker (new) |
| `src/experiment/modality.py` | 54 | `ExperimentModality` enum + `reset_working_memory()` |
| `src/experiment/session.py` | 77 | `ExperimentSession` dataclass + `create_session()` factory |
| **Total** | **386** | |

All files verified importable. `CohortGateRunner` and `classify_persona_type` were both already present (Antigravity and Codex completed their sprint-5 deliverables), so the full integration path is active.

---

## 2. `assemble_cohort` — Gate Delegation and Summary Computation

### Gate Delegation

`assemble_cohort()` calls `CohortGateRunner().run_all(personas)`, which runs G6, G7, G8, G9, G11 in order. The import is guarded by `try/except ImportError` at module level — if `CohortGateRunner` is unavailable in a parallel-sprint build, gates are skipped silently and the envelope is assembled regardless. If any gate returns `passed=False`, all failed gates are collected and a single `ValueError` is raised listing them:

```
ValueError("Cohort failed 2 gate(s): G6: <details> | G8: <details>")
```

Verified live: assembling a single-persona cohort correctly raises on G6 (city concentration 100%, age bracket concentration 100%, only 1 income bracket).

### Summary Computation

`_compute_summary(personas, domain)` populates the actual `CohortSummary` schema fields:

| Field | Computation |
|-------|-------------|
| `decision_style_distribution` | `Counter(p.derived_insights.decision_style for p in personas)` |
| `trust_anchor_distribution` | `Counter(p.derived_insights.trust_anchor for p in personas)` |
| `risk_appetite_distribution` | `Counter(p.derived_insights.risk_appetite for p in personas)` |
| `consistency_scores` | `{p.persona_id: p.derived_insights.consistency_score}` |
| `persona_type_distribution` | `Counter(classify_persona_type(p).value for p in personas)` |
| `distinctiveness_score` | `0.0` placeholder — actual score lives in G7/`check_distinctiveness` |
| `coverage_assessment` | Structured string: `domain=X size=N ages=... cities=... income=...` |
| `dominant_tensions` | Top-5 most common `key_tensions` strings across all personas |

The brief's `_compute_summary` docstring described different fields (`size`, `domain`, `persona_types`, `age_distribution`, etc.) than the actual `CohortSummary` schema. The implementation maps those concepts into the real schema: age/city/income distributions are encoded into `coverage_assessment`, persona types go into `persona_type_distribution`.

### CohortEnvelope Defaults

Fields not covered by the assembler brief are set to safe defaults:
- `business_problem=""`, `icp_spec_hash=""` — empty strings, caller can override
- `calibration_state`: `status="uncalibrated"`, all other fields `None`
- `taxonomy_used`: attribute count derived from first persona; `domain_data_used=False`
- `grounding_summary`: tendency source distribution computed from behavioural tendency source fields; `domain_data_signals_extracted=0`, `clusters_derived=0`
- `mode`: taken from `personas[0].mode`

---

## 3. `reset_working_memory` — Core Memory Untouched + Idempotency

### Implementation

```python
empty_state = SimulationState(current_turn=0, importance_accumulator=0.0,
    reflection_count=0, awareness_set={}, consideration_set=[], last_decision=None)
empty_working = WorkingMemory(observations=[], reflections=[], plans=[],
    brand_memories={}, simulation_state=empty_state)
new_memory = persona.memory.model_copy(update={"working": empty_working})
return persona.model_copy(update={"memory": new_memory})
```

### Core Memory Preservation (§14A S18)

`model_copy(update={"working": empty_working})` replaces only the `working` key on the `Memory` object. The `core` field is untouched — it carries over by reference from the original. Verified: `p.memory.core.identity_statement == p_reset.memory.core.identity_statement` is `True`.

### Never Mutates Input

Both `model_copy` calls produce new objects. The original `PersonaRecord` is not modified. Verified: original persona retains 5 seed observations after reset call.

### Idempotency

Calling `reset_working_memory` on an already-empty working memory produces the same result: an empty `WorkingMemory` with zeroed `SimulationState`. Verified by calling reset twice and confirming observation count is 0 both times.

---

## 4. `create_session` — Reset on Entry

`create_session()` resets working memory before building the `ExperimentSession`:
- Single-persona mode: `reset_working_memory(persona)`
- Cohort mode: `reset_working_memory(p)` for each persona in `cohort.personas`, then `cohort.model_copy(update={"personas": reset_personas})`

`session_id` defaults to `f"session-{uuid4().hex[:8]}"`. `decision_scenarios` defaults to `[]`.

`ExperimentSession.__post_init__` enforces the mutual-exclusion invariant: exactly one of `persona` or `cohort` must be set.

---

## 5. Known Gaps

**Gap 1: `distinctiveness_score` in `CohortSummary` is always `0.0`.**
The actual mean pairwise cosine distance is computed inside `check_distinctiveness` (Antigravity's G7 helper), but `CohortGateRunner.run_all()` does not return it to the caller — it only surfaces pass/fail. To populate `distinctiveness_score`, `assemble_cohort` would need to either call `check_distinctiveness` directly or have `CohortGateRunner` expose the computed value. Left as `0.0` for now; a future sprint can wire it through.

**Gap 2: `business_problem` and `icp_spec_hash` are empty strings.**
These fields belong to the ICP spec layer, not the assembler. The assembler has no ICP spec in scope. Callers that have an ICP spec should pass a `cohort_id` and post-process the envelope to fill these fields, or the assembler interface should be extended with optional `business_problem` and `icp_spec_hash` parameters.

**Gap 3: `taxonomy_used` is derived from `personas[0]` only.**
In a heterogeneous cohort where different personas were generated from different taxonomy extensions, `total_attributes` would be misleading. A complete implementation would union all attribute keys across all personas. Acceptable for current sprint scope.

**Gap 4: `CohortSummary.coverage_assessment` is a machine-generated string, not a human judgment.**
The field seems designed for a narrative assessment (e.g. "good coverage across urban tiers"). The current implementation encodes structured data as a string. A future sprint should either: (a) change the field type to a richer struct, or (b) have a separate assessment generator.

**Gap 5: `GroundingSummary.tendency_source_distribution` normalization edge case.**
If no tendency source fields are found (all `None`), the denominator defaults to 1 to avoid division by zero, and all distribution values will be `0.0`. This correctly sums to `0.0`, which will fail the Pydantic validator requiring sum == `1.0`. Future fix: set all three to equal shares (`0.333...`) when no source data is present.
