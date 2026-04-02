# SPRINT 5 OUTCOME — ANTIGRAVITY
**Engineer:** Antigravity
**Role:** Cohort Quality Gate Runner
**Sprint:** 5 — Cohort Assembly + Experiment Modularity
**Date:** 2026-04-02
**Status:** COMPLETE

---

## 1. Files Modified / Created

| File | Action | Description |
|------|--------|-------------|
| `src/schema/validators.py` | Modified | Added `CohortGateRunner` class + import guards for cohort modules |
| `tests/test_cohort.py` | Created | 18 synthetic cohort tests for G6, G7, G8, G9, G11, and reset_working_memory |

---

## 2. G9 and G11 — Exact Check Logic

### G9 — Tension Completeness

```python
def g9_tension_completeness(self, personas: list[PersonaRecord]) -> ValidationResult:
    failures: list[str] = []
    for persona in personas:
        if len(persona.derived_insights.key_tensions) < 1:
            failures.append(
                f"Persona {persona.persona_id}: no tensions in derived_insights.key_tensions"
            )
    return ValidationResult(gate="G9", passed=len(failures) == 0, failures=failures)
```

Iterates every persona. Checks `len(persona.derived_insights.key_tensions) >= 1`. Collects failures as `"Persona {pid}: no tensions in derived_insights.key_tensions"`.

### G11 — Tendency Source

```python
def g11_tendency_source(self, personas: list[PersonaRecord]) -> ValidationResult:
    failures: list[str] = []
    for persona in personas:
        for field_name in ["price_sensitivity", "switching_propensity", "trust_orientation"]:
            obj = getattr(persona.behavioural_tendencies, field_name, None)
            if obj is not None and hasattr(obj, "source") and obj.source is None:
                failures.append(
                    f"Persona {persona.persona_id}: {field_name}.source is None"
                )
    return ValidationResult(gate="G11", passed=len(failures) == 0, failures=failures)
```

Checks only the three fields specified in the brief: `price_sensitivity`, `switching_propensity`, `trust_orientation`. Skips fields that don't have a `source` attribute (guard via `hasattr`). Collects failures as `"Persona {pid}: {field_name}.source is None"`.

---

## 3. Test Results Table

| Test Class | Test | Result |
|---|---|---|
| TestG6Distribution | test_g6_passes_diverse_cohort | PASS |
| TestG6Distribution | test_g6_fails_city_concentration | PASS |
| TestG6Distribution | test_g6_fails_age_concentration | PASS |
| TestG6Distribution | test_g6_fails_insufficient_income_brackets | PASS |
| TestG7Distinctiveness | test_g7_passes_diverse_cohort | PASS |
| TestG7Distinctiveness | test_g7_fails_identical_cohort | PASS |
| TestG7Distinctiveness | test_g7_identifies_most_similar_pair | PASS |
| TestG8TypeCoverage | test_g8_passes_3_personas_3_types | PASS |
| TestG8TypeCoverage | test_g8_fails_3_personas_2_types | PASS |
| TestG8TypeCoverage | test_g8_passes_5_personas_4_types | PASS |
| TestG8TypeCoverage | test_g8_fails_5_personas_3_types | PASS |
| TestG9TensionCompleteness | test_g9_passes_all_have_tensions | PASS |
| TestG9TensionCompleteness | test_g9_fails_persona_with_no_tensions | PASS |
| TestG11TendencySource | test_g11_passes_all_sources_set | PASS |
| TestG11TendencySource | test_g11_fails_null_source | PASS |
| TestResetWorkingMemory | test_reset_clears_working_fields | PASS |
| TestResetWorkingMemory | test_reset_preserves_core_memory | PASS |
| TestResetWorkingMemory | test_reset_is_idempotent | PASS |

**Summary: 18 passed, 0 failed, 0 skipped**

All tests run against the actual module implementations (OpenCode's `diversity_checker.py`, `distinctiveness.py`, `type_coverage.py` and Cursor's `experiment/modality.py` — all were present in the repo at test time).

---

## 4. Known Gaps

**Gap 1: G9 test uses `model_construct` to bypass Pydantic validation.**
Pydantic enforces `key_tensions >= 1` at construction time, so we cannot produce a `DerivedInsights` with an empty tensions list via normal instantiation. The test uses `DerivedInsights.model_construct(**insights_dict)` with `key_tensions=[]` to bypass this. This is intentional — the gate tests the detector, not Pydantic. If Pydantic's validation changes (e.g. min length removed), this approach remains valid.

**Gap 2: G11 test uses `model_construct` for null source.**
Same approach as G9 — `PriceSensitivityBand.model_construct(**ps_dict)` with `source=None` bypasses Pydantic's `TendencySource` literal validator. The gate must handle None even if schema doesn't allow it in practice (e.g. LLM output may violate it before validation, or schema may relax over time).

**Gap 3: G7 `test_g7_passes_diverse_cohort` requires careful attribute injection.**
The base fixture's `personality_type` attribute lives in both `psychology` and `identity` categories. The test helper must override it in both to avoid the first-match-wins behaviour of `_get_attr_value`. This is a fragility tied to the multi-category attribute model — future persona schema changes may require updating the helper.

**Gap 4: G8 coverage rule for non-standard cohort sizes.**
`_required_types(n)` returns `min(n, 8)` for sizes not in `{3, 5, 10}`. This means a cohort of 4 requires 4 distinct types. Tests only cover sizes 3 and 5 (per the brief). A test for size 4 or 7 would increase rule coverage.

**Gap 5: G6 `test_g6_passes_diverse_cohort` uses non-standard income bracket strings.**
The test uses strings like `"lower-middle"` and `"upper-middle"`. These are not validated against a fixed enum in the current schema. If a future schema adds enum validation for `income_bracket`, these test strings may need updating.

**Gap 6: Import guards produce silent pass on missing modules.**
When `check_diversity`, `check_distinctiveness`, or `check_type_coverage` are absent (ImportError), G6, G7, G8 return `passed=True` with a warning. This is safe for parallel sprint builds but means failures in those gates are silent if the cohort modules are missing. Once all sprint deliverables are merged, the import guards should be removed and the modules imported directly.
