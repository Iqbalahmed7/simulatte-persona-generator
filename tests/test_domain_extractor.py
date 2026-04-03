"""tests/test_domain_extractor.py

Sprint 20 — test suite for src/taxonomy/domain_extractor.py

No live LLM calls — the llm_client is mocked throughout.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schema.icp_spec import ICPSpec
from src.taxonomy.domain_extractor import DomainAttribute, extract_domain_attributes

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

# Minimal ICP spec used across tests
_ICP = ICPSpec(
    domain="child_nutrition",
    business_problem="Understand why urban Indian parents defer purchasing Nutrimix",
    target_segment="Urban Indian parents, children aged 2-12, Tier 1-2 cities",
    anchor_traits=["pediatrician_trust", "clean_label_preference", "child_acceptance_concern"],
)

# 25 synthetic reviews (more than a "small" corpus, less than _MIN_CORPUS_SIZE=200)
SYNTHETIC_CORPUS_SMALL = [
    "Our pediatrician recommended Nutrimix and we immediately ordered it.",
    "I checked the ingredients carefully — no artificial colours, finally a clean product.",
    "My daughter refused to drink it after three days. Taste is really the dealbreaker.",
    "The price is a bit steep but I trust my doctor's advice.",
    "Clean label matters to me more than brand name.",
    "My son liked the chocolate flavour but hated the vanilla.",
    "I compare every nutritional supplement with what the doctor says first.",
    "The packaging is honest — no hidden sugar claims.",
    "Would switch brands if price dropped elsewhere.",
    "My child's pediatrician gave this a thumbs up.",
    "It's pricey but the clean ingredients justify the premium.",
    "My toddler outright refused after sip one.",
    "I researched six alternatives before trusting a professional recommendation.",
    "No artificial preservatives is a must-have for our family.",
    "My kids are picky — taste acceptance is everything.",
    "Checked with our family doctor before buying — felt confident.",
    "The chocolate variant was a hit; plain was ignored.",
    "I prioritise ingredient transparency over price.",
    "Cost is secondary when a doctor endorses a product.",
    "My daughter liked the smell but wouldn't drink more than half a cup.",
    "Clean label products always catch my eye first.",
    "Switched from another brand after our paediatrician said this was better.",
    "Would buy again — doctor recommended, no junk ingredients.",
    "Taste acceptance is the single biggest barrier in our house.",
    "Price consciousness is real but health wins every time.",
]

# Build a corpus of ≥200 items by repeating the small set
CORPUS_200 = SYNTHETIC_CORPUS_SMALL * 8  # 200 items

# A valid 10-attribute JSON array the mock LLM returns
_TEN_ATTRS_JSON = json.dumps([
    {
        "name": "pediatrician_trust",
        "description": "Degree to which the consumer trusts pediatrician recommendations.",
        "valid_range": "0.0-1.0",
        "example_values": ["low trust", "moderate trust", "high trust"],
        "signal_count": 45,
    },
    {
        "name": "clean_label_preference",
        "description": "Preference for products with no artificial additives.",
        "valid_range": "0.0-1.0",
        "example_values": ["ignores labels", "scans labels", "rejects non-clean"],
        "signal_count": 38,
    },
    {
        "name": "child_acceptance_concern",
        "description": "Concern about whether the child will accept the taste.",
        "valid_range": "0.0-1.0",
        "example_values": ["not concerned", "somewhat concerned", "very concerned"],
        "signal_count": 30,
    },
    {
        "name": "price_sensitivity",
        "description": "Sensitivity to product cost when making purchase decisions.",
        "valid_range": "low|medium|high",
        "example_values": ["price-insensitive", "balanced", "price-driven"],
        "signal_count": 25,
    },
    {
        "name": "brand_switch_propensity",
        "description": "Willingness to switch to an alternative brand.",
        "valid_range": "0.0-1.0",
        "example_values": ["loyal", "conditionally loyal", "opportunistic"],
        "signal_count": 20,
    },
    {
        "name": "ingredient_scrutiny",
        "description": "Degree of detail in which a consumer reads ingredient lists.",
        "valid_range": "0.0-1.0",
        "example_values": ["skims", "reads", "deep-dives"],
        "signal_count": 18,
    },
    {
        "name": "doctor_endorsement_weight",
        "description": "How much a medical professional's endorsement influences the purchase.",
        "valid_range": "0.0-1.0",
        "example_values": ["uninfluenced", "slightly influenced", "strongly influenced"],
        "signal_count": 15,
    },
    {
        "name": "taste_driven_retention",
        "description": "Likelihood of repeat purchase driven by the child's taste response.",
        "valid_range": "0.0-1.0",
        "example_values": ["unaffected", "moderate factor", "decisive factor"],
        "signal_count": 12,
    },
    {
        "name": "health_premium_tolerance",
        "description": "Willingness to pay a premium for health-positioned products.",
        "valid_range": "0.0-1.0",
        "example_values": ["unwilling", "conditional", "willing"],
        "signal_count": 10,
    },
    {
        "name": "packaging_transparency_value",
        "description": "How much the consumer values transparent product labelling.",
        "valid_range": "0.0-1.0",
        "example_values": ["indifferent", "prefers", "requires"],
        "signal_count": 8,
    },
])


def _make_mock_client(response_text: str) -> AsyncMock:
    """Build a mock llm_client whose complete() method returns *response_text*."""
    client = AsyncMock()
    client.complete = AsyncMock(return_value=response_text)
    return client


def _run(coro):
    """Run a coroutine synchronously (test helper).

    Uses asyncio.run() to create a fresh event loop each time, which
    avoids 'no current event loop' errors when the full test suite is run
    after other tests that close the default loop.
    """
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExtractDomainAttributes:

    def test_empty_corpus_returns_empty(self):
        """A corpus smaller than _MIN_CORPUS_SIZE (200) returns [] without any LLM call."""
        mock_client = _make_mock_client(_TEN_ATTRS_JSON)
        result = _run(
            extract_domain_attributes(SYNTHETIC_CORPUS_SMALL, _ICP, llm_client=mock_client)
        )
        assert result == []
        # complete() must NOT have been called
        mock_client.complete.assert_not_called()

    def test_icp_anchor_traits_set_source(self):
        """Attributes whose name matches an ICP anchor trait get extraction_source=='icp_anchor'."""
        mock_client = _make_mock_client(_TEN_ATTRS_JSON)
        result = _run(
            extract_domain_attributes(CORPUS_200, _ICP, llm_client=mock_client)
        )
        anchor_attrs = [a for a in result if a.name in {"pediatrician_trust", "clean_label_preference", "child_acceptance_concern"}]
        assert len(anchor_attrs) == 3, "All three anchor traits should be in the result"
        for attr in anchor_attrs:
            assert attr.extraction_source == "icp_anchor", (
                f"{attr.name} should have extraction_source='icp_anchor', got {attr.extraction_source!r}"
            )

    def test_corpus_attributes_set_source(self):
        """Attributes NOT in the ICP anchor list get extraction_source=='corpus'."""
        mock_client = _make_mock_client(_TEN_ATTRS_JSON)
        result = _run(
            extract_domain_attributes(CORPUS_200, _ICP, llm_client=mock_client)
        )
        corpus_attrs = [a for a in result if a.name not in {"pediatrician_trust", "clean_label_preference", "child_acceptance_concern"}]
        assert len(corpus_attrs) > 0, "Expected some corpus-sourced attributes"
        for attr in corpus_attrs:
            assert attr.extraction_source == "corpus", (
                f"{attr.name} should have extraction_source='corpus', got {attr.extraction_source!r}"
            )

    def test_minimum_attributes_extracted(self):
        """When the LLM returns 10 valid attributes, all 10 are returned."""
        mock_client = _make_mock_client(_TEN_ATTRS_JSON)
        result = _run(
            extract_domain_attributes(CORPUS_200, _ICP, llm_client=mock_client)
        )
        assert len(result) == 10
        assert all(isinstance(a, DomainAttribute) for a in result)

    def test_malformed_json_retry(self):
        """First LLM call returns invalid JSON; second returns valid → succeeds."""
        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(
            side_effect=["THIS IS NOT JSON !!!", _TEN_ATTRS_JSON]
        )
        result = _run(
            extract_domain_attributes(CORPUS_200, _ICP, llm_client=mock_client)
        )
        assert len(result) == 10
        assert mock_client.complete.call_count == 2

    def test_malformed_json_both_fail(self):
        """Both LLM calls return invalid JSON → returns [] without crashing."""
        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(
            side_effect=["GARBAGE #1", "GARBAGE #2"]
        )
        result = _run(
            extract_domain_attributes(CORPUS_200, _ICP, llm_client=mock_client)
        )
        # Must not raise; returns empty list (or partial — both are acceptable)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_no_demographic_attributes_pass_through(self):
        """If the LLM accidentally returns a demographic attr like 'age', it is included
        (exclusion is the prompt's job, not the parser's — spec says pass-through)."""
        demographic_json = json.dumps([
            {
                "name": "age",
                "description": "Consumer's age.",
                "valid_range": "0.0-1.0",
                "example_values": ["young", "middle", "old"],
                "signal_count": 50,
            }
        ])
        mock_client = _make_mock_client(demographic_json)
        result = _run(
            extract_domain_attributes(CORPUS_200, _ICP, llm_client=mock_client)
        )
        assert len(result) == 1
        assert result[0].name == "age"
