"""tests/test_domain_merger.py

Sprint 20 — test suite for src/taxonomy/domain_merger.py

All tests are deterministic (no LLM calls).
"""

from __future__ import annotations

import copy

import pytest

from src.taxonomy.domain_extractor import DomainAttribute
from src.taxonomy.attribute_ranker import RankedAttribute
from src.taxonomy.domain_merger import (
    detect_conflicts,
    get_domain_attribute_names,
    merge_taxonomy,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Minimal base taxonomy dict mirroring the six required category keys.
BASE_FIXTURE: dict = {
    "psychology": {
        "brand_loyalty": {
            "description": "Degree of loyalty to a brand.",
            "valid_range": "0.0-1.0",
            "layer": 1,
        },
        "risk_tolerance": {
            "description": "Willingness to take risks.",
            "valid_range": "0.0-1.0",
            "layer": 1,
        },
    },
    "values": {
        "price_consciousness": {
            "description": "Sensitivity to price.",
            "valid_range": "0.0-1.0",
            "layer": 1,
        },
    },
    "social": {},
    "lifestyle": {},
    "identity": {},
    "decision_making": {},
}

_BASE_CATEGORIES = {"psychology", "values", "social", "lifestyle", "identity", "decision_making"}


def _domain_attr(name: str, signal_count: int = 10) -> DomainAttribute:
    return DomainAttribute(
        name=name,
        description=f"Description for {name}.",
        valid_range="0.0-1.0",
        example_values=["low", "medium", "high"],
        signal_count=signal_count,
        extraction_source="corpus",
    )


SAMPLE_DOMAIN_ATTRS = [
    _domain_attr("pediatrician_trust"),
    _domain_attr("clean_label_preference"),
    _domain_attr("child_acceptance_concern"),
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMergeTaxonomy:

    def test_base_not_mutated(self):
        """merge_taxonomy() must not mutate the original base dict."""
        base_copy = copy.deepcopy(BASE_FIXTURE)
        merge_taxonomy(BASE_FIXTURE, SAMPLE_DOMAIN_ATTRS)
        assert BASE_FIXTURE == base_copy, "Original base dict was mutated by merge_taxonomy()"

    def test_domain_specific_key_added(self):
        """Result always contains a 'domain_specific' key."""
        result = merge_taxonomy(BASE_FIXTURE, SAMPLE_DOMAIN_ATTRS)
        assert "domain_specific" in result

    def test_base_keys_preserved(self):
        """All six base category keys are present in the merged result."""
        result = merge_taxonomy(BASE_FIXTURE, SAMPLE_DOMAIN_ATTRS)
        for key in _BASE_CATEGORIES:
            assert key in result, f"Base category key '{key}' missing from merged result"

    def test_layer_2_field_set(self):
        """Every entry in domain_specific has 'layer': 2."""
        result = merge_taxonomy(BASE_FIXTURE, SAMPLE_DOMAIN_ATTRS)
        domain_specific = result["domain_specific"]
        assert len(domain_specific) > 0
        for name, entry in domain_specific.items():
            assert entry.get("layer") == 2, (
                f"domain_specific['{name}']['layer'] expected 2, got {entry.get('layer')!r}"
            )

    def test_empty_attrs_gives_empty_domain_specific(self):
        """merge_taxonomy(base, []) returns a result with 'domain_specific': {}."""
        result = merge_taxonomy(BASE_FIXTURE, [])
        assert result["domain_specific"] == {}

    def test_prior_domain_specific_replaced(self):
        """If base already has 'domain_specific', it is replaced entirely by the new merge."""
        base_with_prior = copy.deepcopy(BASE_FIXTURE)
        base_with_prior["domain_specific"] = {
            "old_attr": {"description": "stale", "layer": 2}
        }
        result = merge_taxonomy(base_with_prior, SAMPLE_DOMAIN_ATTRS)
        # Old key must not survive
        assert "old_attr" not in result["domain_specific"]
        # New keys must be present
        for attr in SAMPLE_DOMAIN_ATTRS:
            assert attr.name in result["domain_specific"]

    def test_conflict_detection(self):
        """detect_conflicts() returns names that exist in both base and domain_attrs."""
        conflicting = _domain_attr("brand_loyalty")  # also in BASE_FIXTURE["psychology"]
        conflicts = detect_conflicts(BASE_FIXTURE, [conflicting])
        assert "brand_loyalty" in conflicts

    def test_no_conflict_when_no_overlap(self):
        """detect_conflicts() returns [] when there are no overlapping names."""
        unique_attrs = [_domain_attr("completely_unique_attr_xyz")]
        conflicts = detect_conflicts(BASE_FIXTURE, unique_attrs)
        assert conflicts == []

    def test_get_domain_attribute_names(self):
        """get_domain_attribute_names() returns the correct set of domain_specific keys."""
        result = merge_taxonomy(BASE_FIXTURE, SAMPLE_DOMAIN_ATTRS)
        names = get_domain_attribute_names(result)
        expected = {a.name for a in SAMPLE_DOMAIN_ATTRS}
        assert names == expected

    def test_ranked_attribute_unwrapped(self):
        """merge_taxonomy() works when passed RankedAttribute objects (wraps .attr)."""
        ranked = [
            RankedAttribute(attr=_domain_attr("ranked_attr_one"), composite_score=0.9),
            RankedAttribute(attr=_domain_attr("ranked_attr_two"), composite_score=0.7),
        ]
        result = merge_taxonomy(BASE_FIXTURE, ranked)
        domain_specific = result["domain_specific"]
        assert "ranked_attr_one" in domain_specific
        assert "ranked_attr_two" in domain_specific
        for entry in domain_specific.values():
            assert entry["layer"] == 2
