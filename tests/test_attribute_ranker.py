"""tests/test_attribute_ranker.py

Sprint 20 — test suite for src/taxonomy/attribute_ranker.py

All tests are deterministic (no LLM calls).
"""

from __future__ import annotations

import pytest

from src.taxonomy.base_taxonomy import BASE_TAXONOMY
from src.taxonomy.attribute_ranker import RankedAttribute, rank_attributes
from src.taxonomy.domain_extractor import DomainAttribute

# ---------------------------------------------------------------------------
# Real base taxonomy names (from the actual base_taxonomy module)
# ---------------------------------------------------------------------------

BASE_NAMES: set[str] = {a.name for a in BASE_TAXONOMY}

# Sanity: "brand_loyalty" must be in the base taxonomy for exclusion tests to work.
assert "brand_loyalty" in BASE_NAMES, (
    "'brand_loyalty' expected in BASE_TAXONOMY — check base_taxonomy.py"
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _attr(
    name: str,
    signal_count: int = 20,
    description: str = "A neutral attribute description.",
    valid_range: str = "0.0-1.0",
) -> DomainAttribute:
    """Convenience factory for DomainAttribute test fixtures."""
    return DomainAttribute(
        name=name,
        description=description,
        valid_range=valid_range,
        example_values=["low", "medium", "high"],
        signal_count=signal_count,
        extraction_source="corpus",
    )


# ---------------------------------------------------------------------------
# 10-attribute fixture set used across tests
# ---------------------------------------------------------------------------

ATTRS_10: list[DomainAttribute] = [
    _attr("pediatrician_trust",      signal_count=45, description="How much a consumer trusts doctor recommendations to buy or choose supplements.", valid_range="0.0-1.0"),
    _attr("clean_label_preference",  signal_count=38, description="Preference for products with no artificial additives when making purchase decisions.", valid_range="0.0-1.0"),
    _attr("child_acceptance_concern", signal_count=30, description="Concern about whether the child will accept the taste and trust the product.", valid_range="0.0-1.0"),
    _attr("price_sensitivity",       signal_count=25, description="Degree to which price affects the decision to buy.", valid_range="categorical: [low, medium, high]"),
    _attr("ingredient_scrutiny",     signal_count=18, description="Depth of review of ingredient lists before deciding to purchase.", valid_range="0.0-1.0"),
    _attr("taste_driven_retention",  signal_count=12, description="Likelihood that child's taste response drives repeat purchase.", valid_range="0.0-1.0"),
    _attr("health_premium_tolerance", signal_count=10, description="Willingness to pay a premium for health-positioned products.", valid_range="0.0-1.0"),
    _attr("packaging_transparency_value", signal_count=8, description="Value placed on transparent labelling.", valid_range="categorical: [a, b]"),
    _attr("low_signal_attr",         signal_count=2,  description="Very rarely mentioned attribute.", valid_range="0.0-1.0"),
    _attr("brand_loyalty",           signal_count=20, description="Brand loyalty metric — exact base taxonomy name.", valid_range="0.0-1.0"),
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRankAttributes:

    def test_empty_input_returns_empty(self):
        """rank_attributes([], ...) returns an empty list."""
        result = rank_attributes([], BASE_NAMES, total_signals=200)
        assert result == []

    def test_low_signal_count_excluded(self):
        """Attribute with signal_count < 3 is excluded from output."""
        result = rank_attributes(ATTRS_10, BASE_NAMES, total_signals=200)
        returned_names = {ra.attr.name for ra in result}
        assert "low_signal_attr" not in returned_names

    def test_exact_base_name_excluded(self):
        """Attribute named exactly 'brand_loyalty' (a real base taxonomy name) is excluded."""
        result = rank_attributes(ATTRS_10, BASE_NAMES, total_signals=200)
        returned_names = {ra.attr.name for ra in result}
        assert "brand_loyalty" not in returned_names

    def test_near_duplicate_excluded(self):
        """Attribute named 'brand_loyalty_score' is excluded by near-duplicate detection."""
        near_dup = _attr("brand_loyalty_score", signal_count=20)
        result = rank_attributes([near_dup], BASE_NAMES, total_signals=200)
        returned_names = {ra.attr.name for ra in result}
        assert "brand_loyalty_score" not in returned_names

    def test_continuous_scores_higher_than_categorical(self):
        """'0.0-1.0' range outscores 'categorical: [a,b]' when other factors are equal."""
        continuous = _attr(
            "novel_continuous_attr",
            signal_count=20,
            description="A neutral description.",
            valid_range="0.0-1.0",
        )
        categorical = _attr(
            "novel_categorical_attr",
            signal_count=20,
            description="A neutral description.",
            valid_range="categorical: [a, b]",
        )
        result = rank_attributes([continuous, categorical], BASE_NAMES, total_signals=200)
        assert len(result) == 2
        scores = {ra.attr.name: ra.composite_score for ra in result}
        assert scores["novel_continuous_attr"] > scores["novel_categorical_attr"], (
            f"Continuous ({scores['novel_continuous_attr']:.3f}) should beat "
            f"categorical ({scores['novel_categorical_attr']:.3f})"
        )

    def test_decision_language_boosts_score(self):
        """Description with 'buy' and 'trust' scores higher than a neutral description."""
        boosted = _attr(
            "decision_boosted_attr",
            signal_count=20,
            description="Captures how much consumers trust the product and choose to buy it.",
        )
        neutral = _attr(
            "neutral_lang_attr",
            signal_count=20,
            description="A general attribute about colour preference.",
        )
        result = rank_attributes([boosted, neutral], BASE_NAMES, total_signals=200)
        scores = {ra.attr.name: ra.composite_score for ra in result}
        assert scores["decision_boosted_attr"] > scores["neutral_lang_attr"], (
            f"Boosted ({scores['decision_boosted_attr']:.3f}) should beat "
            f"neutral ({scores['neutral_lang_attr']:.3f})"
        )

    def test_top_n_respected(self):
        """rank_attributes(..., top_n=3) returns at most 3 results."""
        result = rank_attributes(ATTRS_10, BASE_NAMES, total_signals=200, top_n=3)
        assert len(result) <= 3

    def test_results_sorted_descending(self):
        """Returned list is sorted in descending order by composite_score."""
        result = rank_attributes(ATTRS_10, BASE_NAMES, total_signals=200)
        scores = [ra.composite_score for ra in result]
        assert scores == sorted(scores, reverse=True), (
            f"Scores are not in descending order: {scores}"
        )

    def test_returns_ranked_attribute_objects(self):
        """Each returned item is a RankedAttribute with a composite_score float."""
        result = rank_attributes(ATTRS_10, BASE_NAMES, total_signals=200)
        assert len(result) > 0
        for item in result:
            assert isinstance(item, RankedAttribute)
            assert isinstance(item.composite_score, float)
