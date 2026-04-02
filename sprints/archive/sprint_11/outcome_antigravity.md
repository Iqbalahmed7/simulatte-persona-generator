# SPRINT 11 OUTCOME — ANTIGRAVITY

**Role:** Pipeline Integration Gate Tests
**Sprint:** 11 — Production Entry Point + Technical Debt Clearance
**Date:** 2026-04-02

---

## 1. File Created

**`tests/test_sprint11_gates.py`** — 156 lines

8 integration gate tests verifying the complete Sprint 11 pipeline: G7 distinctiveness, HC3 constraint, memory promotion executor, CLI entry point, LoopResult promoted_memory_ids, business_problem parameter, and a full structural end-to-end run.

---

## 2. Carry-Forwards Verified Closed

| Carry-Forward | Test | Status |
|---|---|---|
| G7 distinctiveness_score populated (not hardcoded 0.0) | test_g7_distinctiveness_score_not_hardcoded | CLOSED |
| icp_spec_hash is a 16-char hex string | test_icp_spec_hash_populated | CLOSED |
| HC3 constraint active (health_supplement_belief in taxonomy) | test_hc3_active | CLOSED |
| Memory promotion executor importable (Goose) | test_promotion_executor_importable | CLOSED |
| LoopResult.promoted_memory_ids field exists and defaults to [] | test_loop_result_promoted_field | CLOSED |
| CLI entry point importable (Cursor) | test_cli_importable | CLOSED |
| assemble_cohort accepts business_problem parameter (Codex) | test_business_problem_accepted | CLOSED |
| Full structural pipeline spec to envelope (no LLM) | test_full_pipeline_structural | CLOSED |

---

## 3. Test Results: 8/8

```
PASSED  tests/test_sprint11_gates.py::test_g7_distinctiveness_score_not_hardcoded
PASSED  tests/test_sprint11_gates.py::test_icp_spec_hash_populated
PASSED  tests/test_sprint11_gates.py::test_hc3_active
PASSED  tests/test_sprint11_gates.py::test_promotion_executor_importable
PASSED  tests/test_sprint11_gates.py::test_loop_result_promoted_field
PASSED  tests/test_sprint11_gates.py::test_cli_importable
PASSED  tests/test_sprint11_gates.py::test_business_problem_accepted
PASSED  tests/test_sprint11_gates.py::test_full_pipeline_structural
```

---

## 4. Full Suite Result

```
platform darwin -- Python 3.9.6, pytest-8.4.2
186 passed, 10 skipped in 1.16s
```

Previous suite count was 155 passed before Sprint 11. Suite grew by 31 tests across all Sprint 11 engineer deliverables.

---

## 5. Failures

None — all 8 tests pass.

---

## 6. Implementation Notes

Three adjustments were required to align tests with the actual codebase vs the brief's pseudocode:

- **icp_spec_hash location**: Brief referenced `envelope.taxonomy_meta.icp_spec_hash` but the field is top-level on `CohortEnvelope` (`envelope.icp_spec_hash`). Tests use the top-level field.
- **Attribute.source values**: Brief used `source="proxy"` but `AttributeSource` only accepts `"sampled"`, `"inferred"`, `"anchored"`, or `"domain_data"`. Tests use `"sampled"`.
- **HC3 violation detection**: `ConstraintViolation` has no `__str__` method; filter uses `v.constraint_id == "HC3"` and `v.attr_b` attribute checks rather than `str(v)`.
- **LoopResult constructor**: Brief passed `persona=None, decision_output=None` but `LoopResult` is a dataclass requiring an `Observation` as its first positional field. Tests construct a minimal `Observation` object inline.
