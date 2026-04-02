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
