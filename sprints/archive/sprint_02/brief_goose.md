# SPRINT 2 BRIEF — GOOSE
**Role:** Deterministic Computation Engineer
**Sprint:** 2 — Identity Constructor
**Spec check:** Master Spec §5 (derived_insights, behavioural_tendencies schemas), §10 (tendency-attribute consistency), §14A S2 (tendencies are soft priors — settled)
**Previous rating:** 12/20 — 7 integration bugs found and patched. Filling logic and prompt design were sound. Integration verification required for Sprint 2.

---

## Your Job This Sprint

You own the two deterministic computation components: `derived_insights.py` (computes decision style, trust anchor, etc. from attributes — no LLM) and `tendency_estimator.py` (assembles the natural-language tendency fields from attribute values — no LLM).

Two files. Zero LLM calls.

---

## File 1: `src/generation/derived_insights.py`

### What It Does

Computes `DerivedInsights` deterministically from the filled attribute profile. No LLM calls — all derivations are rule-based formulas.

### Interface

```python
from src.schema.persona import DerivedInsights, Attribute, DemographicAnchor

class DerivedInsightsComputer:

    def compute(
        self,
        attributes: dict[str, dict[str, Attribute]],
        demographic_anchor: DemographicAnchor,
    ) -> DerivedInsights:
        """
        Computes all DerivedInsights fields from attributes.
        No LLM calls. All rule-based.
        """
        ...
```

### Derivation Rules

**`decision_style`** — Literal["emotional","analytical","habitual","social"]

Use these attribute thresholds (all from `attributes`):
```python
emotional_score   = avg(emotional_persuasion_susceptibility, fear_appeal_responsiveness)
analytical_score  = avg(information_need, research_before_purchase)
habitual_score    = avg(routine_adherence, status_quo_bias)
social_score      = avg(social_proof_bias, peer_influence_strength)

decision_style = argmax(emotional, analytical, habitual, social)
```
If a tie, prefer: analytical > social > emotional > habitual.

**`decision_style_score`** — 0.0–1.0

The winning score normalised to [0,1]:
```python
decision_style_score = winning_score / (sum_of_all_scores or 1.0)
```

**`trust_anchor`** — Literal["self","peer","authority","family"]

Map directly from the anchor attribute `trust_orientation_primary` value. This is already categorical — just read it.

**`risk_appetite`** — Literal["low","medium","high"]

```python
rt = risk_tolerance value (float)
if rt < 0.35:   "low"
elif rt < 0.65: "medium"
else:           "high"
```

**`primary_value_orientation`** — Literal["price","quality","brand","convenience","features"]

Map from `primary_value_driver` anchor attribute:
```
"price"         → "price"
"quality"       → "quality"
"brand"         → "brand"
"convenience"   → "convenience"
"relationships" → "quality"   # closest proxy
"status"        → "brand"     # closest proxy
```

**`coping_mechanism`** — CopingMechanism

Use `tension_seed` anchor attribute to derive:
```
"aspiration_vs_constraint"  → type="routine_control",      description="..."
"independence_vs_validation"→ type="social_validation",    description="..."
"quality_vs_budget"         → type="research_deep_dive",   description="..."
"loyalty_vs_curiosity"      → type="optimism_bias",        description="..."
"control_vs_delegation"     → type="denial",               description="..."
```

Write a 1-sentence `description` for each that references the persona's tension.

**`consistency_score`** — int 0–100

Measures how internally consistent the attribute profile is. Use correlation constraint satisfaction as a proxy:
```python
# For each pair in KNOWN_CORRELATIONS:
# - positive pair: score = 1 - abs(val_a - val_b)
# - negative pair: score = abs(val_a - val_b)
# consistency_score = int(mean(all pair scores) * 100)
```
If no correlation pairs can be evaluated (all values missing), default to 75.

**`consistency_band`** — Literal["low","medium","high"]
```
0–49   → "low"
50–74  → "medium"
75–100 → "high"
```

**`key_tensions`** — list[str] (≥ 1 required)

Derive from soft constraint checks + the tension_seed:
1. Always include: a human-readable version of `tension_seed` (e.g., "aspiration_vs_constraint" → "Aspires to more than current constraints allow")
2. Check soft constraints from §10 and add any that apply as tension strings
3. Check for any attribute pairs with extreme divergence (|val_a - val_b| > 0.6 on a positive-correlation pair) and add as tension

### Safe Attribute Access

Use a helper:
```python
def _attr(self, attributes: dict, category: str, name: str) -> float | str | None:
    try:
        return attributes[category][name].value
    except KeyError:
        return None
```
All derivations must handle None gracefully (use defaults when attributes are missing).

---

## File 2: `src/generation/tendency_estimator.py`

### What It Does

Computes `BehaviouralTendencies` from the filled attribute profile using proxy formulas. No LLM calls. All tendency fields carry `source="proxy"` since no domain data is available at this stage.

### Interface

```python
from src.schema.persona import (
    BehaviouralTendencies, TendencyBand, PriceSensitivityBand,
    TrustOrientation, TrustWeights, Objection, Attribute, DerivedInsights
)

class TendencyEstimator:

    def estimate(
        self,
        attributes: dict[str, dict[str, Attribute]],
        derived_insights: DerivedInsights,
    ) -> BehaviouralTendencies:
        """
        Computes BehaviouralTendencies from attributes + derived_insights.
        All fields carry source="proxy".
        No LLM calls.
        """
        ...
```

### Proxy Formulas

**`price_sensitivity`** — PriceSensitivityBand

```python
score = avg(budget_consciousness, deal_seeking_intensity, economic_constraint_level)
# economic_constraint_level is an anchor attribute in the "values" category

if score < 0.35:   band = "low"
elif score < 0.55: band = "medium"
elif score < 0.75: band = "high"
else:              band = "extreme"
```

Description template: `"You tend to be [band] price-sensitive — [1-sentence behavioural description based on band and score]."`

**`trust_orientation`** — TrustOrientation

Compute weights from attributes:
```python
weights = TrustWeights(
    expert    = clamp(authority_bias, 0.0, 1.0),
    peer      = clamp(social_proof_bias * 0.9 + peer_influence_strength * 0.1, 0.0, 1.0),
    brand     = clamp(brand_loyalty * 0.7 + national_brand_attachment * 0.3, 0.0, 1.0),
    # national_brand_attachment may not exist in base taxonomy — use brand_loyalty alone if missing
    ad        = clamp(ad_receptivity, 0.0, 1.0),
    community = clamp(online_community_trust, 0.0, 1.0),
    influencer= clamp(influencer_susceptibility, 0.0, 1.0),
)
dominant = name of the highest-weight key
```

For attributes missing from the profile, use 0.3 as a neutral default.

Description: `"You're most influenced by [dominant] — [1-sentence description of trust pattern]."`

**`switching_propensity`** — TendencyBand

```python
score = avg(1 - brand_loyalty, indie_brand_openness, 1 - routine_adherence)
# Inverted brand_loyalty and routine_adherence: low loyalty + high openness → high switching

if score < 0.35:   band = "low"
elif score < 0.65: band = "medium"
else:              band = "high"
```

**`objection_profile`** — list[Objection]

Generate 2–4 objections using rule-based logic:
```python
objections = []

if price_sensitivity.band in ("high", "extreme"):
    objections.append(Objection(
        objection_type="price_vs_value",
        likelihood="high",
        severity="blocking" if band == "extreme" else "friction"
    ))

if risk_tolerance < 0.35:
    objections.append(Objection(
        objection_type="risk_aversion",
        likelihood="high",
        severity="friction"
    ))

if information_need > 0.70:
    objections.append(Objection(
        objection_type="need_more_information",
        likelihood="medium",
        severity="friction"
    ))

if trust_orientation.dominant in ("peer", "authority") and social_proof_bias < 0.4:
    objections.append(Objection(
        objection_type="social_proof_gap",
        likelihood="medium",
        severity="minor"
    ))

# Always add at least 1 if none generated (fallback)
if not objections:
    objections.append(Objection(
        objection_type="need_more_information",
        likelihood="low",
        severity="minor"
    ))
```

**`reasoning_prompt`** — str

Assemble the natural-language paragraph injected into LLM reasoning context. This is the most important field — it is what makes tendencies usable in cognition.

Template:
```
You tend to be [price_sensitivity.band] price-sensitive — [price_sensitivity.description].
You're most influenced by [trust_orientation.dominant] — [trust_orientation.description].
You tend to [low/medium/high switching: "stay loyal to brands you trust" / "weigh options before switching" / "explore alternatives readily"].
Your main concern when making decisions is typically [primary objection type from objection_profile].
[If key_tensions[0] is available]: You often feel the tension between [key_tensions[0]].
```

---

## Integration Contract

- **Called by Cursor:** `DerivedInsightsComputer.compute()` at Step 2, `TendencyEstimator.estimate()` at Step 4
- **Imports from schema:** `src.schema.persona`
- **Imports from taxonomy:** `from src.taxonomy.base_taxonomy import KNOWN_CORRELATIONS`
- **Exports:** `DerivedInsightsComputer`, `TendencyEstimator`

---

## Constraints

- **Zero LLM calls.** All computation is deterministic formulas. If you feel tempted to call an LLM, encode it as a rule instead.
- **All tendency fields must carry `source="proxy"`.** Per §10 and P10 (settled).
- **`key_tensions` must have ≥ 1 item.** The Pydantic validator will reject an empty list. Guarantee at least the tension_seed-derived tension.
- **Do not import from `identity_constructor.py`** (circular dependency risk). Only import from schema and taxonomy.

---

## Outcome File

When done, write `sprints/outcome_goose.md` (overwrite the Sprint 1 patch version) with:
1. Files created (line counts)
2. Decision style derivation — describe how ties are broken with an example
3. Consistency score — describe the correlation-based formula and its range
4. reasoning_prompt — show an example assembled paragraph
5. Any derivation rules you were uncertain about
6. Known gaps (e.g., attributes referenced in formulas that may be missing from taxonomy)
