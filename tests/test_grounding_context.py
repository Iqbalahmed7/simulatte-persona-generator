"""tests/test_grounding_context.py — Unit tests for grounding_context module.

Sprint 9 — Wire Grounding into Generation Flow.
6 tests, no LLM calls, no --integration flag required.
"""
from __future__ import annotations


def test_grounding_context_has_data():
    from src.grounding.grounding_context import GroundingContext
    ctx = GroundingContext(domain_data=["text 1", "text 2"])
    assert ctx.has_data is True
    assert ctx.data_count == 2


def test_grounding_context_empty():
    from src.grounding.grounding_context import GroundingContext
    ctx = GroundingContext()
    assert ctx.has_data is False
    assert ctx.data_count == 0


def test_compute_distribution_all_proxy():
    from src.grounding.grounding_context import compute_tendency_source_distribution
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    personas = [make_synthetic_persona()]
    dist = compute_tendency_source_distribution(personas)

    assert set(dist.keys()) == {"grounded", "proxy", "estimated"}
    assert dist["grounded"] == 0.0
    assert dist["proxy"] > 0.0
    total = sum(dist.values())
    assert abs(total - 1.0) < 1e-6


def test_compute_distribution_empty_personas():
    from src.grounding.grounding_context import compute_tendency_source_distribution
    dist = compute_tendency_source_distribution([])
    assert dist == {"grounded": 0.0, "proxy": 1.0, "estimated": 0.0}


def test_compute_distribution_sums_to_one():
    """Regardless of mix, distribution must sum to 1.0."""
    from src.grounding.grounding_context import compute_tendency_source_distribution
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    personas = [make_synthetic_persona() for _ in range(5)]
    dist = compute_tendency_source_distribution(personas)
    total = sum(dist.values())
    assert abs(total - 1.0) < 1e-6


def test_build_grounding_summary_from_result():
    """build_grounding_summary_from_result produces valid GroundingSummary."""
    from src.grounding.grounding_context import build_grounding_summary_from_result
    from src.grounding.types import GroundingResult, BehaviouralArchetype
    from src.schema.cohort import GroundingSummary
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    archetype = BehaviouralArchetype(
        archetype_id="arch-1",
        size=5,
        price_sensitivity_band="high",
        trust_orientation_weights={
            "expert": 0.6, "peer": 0.3, "brand": 0.2,
            "ad": 0.1, "community": 0.2, "influencer": 0.1,
        },
        switching_propensity_band="medium",
        primary_objections=["price_vs_value"],
        centroid=[0.7, 0.6, 0.3, 0.2, 0.2, 0.3, 0.2, 0.5, 0.3],
    )

    result = GroundingResult(
        personas=[make_synthetic_persona()],
        archetypes=[archetype],
        signals_extracted=42,
        clusters_derived=1,
    )

    summary = build_grounding_summary_from_result(result)

    assert isinstance(summary, GroundingSummary)
    assert summary.domain_data_signals_extracted == 42
    assert summary.clusters_derived == 1
    assert set(summary.tendency_source_distribution.keys()) == {"grounded", "proxy", "estimated"}
    total = sum(summary.tendency_source_distribution.values())
    assert abs(total - 1.0) < 1e-6
