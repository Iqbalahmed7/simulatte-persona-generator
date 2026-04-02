# SPRINT 10 OUTCOME — ANTIGRAVITY

**Role:** Sarvam Gate Tests — Anti-Stereotypicality + Activation Pre-Check
**Sprint:** 10 — Sarvam Indian Cultural Realism Layer
**Date:** 2026-04-02

---

## 1. File Created

**`tests/test_sarvam_gates.py`** — 140 lines

8 tests written exactly as specified in `current_brief_antigravity.md`, covering activation pre-check, anti-stereotypicality rules S-1 and S-2, settled decisions S21/S22, CR1 invariant, schema extra-field rejection, and scope literal validity.

---

## 2. Test Results: 8/8

```
PASSED  tests/test_sarvam_gates.py::test_activation_precheck_all_conditions
PASSED  tests/test_sarvam_gates.py::test_s1_cultural_reference_traceability
PASSED  tests/test_sarvam_gates.py::test_s2_no_contradiction_in_record
PASSED  tests/test_sarvam_gates.py::test_sarvam_is_india_only
PASSED  tests/test_sarvam_gates.py::test_sarvam_off_by_default
PASSED  tests/test_sarvam_gates.py::test_cr1_invariant_structural
PASSED  tests/test_sarvam_gates.py::test_enrichment_record_rejects_extra_fields
PASSED  tests/test_sarvam_gates.py::test_scope_values_valid
```

---

## 3. S21/S22 Verification Approach

**S21 (off by default):** `SarvamConfig()` instantiated with no arguments; asserted `sarvam_enrichment is False`. An India persona then passed through `should_activate()` with that default config — confirmed `active is False`. Explicit opt-in via `SarvamConfig.enabled()` is the only path to activation.

**S22 (India-only):** Six non-India countries (USA, UK, Germany, Singapore, Australia, Japan) each passed through `should_activate()` with an explicitly enabled config (`SarvamConfig.enabled()`). All six return `active is False`. The reason string is checked to contain either the country name or the word "india" to confirm informative rejection messaging.

---

## 4. CR1 Invariant Test

`test_cr1_invariant_structural` calls `run_cr1_check(persona, persona)` — a self-comparison using the `make_synthetic_persona()` fixture (Priya Mehta, Mumbai). Since both arguments are the same object, the validator's recursive field-by-field diff via `model_dump()` produces zero violations. Asserts `result.passed is True` and `result.violations == []`.

---

## 5. Full Suite Result

```
platform darwin -- Python 3.9.6, pytest-8.4.2
152 passed, 9 skipped in 0.87s
```

Previous suite count was 132 passed. Sprint 10 added 20 tests across the sarvam test files (`test_sarvam_gates.py`, `test_sarvam_activation.py`, `test_sarvam_cr1.py`, `test_sarvam_structural.py`). The 9 skipped tests are integration tests (simulation BV, e2e, survey e2e) requiring `--integration` and a live API key. All 123+ required tests remain passing.

---

## 6. Known Gaps

- **CR2, CR3, CR4 validators** not yet implemented — no tests cover these CR checks. CR1 is the only automated validator currently in place. CR2 (stereotype audit) requires semi-automated LLM evaluation; CR3 and CR4 require human evaluators.
- **S-3 to S-5 rules** (anti-stereotypicality content rules beyond traceability) not covered structurally — they require enricher output from a live LLM enrichment run and are out of scope for Sprint 10 unit gate tests.
- **`enrichment_scope` field** on `SarvamEnrichmentRecord` is a plain `str`, not validated against `SarvamEnrichmentScope` literals. This is intentional — scope is recorded after enrichment completes, not pre-validated by the record schema.
