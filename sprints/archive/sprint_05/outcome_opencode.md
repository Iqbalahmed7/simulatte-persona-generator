# SPRINT 5 OUTCOME — OPENCODE

**Role:** Cohort Diversity + Distinctiveness
**Sprint:** 5 — Cohort Assembly + Experiment Modularity
**Status:** Complete
**Date:** 2026-04-02

---

## 1. Files Created

| File | Lines |
|------|-------|
| `src/cohort/diversity_checker.py` | 137 |
| `src/cohort/distinctiveness.py` | 196 |

Both files import cleanly against the existing `src.schema.persona.PersonaRecord` schema
(`python3 -c “from src.cohort.diversity_checker import check_diversity; from src.cohort.distinctiveness import check_distinctiveness”` passes with no errors).

---

## 2. G6 — Rule Classification (Failures vs Warnings)

### Hard Failures (block cohort from passing Gate 6)

| Rule | Condition | Type |
|------|-----------|------|
| 1. City concentration | Any city > 20% of cohort | FAILURE |
| 2. Age bracket concentration | Any age bracket > 40% of cohort | FAILURE |
| 3. Income bracket coverage | Fewer than 3 distinct income brackets | FAILURE |

### Soft Warnings (reported but do not block)

| Rule | Condition | Type |
|------|-----------|------|
| 4. Decision style distribution | Any `decision_style` > 50% of cohort | WARNING |
| 5. Trust anchor coverage | Fewer than 3 distinct `trust_anchor` values | WARNING |

`DiversityResult.passed` is `True` only when there are zero hard failures. Warnings are always accumulated in `DiversityResult.warnings` and surfaced to the caller regardless of pass/fail status.

---

## 3. G7 — Anchor Vector Encoding: Worked Example

**Persona anchor attribute values:**

| Attribute | Raw Value | Encoding Rule | Encoded Float |
|-----------|-----------|---------------|---------------|
| `personality_type` | `”analytical”` | index 0 in vocab[4] → 0/(4-1) | 0.000 |
| `risk_tolerance` | `0.3` | continuous, use raw | 0.300 |
| `trust_orientation_primary` | `”expert”` | index 2 in vocab[6] → 2/(6-1) | 0.400 |
| `economic_constraint_level` | `0.7` | continuous, use raw | 0.700 |
| `life_stage_priority` | `”family”` | index 1 in vocab[5] → 1/(5-1) | 0.250 |
| `primary_value_driver` | `”quality”` | index 1 in vocab[6] → 1/(6-1) | 0.200 |
| `social_orientation` | `0.4` | continuous, use raw | 0.400 |
| `tension_seed` | `”quality_vs_budget”` | index 2 in vocab[5] → 2/(5-1) | 0.500 |

**Resulting vector:** `[0.0, 0.3, 0.4, 0.7, 0.25, 0.2, 0.4, 0.5]`

Categorical attributes normalise using `index / (len(vocab) - 1)` so that the first value maps to 0.0 and the last to 1.0, spreading the vocabulary evenly across [0, 1]. Missing attributes default to 0.5 (midpoint).

### Attribute lookup

Anchor attributes are stored in `PersonaRecord.attributes` as a nested dict `{category: {attr_name: Attribute}}`. `_get_attr_value` searches all categories for the requested `attr_name`, so callers do not need to know which category a given attribute lives under.

---

## 4. Known Gaps

### Categorical vocab completeness

`_CATEGORICAL_VOCABS` covers the five categorical anchor attributes specified in the brief. Any value not present in the vocab silently defaults to 0.5. If a generator uses extended or domain-specific values, all non-matching personas will encode 0.5 for that dimension, compressing distinctiveness scores toward the centre. A future improvement would be to emit a warning when an unknown categorical value is encountered.

### Missing attribute handling

If a persona does not carry one of the 8 anchor attributes in its `attributes` dict (e.g., generated in `quick` mode without all anchors), the encoder defaults to 0.5. This can artificially inflate mean pairwise distance when many personas share the default. `DistinctivenessResult` does not currently surface a warning for this — a future field (e.g., `missing_attr_warnings: list[str]`) would help diagnosing cohorts with sparse attribute coverage.

### `trust_orientation_primary` storage location

The brief names this attribute `trust_orientation_primary` and it is included in `_CATEGORICAL_VOCABS`. `PersonaRecord` surfaces trust orientation through `behavioural_tendencies.trust_orientation.dominant` and `derived_insights.trust_anchor`, but the encoder reads from `persona.attributes`. If the upstream generator does not write `trust_orientation_primary` into the `attributes` dict, all personas will encode 0.5 for this dimension. Integration should be verified against the generator’s attribute emission list.

### Single-persona cohort

`check_distinctiveness` returns `passed=True` with `mean_pairwise_distance=0.0` for cohorts smaller than 2 personas. This is mathematically correct (no pairs exist) but callers should treat a single-persona cohort as not subject to Gate 7.

### `social_orientation` attribute

This continuous attribute is expected under some category key in `persona.attributes`. If the generator stores it elsewhere or under a different name, the encoder will default to 0.5. The attribute name should be confirmed against the generator’s attribute emission list before Gate 7 is used in production.
