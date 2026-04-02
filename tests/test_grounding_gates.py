"""tests/test_grounding_gates.py — Grounding pipeline gate tests.

Sprint 8 — Grounding Pipeline.
Validates: schema shapes, warning behaviour, G11 tendency source compliance,
GroundingSummary field population, archetype centroid dimensions.

No LLM calls. All tests call run_grounding_pipeline directly (no mocking of
internal stages).
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Test 1: GroundingResult has correct field shapes
# ---------------------------------------------------------------------------

def test_grounding_result_shape():
    """GroundingResult fields are all present and correctly typed."""
    from src.grounding.pipeline import run_grounding_pipeline
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    texts = [
        "I bought this because the price was right.",
        "My doctor recommended it — I switched brands.",
        "Too expensive, I avoided it entirely.",
        "A friend told me to try this product.",
        "Switched because the quality improved.",
    ]
    result = run_grounding_pipeline(texts, [make_synthetic_persona()])

    assert isinstance(result.signals_extracted, int)
    assert result.signals_extracted > 0
    assert isinstance(result.clusters_derived, int)
    assert result.clusters_derived >= 1
    assert isinstance(result.archetypes, list)
    assert len(result.archetypes) == result.clusters_derived
    assert isinstance(result.personas, list)
    assert len(result.personas) == 1


# ---------------------------------------------------------------------------
# Test 2: GroundingSummary can be built from GroundingResult
# ---------------------------------------------------------------------------

def test_grounding_summary_construction():
    """
    After running the pipeline, GroundingSummary can be constructed
    using the result's signals_extracted and clusters_derived.
    The summary must pass GroundingSummary schema validation.
    """
    from src.grounding.pipeline import run_grounding_pipeline
    from src.schema.cohort import GroundingSummary
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    texts = [
        "Switched brands due to high price — my friend suggested the alternative.",
        "Bought after seeing an expert review.",
        "Too expensive — rejected outright.",
        "Found this through a recommendation from a trusted colleague.",
        "The cost was too much, so I avoided it.",
    ]
    result = run_grounding_pipeline(texts, [make_synthetic_persona()])

    # Compute what grounded proportion looks like
    persona = result.personas[0]
    bt = persona.behavioural_tendencies
    sources = [
        bt.price_sensitivity.source,
        bt.trust_orientation.source,
        bt.switching_propensity.source,
    ]
    grounded_count = sources.count("grounded")
    proxy_count = sources.count("proxy")
    total = len(sources)

    grounded_frac = grounded_count / total
    proxy_frac = proxy_count / total
    estimated_frac = 1.0 - grounded_frac - proxy_frac

    summary = GroundingSummary(
        tendency_source_distribution={
            "grounded": grounded_frac,
            "proxy": proxy_frac,
            "estimated": estimated_frac,
        },
        domain_data_signals_extracted=result.signals_extracted,
        clusters_derived=result.clusters_derived,
    )
    # Pydantic validates — if this doesn't raise, schema is satisfied
    assert summary.domain_data_signals_extracted == result.signals_extracted
    assert summary.clusters_derived == result.clusters_derived
    # Distribution must sum to 1.0
    total_dist = sum(summary.tendency_source_distribution.values())
    assert abs(total_dist - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# Test 3: Warning fires below 200 signals
# ---------------------------------------------------------------------------

def test_warning_below_threshold():
    """
    Fewer than 200 input texts → GroundingResult.warning is not None.
    Contains '200' in the warning string.
    """
    from src.grounding.pipeline import run_grounding_pipeline
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    texts = [f"I bought product {i} on sale." for i in range(10)]
    result = run_grounding_pipeline(texts, [make_synthetic_persona()])

    assert result.warning is not None
    assert "200" in result.warning


# ---------------------------------------------------------------------------
# Test 4: No warning at or above 200 signals
# ---------------------------------------------------------------------------

def test_no_warning_above_threshold():
    """
    200+ input texts → GroundingResult.warning is None.
    Each text produces at least 1 signal → 200 texts ≥ 200 signals.
    """
    from src.grounding.pipeline import run_grounding_pipeline
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    # 200 texts — each contains "price" keyword → at least 200 signals extracted
    texts = [f"This product costs too much — item {i}." for i in range(200)]
    result = run_grounding_pipeline(texts, [make_synthetic_persona()])

    assert result.warning is None


# ---------------------------------------------------------------------------
# Test 5: G11 — all tendency sources are valid literals
# ---------------------------------------------------------------------------

def test_g11_tendency_sources_valid():
    """
    G11: Every tendency source must be one of: grounded, proxy, estimated.
    """
    from src.grounding.pipeline import run_grounding_pipeline
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    texts = [
        "Bought because of a doctor's recommendation.",
        "Too expensive — switched to cheaper brand.",
        "My friend suggested this after trying it.",
    ] * 5  # 15 texts

    result = run_grounding_pipeline(texts, [make_synthetic_persona()])
    valid_sources = {"grounded", "proxy", "estimated"}

    for persona in result.personas:
        bt = persona.behavioural_tendencies
        assert bt.price_sensitivity.source in valid_sources, \
            f"Invalid price_sensitivity source: {bt.price_sensitivity.source}"
        assert bt.trust_orientation.source in valid_sources, \
            f"Invalid trust_orientation source: {bt.trust_orientation.source}"
        assert bt.switching_propensity.source in valid_sources, \
            f"Invalid switching_propensity source: {bt.switching_propensity.source}"


# ---------------------------------------------------------------------------
# Test 6: Archetype count within k bounds
# ---------------------------------------------------------------------------

def test_archetype_count_within_bounds():
    """
    With sufficient signals, cluster count should be between 1 and 8.
    """
    from src.grounding.pipeline import run_grounding_pipeline
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    texts = (
        ["I bought this because of the price discount."] * 10 +
        ["My doctor recommended switching brands."] * 10 +
        ["I avoided expensive brands — too costly."] * 10
    )
    result = run_grounding_pipeline(texts, [make_synthetic_persona()])

    assert 1 <= result.clusters_derived <= 8


# ---------------------------------------------------------------------------
# Test 7: Pipeline preserves persona_id
# ---------------------------------------------------------------------------

def test_pipeline_preserves_persona_id():
    """PersonaRecord.persona_id must not change through the pipeline."""
    from src.grounding.pipeline import run_grounding_pipeline
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    original_id = persona.persona_id

    texts = [
        "Switched due to price — too expensive.",
        "My friend recommended this brand.",
        "Bought after reading expert reviews.",
    ]
    result = run_grounding_pipeline(texts, [persona])
    assert result.personas[0].persona_id == original_id


# ---------------------------------------------------------------------------
# Test 8: BehaviouralArchetype centroid is 9-dim
# ---------------------------------------------------------------------------

def test_archetype_centroid_9_dims():
    """Every archetype centroid must be exactly 9 dimensions."""
    from src.grounding.pipeline import run_grounding_pipeline
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    texts = [
        "Too expensive — I avoided it.",
        "My friend recommended this product.",
        "Switched from my old brand because of quality issues.",
        "I bought this after seeing the expert review.",
        "The price was right, so I chose it.",
    ]
    result = run_grounding_pipeline(texts, [make_synthetic_persona()])

    for arch in result.archetypes:
        assert len(arch.centroid) == 9, \
            f"Expected 9-dim centroid, got {len(arch.centroid)}"
