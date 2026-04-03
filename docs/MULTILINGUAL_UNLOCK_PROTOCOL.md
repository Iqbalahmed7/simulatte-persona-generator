# Multilingual Unlock Protocol

**Status:** O15 BLOCKER ACTIVE
**Document type:** Binding governance — Tech Lead sign-off required
**Last updated:** 2026-04-03

---

## Overview

Language generation for Indian regional languages (Hindi, Tamil, Telugu, Marathi,
Bengali, Kannada, Gujarati) is **BLOCKED** pending validation. No language output
code may be merged, deployed, or enabled until:

1. All four CR-V gates produce a `READY` result for the target language, and
2. The Tech Lead issues written sign-off citing the readiness report date and language.

This document defines the evidence requirements, gate pass thresholds, and the
sign-off process that constitutes the unlock path.

---

## Evidence Requirements (per language)

Each language must independently satisfy all four gates before unlock.

### CR1-V — Isolation Test

| Item | Requirement |
|------|-------------|
| Scope | 10-persona isolation run in the target language |
| Pass threshold | All 10 personas complete without error |
| Evidence keys | `n_personas_tested` (≥10), `all_passed` (True) |
| Status this sprint | **NOT_RUN** — O15 blocker active; gate will be activated in a future sprint |

### CR2-V — Stereotype Spot-Check

| Item | Requirement |
|------|-------------|
| Scope | 5-persona manual spot-check |
| Pass threshold | ≥90% of cultural details are attribute-traceable to source data; 0 prohibited script patterns |
| Evidence keys | `n_personas_checked`, `pct_attribute_traceable`, `prohibited_script_count` |
| Status this sprint | **NOT_RUN** — O15 blocker active; gate will be activated in a future sprint |

### CR3-V — Human Evaluator Realism

| Item | Requirement |
|------|-------------|
| Scope | Structured human evaluation by ≥2 native/near-native speakers with domain knowledge |
| Pass threshold | Mean evaluator score ≥4.0/5.0 across all evaluators; no individual dimension score <3.0 |
| Evidence keys | `evaluators` (list of `{name, mean_score, dimension_scores}`), `n_evaluators` |
| Gate logic | `EVIDENCE_NEEDED` if no evaluators submitted; `FAILED` if thresholds not met; `READY` if all thresholds met |

### CR4-V — Bilingual Fidelity

| Item | Requirement |
|------|-------------|
| Scope | Bilingual pair comparison: evaluators shown English and target-language versions of the same persona |
| Pass threshold | ≥4 of 5 pairs confirmed as the same person by evaluators |
| Evidence keys | `pairs_tested` (≥5), `pairs_confirmed` |
| Gate logic | `EVIDENCE_NEEDED` if pairs_tested <5; `FAILED` if pairs_confirmed <4; `READY` if ≥4 confirmed |

---

## Language-Region Pairing Rules

Language output must respect the region of the persona. Cross-language assignment
is prohibited (e.g., generating Hindi output for a Tamil Nadu persona, or Tamil
output for a Delhi persona is an **anti-pattern**).

Region-to-language mappings are governed by `src/grounding/language_region_matrix.py`.
No language gate result is valid if the evidence was collected from personas with
mismatched language-region assignments.

---

## Unlock Process

1. **Collect evidence** for all four CR-V gates for the target language.
2. **Submit evidence** via `readiness_report.py` to produce a `LanguageReadinessReport`.
3. **Verify status:** `LanguageReadinessReport.status` must reach `"READY_FOR_REVIEW"` (all four gates `READY`).
4. **Tech Lead sign-off:** The Tech Lead reviews the report and issues written sign-off that must cite:
   - The target language
   - The readiness report date
   - The gate run date for each CR-V gate
5. **Merge:** Only after written sign-off may language generation code be merged into the main branch.

No step may be skipped. Verbal sign-off does not satisfy step 4.

---

## What Remains Blocked Until Sign-Off

The following are blocked for each language until that language's CR-V gates all pass
and written Tech Lead sign-off is on record:

- Hindi, Tamil, Telugu, Marathi, Bengali, Kannada, Gujarati output generation
- Sarvam language-mode output (any non-English Sarvam inference path)
- Any non-English persona narrative or decision output
- Prompts that instruct the LLM to respond in a regional language
- Post-processing or transliteration layers applied to persona output

Cultural realism attributes (food, festivals, family structure, regional vernacular
markers in English) are **not** blocked — these are part of the existing Indian persona
layer and are not governed by this protocol.

---

## Anti-Pattern: Do Not Conflate Language with Culture

**CA7 (Constitution §13E):** Cultural realism — including regional food preferences,
festival calendars, family structures, and community references — is already
implemented in the Indian persona layer and is active in English output today.

Language output is a **separate, additional layer** requiring its own validation.
A Hindi-speaking persona in Delhi is already culturally realistic in English output.
Adding Hindi-language output does not improve cultural accuracy; it is a distinct
capability that introduces new failure modes (stereotype amplification, script
errors, bilingual incoherence) and therefore requires independent validation before
it can be enabled.

**Do not treat language generation as a proxy for cultural depth.** Cultural depth
is already present. Language generation must earn its own gates.

---

## Gate Implementation Reference

Gates are implemented in `src/validation/language_gates.py`.

```
check_cr1_v(language, evidence)  →  LanguageGateResult
check_cr2_v(language, evidence)  →  LanguageGateResult
check_cr3_v(language, evidence)  →  LanguageGateResult
check_cr4_v(language, evidence)  →  LanguageGateResult
```

`LanguageGateResult.status` is one of:
- `NOT_RUN` — gate not yet activated (O15 blocker)
- `BLOCKED` — prerequisite not met
- `EVIDENCE_NEEDED` — gate defined but no qualifying data submitted
- `READY` — gate passed
- `FAILED` — gate run and failed

`tech_lead_sign_off_required` is a field on `LanguageReadinessReport`
(written separately by Codex), not on individual `LanguageGateResult` objects.

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-04-03 | Cursor (Sprint 29) | Initial governance document; CR-V gate framework defined |
