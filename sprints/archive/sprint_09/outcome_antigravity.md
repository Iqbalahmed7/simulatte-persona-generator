# SPRINT 9 OUTCOME — ANTIGRAVITY

**Role:** Grounded Cohort Gate Tests
**Sprint:** 9 — Wire Grounding into Generation Flow
**Date:** 2026-04-02

---

## 1. File Created

`tests/test_grounded_cohort_gates.py` — 206 lines

8 tests written exactly as specified in `current_brief_antigravity.md`.

---

## 2. Test Results: 2/8 passed

```
PASSED  tests/test_grounded_cohort_gates.py::test_grounding_summary_rejects_wrong_keys
PASSED  tests/test_grounded_cohort_gates.py::test_grounding_context_importable

FAILED  tests/test_grounded_cohort_gates.py::test_g11_all_tendency_sources_valid_after_grounding
FAILED  tests/test_grounded_cohort_gates.py::test_grounding_summary_pydantic_valid
FAILED  tests/test_grounded_cohort_gates.py::test_grounded_mode_consistent
FAILED  tests/test_grounded_cohort_gates.py::test_taxonomy_meta_domain_data_used_grounded
FAILED  tests/test_grounded_cohort_gates.py::test_cohort_id_preserved_after_grounding
FAILED  tests/test_grounded_cohort_gates.py::test_proxy_cohort_mode_unchanged
```

---

## 3. G11 Coverage — Fields Checked

Test 1 (`test_g11_all_tendency_sources_valid_after_grounding`) checks all three tendency source fields on each persona in the envelope:

- `persona.behavioural_tendencies.price_sensitivity.source`
- `persona.behavioural_tendencies.trust_orientation.source`
- `persona.behavioural_tendencies.switching_propensity.source`

Each must be one of `{"grounded", "proxy", "estimated"}`.

---

## 4. Mode Consistency Check — What Was Verified

Test 3 (`test_grounded_mode_consistent`) verifies two levels:

1. `envelope.mode == "grounded"` — the envelope-level mode flag
2. `persona.mode == "grounded"` for every persona in `envelope.personas` — individual persona-level mode flag

Both must agree when `domain_data` is provided to `assemble_cohort()`. A mismatch at the persona level is flagged with the specific `persona_id` in the assertion message.

---

## 5. Full Suite Result

```
platform darwin -- Python 3.9.6, pytest-8.4.2
6 failed, 2 passed in 0.23s
```

**Root cause of 6 failures: single root issue — G6 cohort diversity gate.**

All 6 failing tests call `assemble_cohort()` with one or two instances of `make_synthetic_persona()` (Priya Mehta, Mumbai, age 34, income_bracket="middle"). The G6 gate enforces minimum cohort diversity:

- City concentration: Mumbai = 100% (max allowed: 20%)
- Age bracket: 25-34 = 100% (max allowed: 40%)
- Income diversity: 1 distinct bracket (minimum required: 3)

This causes `assemble_cohort()` to raise `ValueError: Cohort failed 1 gate(s): G6: ...` before any grounding or envelope construction occurs.

**The two passing tests do not call `assemble_cohort()`:**

- Test 6: validates `GroundingSummary` schema directly — passes correctly
- Test 8: imports `GroundingContext`, `compute_tendency_source_distribution`, `build_grounding_summary_from_result` from `src.grounding.grounding_context` — passes correctly (OpenCode's Sprint 9 file is present)

**Confirmed: both Sprint 9 dependencies exist:**

- `src/cohort/assembler.py` already has `domain_data: list[str] | None = None` parameter (Codex's change present)
- `src/grounding/grounding_context.py` exists with all required symbols (OpenCode's change present)

---

## 6. Known Gaps

**Blocking gap (not Antigravity's responsibility to fix):**

The `make_synthetic_persona()` fixture produces a single-persona output that is intentionally designed for BV tests, not cohort-level tests. The G6 gate correctly enforces cohort diversity — it is working as designed. The fix is one of:

a) A multi-persona fixture that satisfies G6 diversity requirements (different cities, ages, income brackets) — should be added to `tests/fixtures/` by the fixture owner or the cohort test author.

b) A `bypass_cohort_gates=True` flag on `assemble_cohort()` for unit test scenarios — a Codex Sprint 9 addition that would allow tests to verify grounding behaviour independent of cohort-gate enforcement.

Neither of these is within Antigravity's sprint scope. The tests are correctly written per spec. They will pass once either (a) or (b) is in place.

**No spec drift detected in passing tests.** The `GroundingSummary` Pydantic validator correctly rejects distributions with missing keys (Test 6), and `GroundingContext.has_data` returns `True` for non-empty input (Test 8).
