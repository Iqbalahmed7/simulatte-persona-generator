# SPRINT 8 OUTCOME — GOOSE

**Role:** Feature Constructor + Tendency Assigner
**Sprint:** 8 — Grounding Pipeline
**Date:** 2026-04-02
**Status:** COMPLETE

---

## 1. Files Created

| File | Lines | Notes |
|------|-------|-------|
| `src/grounding/feature_constructor.py` | 141 | Stage 2 — Signal aggregation, no LLM |
| `src/grounding/tendency_assigner.py` | 226 | Stage 4 — Tendency upgrade, no LLM |
| `tests/test_grounding_features.py` | 153 | 8 unit tests, all passing |

**Files modified (not created):**
- `tests/fixtures/synthetic_persona.py` — changed all three tendency `source` values from `"grounded"` to `"proxy"` (semantically correct: pre-grounding persona should have proxy sources; required for test 5 contract)
- `tests/test_grounding_pipeline.py` — updated `test_pipeline_upgrades_tendency_source` mock from passthrough `lambda p, _: p` to a mock that actually simulates the source upgrade, decoupling the test from the fixture's hardcoded source value

Note: `src/grounding/types.py` and `src/grounding/__init__.py` already existed (written by OpenCode). No stub was needed.

---

## 2. Feature Construction — Aggregation Logic

**`construct_features(signals: list[Signal]) -> BehaviouralFeatures`**

Empty input returns all-zero `BehaviouralFeatures` with `signal_count=0`.

**price_salience_index**: Count of `signal_type == "price_mention"` divided by total signal count.

**trust_source_distribution**: Each `trust_citation` signal scanned for keyword groups:
- `expert/doctor/certified` → expert
- `friend/peer/colleague` → peer
- `brand/branded` → brand
- `review/community/users` → community
- anything else → ad (catch-all)

Proportions among trust_citation signals only. If none: all zeros.

**switching_trigger_taxonomy**: Each `switching` signal scanned:
- `price/cost/expensive/cheap` → price
- `quality/feature/better` → feature
- `service/support/delivery` → service
- `competition/competitor/rival` → competitive
- `moved/life/baby/job/home` → life_change
- default fallback → price

**purchase_trigger_taxonomy**: Each `purchase_trigger` signal scanned:
- `need/essential/required/must` → need
- `recommend/told me/suggested` → recommendation
- `trial/tried/sample/free` → trial
- `sale/discount/promotion/offer` → promotion
- `event/occasion/gift/birthday` → event
- default fallback → need

**objection_cluster_frequencies**: `rejection` signals scanned:
- price keywords → price bucket
- `trust/doubt` → trust bucket
- otherwise → information bucket

All taxonomy dicts always have exactly their required keys (zeroed if no signals present).

---

## 3. Tendency Assigner — Persona-to-Vector + Archetype Selection

**`_persona_to_vector(persona)`** uses `persona.behavioural_tendencies` directly:

| Dim | Source |
|-----|--------|
| 0 | `price_sensitivity.band` mapped: extreme=0.9, high=0.7, medium=0.4, low=0.15 |
| 1 | `trust_orientation.weights.expert` |
| 2 | `trust_orientation.weights.peer` |
| 3 | `trust_orientation.weights.brand` |
| 4 | `trust_orientation.weights.community` |
| 5 | 0.8 if `switching_propensity.band == "high"` else 0.2 |
| 6 | 0.3 if `switching_propensity.band != "low"` else 0.1 |
| 7 | 0.6 (neutral default) |
| 8 | `trust_orientation.weights.peer * 0.8` |

**Archetype selection**: Euclidean distance between persona vector and each archetype's `centroid`. Nearest wins. Empty archetypes list returns persona unchanged.

**`_build_grounded_tendencies`**:
- `price_sensitivity`: band from archetype; description format `f"You tend to be {band} price-sensitive — {PRICE_BAND_DESCRIPTIONS[band]}"` exactly matching `tendency_estimator.py`; source=`"grounded"`
- `trust_orientation`: weights from archetype (clamped to [0,1]); dominant = max-weight key; description `f"You're most influenced by {dominant} — {DOMINANT_DESCRIPTIONS[dominant]}"`; source=`"grounded"`
- `switching_propensity`: band from archetype; descriptions matching `tendency_estimator.py`; source=`"grounded"`
- `objection_profile`: mapped from `primary_objections` strings via lookup table; default fallback `need_more_information/low/minor`
- `reasoning_prompt`: copied unchanged from existing `persona.behavioural_tendencies.reasoning_prompt`

Return: `persona.model_copy(update={"behavioural_tendencies": new_bt})`

---

## 4. Test Results

```
tests/test_grounding_features.py::test_empty_signals_returns_zero_features   PASSED
tests/test_grounding_features.py::test_price_salience_index                  PASSED
tests/test_grounding_features.py::test_trust_source_distribution_valid       PASSED
tests/test_grounding_features.py::test_switching_trigger_taxonomy            PASSED
tests/test_grounding_features.py::test_assign_grounded_no_archetypes         PASSED
tests/test_grounding_features.py::test_assign_grounded_upgrades_source       PASSED
tests/test_grounding_features.py::test_persona_to_vector_shape               PASSED
tests/test_grounding_features.py::test_behavioural_features_to_vector_shape  PASSED

8 passed in 0.18s
```

Full suite: **91 passed, 9 skipped** (skipped tests require `--integration` flag; unchanged from pre-sprint state).

---

## 5. Known Gaps

**Gap 1: Keyword matching is order-dependent.**
The `elif` chain means the first matching keyword group wins. A signal with both "price" and "feature" keywords classifies as "price". Multi-label classification would be more accurate for complex signals.

**Gap 2: Single rejection signal → single objection bucket.**
A rejection signal could plausibly belong to multiple objection clusters, but only the first-matching bucket is credited. This limits objection_cluster_frequencies granularity.

**Gap 3: Dimension 7 (trigger_need) is hardcoded to 0.6.**
There is no direct persona attribute for purchase trigger tendency, so 0.6 is used as a neutral default per-spec. This reduces archetype matching precision for purchase-trigger-heavy archetypes.

**Gap 4: No normalisation on trust_orientation_weights.**
Archetype weights are clamped to [0,1] individually but not normalised to sum to 1. This matches `TrustWeights` schema (which does not require normalisation) but may produce dominant channel selection that differs from what a normalised distribution would yield.

**Gap 5: Fixture source change may affect future sprint assumptions.**
Changing `synthetic_persona.py` from `source="grounded"` to `source="proxy"` is semantically correct but required updating `test_grounding_pipeline.py` too. Future engineers should be aware that the fixture now represents a pre-grounding state.
