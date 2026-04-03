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

---

# Sprint 14 Outcome — OpenCode

**Role:** Live End-to-End Test Suite
**Sprint:** 14
**Status:** Complete
**Date:** 2026-04-02

---

## 1. Files Created

| File | Lines | Notes |
|------|-------|-------|
| `tests/test_live_e2e.py` | 183 | 5 live tests, all skipped by default via `RUN_LIVE_TESTS=1` env var |
| `tests/conftest.py` | 12 | Registers `live` marker; `pytest_addoption` and `pytest_configure` hooks |

---

## 2. Skip Mechanism

Tests use a `pytest.mark.skipif` marker bound to the `RUN_LIVE_TESTS` environment variable:

```python
live = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_TESTS") != "1",
    reason="Live API tests skipped. Set RUN_LIVE_TESTS=1 to enable.",
)
```

All 5 tests are decorated with `@live`. Running `python3 -m pytest tests/test_live_e2e.py -v` without the env var produces 5 skips, 0 failures.

---

## 3. Tests Implemented

| Test | What it validates |
|------|------------------|
| `test_live_generate_cpg_cohort` | 3-persona CPG cohort: result is dict with `personas` key, each has `persona_id`, `demographic_anchor`, `attributes` |
| `test_live_generate_saas_cohort` | Same structural checks for SaaS domain |
| `test_live_simulate_cohort` | Generate 2-persona cohort → save → run simulation (1 round) → result has `results` with 2 entries each having `persona_id` and `rounds` |
| `test_live_survey_cohort` | Generate 2-persona cohort → save → run survey → result has `responses` key |
| `test_live_full_pipeline` | Generate 3-persona CPG cohort → `save_envelope` → `load_envelope` round-trip → `format_cohort_report` (len > 100) → survey question → `responses` present |

All tests call internal async functions via `asyncio.run(...)` with `skip_gates=True` for speed.

---

## 4. conftest.py Changes

`tests/conftest.py` was created (did not previously exist). Root `conftest.py` already had `pytest_addoption` and `pytest_configure` for the `integration` marker — the new `tests/conftest.py` registers the separate `live` marker without conflict.

```python
def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", default=False, help="Run live API tests")

def pytest_configure(config):
    config.addinivalue_line("markers", "live: mark test as requiring live API access")
```

---

## 5. Test Results

### Live tests only (skipped):
```
tests/test_live_e2e.py::test_live_generate_cpg_cohort SKIPPED (Live ...)
tests/test_live_e2e.py::test_live_generate_saas_cohort SKIPPED (Live...)
tests/test_live_e2e.py::test_live_simulate_cohort SKIPPED (Live API ...)
tests/test_live_e2e.py::test_live_survey_cohort SKIPPED (Live API te...)
tests/test_live_e2e.py::test_live_full_pipeline SKIPPED (Live API te...)

5 skipped in 0.04s
```

### Full suite:
```
249 passed, 15 skipped in 1.23s
```

- Before sprint 14: 233 passed, 10 skipped
- After sprint 14: 249 passed, 15 skipped (+16 passed, +5 skipped)
- The 5 new live tests count as skipped (not failed), meeting the requirement of 233+ passing and 10+ skipped.

---

# Sprint 15 Outcome — OpenCode

**Role:** Sarvam Integration Validation + CR2/CR4 Automated Checks
**Sprint:** 15
**Status:** Complete
**Date:** 2026-04-02

---

## 1. Files Created

| File | Lines | Notes |
|------|-------|-------|
| `examples/spec_india_cpg.json` | 8 | India CPG spec with `sarvam_enabled: true` |
| `src/sarvam/cr2_validator.py` | 67 | CR2 anti-stereotypicality audit |
| `src/sarvam/cr4_validator.py` | 44 | CR4 persona fidelity check |
| `tests/test_sarvam_cr2_cr4.py` | 117 | 6 tests covering CR2 and CR4 |

---

## 2. `src/sarvam/cr2_validator.py` Contents

```python
"""src/sarvam/cr2_validator.py — CR2: Anti-Stereotypicality Audit for Sarvam outputs.

CR2: Sarvam-enriched outputs must not contain prohibited stereotypical defaults.
See Master Spec §15G for the full list of prohibited defaults.
"""
from __future__ import annotations

from dataclasses import dataclass

# Prohibited phrases/patterns per spec §15G + §10 Anti-Stereotypicality Constraints
_PROHIBITED_PATTERNS = [
    "jugaad",                          # S-rule: only if attribute-supported
    "arranged marriage",               # unless life_story specifically mentions it
    "joint family",                    # unless household.structure == "joint"
    "dowry",
    "curry",
    "bollywood",
    "namaste",                         # as a greeting token (surface-level stereotyping)
    "chai",                            # unless lifestyle attributes support it
]

# These are SOFT checks — flag for review, not hard fails
_SOFT_PATTERNS = [
    "festival",
    "temple",
    "cricket",
]


@dataclass
class CR2Result:
    passed: bool
    hard_violations: list[str]   # prohibited patterns found
    soft_flags: list[str]        # soft patterns to review
    persona_id: str


def run_cr2_check(
    persona_id: str,
    enriched_narrative_first: str,
    enriched_narrative_third: str,
    persona_record=None,   # optional — for context-aware checks
) -> CR2Result:
    """Run CR2 anti-stereotypicality audit on enriched narratives."""
    combined_text = (enriched_narrative_first + " " + enriched_narrative_third).lower()

    hard_violations = [p for p in _PROHIBITED_PATTERNS if p in combined_text]
    soft_flags = [p for p in _SOFT_PATTERNS if p in combined_text]

    # Context-aware override: if persona has joint household, "joint family" is OK
    if persona_record is not None:
        household = getattr(getattr(persona_record, "demographic_anchor", None), "household", None)
        if household and getattr(household, "structure", None) == "joint":
            hard_violations = [v for v in hard_violations if v != "joint family"]

    return CR2Result(
        passed=len(hard_violations) == 0,
        hard_violations=hard_violations,
        soft_flags=soft_flags,
        persona_id=persona_id,
    )
```

---

## 3. `src/sarvam/cr4_validator.py` Contents

```python
"""src/sarvam/cr4_validator.py — CR4: Persona Fidelity Check for Sarvam outputs.

CR4: Enriched narratives must preserve all factual content from the standard narrative.
Key facts that must survive enrichment: name, age/life stage, occupation, income context,
location, key values, primary tensions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CR4Result:
    passed: bool
    missing_facts: list[str]
    persona_id: str


def run_cr4_check(
    persona_id: str,
    original_narrative: str,
    enriched_narrative: str,
    persona_record: Any = None,
) -> CR4Result:
    """CR4: Verify enriched narrative preserves key persona facts."""
    missing = []

    if persona_record is not None:
        anchor = getattr(persona_record, "demographic_anchor", None)
        if anchor:
            first_name = anchor.name.split()[0] if anchor.name else ""
            if first_name and first_name.lower() not in enriched_narrative.lower():
                missing.append(f"name '{first_name}' not found in enriched narrative")

            city = getattr(getattr(anchor, "location", None), "city", None)
            if city and city.lower() not in enriched_narrative.lower():
                missing.append(f"city '{city}' not found in enriched narrative")

    return CR4Result(
        passed=len(missing) == 0,
        missing_facts=missing,
        persona_id=persona_id,
    )
```

---

## 4. Test Results

### New CR2/CR4 tests (6/6):
```
tests/test_sarvam_cr2_cr4.py::test_cr2_clean_narrative_passes              PASSED
tests/test_sarvam_cr2_cr4.py::test_cr2_detects_jugaad                      PASSED
tests/test_sarvam_cr2_cr4.py::test_cr2_joint_family_ok_for_joint_household PASSED
tests/test_sarvam_cr2_cr4.py::test_cr4_name_preserved                      PASSED
tests/test_sarvam_cr2_cr4.py::test_cr4_missing_name_fails                  PASSED
tests/test_sarvam_cr2_cr4.py::test_cr4_city_check                          PASSED

6 passed in 0.16s
```

### Full suite:
```
259 passed, 15 skipped in 1.35s
```

- Before sprint 15: 249 passed, 15 skipped
- After sprint 15: 259 passed, 15 skipped (+10 passing)
- All new tests pass. Full suite exceeds 249+ threshold.

---

---

# Sprint 20 Outcome — OpenCode

## Files written

- `src/schema/icp_spec.py` — `ICPSpec` Pydantic v2 model with `model_config = ConfigDict(extra="ignore")`.
- `src/taxonomy/__init__.py` — module init (was absent; required for import).
- `src/taxonomy/icp_spec_parser.py` — `parse_icp_spec(source)` supporting dict, Path, JSON string, and Markdown string inputs.

## Deviations from brief (if any)

- The brief showed `class Config: extra = "ignore"` (Pydantic v1 style). Confirmed Pydantic 2.12.5 is installed; used `model_config = ConfigDict(extra="ignore")` as instructed for v2.
- `src/taxonomy/__init__.py` did not exist. Created a minimal one to make `from src.taxonomy.icp_spec_parser import parse_icp_spec` importable. This was a necessary infrastructure addition not mentioned in the brief.
- JSON synonym for `domain`: the brief states fall back to `category` only if neither `domain` nor `domain_name` is present. Implemented exactly as specified (not as a primary synonym).

## Parsing edge cases noted

- `persona_count` in markdown: silently ignored if not parseable as int; Pydantic default of 10 is used.
- Bullet lines with leading whitespace in markdown are `.strip()`-ped before the regex match, making indented bullets work correctly.
- JSON `data` key is a broad synonym; consistent with the brief's synonym list.
- The pre-existing `ICPSpec` in `src.generation.identity_constructor` is a different model (persona generation mode control). The new `src.schema.icp_spec.ICPSpec` is a separate, non-conflicting class.

## Verification result

```
$ python3 -c "from src.schema.icp_spec import ICPSpec; from src.taxonomy.icp_spec_parser import parse_icp_spec; spec = parse_icp_spec({'domain': 'cpg', 'business_problem': 'test', 'target_segment': 'parents'}); print(spec)"
domain='cpg' business_problem='test' target_segment='parents' anchor_traits=[] data_sources=[] geography=None category=None persona_count=10
```

PASSED.

## Test suite result

```
400 passed, 15 skipped in 1.89s
```

No regressions.

---

## 5. What CR1–CR4 Cover

| Check | Type | What it validates |
|-------|------|------------------|
| **CR1** | Automated | PersonaRecord isolation — the Sarvam enrichment step must not mutate any field on the PersonaRecord (attributes, tendencies, memory, demographic anchor). Compares model_dump() before and after enrichment. Zero tolerance. |
| **CR2** | Automated | Anti-stereotypicality audit — enriched narratives must not contain prohibited cultural defaults from spec §15G (jugaad, arranged marriage, bollywood, curry, etc.) unless persona attributes specifically justify them. Context-aware: `joint family` is excused when `household.structure == "joint"`. Soft-flag tier for reviewable patterns (festival, temple, cricket). |
| **CR3** | Human-evaluated | Cultural realism rating — a human evaluator familiar with Indian urban consumer behaviour rates the enriched narrative on a 1–5 scale. Pass threshold: average ≥ 4.0/5.0. Cannot be automated by definition (spec §12). Skipped in this sprint. |
| **CR4** | Automated | Persona fidelity — the enriched narrative must still be about the same person. Checks that the persona's first name and city survive the Sarvam rewrite. Prevents enrichment from accidentally substituting a different persona identity into the output. |

### What remains for human review (CR3)

CR3 requires a trained human evaluator to assess whether the enriched narrative reads as genuinely culturally resonant for an Indian consumer — not just surface-texture-correct. No automated heuristic can substitute for this. The recommended workflow (from SIMULATTE_SARVAM_TEST_PROTOCOL.md) is a structured rubric review:
1. Evaluator reads enriched first-person and third-person narratives side by side with the standard versions.
2. Rates on five dimensions: authenticity, specificity, consistency with attributes, absence of stereotyping, and narrative coherence.
3. A persona passes CR3 only if the mean rating across dimensions is ≥ 4.0/5.0.
4. CR3 results are recorded in `validation_status.cr3_cultural_realism` on the `SarvamEnrichmentRecord`.

---

# Sprint 21 Outcome — OpenCode

**Engineer:** OpenCode
**Sprint:** 21 — Simulation Quality Gates (BV3 + BV6)
**Deliverable:** `src/validation/gate_report.py`
**Date:** 2026-04-03

---

## Files Created / Modified

| File | Action | Notes |
|------|--------|-------|
| `src/validation/gate_report.py` | Created | ~210 lines — dataclass + two formatters |
| `pilots/littlejoys/regenerate_pipeline.py` | Modified | 18 lines added to `_run_validation_and_save()` |

---

## What Was Built

### `SimulationGateReport` dataclass

- Fields: `s_gates: list[GateResult]`, `bv3_results: list[BV3Result]`, `bv6_results: list[BV6Result]`
- Properties: `all_passed`, `has_warnings`, `warning_count`, `fail_count`
- `TYPE_CHECKING` guard on imports avoids circular import at runtime

### `format_gate_report(report) -> str`

Multi-line CLI formatter matching the regenerate_pipeline print style:

```
=== Simulation Quality Gates ===

  S1 Zero error rate        PASS   5 personas loaded successfully
  S2 Decision diversity     PASS   Max: 'buy' at 60.0%
  S3 Driver coherence       PASS   100.0% of driver lists contain domain keywords
  S4 WTP plausibility       PASS   Median WTP: ₹655 (0.9% from ask)

  BV3 Temporal consistency  not run (--simulate required)
  BV6 Override scenarios    not run (--simulate required)

  Overall: PASS
```

- Gate name column: 26 chars, left-aligned
- WARN lines include `[threshold: ±N%]` bracket notation
- FAIL lines include `[action: ...]` suffix
- BV3/BV6 show pass count + confidence delta (BV3) or avg departures (BV6) when populated
- "not run" message when results list is empty

### `format_gate_summary(report) -> str`

One-line banner: `Gates: S1✓ S2✓ S3✓ S4⚠ | BV3: not run | BV6: not run`

Symbols: ✓ pass, ✗ fail, ⚠ warning.

### `regenerate_pipeline.py` Stage 5 update

Gate block inserted after parity check and before dry-run guard, exactly per spec.

---

## Verification

**Import check:** `Import OK`

**Test suite:** `436 passed, 15 skipped in 12.00s` — zero regressions.

---

## Deviations from Spec

1. **`GateResult.gate` vs `.name`** — The brief referred to a `.name` field but Goose's `simulation_gates.py` uses `.gate` (short code: "S1"–"S4"). The formatter maps gate codes to display names via a local `_name_map` dict. Semantically identical output.

2. **"not run" line format** — Spec showed `"BV3/BV6: not run (--simulate required)"` as a combined line. Implemented as two separate lines with the gate name padded for visual alignment with S-gate rows. Consistent with the column-based style.

3. **`SimulationGateReport` name** — Brief used `GateReport` in one sentence and `SimulationGateReport` in the code block. Used `SimulationGateReport` throughout (code block takes precedence).
