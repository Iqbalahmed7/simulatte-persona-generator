"""tests/test_template_library.py

Sprint 26 — Antigravity test suite for the domain template library,
template selector, and collision detector.

No LLM calls. All tests are deterministic.
"""

from __future__ import annotations

import copy

import pytest

from src.taxonomy.base_taxonomy import BASE_TAXONOMY
from src.taxonomy.collision_detector import (
    CollisionEntry,
    CollisionReport,
    detect_collisions,
)
from src.taxonomy.domain_templates.cpg import CPG_DOMAIN_ATTRIBUTES
from src.taxonomy.domain_templates.ecommerce import ECOMMERCE_DOMAIN_ATTRIBUTES
from src.taxonomy.domain_templates.education import EDUCATION_DOMAIN_ATTRIBUTES
from src.taxonomy.domain_templates.financial_services import (
    FINANCIAL_SERVICES_DOMAIN_ATTRIBUTES,
)
from src.taxonomy.domain_templates.healthcare_wellness import (
    HEALTHCARE_WELLNESS_DOMAIN_ATTRIBUTES,
)
from src.taxonomy.domain_templates.saas import SAAS_DOMAIN_ATTRIBUTES
from src.taxonomy.template_selector import (
    LOW_CONFIDENCE_THRESHOLD,
    TemplateMatch,
    select_template,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Base taxonomy attribute names — resolved once for all tests.
_BASE_TAXONOMY_NAMES: list[str] = [a.name for a in BASE_TAXONOMY]
_BASE_TAXONOMY_NAMES_SET: set[str] = set(_BASE_TAXONOMY_NAMES)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class SimpleICP:
    """Minimal duck-typed ICP object for template_selector tests."""

    def __init__(
        self,
        domain: str = "",
        description: str = "",
        sector: str = "",
        name: str = "",
        business_problem: str = "",
        target_segment: str = "",
    ) -> None:
        self.domain = domain
        self.description = description
        self.sector = sector
        self.name = name
        self.business_problem = business_problem
        self.target_segment = target_segment


# ---------------------------------------------------------------------------
# TestTemplateStructure — 8 attribute-count tests + 4 duplicate-name tests
# ---------------------------------------------------------------------------


class TestTemplateStructure:
    """Structure validation for all four new domain templates."""

    # financial_services ────────────────────────────────────────────────────

    def test_financial_services_attribute_count_in_range(self):
        count = len(FINANCIAL_SERVICES_DOMAIN_ATTRIBUTES)
        assert 35 <= count <= 55, (
            f"FINANCIAL_SERVICES_DOMAIN_ATTRIBUTES has {count} attributes; "
            "expected 35–55."
        )

    def test_financial_services_no_is_anchor_true(self):
        offenders = [
            a.name
            for a in FINANCIAL_SERVICES_DOMAIN_ATTRIBUTES
            if getattr(a, "is_anchor", False) is True
        ]
        assert offenders == [], (
            f"Financial services attrs with is_anchor=True: {offenders}"
        )

    # healthcare_wellness ────────────────────────────────────────────────────

    def test_healthcare_wellness_attribute_count_in_range(self):
        count = len(HEALTHCARE_WELLNESS_DOMAIN_ATTRIBUTES)
        assert 35 <= count <= 55, (
            f"HEALTHCARE_WELLNESS_DOMAIN_ATTRIBUTES has {count} attributes; "
            "expected 35–55."
        )

    def test_healthcare_wellness_no_is_anchor_true(self):
        offenders = [
            a.name
            for a in HEALTHCARE_WELLNESS_DOMAIN_ATTRIBUTES
            if getattr(a, "is_anchor", False) is True
        ]
        assert offenders == [], (
            f"Healthcare wellness attrs with is_anchor=True: {offenders}"
        )

    # ecommerce ─────────────────────────────────────────────────────────────

    def test_ecommerce_attribute_count_in_range(self):
        count = len(ECOMMERCE_DOMAIN_ATTRIBUTES)
        assert 35 <= count <= 55, (
            f"ECOMMERCE_DOMAIN_ATTRIBUTES has {count} attributes; "
            "expected 35–55."
        )

    def test_ecommerce_no_is_anchor_true(self):
        offenders = [
            a.name
            for a in ECOMMERCE_DOMAIN_ATTRIBUTES
            if getattr(a, "is_anchor", False) is True
        ]
        assert offenders == [], (
            f"Ecommerce attrs with is_anchor=True: {offenders}"
        )

    # education ─────────────────────────────────────────────────────────────

    def test_education_attribute_count_in_range(self):
        count = len(EDUCATION_DOMAIN_ATTRIBUTES)
        assert 35 <= count <= 55, (
            f"EDUCATION_DOMAIN_ATTRIBUTES has {count} attributes; "
            "expected 35–55."
        )

    def test_education_no_is_anchor_true(self):
        offenders = [
            a.name
            for a in EDUCATION_DOMAIN_ATTRIBUTES
            if getattr(a, "is_anchor", False) is True
        ]
        assert offenders == [], (
            f"Education attrs with is_anchor=True: {offenders}"
        )

    # No intra-template duplicate names ─────────────────────────────────────

    def test_financial_services_no_duplicate_names(self):
        names = [a.name for a in FINANCIAL_SERVICES_DOMAIN_ATTRIBUTES]
        assert len(set(names)) == len(names), (
            "Duplicate names in FINANCIAL_SERVICES_DOMAIN_ATTRIBUTES: "
            f"{[n for n in names if names.count(n) > 1]}"
        )

    def test_healthcare_wellness_no_duplicate_names(self):
        names = [a.name for a in HEALTHCARE_WELLNESS_DOMAIN_ATTRIBUTES]
        assert len(set(names)) == len(names), (
            "Duplicate names in HEALTHCARE_WELLNESS_DOMAIN_ATTRIBUTES: "
            f"{[n for n in names if names.count(n) > 1]}"
        )

    def test_ecommerce_no_duplicate_names(self):
        names = [a.name for a in ECOMMERCE_DOMAIN_ATTRIBUTES]
        assert len(set(names)) == len(names), (
            "Duplicate names in ECOMMERCE_DOMAIN_ATTRIBUTES: "
            f"{[n for n in names if names.count(n) > 1]}"
        )

    def test_education_no_duplicate_names(self):
        names = [a.name for a in EDUCATION_DOMAIN_ATTRIBUTES]
        assert len(set(names)) == len(names), (
            "Duplicate names in EDUCATION_DOMAIN_ATTRIBUTES: "
            f"{[n for n in names if names.count(n) > 1]}"
        )


# ---------------------------------------------------------------------------
# TestMergeTaxonomy — merge_taxonomy() integration (4 tests)
# ---------------------------------------------------------------------------


class TestMergeTaxonomy:
    """Integration tests for merge_taxonomy() with each new domain template."""

    # Build a minimal base dict matching the expected contract of merge_taxonomy.
    _BASE_DICT: dict = {
        "psychology": {"risk_tolerance": {"description": "Risk tolerance.", "valid_range": "0.0-1.0", "layer": 1}},
        "values": {"brand_loyalty": {"description": "Brand loyalty.", "valid_range": "0.0-1.0", "layer": 1}},
        "social": {},
        "lifestyle": {},
        "identity": {},
        "decision_making": {},
    }

    @staticmethod
    def _make_domain_attrs(template_attrs):
        """Convert AttributeDefinition list to DomainAttribute-compatible objects."""
        from src.taxonomy.domain_extractor import DomainAttribute

        return [
            DomainAttribute(
                name=a.name,
                description=a.description or f"Domain attr {a.name}",
                valid_range="0.0-1.0",
                example_values=[],
                signal_count=5,
                extraction_source="template_fallback",
            )
            for a in template_attrs
        ]

    def _base_copy(self):
        return copy.deepcopy(self._BASE_DICT)

    def test_merge_financial_services_succeeds(self):
        from src.taxonomy.domain_merger import merge_taxonomy

        domain_attrs = self._make_domain_attrs(FINANCIAL_SERVICES_DOMAIN_ATTRIBUTES)
        merged = merge_taxonomy(self._base_copy(), domain_attrs)

        # Returns a dict (not a list); verify domain_specific was added.
        assert isinstance(merged, dict)
        assert "domain_specific" in merged

        # domain_specific contains all the template attribute names.
        domain_names = set(merged["domain_specific"].keys())
        expected_names = {a.name for a in FINANCIAL_SERVICES_DOMAIN_ATTRIBUTES}
        assert expected_names == domain_names

        # Base layer keys are intact and unchanged.
        assert "psychology" in merged
        assert "risk_tolerance" in merged["psychology"]

    def test_merge_healthcare_wellness_succeeds(self):
        from src.taxonomy.domain_merger import merge_taxonomy

        domain_attrs = self._make_domain_attrs(HEALTHCARE_WELLNESS_DOMAIN_ATTRIBUTES)
        merged = merge_taxonomy(self._base_copy(), domain_attrs)

        assert isinstance(merged, dict)
        assert "domain_specific" in merged

        domain_names = set(merged["domain_specific"].keys())
        expected_names = {a.name for a in HEALTHCARE_WELLNESS_DOMAIN_ATTRIBUTES}
        assert expected_names == domain_names

        assert "values" in merged
        assert "brand_loyalty" in merged["values"]

    def test_merge_ecommerce_succeeds(self):
        from src.taxonomy.domain_merger import merge_taxonomy

        domain_attrs = self._make_domain_attrs(ECOMMERCE_DOMAIN_ATTRIBUTES)
        merged = merge_taxonomy(self._base_copy(), domain_attrs)

        assert isinstance(merged, dict)
        assert "domain_specific" in merged

        domain_names = set(merged["domain_specific"].keys())
        expected_names = {a.name for a in ECOMMERCE_DOMAIN_ATTRIBUTES}
        assert expected_names == domain_names

        assert "social" in merged

    def test_merge_education_succeeds(self):
        from src.taxonomy.domain_merger import merge_taxonomy

        domain_attrs = self._make_domain_attrs(EDUCATION_DOMAIN_ATTRIBUTES)
        merged = merge_taxonomy(self._base_copy(), domain_attrs)

        assert isinstance(merged, dict)
        assert "domain_specific" in merged

        domain_names = set(merged["domain_specific"].keys())
        expected_names = {a.name for a in EDUCATION_DOMAIN_ATTRIBUTES}
        assert expected_names == domain_names

        assert "lifestyle" in merged


# ---------------------------------------------------------------------------
# TestP8Separation — P8 scan: domain layer stays separate from base layer
# ---------------------------------------------------------------------------


class TestP8Separation:
    """P8 Constitution: domain-specific attributes must not appear in base taxonomy."""

    def test_new_template_names_not_in_base_taxonomy(self):
        """None of the four new templates' attribute names appear in BASE_TAXONOMY,
        excluding the single known overlap ('health_anxiety') that was present in
        HEALTHCARE_WELLNESS_DOMAIN_ATTRIBUTES before Sprint 26 rectification.

        Sprint 26 finding: 'health_anxiety' exists in both healthcare_wellness
        template and BASE_TAXONOMY. This is a documented P8 overlap; the clinical
        context ('worry driving medical consultations') differs semantically from
        the base definition ('worry about health or safety risks') but the names
        collide. The overlap is tracked here so any *new* violations are caught
        immediately.
        """
        # Known pre-existing overlap accepted by the team — do not add to this set
        # without explicit constitution review.
        _KNOWN_P8_OVERLAPS: set[str] = {"health_anxiety"}

        new_template_names: set[str] = set()
        for template in (
            FINANCIAL_SERVICES_DOMAIN_ATTRIBUTES,
            HEALTHCARE_WELLNESS_DOMAIN_ATTRIBUTES,
            ECOMMERCE_DOMAIN_ATTRIBUTES,
            EDUCATION_DOMAIN_ATTRIBUTES,
        ):
            for a in template:
                new_template_names.add(a.name)

        collisions = (new_template_names & _BASE_TAXONOMY_NAMES_SET) - _KNOWN_P8_OVERLAPS
        assert collisions == set(), (
            f"P8 violation — these domain attribute names are also in BASE_TAXONOMY "
            f"(excluding known overlaps {sorted(_KNOWN_P8_OVERLAPS)}): "
            f"{sorted(collisions)}"
        )


# ---------------------------------------------------------------------------
# TestTemplateSelector — correct top-match, confidence, determinism
# ---------------------------------------------------------------------------


class TestTemplateSelector:
    """Tests for select_template() keyword matching and confidence thresholds."""

    # Correct top-match ──────────────────────────────────────────────────────

    def test_fintech_icp_top_match_is_financial_services(self):
        icp = SimpleICP(
            domain="fintech lending platform",
            description="Digital mortgage and credit risk scoring for retail banking customers.",
        )
        results = select_template(icp)
        assert results[0].template_name == "financial_services", (
            f"Expected top match 'financial_services', got '{results[0].template_name}'"
        )

    def test_edtech_icp_top_match_is_education(self):
        icp = SimpleICP(
            domain="edtech upskilling platform",
            description="Online learning and certification courses for corporate reskilling.",
        )
        results = select_template(icp)
        assert results[0].template_name == "education", (
            f"Expected top match 'education', got '{results[0].template_name}'"
        )

    def test_healthcare_icp_top_match_is_healthcare_wellness(self):
        icp = SimpleICP(
            domain="digital healthcare provider",
            description="Telehealth and patient engagement for NHS-linked clinical diagnostic services.",
        )
        results = select_template(icp)
        assert results[0].template_name == "healthcare_wellness", (
            f"Expected top match 'healthcare_wellness', got '{results[0].template_name}'"
        )

    def test_ecommerce_icp_top_match_is_ecommerce(self):
        icp = SimpleICP(
            domain="online retail marketplace",
            description="D2C ecommerce platform with cart, checkout, and last-mile delivery.",
        )
        results = select_template(icp)
        assert results[0].template_name == "ecommerce", (
            f"Expected top match 'ecommerce', got '{results[0].template_name}'"
        )

    def test_cpg_icp_top_match_is_cpg(self):
        icp = SimpleICP(
            domain="consumer goods FMCG",
            description="Grocery and packaged food brand loyalty analysis for supermarket shelves.",
        )
        results = select_template(icp)
        assert results[0].template_name == "cpg", (
            f"Expected top match 'cpg', got '{results[0].template_name}'"
        )

    # Confidence and LOW_CONFIDENCE_THRESHOLD ────────────────────────────────

    def test_ambiguous_icp_top_confidence_below_threshold(self):
        """An ICP with no domain keywords should score below LOW_CONFIDENCE_THRESHOLD."""
        icp = SimpleICP(
            domain="general purpose",
            description="A typical company selling things to people.",
        )
        results = select_template(icp)
        assert results[0].confidence < LOW_CONFIDENCE_THRESHOLD, (
            f"Expected top confidence < {LOW_CONFIDENCE_THRESHOLD}, "
            f"got {results[0].confidence} for template '{results[0].template_name}'"
        )

    def test_all_six_templates_always_returned(self):
        """select_template always returns all 6 templates, even when confidence is low."""
        icp = SimpleICP(domain="", description="")
        results = select_template(icp)
        assert len(results) == 6, (
            f"Expected 6 TemplateMatch results, got {len(results)}"
        )
        returned_names = {r.template_name for r in results}
        expected_names = {
            "cpg", "saas", "financial_services",
            "healthcare_wellness", "ecommerce", "education",
        }
        assert returned_names == expected_names, (
            f"Missing templates: {expected_names - returned_names}"
        )

    # Determinism ─────────────────────────────────────────────────────────────

    def test_select_template_is_deterministic(self):
        """Two calls with identical input produce identical output."""
        icp = SimpleICP(
            domain="fintech banking investment",
            description="Credit risk and mortgage analytics.",
        )
        results_1 = select_template(icp)
        results_2 = select_template(icp)

        assert len(results_1) == len(results_2)
        for m1, m2 in zip(results_1, results_2):
            assert m1.template_name == m2.template_name
            assert m1.confidence == m2.confidence
            assert sorted(m1.matched_keywords) == sorted(m2.matched_keywords)


# ---------------------------------------------------------------------------
# TestCollisionDetector — exact, near_duplicate, template_collision, empty
# ---------------------------------------------------------------------------


class TestCollisionDetector:
    """Tests for detect_collisions() covering all three collision types."""

    # Exact collision ─────────────────────────────────────────────────────────

    def test_exact_collision_detected_for_base_taxonomy_name(self):
        """health_anxiety is in both anchor_traits and BASE_TAXONOMY → exact collision."""
        # Confirm health_anxiety is actually in BASE_TAXONOMY
        assert "health_anxiety" in _BASE_TAXONOMY_NAMES_SET, (
            "Test pre-condition failed: 'health_anxiety' not found in BASE_TAXONOMY."
        )
        report = detect_collisions(
            icp_anchor_traits=["health_anxiety"],
            base_taxonomy_names=_BASE_TAXONOMY_NAMES,
            template_attributes=[],
        )
        assert len(report.exact_collisions) == 1
        entry = report.exact_collisions[0]
        assert entry.attribute_name == "health_anxiety"
        assert entry.collision_type == "exact"
        assert entry.collided_with == "health_anxiety"
        assert entry.jaccard_similarity == 1.0

    def test_exact_collision_report_has_collisions_and_summary_contains_exact(self):
        """CollisionReport.has_collisions is True and summary() mentions 'exact'."""
        assert "health_anxiety" in _BASE_TAXONOMY_NAMES_SET
        report = detect_collisions(
            icp_anchor_traits=["health_anxiety"],
            base_taxonomy_names=_BASE_TAXONOMY_NAMES,
            template_attributes=[],
        )
        assert report.has_collisions is True
        summary_text = report.summary()
        assert "exact" in summary_text.lower(), (
            f"Expected 'exact' in summary(), got: {summary_text!r}"
        )

    # Near-duplicate collision ────────────────────────────────────────────────

    def test_near_duplicate_detected_when_jaccard_exceeds_threshold(self):
        """brand_loyalty_score vs brand_loyalty → Jaccard > 0.6 → near_duplicate."""
        # Verify brand_loyalty is in BASE_TAXONOMY
        assert "brand_loyalty" in _BASE_TAXONOMY_NAMES_SET, (
            "Test pre-condition failed: 'brand_loyalty' not found in BASE_TAXONOMY."
        )
        # brand_loyalty_score tokens: {brand, loyalty, score}
        # brand_loyalty tokens: {brand, loyalty}
        # Jaccard = 2/3 ≈ 0.667 > 0.6
        report = detect_collisions(
            icp_anchor_traits=["brand_loyalty_score"],
            base_taxonomy_names=_BASE_TAXONOMY_NAMES,
            template_attributes=[],
        )
        assert len(report.near_duplicate_collisions) >= 1, (
            "Expected at least one near_duplicate collision for 'brand_loyalty_score'."
        )
        entry = report.near_duplicate_collisions[0]
        assert entry.collision_type == "near_duplicate"
        assert entry.jaccard_similarity > 0.6

    def test_exact_collision_not_also_reported_as_near_duplicate(self):
        """An exact collision should not additionally appear as a near_duplicate."""
        assert "health_anxiety" in _BASE_TAXONOMY_NAMES_SET
        report = detect_collisions(
            icp_anchor_traits=["health_anxiety"],
            base_taxonomy_names=_BASE_TAXONOMY_NAMES,
            template_attributes=[],
        )
        near_dup_trait_names = [e.attribute_name for e in report.near_duplicate_collisions]
        assert "health_anxiety" not in near_dup_trait_names, (
            "health_anxiety was reported as both exact and near_duplicate, "
            "but exact matches must exclude near_duplicate detection."
        )

    # Template collision ──────────────────────────────────────────────────────

    def test_template_collision_detected_for_matching_template_attr(self):
        """credit_risk_tolerance in anchor_traits matches the financial_services template."""
        template_attr_names = [a.name for a in FINANCIAL_SERVICES_DOMAIN_ATTRIBUTES]
        assert "credit_risk_tolerance" in template_attr_names, (
            "Test pre-condition failed: 'credit_risk_tolerance' not in "
            "FINANCIAL_SERVICES_DOMAIN_ATTRIBUTES."
        )
        report = detect_collisions(
            icp_anchor_traits=["credit_risk_tolerance"],
            base_taxonomy_names=_BASE_TAXONOMY_NAMES,
            template_attributes=template_attr_names,
        )
        assert len(report.template_collisions) == 1
        entry = report.template_collisions[0]
        assert entry.attribute_name == "credit_risk_tolerance"
        assert entry.collision_type == "template_collision"
        assert entry.collided_with == "credit_risk_tolerance"
        assert entry.jaccard_similarity == 0.0

    def test_empty_anchor_traits_produces_no_collisions(self):
        """An empty anchor_traits list should produce a report with has_collisions=False."""
        template_attr_names = [a.name for a in FINANCIAL_SERVICES_DOMAIN_ATTRIBUTES]
        report = detect_collisions(
            icp_anchor_traits=[],
            base_taxonomy_names=_BASE_TAXONOMY_NAMES,
            template_attributes=template_attr_names,
        )
        assert report.has_collisions is False
        assert report.summary() == "no collisions"


# ---------------------------------------------------------------------------
# TestICPParserIntegration — collision_report attachment via parse_icp_spec
# ---------------------------------------------------------------------------


class TestICPParserIntegration:
    """Integration test: parse_icp_spec attaches a live CollisionReport."""

    def test_parse_icp_spec_with_base_taxonomy_collision_attaches_report(self):
        """Parsing an ICP spec whose anchor_traits contain a known base taxonomy
        attribute name should produce spec.collision_report with has_collisions=True."""
        from src.taxonomy.icp_spec_parser import parse_icp_spec

        # health_anxiety is in BASE_TAXONOMY (confirmed above in collision tests).
        icp_dict = {
            "domain": "digital healthcare",
            "business_problem": "Understand patient health-seeking behaviour.",
            "target_segment": "UK adults 30-60 with chronic conditions.",
            "anchor_traits": ["health_anxiety"],
        }

        spec = parse_icp_spec(icp_dict)

        assert spec.collision_report is not None, (
            "parse_icp_spec() did not attach a collision_report to the ICPSpec."
        )
        assert spec.collision_report.has_collisions is True, (
            "Expected has_collisions=True because 'health_anxiety' is in BASE_TAXONOMY, "
            f"but got: {spec.collision_report.summary()}"
        )
