"""tests/test_grounding_features.py

Sprint 8 — Grounding Pipeline tests.
8 unit tests covering feature construction and tendency assignment.
No LLM calls.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Test 1: Empty signals → all-zero features
# ---------------------------------------------------------------------------

def test_empty_signals_returns_zero_features():
    from src.grounding.feature_constructor import construct_features
    features = construct_features([])
    assert features.signal_count == 0
    assert features.price_salience_index == 0.0
    assert all(v == 0.0 for v in features.trust_source_distribution.values())


# ---------------------------------------------------------------------------
# Test 2: Price salience index correct
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Test 3: Trust source distribution sums ≤ 1.0
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Test 4: Switching trigger taxonomy populated
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Test 5: assign_grounded_tendencies with no archetypes
# ---------------------------------------------------------------------------

def test_assign_grounded_no_archetypes():
    """Empty archetypes list → persona returned unchanged."""
    from src.grounding.tendency_assigner import assign_grounded_tendencies
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    persona = make_synthetic_persona()
    result = assign_grounded_tendencies(persona, [])
    assert result.behavioural_tendencies.price_sensitivity.source == "proxy"


# ---------------------------------------------------------------------------
# Test 6: assign_grounded_tendencies upgrades source
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Test 7: persona_to_vector produces 9 dims
# ---------------------------------------------------------------------------

def test_persona_to_vector_shape():
    from src.grounding.tendency_assigner import _persona_to_vector
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    persona = make_synthetic_persona()
    v = _persona_to_vector(persona)
    assert len(v) == 9
    assert all(isinstance(x, float) for x in v)
    assert all(0.0 <= x <= 1.0 for x in v)


# ---------------------------------------------------------------------------
# Test 8: BehaviouralFeatures.to_vector() compatibility
# ---------------------------------------------------------------------------

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
