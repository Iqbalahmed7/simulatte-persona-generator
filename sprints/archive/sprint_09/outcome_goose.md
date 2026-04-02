# SPRINT 9 OUTCOME — GOOSE

**Role:** Grounding Integration Tests
**Sprint:** 9 — Wire Grounding into Generation Flow
**Date:** 2026-04-02
**Status:** COMPLETE

---

## 1. File Created

**`tests/test_grounding_integration.py`** — 500 lines

---

## 2. Test Results

**8/8 passed**

```
tests/test_grounding_integration.py::test_full_grounded_cohort_envelope_shape PASSED
tests/test_grounding_integration.py::test_grounded_cohort_grounding_summary_populated PASSED
tests/test_grounding_integration.py::test_taxonomy_meta_domain_data_used PASSED
tests/test_grounding_integration.py::test_grounded_source_proportion_positive PASSED
tests/test_grounding_integration.py::test_proxy_cohort_zeros_in_grounding_summary PASSED
tests/test_grounding_integration.py::test_multi_persona_grounded_cohort PASSED
tests/test_grounding_integration.py::test_grounded_cohort_below_200_still_builds PASSED
tests/test_grounding_integration.py::test_icp_spec_domain_data_field PASSED

8 passed in 0.22s
```

---

## 3. Edge Cases Observed

### Codex's `domain_data` parameter was already present
The brief said to write the tests anyway in case Codex's assembler change hadn't landed. In practice, `assemble_cohort()` already had the `domain_data` parameter with the full grounding pipeline integration. The tests ran against the real implementation from the first run.

### Cohort gate failures with naive test personas
The brief's test stubs call `make_synthetic_persona()` directly and pass lists of 2–3 personas. This fails in practice because `assemble_cohort()` runs G6 (distribution), G7 (distinctiveness), and G8 (type coverage) gates before the grounding pipeline executes.

`make_synthetic_persona()` always returns the same "Priya Mehta" persona (Mumbai, age 34, middle income, social/peer archetype). Lists of clones fail:
- **G6**: all personas in the same city (100% > 20% max), same age bracket (100% > 40% max), only 1 income bracket (minimum 3 required).
- **G7**: mean pairwise cosine distance = 0.000 (identical 8-anchor vectors), below threshold 0.35.
- **G8**: all personas classify as the same type; 5-persona cohort requires 4 distinct types.

### Resolution: `_make_diverse_cohort()` helper
A `_make_diverse_cohort()` helper was built that constructs 5 personas with:
- 5 distinct cities (Mumbai, Delhi, Chennai, Kolkata, Bangalore)
- 5 distinct age brackets (25-34, 45-54, 18-24, 35-44, 55-64)
- 4 distinct income brackets
- All 8 G7 anchor attributes explicitly set with maximally varied values → mean cosine distance > 0.35
- 5 distinct persona archetypes covering 5 G8 types: Social Validator, Loyalist, Aspirant, Anxious Optimizer, Pragmatist

### Single-cluster grounding with small datasets (Test 7)
With 3 texts, the pipeline extracts only 3 signals (below the 200-signal warning threshold). `derive_clusters()` produces 1 archetype from 3 vectors — correct behaviour at small scale. Both `clusters_derived >= 1` and `signals_extracted > 0` are satisfied. The pipeline does not raise at sub-threshold signal counts.

---

## 4. Full Suite Result

```
8 passed in 0.22s
```

---

## 5. Known Gaps

**Gap 1: Brief stubs vs. gate reality.**
The brief's original test stubs pass `make_synthetic_persona()` clones directly to `assemble_cohort()`. These fail gates G6/G7/G8 in the current system. The test file uses a purpose-built diverse cohort helper. If the brief is used as a template for future sprint tests, writers should account for cohort diversity requirements.

**Gap 2: Test 1 persona count changed from 2 to 5.**
The brief specifies `len(envelope.personas) == 2`. The working implementation uses 5 personas to satisfy G8 (which requires 4 distinct types for N=5). If cohort gate thresholds are relaxed in a future sprint, the brief's original 2-persona version could be restored.

**Gap 3: `ICPSpec.domain_data` pre-existed Sprint 9.**
Test 8 passes trivially because `ICPSpec.domain_data` was introduced in an earlier sprint. It remains a useful regression guard.

**Gap 4: `GroundingSummary` field naming mismatch between pipeline and schema.**
`GroundingResult.signals_extracted` maps to `GroundingSummary.domain_data_signals_extracted`. The assembler bridges this correctly in the current implementation, but the naming asymmetry is a latent maintenance risk.
