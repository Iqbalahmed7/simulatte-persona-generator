"""Tests for the Grounding Pipeline orchestrator.

Sprint 8 — Grounding Pipeline.
All stage functions are mocked so these tests run without the other
engineers' files (feature_constructor, cluster_deriver, tendency_assigner).

Tests:
  1. test_pipeline_raises_on_empty_texts
  2. test_pipeline_returns_correct_shape
  3. test_pipeline_warning_below_threshold
  4. test_pipeline_with_no_personas
  5. test_pipeline_upgrades_tendency_source
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from src.grounding.types import BehaviouralArchetype, BehaviouralFeatures, Signal


# ---------------------------------------------------------------------------
# Shared helpers / fixtures
# ---------------------------------------------------------------------------

def _make_archetype(archetype_id: str = "arch-1") -> BehaviouralArchetype:
    """Build a minimal BehaviouralArchetype for mock returns."""
    return BehaviouralArchetype(
        archetype_id=archetype_id,
        size=5,
        price_sensitivity_band="high",
        trust_orientation_weights={"expert": 0.4, "peer": 0.6, "brand": 0.3,
                                   "ad": 0.1, "community": 0.5, "influencer": 0.2},
        switching_propensity_band="medium",
        primary_objections=["price", "trust"],
        centroid=[0.5, 0.4, 0.6, 0.3, 0.5, 0.4, 0.2, 0.3, 0.5],
    )


def _make_signals(n: int = 3) -> list[Signal]:
    """Return n minimal Signal stubs for mock returns."""
    return [
        Signal(id=f"sig-{i}", text=f"text {i}", signal_type="price_mention")
        for i in range(n)
    ]


def _make_features() -> BehaviouralFeatures:
    """Return a minimal BehaviouralFeatures stub for mock returns."""
    return BehaviouralFeatures(
        price_salience_index=0.5,
        trust_source_distribution={"expert": 0.4, "peer": 0.6, "brand": 0.3,
                                   "ad": 0.1, "community": 0.5},
        switching_trigger_taxonomy={"price": 0.4, "feature": 0.2, "service": 0.3,
                                    "competitive": 0.1, "life_change": 0.0},
        purchase_trigger_taxonomy={"need": 0.5, "recommendation": 0.3, "trial": 0.1,
                                   "promotion": 0.1, "event": 0.0},
        objection_cluster_frequencies={"price": 0.5, "trust": 0.3, "information": 0.2},
        signal_count=3,
    )


# Patch targets — all stage functions are imported lazily inside pipeline.py
_EXTRACT = "src.grounding.signal_extractor.extract_signals"
_VECTORS = "src.grounding.signal_extractor.signals_to_vectors"
_CONSTRUCT = "src.grounding.feature_constructor.construct_features"
_CLUSTER = "src.grounding.cluster_deriver.derive_clusters"
_ASSIGN = "src.grounding.tendency_assigner.assign_grounded_tendencies"


# ---------------------------------------------------------------------------
# Test 1: Pipeline raises on empty input
# ---------------------------------------------------------------------------

def test_pipeline_raises_on_empty_texts():
    from src.grounding.pipeline import run_grounding_pipeline
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    with pytest.raises(ValueError, match="empty"):
        run_grounding_pipeline([], [persona])


# ---------------------------------------------------------------------------
# Test 2: Pipeline returns correct shape
# ---------------------------------------------------------------------------

def test_pipeline_returns_correct_shape():
    """5 texts, 2 personas → GroundingResult with 2 updated personas, archetypes derived,
    signals_extracted > 0, clusters_derived == len(archetypes).
    """
    from src.grounding.pipeline import run_grounding_pipeline
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    texts = [
        "I bought this because my friend recommended it.",
        "Too expensive, I avoided it.",
        "Switched from my usual brand due to the high price.",
        "A trusted expert reviewed this positively.",
        "The price point was reasonable so I tried it.",
    ]
    personas = [make_synthetic_persona(), make_synthetic_persona()]

    mock_signals = _make_signals(5)
    mock_archetypes = [_make_archetype("arch-1"), _make_archetype("arch-2")]
    mock_features = _make_features()
    mock_vectors = [[0.0] * 9] * 5

    with patch(_EXTRACT, return_value=mock_signals), \
         patch(_VECTORS, return_value=mock_vectors), \
         patch(_CONSTRUCT, return_value=mock_features), \
         patch(_CLUSTER, return_value=mock_archetypes), \
         patch(_ASSIGN, side_effect=lambda p, _archetypes: p):

        result = run_grounding_pipeline(texts, personas)

    assert result.signals_extracted > 0
    assert result.clusters_derived == len(result.archetypes)
    assert len(result.personas) == 2


# ---------------------------------------------------------------------------
# Test 3: Warning fires below threshold
# ---------------------------------------------------------------------------

def test_pipeline_warning_below_threshold():
    """Fewer than 200 signals → warning string populated containing '200'."""
    from src.grounding.pipeline import run_grounding_pipeline
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    texts = [
        "I switched brands because the price was too high.",
        "A friend told me to try this product.",
        "Bought it on sale.",
    ]

    mock_signals = _make_signals(3)  # 3 < 200 → should trigger warning
    mock_archetypes = [_make_archetype()]
    mock_features = _make_features()
    mock_vectors = [[0.0] * 9] * 3

    with patch(_EXTRACT, return_value=mock_signals), \
         patch(_VECTORS, return_value=mock_vectors), \
         patch(_CONSTRUCT, return_value=mock_features), \
         patch(_CLUSTER, return_value=mock_archetypes), \
         patch(_ASSIGN, side_effect=lambda p, _archetypes: p):

        result = run_grounding_pipeline(texts, [make_synthetic_persona()])

    assert result.warning is not None
    assert "200" in result.warning


# ---------------------------------------------------------------------------
# Test 4: Pipeline with empty personas list
# ---------------------------------------------------------------------------

def test_pipeline_with_no_personas():
    """Zero personas is valid — pipeline still runs signal/cluster stages."""
    from src.grounding.pipeline import run_grounding_pipeline

    texts = [
        "I bought this because it was on sale.",
        "Switched from my usual brand — the price doubled.",
        "A trusted friend recommended it.",
    ]

    mock_signals = _make_signals(3)
    mock_archetypes = [_make_archetype()]
    mock_features = _make_features()
    mock_vectors = [[0.0] * 9] * 3

    with patch(_EXTRACT, return_value=mock_signals), \
         patch(_VECTORS, return_value=mock_vectors), \
         patch(_CONSTRUCT, return_value=mock_features), \
         patch(_CLUSTER, return_value=mock_archetypes), \
         patch(_ASSIGN, side_effect=lambda p, _archetypes: p):

        result = run_grounding_pipeline(texts, [])

    assert result.signals_extracted > 0
    assert len(result.personas) == 0


# ---------------------------------------------------------------------------
# Test 5: Grounded tendencies have correct source
# ---------------------------------------------------------------------------

def test_pipeline_upgrades_tendency_source():
    """After pipeline runs, at least one tendency on each persona
    should carry source='grounded'.
    """
    from src.grounding.pipeline import run_grounding_pipeline
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    texts = [
        "I always check the price before buying — bought after a discount.",
        "Switched brands because this one was cheaper.",
        "A peer recommended this and I trusted them.",
        "Too expensive, I rejected it outright.",
        "Found this through an expert review — decided to buy.",
    ] * 5  # 25 signals total

    persona = make_synthetic_persona()

    # Mock assign_grounded_tendencies to simulate upgrading tendency sources
    # from "proxy" to "grounded" (as the real function does).
    def _mock_assign(p, _archetypes):
        from src.schema.persona import (
            BehaviouralTendencies, PriceSensitivityBand, TendencyBand,
            TrustOrientation,
        )
        bt = p.behavioural_tendencies
        new_bt = BehaviouralTendencies(
            price_sensitivity=PriceSensitivityBand(
                band=bt.price_sensitivity.band,
                description=bt.price_sensitivity.description,
                source="grounded",
            ),
            trust_orientation=TrustOrientation(
                weights=bt.trust_orientation.weights,
                dominant=bt.trust_orientation.dominant,
                description=bt.trust_orientation.description,
                source="grounded",
            ),
            switching_propensity=TendencyBand(
                band=bt.switching_propensity.band,
                description=bt.switching_propensity.description,
                source="grounded",
            ),
            objection_profile=bt.objection_profile,
            reasoning_prompt=bt.reasoning_prompt,
        )
        return p.model_copy(update={"behavioural_tendencies": new_bt})

    mock_signals = _make_signals(25)
    mock_archetypes = [_make_archetype()]
    mock_features = _make_features()
    mock_vectors = [[0.0] * 9] * 25

    with patch(_EXTRACT, return_value=mock_signals), \
         patch(_VECTORS, return_value=mock_vectors), \
         patch(_CONSTRUCT, return_value=mock_features), \
         patch(_CLUSTER, return_value=mock_archetypes), \
         patch(_ASSIGN, side_effect=_mock_assign):

        result = run_grounding_pipeline(texts, [persona])

    updated = result.personas[0]
    bt = updated.behavioural_tendencies
    sources = {
        bt.price_sensitivity.source,
        bt.trust_orientation.source,
        bt.switching_propensity.source,
    }
    assert "grounded" in sources, (
        f"Expected at least one grounded tendency. Got sources: {sources}"
    )
