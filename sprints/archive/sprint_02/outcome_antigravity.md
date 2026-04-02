# SPRINT 2 OUTCOME — ANTIGRAVITY
**Engineer:** Antigravity
**Sprint:** 2 — Identity Constructor
**Date:** 2026-04-02

---

## 1. Methods Added

Both G4 and G5 are present in `src/schema/validators.py` as instance methods of `PersonaValidator`:

- `g4_narrative_completeness(self, persona: PersonaRecord) -> ValidationResult`
- `g5_narrative_attribute_alignment(self, persona: PersonaRecord) -> ValidationResult`

Neither method modifies nor replaces G1, G2, or G3. They are appended after G3.

---

## 2. G4 Word Count Thresholds — Rationale

| Field | Threshold | Rationale |
|---|---|---|
| `narrative.first_person` | 50 words | A first-person voice needs enough length to feel authored, not templated. 50 words is roughly 3-4 sentences — enough to establish voice, situation, and one attitude or value. |
| `narrative.third_person` | 80 words | Third-person narrative carries more descriptive burden: it must orient an external reader to who this person is, their context, and their behavioural stance. 80 words (roughly 5-6 sentences) sets a floor that prevents single-paragraph stubs. Third-person is typically longer than first-person in generated output because it includes contextual framing the persona would not self-narrate. |
| `memory.core.identity_statement` | 10 words | An identity statement below 10 words is almost certainly a fragment or placeholder. 10 words allows a minimal complete sentence ("I am a pragmatic professional who values stability and trust."). |
| `memory.core.tendency_summary` | 20 words | A tendency summary must convey direction across multiple attributes. 20 words is the minimum for naming at least two tendencies in a coherent sentence. |

These thresholds are specified in the brief. They are intentionally lenient — they set a floor against empty/stub output, not a quality ceiling.

---

## 3. G5 Keyword Lists — Full Set Per Rule

### Rule 1: brand_loyalty > 0.80 (brand-agnostic phrases)
- `"brand agnostic"`
- `"no brand preference"`
- `"doesn't care about brands"`
- `"does not care about brands"` (added: normalises contraction variant)
- `"any brand"`

### Rule 2: switching_propensity.band == "low" (high-switching phrases)
- `"loves trying new brands"`
- `"always exploring"`
- `"frequent switcher"`
- `"brand hopper"`

### Rule 3: price_sensitivity.band in ("high", "extreme") (price-indifferent phrases)
- `"money is no object"`
- `"price doesn't matter"`
- `"price does not matter"` (added: normalises contraction variant)
- `"never looks at price"`

### Rule 4: trust_orientation.dominant == "self" (social-conformity phrases)
- `"follows the crowd"`
- `"does what others do"`
- `"easily influenced"`

### Rule 5: risk_appetite == "low" (risk-embracing phrases)
- `"thrill-seeker"`
- `"thrill seeker"` (added: normalises hyphen variant)
- `"loves risk"`
- `"takes bold bets"`
- `"impulsive"`

All matching is case-insensitive (both narrative fields are lowercased before scanning). Both `narrative.first_person` and `narrative.third_person` are concatenated and scanned together.

Contraction and punctuation variants (`"does not"` alongside `"doesn't"`, `"thrill seeker"` alongside `"thrill-seeker"`) were added beyond the brief's minimum set because the lowercased combined narrative will contain the expanded form when apostrophes are present in the original. This covers no additional interpretive ground — it is purely a string-matching hygiene addition.

---

## 4. `validate_all` Signature Change — Backward Compatibility

Old signature:
```python
def validate_all(self, persona: PersonaRecord) -> list[ValidationResult]:
```

New signature:
```python
def validate_all(
    self,
    persona: PersonaRecord,
    include_narrative: bool = False,
) -> list[ValidationResult]:
```

`include_narrative` defaults to `False`. All existing callers that pass only `persona` continue to work without modification — they receive exactly the same G1/G2/G3 result list as before. G4 and G5 are only appended when `include_narrative=True` is explicitly passed. This matches the integration contract (`PersonaValidator.validate_all(persona, include_narrative=True)` at Step 7 of identity build).

---

## 5. Known Gaps — Contradictions Not Detectable by Keyword Scanning

The following contradiction patterns exist in theory but cannot be reliably detected without LLM-based interpretation:

1. **Semantic paraphrase of excluded phrases.** A narrative that says "she never fixates on the price tag" is semantically equivalent to "never looks at price" but will not be caught. Keyword scanning catches literals only.

2. **Implicit brand loyalty contradictions.** A narrative could describe a persona switching brands repeatedly in their life stories without using any of the flagged phrases. Only explicit statements are caught.

3. **Tone-attribute mismatches.** A persona with `risk_appetite == "low"` described as "adventurous and spontaneous" is contradictory, but neither word is in the flagged phrase list because they require interpretation to confirm contradiction (an adventurous cook is not the same as a financial risk-taker).

4. **Cross-field internal contradictions.** G5 checks narrative against attributes, but does not check the narrative against itself. A first-person and third-person narrative could contradict each other.

5. **Negation handling.** The phrase "does not love trying new brands" would not be flagged even though it contains a fragment of a flagged phrase. The current implementation uses substring matching with no negation awareness.

6. **Switching propensity phrase ambiguity.** "Always exploring new recipes" would match the `"always exploring"` phrase even though it refers to cooking, not brand switching. The phrase list was specified in the brief and is kept as-is; removing it would require interpretation beyond keyword matching.

---

## Sprint 1 Archive

The Sprint 1 outcome content (files created, HC1-HC6, TR1-TR8, stratification, correlation checks, patch notes) has been superseded by this Sprint 2 outcome file. The Sprint 1 content is preserved in `sprints/archive/` if reference is needed.

---

## 2. Hard Constraints (HC1–HC6)

All six constraints align with Master Spec §10. Each `ConstraintViolation` now carries a `suggested_fix` field so callers can choose whether to auto-correct or surface the violation upstream.

| HC# | Condition | Test Case | suggested_fix |
|-----|-----------|-----------|---------------|
| HC1 | `income_bracket` contains `"poverty"` AND `premium_quality_preference > 0.85` | Persona with `income_bracket: "below_poverty"` and `premium_quality_preference: 0.91` → violation flagged | Reduce premium_quality_preference to ≤ 0.55 |
| HC2 | `urban_tier` in `{"tier3", "rural"}` AND `digital_payment_comfort > 0.85` | Persona with `urban_tier: "rural"` and `digital_payment_comfort: 0.92` → violation flagged | Reduce digital_payment_comfort to ≤ 0.55 |
| HC3 | `health_anxiety < 0.2` AND `health_supplement_belief > 0.80` | Persona with `health_anxiety: 0.10` and `health_supplement_belief: 0.88` → violation flagged. If `health_supplement_belief` is absent from the persona (attribute not yet in taxonomy), check is silently skipped — no error raised | Reduce health_supplement_belief to ≤ 0.50 |
| HC4 | `age < 25` AND `brand_loyalty > 0.80` | Persona with `age: 22` and `brand_loyalty: 0.85` → violation flagged | Reduce brand_loyalty to ≤ 0.55 |
| HC5 | `income_bracket` contains `"high"` or `"top"` AND `deal_seeking_intensity > 0.85` | Persona with `income_bracket: "top_bracket"` and `deal_seeking_intensity: 0.90` → violation flagged | Reduce deal_seeking_intensity to ≤ 0.55 |
| HC6 | `risk_tolerance > 0.80` AND `loss_aversion > 0.80` | Persona with `risk_tolerance: 0.85` and `loss_aversion: 0.87` → violation flagged | Reduce loss_aversion to ≤ 0.50 |

**Implementation note for HC3:** `health_supplement_belief` is not present in `BASE_TAXONOMY`. The checker reads it via `_get_attr_value`, which returns `None` on a `KeyError`. The condition `health_supp is not None` gates the entire check, so no violation is raised and no exception is thrown when the attribute is absent. The check will activate automatically once the attribute is added to the taxonomy.

---

## 3. Tendency-Attribute Rules (TR1–TR8)

All eight rules align with Master Spec §10. The check direction is now attribute-to-tendency (not tendency-to-attribute as in the original Sprint 1 implementation). Missing attributes are skipped silently.

| TR# | Condition | Required | Category lookup | Test Case |
|-----|-----------|----------|----------------|-----------|
| TR1 | `budget_consciousness > 0.70` | `price_sensitivity.band` in `{"high", "extreme"}` | `values` | `budget_consciousness: 0.80`, band `"low"` → failure |
| TR2 | `budget_consciousness < 0.35` | `price_sensitivity.band` in `{"low", "medium"}` | `values` | `budget_consciousness: 0.20`, band `"extreme"` → failure |
| TR3 | `brand_loyalty > 0.70` | `switching_propensity.band == "low"` | `values` | `brand_loyalty: 0.85`, band `"high"` → failure |
| TR4 | `social_proof_bias > 0.65` | `trust_orientation.weights.peer >= 0.65` | `social` | `social_proof_bias: 0.75`, `weights.peer: 0.40` → failure |
| TR5 | `authority_bias > 0.65` | `trust_orientation.weights.expert >= 0.65` | `social` | `authority_bias: 0.70`, `weights.expert: 0.30` → failure |
| TR6 | `ad_receptivity < 0.30` | `trust_orientation.weights.ad <= 0.25` | `lifestyle` | `ad_receptivity: 0.15`, `weights.ad: 0.40` → failure |
| TR7 | `information_need > 0.70` | `objection_profile` includes `"need_more_information"` | `psychology` | `information_need: 0.85`, no matching objection → failure |
| TR8 | `risk_tolerance < 0.30` | `objection_profile` includes `"risk_aversion"` | `psychology` | `risk_tolerance: 0.15`, no matching objection → failure |

**Key differences from original Sprint 1 TR rules:** The old rules were tendency-to-attribute (e.g., "if band is extreme, check the attribute"). The new rules are attribute-to-tendency (e.g., "if the attribute is high, the band must match"). TR4–TR6 now validate trust weight floats directly rather than the `dominant` string. TR7–TR8 now require presence of specific `objection_type` values in `objection_profile` rather than checking `derived_insights.risk_appetite`.

---

## 4. Stratification Test — Synthetic 20-Persona Pool, Target N=10

**Method:** The `CohortStratifier` extracts an 8-element anchor vector per persona (continuous attributes used directly; categorical attributes encoded as `option_index / (len(options) - 1)`). A centroid is computed as the mean of all 20 vectors. Each persona is ranked by cosine distance from the centroid.

**Reasoning through the 5:3:2 breakdown:**

Starting from 20 candidates with a target of 10:

- `round(0.5 * 10) = 5` near-center slots
- `round(0.3 * 10) = 3` mid-range slots
- `10 - 5 - 3 = 2` far-outlier slots

With 20 candidates sorted by ascending cosine distance from the centroid:

- **Near-center (5 personas):** The 5 candidates with the smallest cosine distances — positions 1–5 in the sorted list. These are the "average" personas closest to the population mean. In a typical LLM-generated pool, the majority of candidates cluster here; selecting only 5 of the ~14 near-center candidates prevents the cohort from being dominated by the modal type.

- **Mid-range (3 personas):** The next band, positions 7–13 in distance rank (after excluding near-center picks). These represent personas with meaningful but not extreme deviations on one or two anchor dimensions — e.g., high `risk_tolerance` with otherwise average values.

- **Far-outliers (2 personas):** The 2 candidates with the highest cosine distances — positions 19–20 in the sorted list. These are the edge personas: e.g., a combination of extreme `economic_constraint_level` + `independent_open` personality + `aspiration_vs_constraint` tension seed. Without deliberate selection, these would almost never appear in an unweighted sample of 10 from 20.

**Expected result:** A cohort of [5, 3, 2] across near/mid/far. This is within the ±1 tolerance spec (acceptable bands: 4–6 / 2–4 / 1–3). The stratification ensures the cohort covers realistic variation rather than 10 near-identical "median consumer" personas.

---

## 5. Correlation Soft Check — Hardest Encodings

The `check_correlation_consistency` method evaluates the 8 pairs in `KNOWN_CORRELATIONS`.

**Hardest to encode:** `("brand_loyalty", "indie_brand_openness", "negative")`.

The difficulty is threshold calibration. A violation flag at `a + b > 1.5` avoids false positives for "moderate explorers" (e.g., loyalty `0.6`, openness `0.6` → sum `1.2`, no flag) while catching true contradictions (e.g., loyalty `0.9`, openness `0.9` → sum `1.8`, flagged). The symmetric sum approach means the checker does not need to know which attribute is the "driver," which simplifies the implementation but requires the `1.5` threshold to be empirically reasonable across the population prior distributions.

**Second hardest:** `("risk_tolerance", "status_quo_bias", "negative")`. A persona can legitimately be risk-tolerant in some domains while maintaining habitual routines in others. The `a + b > 1.5` threshold still catches extreme simultaneous highs but produces more soft warnings in practice than the brand/indie pair.

---

## 6. Known Gaps and Edge Cases

- **HC3 deferred:** `health_supplement_belief` is not yet in `BASE_TAXONOMY`. The HC3 check silently no-ops on all current personas. It will activate automatically once the attribute is added to the taxonomy without any code change required.

- **HC1/HC5 string matching:** `income_bracket` is a free-form string. The partial-match strategy (`"poverty" in income_bracket.lower()` for HC1, `"high" in ... or "top" in ...` for HC5) is intentionally permissive to handle varied casing and phrasing (e.g., `"Below Poverty Line"`, `"top-bracket"`, `"HIGH INCOME"`). A persona with `income_bracket: "high_potential_low_income"` would incorrectly trigger HC5 — the taxonomy should constrain this field to a canonical enum in a future sprint.

- **TR4/TR5 category for `authority_bias`:** In `BASE_TAXONOMY`, `authority_bias` is in the `social` category (not `psychology`). The G3 implementation uses `_get_attr_value(persona, "social", "authority_bias")`, which is correct. This differs from the old Sprint 1 TR4 which used `"psychology"` — the old lookup would have silently returned `None` for all personas.

- **Small pool edge cases:** With `target_size = 3`, the 5:3:2 formula produces `round(1.5)=2` / `round(0.9)=1` / `0` far — the far band collapses to zero. The stratifier fills the remainder into far, giving 2/1/0, which is within the ±1 tolerance for near (acceptable 1–3) but produces no far-outlier representation. Callers should enforce `target_size ≥ 5` for meaningful stratification.

- **Cosine distance at zero vector:** If a persona has no continuous anchor attributes filled (all None or categorical-only), the anchor vector may be all-zero. Cosine similarity is undefined for zero vectors; the implementation should add a small epsilon guard, which is currently absent.

---

## Patch Notes

### Patch — Fix 1: `check_hard_constraints` rewritten to match Master Spec §10

**File:** `src/generation/constraint_checker.py`

The original HC1–HC6 checked structural/demographic contradictions (age vs. life_stage, dual_income vs. household structure, risk_appetite string vs. status_quo_bias, etc.). These did not match Master Spec §10.

The rewritten HC1–HC6 check behavioral-economic contradictions using income bracket and attribute values:

| # | Old | New |
|---|-----|-----|
| HC1 | `age < 22 AND life_stage == "established"` | `income_bracket contains "poverty" AND premium_quality_preference > 0.85` |
| HC2 | `dual_income AND structure == "single-parent"` | `urban_tier in {"tier3","rural"} AND digital_payment_comfort > 0.85` |
| HC3 | `risk_appetite == "high" AND status_quo_bias > 0.8` | `health_anxiety < 0.2 AND health_supplement_belief > 0.80` (silently skipped if attr absent) |
| HC4 | `trust_anchor == "self" AND authority_bias > 0.85` | `age < 25 AND brand_loyalty > 0.80` |
| HC5 | `brand_loyalty > 0.9 AND indie_brand_openness > 0.85` | `income_bracket contains "high"/"top" AND deal_seeking_intensity > 0.85` |
| HC6 | `decision_style == "analytical" AND information_need < 0.1` | `risk_tolerance > 0.80 AND loss_aversion > 0.80` |

`ConstraintViolation` gained a `suggested_fix: str | None` field, exposed in `to_dict()`. All violations populate this field with the spec's prescribed correction.

### Patch — Fix 2: `g3_tendency_attribute_consistency` rewritten to match Master Spec §10

**File:** `src/schema/validators.py`

The original TR1–TR8 checked tendency → attribute consistency (e.g., "if band is extreme, verify the attribute is high"). The rewritten TR1–TR8 check attribute → tendency consistency (e.g., "if the attribute is high, verify the band is correct"). This is the direction specified in Master Spec §10.

TR4–TR6 now validate `TrustWeights` float fields (`.peer`, `.expert`, `.ad`) rather than the `dominant` string. TR7–TR8 now require the presence of a specific `objection_type` in `objection_profile` rather than checking `derived_insights.risk_appetite` string labels.

Missing attributes are silently skipped in both HC and TR checks — a missing attribute cannot constitute a violation.
