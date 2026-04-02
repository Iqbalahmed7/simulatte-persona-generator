# Sprint 12 Outcome — OpenCode

**Role:** Health & Wellness Domain Template
**Sprint:** 12 — Persistence + Reporting
**Status:** Complete
**Date:** 2026-04-02

---

## 1. Files Created (Line Counts)

| File | Lines | Notes |
|------|-------|-------|
| `src/taxonomy/domain_templates/health_wellness.py` | 261 | 27 attributes across 4 categories + DomainTemplate wrapper dataclass |
| `tests/test_domain_health.py` | 62 | 6 tests, all passing |

---

## 2. Attribute Categories Overview

| Category | Count | Sample Attributes |
|----------|-------|------------------|
| `health_attitudes` | 7 | preventive_health_orientation, holistic_health_belief, scepticism_of_pharma, fitness_identity, body_image_concern, natural_product_preference, health_fatalism |
| `health_behaviours` | 6 | exercise_frequency, dietary_restriction_adherence, sleep_hygiene, stress_management_activity, healthcare_provider_visit_frequency, self_monitoring_behaviour |
| `health_consumption` | 6 | supplement_spend_willingness, functional_food_adoption, pharmacy_vs_online_channel_preference, brand_loyalty_health_products, subscription_model_affinity, premium_health_product_tolerance |
| `health_information` | 8 | doctor_recommendation_weight, peer_health_influence, social_media_health_content_consumption, clinical_evidence_requirement, health_influencer_trust, label_reading_diligence, alternative_medicine_openness, wellness_app_engagement |

Total: 27 attributes. All `continuous`, all `population_prior` in [0.0, 1.0]. No name clashes with base taxonomy.

---

## 3. Template Loader Registration Approach

The codebase uses `DOMAIN_REGISTRY: dict[str, list[AttributeDefinition]]` in `template_loader.py`. Registration added:

```python
from src.taxonomy.domain_templates.health_wellness import HEALTH_WELLNESS_DOMAIN_ATTRIBUTES
# Added to DOMAIN_REGISTRY dict:
"health_wellness": HEALTH_WELLNESS_DOMAIN_ATTRIBUTES,
```

The `DomainTemplate` dataclass was defined inside `health_wellness.py` (not `template_loader.py`) to expose `HEALTH_WELLNESS_TEMPLATE` with `.domain` and `.attributes` properties — required by the pre-written `test_cli_integration.py::test_hw_template_loadable`.

---

## 4. Test Results (6/6)

```
tests/test_domain_health.py::test_hw_template_loads                           PASSED
tests/test_domain_health.py::test_hw_template_attribute_count                 PASSED
tests/test_domain_health.py::test_hw_template_valid_defaults                  PASSED
tests/test_domain_health.py::test_hw_template_categories                      PASSED
tests/test_domain_health.py::test_template_loader_finds_hw                    PASSED
tests/test_domain_health.py::test_hw_no_name_clashes_with_base_taxonomy       PASSED
```

---

## 5. Full Suite Result

```
1 failed, 216 passed, 10 skipped
```

- Before sprint: 186 passed, 10 skipped
- After sprint: 216 passed (+30), 10 skipped
- 1 pre-existing failure: `tests/test_cli_integration.py::test_generate_writes_json`

The pre-existing failure mocks `src.cli._run_generation` entirely, but the file-writing logic lives inside that function — so the output file is never created under the mock. This bug was present before this sprint and is owned by the Cursor persistence module.

---

## 6. Known Gaps

- `DomainTemplate` dataclass lives in `health_wellness.py`. If other domains need it, it should be extracted to `template_loader.py` and re-exported.
- The four health category strings (`health_attitudes`, `health_behaviours`, `health_consumption`, `health_information`) are not in the `Category` Literal in `base_taxonomy.py`. This is intentional (domain-specific categories extend the base set) and does not cause runtime errors, but static type-checkers will flag it.
- `test_generate_writes_json` remains broken (pre-existing Sprint 12 issue, not caused by this work).

---

---

# Sprint 13 Outcome — OpenCode

**Role:** SaaS Domain Validation + examples/spec_saas.json
**Sprint:** 13
**Status:** Complete
**Date:** 2026-04-02

---

## 1. Files Created

| File | Notes |
|------|-------|
| `examples/spec_saas.json` | ICP spec stub for SaaS domain with required keys |
| `tests/test_saas_domain.py` | 5 tests covering taxonomy loading, pool validation, anchor sampling, and spec JSON |

## 2. Files Modified

None. All existing SaaS-related files (`src/taxonomy/domain_templates/saas.py`, `src/taxonomy/domain_templates/template_loader.py`, `src/generation/demographic_sampler.py`) were already correct.

---

## 3. Schema Validation Findings

### `src/taxonomy/domain_templates/template_loader.py`
- "saas" was already present in `DOMAIN_REGISTRY`. No fix required.
- Import of `SAAS_DOMAIN_ATTRIBUTES` was already present. No fix required.

### `src/generation/demographic_sampler.py` — `_SAAS_POOL`
Checked all 8 entries against valid schema Literals:

| Check | Result |
|-------|--------|
| `Household.structure` values | All valid: `nuclear`, `other`, `couple-no-kids` |
| Ages (18–65 range) | All valid: 27–52 |
| `income_bracket` values | All valid: `middle`, `upper-middle` |
| `Location.urban_tier` values | All valid: all entries use `metro` |
| No `tier1` values | Confirmed — `tier1` is not a valid `UrbanTier` literal; none present |

No fixes were required in the SaaS pool.

### `src/schema/persona.py` — Reference Literals
- `UrbanTier = Literal["metro", "tier2", "tier3", "rural"]` — note: `tier1` is NOT valid
- `HouseholdStructure = Literal["nuclear", "joint", "single-parent", "couple-no-kids", "other"]`
- `income_bracket` field is typed as plain `str` (no Literal restriction in Pydantic model)

---

## 4. Test Results (5/5)

```
tests/test_saas_domain.py::test_saas_taxonomy_loads          PASSED
tests/test_saas_domain.py::test_saas_domain_attrs_load       PASSED
tests/test_saas_domain.py::test_saas_pool_structure_valid    PASSED
tests/test_saas_domain.py::test_saas_sample_anchor           PASSED
tests/test_saas_domain.py::test_saas_spec_json_exists        PASSED
```

---

## 5. Full Suite Result

```
233 passed, 10 skipped
```

- Before sprint 13: 217 passed, 10 skipped
- After sprint 13: 233 passed, 10 skipped (net +16 from prior sprint accumulation + 5 new)
- All new tests pass. Full suite meets the 217+ threshold with 10 skipped.
