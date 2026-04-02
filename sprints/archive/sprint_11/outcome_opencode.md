# SPRINT 11 OUTCOME — OPENCODE

**Role:** HC3 Taxonomy Fix + Structural Smoke Tests
**Sprint:** 11 — Production Entry Point + Technical Debt Clearance
**Status:** Complete
**Date:** 2026-04-02

---

## 1. Lines Changed in base_taxonomy.py

Two changes made to `src/taxonomy/base_taxonomy.py`:

**Change 1 — Added `health_supplement_belief` attribute (after `health_anxiety` in psychology block):**
```python
_continuous(
    "health_supplement_belief",
    "psychology",
    "Belief in the efficacy of dietary supplements, vitamins, and nutraceuticals. "
    "High values indicate strong supplement advocacy; low values indicate skepticism.",
    0.45,
),
```

**Change 2 — Updated `_validate_taxonomy()` expected count:**
Changed `"psychology": 30` to `"psychology": 31` to reflect the new attribute.
The validator enforces exact category counts; without this change it raises a `ValueError` on import.

---

## 2. HC3 Activation Confirmed

```
health_supplement_belief in taxonomy: True
category: psychology
attr_type: continuous
population_prior: 0.45
Total taxonomy size: 151
```

The constraint checker (`src/generation/constraint_checker.py`) already had HC3 logic that silently no-opped when `health_supplement_belief` returned `None` from `_get_attr_value`. Adding the attribute to the `psychology` category activates the check automatically on any persona carrying both `health_anxiety < 0.2` and `health_supplement_belief > 0.80`.

---

## 3. Smoke Test Results (7/7)

```
tests/test_smoke.py::test_schema_imports                          PASSED
tests/test_smoke.py::test_taxonomy_has_health_supplement_belief   PASSED
tests/test_smoke.py::test_health_supplement_belief_category       PASSED
tests/test_smoke.py::test_hc3_activates_after_fix                 PASSED
tests/test_smoke.py::test_all_src_modules_importable              PASSED
tests/test_smoke.py::test_sarvam_smoke_non_india                  PASSED
tests/test_smoke.py::test_hc3_absent_attribute_no_op              PASSED

7 passed in 0.50s
```

**Adjustments made vs brief spec:**
- Test 3: brief used `attr.type` but `AttributeDefinition` exposes `attr_type`; corrected to `attr.attr_type`.
- Test 4: brief used `source="proxy"` but `AttributeSource` literal only allows `"sampled" | "inferred" | "anchored" | "domain_data"`; corrected to `source="sampled"`.
- Test 7: brief stripped from `"lifestyle"` only; checker reads from `"psychology"`; added stripping from both categories for robustness.

---

## 4. Full Suite Result

```
172 passed, 10 skipped in 0.95s
```

Net +7 tests added (smoke tests). All pre-existing 165 tests continue to pass. Exceeds required 155+ threshold.

---

## 5. Known Gaps

- The psychology category now has 31 attributes rather than the original 30. Any future comments or documentation referencing "30 psychology attributes" will be stale.
- `health_supplement_belief` has a `population_prior` of 0.45 (mid-range skepticism). This placeholder has not been validated against domain data; it is consistent with the broader taxonomy calibration approach.
- The synthetic persona fixture (`make_synthetic_persona`) does not include `health_supplement_belief` in its attributes dict. This is intentional — test 7 validates the graceful no-op path when the attribute is absent from a specific persona.
