# SPRINT 2 OUTCOME — GOOSE
**Engineer:** Goose
**Role:** Deterministic Computation Engineer
**Sprint:** 2 — Identity Constructor
**Date:** 2026-04-02
**Status:** COMPLETE

---

## 1. Files Created

| File | Lines | Description |
|------|-------|-------------|
| `src/generation/derived_insights.py` | 418 | `DerivedInsightsComputer` — rule-based derivation of all DerivedInsights fields |
| `src/generation/tendency_estimator.py` | 414 | `TendencyEstimator` — proxy-formula assembly of all BehaviouralTendencies fields |

Zero LLM calls in either file. All computation is deterministic formulas.

---

## 2. Decision Style Derivation — Tie-Breaking

Four scores are computed:
- `emotional_score = avg(emotional_persuasion_susceptibility, fear_appeal_responsiveness)`
- `analytical_score = avg(information_need, research_before_purchase)`
- `habitual_score = avg(routine_adherence, status_quo_bias)`
- `social_score = avg(social_proof_bias, peer_influence_strength)`

The winning style is the argmax. On a tie, priority order is: **analytical > social > emotional > habitual**.

**Example (tie):** Suppose `analytical_score = 0.60` and `social_score = 0.60`, both above emotional and habitual. Both tie for max. The tie-break selects `"analytical"` because it appears first in the priority list. The `decision_style_score` is `0.60 / (sum of all four scores)`, normalised to [0,1].

**Implementation detail:** The four `TendencyBandLabel` literals are iterated in priority order; the first one whose score equals `winning_score` is selected. This guarantees determinism even with floating-point equality (values come from the same `avg()` formula, so exact equality is possible when attributes are identical).

---

## 3. Consistency Score — Correlation-Based Formula

For each pair in `KNOWN_CORRELATIONS` (8 pairs):

```
positive pair: pair_score = 1 - abs(val_a - val_b)
  → 1.0 when values are identical (maximum consistency)
  → 0.0 when values are at opposite extremes

negative pair: pair_score = abs(val_a - val_b)
  → 1.0 when values are at opposite extremes (consistent with expected inverse relationship)
  → 0.0 when values are identical (inconsistent: should diverge, but don't)

consistency_score = int(mean(all evaluable pair_scores) * 100)
```

**Range:** 0–100. If no pairs can be evaluated (all referenced attributes missing), defaults to 75.

**Band mapping:**
- 0–49 → "low"
- 50–74 → "medium"
- 75–100 → "high"

**Example:** A profile where `budget_consciousness=0.7` and `deal_seeking_intensity=0.8` (positive pair) scores `1 - abs(0.7 - 0.8) = 0.90`. A profile where `brand_loyalty=0.8` and `indie_brand_openness=0.8` (negative pair) scores `abs(0.8 - 0.8) = 0.0` — correctly flagging an internal contradiction.

---

## 4. reasoning_prompt — Example Assembled Paragraph

For a persona with high price sensitivity, expert trust dominance, high switching propensity, price_vs_value objection, and a quality_vs_budget tension:

```
You tend to be high price-sensitive — you consistently seek deals and carefully weigh every
purchase against your available budget before committing.
You're most influenced by expert — you give heavy weight to credentialed experts and official
sources when evaluating options.
You tend to explore alternatives readily.
Your main concern when making decisions is typically price vs value.
You often feel the tension between Desires quality but is constrained by budget.
```

The `description` fields from `PriceSensitivityBand` and `TrustOrientation` are used directly (they already contain full sentences), avoiding double-prefixing. Switching propensity maps to one of three natural-language phrases: "stay loyal to brands you trust" / "weigh options before switching" / "explore alternatives readily".

---

## 5. Derivation Rules — Uncertainties

**`trust_anchor` vs `trust_orientation.dominant`:** The brief specifies `trust_anchor` (on DerivedInsights) reads directly from the `trust_orientation_primary` categorical attribute, while `trust_orientation.dominant` (on BehaviouralTendencies) is derived from the computed TrustWeights. These can diverge — e.g., a persona anchored to "authority" may have `peer` emerge as the highest computed weight. This is intentional: `trust_anchor` is identity-level (how they self-identify), `dominant` is behavioural (what actually moves them). The implementation honours this distinction.

**Soft-constraint thresholds:** The brief references §10 for soft constraints but does not enumerate them explicitly for this module. I implemented five representative soft-constraint checks drawn from the KNOWN_CORRELATIONS pairs and their semantically logical inversions. The threshold used (divergence > 0.4) was chosen as a reasonable signal; the brief only specifies > 0.6 for "extreme divergence" on positive-correlation pairs, which is also checked separately.

**`coping_mechanism.description`:** The brief asks for a "1-sentence description that references the persona's tension." The five coping descriptions are static templates per tension_seed (no demographic personalisation), as this is deterministic computation with no LLM. Templates are written in second-person to match the rest of the reasoning_prompt register.

---

## 6. Known Gaps — Attributes Referenced but Potentially Missing from Taxonomy

| Attribute | Used In | Status |
|-----------|---------|--------|
| `national_brand_attachment` | `trust_orientation` brand weight | Not in base taxonomy — handled with None-check, falls back to `brand_loyalty` alone |
| `economic_constraint_level` | `price_sensitivity` score | Present in base taxonomy (values category, anchor_order=4) |
| `research_before_purchase` | `decision_style` analytical score | Present in base taxonomy (decision_making) |
| `routine_adherence` | `decision_style` habitual score + `switching_propensity` | Present in base taxonomy (lifestyle) |
| `indie_brand_openness` | `switching_propensity` | Present in base taxonomy (values) |
| `ad_receptivity` | `trust_orientation` ad weight | Present in base taxonomy (lifestyle) |
| `online_community_trust` | `trust_orientation` community weight | Present in base taxonomy (social) |
| `influencer_susceptibility` | `trust_orientation` influencer weight | Present in base taxonomy (social) |
| `peer_influence_strength` | `decision_style` social score + trust weights | Present in base taxonomy (social) |

All attribute accesses go through `_attr()` which returns None on KeyError. All derivation formulas substitute a safe default (0.3–0.5 depending on context) when an attribute is missing. No derivation will raise an exception on a sparse profile.
