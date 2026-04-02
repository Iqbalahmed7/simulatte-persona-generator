# SPRINT 8 BRIEF — GOOSE
**Role:** Feature Constructor + Tendency Assigner
**Sprint:** 8 — Grounding Pipeline
**Spec ref:** Master Spec §7 Stages 2 & 4 (Feature Construction + Tendency Assignment)
**Previous rating:** 19/20

---

## Context

Sprint 8 builds the Grounding Pipeline. Your job covers two stages:

- **Stage 2** (`feature_constructor.py`): Aggregate a list of `Signal` objects into a `BehaviouralFeatures` summary.
- **Stage 4** (`tendency_assigner.py`): For a given `PersonaRecord`, find the nearest `BehaviouralArchetype` and upgrade its `BehaviouralTendencies` from `source="proxy"` to `source="grounded"`.

All types come from `src/grounding/types.py` (written by OpenCode). You import from there — do not redefine types.

---

## Types contract (from `src/grounding/types.py`)

```python
from src.grounding.types import Signal, BehaviouralFeatures, BehaviouralArchetype

# BehaviouralFeatures fields:
#   price_salience_index: float
#   trust_source_distribution: dict[str, float]   # expert/peer/brand/ad/community
#   switching_trigger_taxonomy: dict[str, float]  # price/feature/service/competitive/life_change
#   purchase_trigger_taxonomy: dict[str, float]   # need/recommendation/trial/promotion/event
#   objection_cluster_frequencies: dict[str, float]  # price/trust/information
#   signal_count: int
#   to_vector() -> list[float]   # 9-dim vector — do not reimplement, use as-is
```

---

## File 1: `src/grounding/feature_constructor.py`

```python
"""Aggregate Signal list into BehaviouralFeatures.

Sprint 8 — Grounding Pipeline Stage 2.
No LLM calls. Pure rule-based aggregation.
"""
from __future__ import annotations

from src.grounding.types import Signal, BehaviouralFeatures


def construct_features(signals: list[Signal]) -> BehaviouralFeatures:
    """Aggregate a list of Signals into BehaviouralFeatures.

    Args:
        signals: List of Signal objects (may be empty).

    Returns:
        BehaviouralFeatures with all proportions in [0.0, 1.0].
        If signals is empty, returns all-zero BehaviouralFeatures.
    """
    ...
```

### Aggregation rules:

```
signal_count = len(signals)

If signal_count == 0:
    return BehaviouralFeatures(
        price_salience_index=0.0,
        trust_source_distribution={"expert": 0.0, "peer": 0.0, "brand": 0.0, "ad": 0.0, "community": 0.0},
        switching_trigger_taxonomy={"price": 0.0, "feature": 0.0, "service": 0.0, "competitive": 0.0, "life_change": 0.0},
        purchase_trigger_taxonomy={"need": 0.0, "recommendation": 0.0, "trial": 0.0, "promotion": 0.0, "event": 0.0},
        objection_cluster_frequencies={"price": 0.0, "trust": 0.0, "information": 0.0},
        signal_count=0,
    )

price_salience_index:
    count of signals where signal_type == "price_mention"
    divided by signal_count

trust_source_distribution (proportion of trust_citation signals by inferred source):
    For each trust_citation signal, scan text.lower() for:
        "expert" or "doctor" or "certified" → expert
        "friend" or "peer" or "colleague"   → peer
        "brand" or "branded"                → brand
        "review" or "community" or "users"  → community
        anything else                        → ad (catch-all)
    Compute proportion of each category among ALL trust_citation signals.
    If zero trust_citation signals: all zeros.

switching_trigger_taxonomy (proportion of switching signals by trigger type):
    For each switching signal, scan text.lower() for:
        any of {"price", "cost", "expensive", "cheap"}  → price
        any of {"quality", "feature", "better"}          → feature
        any of {"service", "support", "delivery"}        → service
        any of {"competition", "competitor", "rival"}    → competitive
        any of {"moved", "life", "baby", "job", "home"}  → life_change
        default                                          → price (fallback)
    Compute proportion of each category among ALL switching signals.
    If zero switching signals: all zeros.

purchase_trigger_taxonomy (proportion of purchase_trigger signals by trigger type):
    For each purchase_trigger signal, scan text.lower() for:
        any of {"need", "essential", "required", "must"}  → need
        any of {"recommend", "told me", "suggested"}       → recommendation
        any of {"trial", "tried", "sample", "free"}        → trial
        any of {"sale", "discount", "promotion", "offer"}  → promotion
        any of {"event", "occasion", "gift", "birthday"}   → event
        default                                            → need (fallback)
    Compute proportion of each category among ALL purchase_trigger signals.
    If zero purchase_trigger signals: all zeros.

objection_cluster_frequencies:
    Computed across rejection signals:
        text.lower() has price keyword       → "price" bucket
        text.lower() has "trust" / "doubt"  → "trust" bucket
        otherwise                            → "information" bucket
    If zero rejection signals: all zeros.
```

---

## File 2: `src/grounding/tendency_assigner.py`

```python
"""Assign grounded BehaviouralTendencies to a PersonaRecord.

Sprint 8 — Grounding Pipeline Stage 4.
No LLM calls.
"""
from __future__ import annotations

import math

from src.grounding.types import BehaviouralArchetype
from src.schema.persona import PersonaRecord


def assign_grounded_tendencies(
    persona: PersonaRecord,
    archetypes: list[BehaviouralArchetype],
) -> PersonaRecord:
    """Find nearest archetype and upgrade persona's BehaviouralTendencies.

    Steps:
    1. Convert persona attributes to a 9-dim feature vector
       using _persona_to_vector().
    2. Find nearest BehaviouralArchetype by Euclidean distance to centroid.
    3. Build new BehaviouralTendencies from nearest archetype,
       all fields with source="grounded".
    4. Return updated PersonaRecord via model_copy(update={"behavioural_tendencies": ...}).

    If archetypes is empty, return persona unchanged.
    """
    ...
```

### Persona-to-vector conversion

The same 9 dimensions as `BehaviouralFeatures.to_vector()`. Use persona attributes to estimate each dimension:

```python
def _persona_to_vector(persona: PersonaRecord) -> list[float]:
    """Convert persona attributes to a 9-dim feature vector for archetype matching.

    Dimension map:
      0: price_salience_index  → proxy from price_sensitivity.band:
            "extreme" → 0.9, "high" → 0.7, "medium" → 0.4, "low" → 0.15
      1: trust_expert          → trust_orientation.weights.expert
      2: trust_peer            → trust_orientation.weights.peer
      3: trust_brand           → trust_orientation.weights.brand
      4: trust_community       → trust_orientation.weights.community
      5: switching_price       → 0.8 if switching_propensity.band == "high" else 0.2
      6: switching_service     → 0.3 if switching_propensity.band != "low" else 0.1
      7: trigger_need          → 0.6 (neutral default — no direct attribute)
      8: trigger_rec           → trust_orientation.weights.peer * 0.8
    """
    ...
```

### Building grounded tendencies from archetype

```python
def _build_grounded_tendencies(archetype: BehaviouralArchetype, persona: PersonaRecord):
    """Build new BehaviouralTendencies from archetype, source='grounded'.

    Rules:
    - price_sensitivity: band and source from archetype.price_sensitivity_band.
      Description: reuse from existing TendencyEstimator descriptions — just update band + source.
      Use this exact description format:
        f"You tend to be {band} price-sensitive — {PRICE_BAND_DESCRIPTIONS[band]}"
      Where PRICE_BAND_DESCRIPTIONS matches the ones in tendency_estimator.py.

    - trust_orientation: weights from archetype.trust_orientation_weights.
      dominant = key with max weight.
      description: f"You're most influenced by {dominant} — {DOMINANT_DESCRIPTIONS[dominant]}"
      source = "grounded"

    - switching_propensity: band from archetype.switching_propensity_band.
      Source = "grounded". Use same descriptions as TendencyEstimator.

    - objection_profile: derive from archetype.primary_objections.
      Map each objection string to an Objection object:
        "price_vs_value"        → Objection(objection_type="price_vs_value", likelihood="high", severity="friction")
        "switching_cost_concern" → Objection(objection_type="switching_cost_concern", likelihood="medium", severity="minor")
        "need_more_information"  → Objection(objection_type="need_more_information", likelihood="medium", severity="friction")
      Default fallback: Objection(objection_type="need_more_information", likelihood="low", severity="minor")

    - reasoning_prompt: reuse existing persona.behavioural_tendencies.reasoning_prompt
      (tendencies updated but narrative context unchanged).

    All imports needed:
        from src.schema.persona import (
            BehaviouralTendencies, PriceSensitivityBand, TrustOrientation,
            TrustWeights, TendencyBand, Objection,
        )
    """
    ...
```

---

## Tests: `tests/test_grounding_features.py`

### Test 1: Empty signals → all-zero features

```python
def test_empty_signals_returns_zero_features():
    from src.grounding.feature_constructor import construct_features
    features = construct_features([])
    assert features.signal_count == 0
    assert features.price_salience_index == 0.0
    assert all(v == 0.0 for v in features.trust_source_distribution.values())
```

### Test 2: Price salience index correct

```python
def test_price_salience_index():
    """3 price signals out of 5 total → price_salience_index = 0.6."""
    from src.grounding.feature_constructor import construct_features
    from src.grounding.types import Signal
    signals = [
        Signal(id="1", text="too expensive", signal_type="price_mention"),
        Signal(id="2", text="too expensive", signal_type="price_mention"),
        Signal(id="3", text="too expensive", signal_type="price_mention"),
        Signal(id="4", text="I bought it", signal_type="purchase_trigger"),
        Signal(id="5", text="my friend said", signal_type="trust_citation"),
    ]
    features = construct_features(signals)
    assert abs(features.price_salience_index - 0.6) < 1e-9
    assert features.signal_count == 5
```

### Test 3: Trust source distribution sums ≤ 1.0

```python
def test_trust_source_distribution_valid():
    from src.grounding.feature_constructor import construct_features
    from src.grounding.types import Signal
    signals = [
        Signal(id="1", text="my doctor recommended it", signal_type="trust_citation"),
        Signal(id="2", text="my friend suggested this", signal_type="trust_citation"),
        Signal(id="3", text="a community review said", signal_type="trust_citation"),
    ]
    features = construct_features(signals)
    total = sum(features.trust_source_distribution.values())
    assert abs(total - 1.0) < 1e-9 or total <= 1.0
    # Keys must all be present
    assert set(features.trust_source_distribution.keys()) == {
        "expert", "peer", "brand", "ad", "community"
    }
```

### Test 4: Switching trigger taxonomy populated

```python
def test_switching_trigger_taxonomy():
    from src.grounding.feature_constructor import construct_features
    from src.grounding.types import Signal
    signals = [
        Signal(id="1", text="switched because the price doubled", signal_type="switching"),
        Signal(id="2", text="switched because quality declined", signal_type="switching"),
    ]
    features = construct_features(signals)
    assert set(features.switching_trigger_taxonomy.keys()) == {
        "price", "feature", "service", "competitive", "life_change"
    }
    assert features.switching_trigger_taxonomy["price"] > 0
```

### Test 5: assign_grounded_tendencies with no archetypes

```python
def test_assign_grounded_no_archetypes():
    """Empty archetypes list → persona returned unchanged."""
    from src.grounding.tendency_assigner import assign_grounded_tendencies
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    persona = make_synthetic_persona()
    result = assign_grounded_tendencies(persona, [])
    assert result.behavioural_tendencies.price_sensitivity.source == "proxy"
```

### Test 6: assign_grounded_tendencies upgrades source

```python
def test_assign_grounded_upgrades_source():
    """With archetypes present, at least one tendency should be 'grounded'."""
    from src.grounding.tendency_assigner import assign_grounded_tendencies
    from src.grounding.types import BehaviouralArchetype
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    archetype = BehaviouralArchetype(
        archetype_id="arch-1",
        size=10,
        price_sensitivity_band="high",
        trust_orientation_weights={
            "expert": 0.6, "peer": 0.3, "brand": 0.2,
            "ad": 0.1, "community": 0.2, "influencer": 0.1,
        },
        switching_propensity_band="medium",
        primary_objections=["price_vs_value"],
        centroid=[0.7, 0.6, 0.3, 0.2, 0.2, 0.3, 0.2, 0.5, 0.3],
    )

    result = assign_grounded_tendencies(persona, [archetype])
    bt = result.behavioural_tendencies
    sources = {bt.price_sensitivity.source, bt.trust_orientation.source, bt.switching_propensity.source}
    assert "grounded" in sources
```

### Test 7: persona_to_vector produces 9 dims

```python
def test_persona_to_vector_shape():
    from src.grounding.tendency_assigner import _persona_to_vector
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    persona = make_synthetic_persona()
    v = _persona_to_vector(persona)
    assert len(v) == 9
    assert all(isinstance(x, float) for x in v)
    assert all(0.0 <= x <= 1.0 for x in v)
```

### Test 8: BehaviouralFeatures.to_vector() compatibility

```python
def test_behavioural_features_to_vector_shape():
    """to_vector() on BehaviouralFeatures returns 9 floats."""
    from src.grounding.feature_constructor import construct_features
    from src.grounding.types import Signal
    signals = [
        Signal(id="1", text="too expensive, avoided it", signal_type="price_mention"),
        Signal(id="2", text="switched brands due to price", signal_type="switching"),
    ]
    features = construct_features(signals)
    v = features.to_vector()
    assert len(v) == 9
    assert all(isinstance(x, float) for x in v)
```

---

## Constraints

- No LLM calls.
- `construct_features([])` must not crash — return all-zero features.
- `assign_grounded_tendencies(persona, [])` must return the persona unchanged.
- `trust_source_distribution` must always have exactly the keys: expert, peer, brand, ad, community.
- `switching_trigger_taxonomy` must always have exactly: price, feature, service, competitive, life_change.
- `purchase_trigger_taxonomy` must always have exactly: need, recommendation, trial, promotion, event.
- `objection_cluster_frequencies` must always have exactly: price, trust, information.
- 8 tests, all pass without `--integration`.

---

## Outcome File

When done, write `sprints/outcome_goose.md` with:
1. Files created (line counts)
2. Feature construction — aggregation logic for each field
3. Tendency assigner — persona-to-vector approach + archetype selection
4. Test results (pass/fail)
5. Known gaps
