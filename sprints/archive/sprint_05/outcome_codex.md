# SPRINT 5 OUTCOME — CODEX

## 1. Files Created

| File | Lines |
|------|-------|
| `src/cohort/__init__.py` | 0 (empty module marker) |
| `src/cohort/type_coverage.py` | 389 |

---

## 2. Classification Rules — Scoring Table

All scores are 0–1. The type with the highest score wins. Ties broken by enum order (first wins). If all scores are 0, defaults to `PRAGMATIST`.

| Type | Signal | Points |
|------|--------|--------|
| **The Pragmatist** | `price_sensitivity.band` in ("high", "extreme") | +0.4 |
| | `switching_propensity.band` in ("high", "extreme") | +0.3 |
| | `brand_loyalty` < 0.35 | +0.3 |
| **The Loyalist** | `switching_propensity.band` in ("low", "very_low") | +0.4 |
| | `derived_insights.decision_style` == "habitual" | +0.4 |
| | `brand_loyalty` > 0.75 | +0.2 |
| **The Aspirant** | `tension_seed` == "aspiration_vs_constraint" | +0.5 |
| | `primary_value_driver` in ("status", "brand") | +0.3 |
| | `economic_constraint_level` > 0.6 | +0.2 |
| **The Anxious Optimizer** | `derived_insights.decision_style` == "analytical" | +0.4 |
| | `risk_tolerance` < 0.3 | +0.3 |
| | `analysis_paralysis` > 0.6 (if present) | +0.3 |
| **The Social Validator** | `derived_insights.trust_anchor` == "peer" | +0.5 |
| | `derived_insights.decision_style` == "social" | +0.3 |
| | `social_proof_bias` > 0.65 | +0.2 |
| **The Value Rebel** | `tension_seed` == "independence_vs_validation" | +0.3 |
| | `social_orientation` < 0.3 (continuous only) | +0.3 |
| | `brand_loyalty` < 0.25 | +0.2 |
| | `primary_value_driver` not in ("brand", "status") | +0.2 |
| **The Reluctant User** | `switching_propensity.band` in ("high", "extreme") | +0.3 |
| | `brand_loyalty` < 0.4 | +0.2 |
| | `tension_seed` == "loyalty_vs_curiosity" | +0.3 |
| | `risk_tolerance` < 0.4 | +0.2 |
| **The Power User** | `derived_insights.decision_style` == "analytical" | +0.2 |
| | `brand_loyalty` > 0.80 | +0.4 |
| | `switching_propensity.band` in ("very_low", "low") | +0.4 |

---

## 3. `check_type_coverage` — Behaviour by Cohort Size

```
_COVERAGE_RULES = {3: 3, 5: 4, 10: 8}

def _required_types(n):
    if n >= 10: return 8
    return _COVERAGE_RULES.get(n, min(n, 8))
```

| N | Required distinct types | Passes if |
|---|------------------------|-----------|
| 3 | 3 | >= 3 of 8 types present |
| 5 | 4 | >= 4 of 8 types present |
| 10 | 8 | all 8 types present |
| 11+ | 8 | all 8 types present |

Return signature: `(passed: bool, present_types: list[PersonaType], missing_types: list[PersonaType])`

- `present_types` and `missing_types` are always sorted in enum declaration order.
- The union of present and missing always equals all 8 PersonaType members.

---

## 4. Known Gaps

**Attribute absence handling**
`_get_attr_value` returns `None` when an attribute is absent. All scoring branches guard with `is not None` checks, so missing attributes silently contribute 0 points. This is correct per spec but means sparse personas may land on PRAGMATIST by default even if that is not semantically correct.

**`social_orientation` type ambiguity**
The spec scores `social_orientation < 0.3` implying a continuous float, but the existing synthetic fixture stores it as a categorical string (`"community"`). The implementation guards with `isinstance(..., (int, float))`, so categorical values silently yield 0 for this signal. Downstream generators should ensure `social_orientation` is continuous when Value Rebel classification is needed.

**Tie-breaking**
Ties are broken by enum order (PRAGMATIST wins over LOYALIST, etc.). This is deterministic but may not reflect semantic priority. No spec guidance on preferred tie-breaking order was provided beyond "first one wins."

**`analysis_paralysis` attribute**
Marked as optional in the spec ("if present"). Absent in current fixtures. The implementation handles absence correctly (0 contribution).

**Cohort sizes not in the coverage rule table**
For N in {1, 2, 4, 6, 7, 8, 9}, `_required_types` falls back to `min(N, 8)`. This means N=4 requires 4 distinct types, and N=6/7/8/9 require 6/7/8/8 respectively. This is the specified fallback behaviour.
