"""tests/test_icp_spec_parser.py

Sprint 20 — test suite for src/taxonomy/icp_spec_parser.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.schema.icp_spec import ICPSpec
from src.taxonomy.icp_spec_parser import parse_icp_spec

# ---------------------------------------------------------------------------
# Markdown fixture
# ---------------------------------------------------------------------------

MARKDOWN_ICP = """
## Domain
child_nutrition

## Business Problem
Understand why urban Indian parents defer purchasing Littlejoys Nutrimix despite awareness

## Target Segment
Urban Indian parents with children aged 2-12, Tier 1-2 cities, household income 8-30 LPA

## Anchor Traits
- pediatrician_trust
- clean_label_preference
- child_acceptance_concern

## Data Sources
- 2010 consumer signals from LittleJoys research corpus

## Geography
India (Tier 1-2 cities)

## Category
CPG
"""

# Markdown missing the required ## Business Problem section
MARKDOWN_MISSING_PROBLEM = """
## Domain
child_nutrition

## Target Segment
Urban Indian parents with children aged 2-12, Tier 1-2 cities
"""

# Markdown with no Anchor Traits section at all
MARKDOWN_NO_ANCHOR_TRAITS = """
## Domain
child_nutrition

## Business Problem
Understand purchase deferral patterns

## Target Segment
Urban Indian parents, children 2-12, Tier 1-2 cities
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestParseICPSpec:

    # --- JSON dict input ---

    def test_parse_json_dict(self):
        """Parses a plain dict with required fields into a correct ICPSpec."""
        data = {
            "domain": "cpg",
            "business_problem": "Understand why parents delay buying supplements.",
            "target_segment": "Urban parents, children 2-12.",
        }
        spec = parse_icp_spec(data)
        assert isinstance(spec, ICPSpec)
        assert spec.domain == "cpg"
        assert spec.business_problem == "Understand why parents delay buying supplements."
        assert spec.target_segment == "Urban parents, children 2-12."

    def test_parse_json_synonyms(self):
        """Keys 'problem', 'segment', 'anchors' are accepted as synonyms."""
        data = {
            "domain": "saas",
            "problem": "Reduce churn in B2B SaaS.",
            "segment": "Mid-market SaaS buyers.",
            "anchors": ["vendor_trust", "roi_focus"],
        }
        spec = parse_icp_spec(data)
        assert spec.business_problem == "Reduce churn in B2B SaaS."
        assert spec.target_segment == "Mid-market SaaS buyers."
        assert "vendor_trust" in spec.anchor_traits
        assert "roi_focus" in spec.anchor_traits

    def test_parse_json_string(self):
        """A JSON string (not a dict) is parsed correctly."""
        json_str = json.dumps({
            "domain": "cpg",
            "business_problem": "Understand purchase deferral.",
            "target_segment": "Urban parents.",
        })
        spec = parse_icp_spec(json_str)
        assert spec.domain == "cpg"

    def test_extra_fields_ignored(self):
        """Unknown keys in the JSON dict do not raise an error."""
        data = {
            "domain": "cpg",
            "business_problem": "Understand purchase deferral.",
            "target_segment": "Urban parents.",
            "foo": "bar",
            "unknown_field": 42,
        }
        spec = parse_icp_spec(data)  # must not raise
        assert spec.domain == "cpg"

    def test_default_persona_count(self):
        """When persona_count is absent, it defaults to 10."""
        data = {
            "domain": "cpg",
            "business_problem": "Understand purchase deferral.",
            "target_segment": "Urban parents.",
        }
        spec = parse_icp_spec(data)
        assert spec.persona_count == 10

    # --- Markdown input ---

    def test_parse_markdown(self):
        """Full markdown fixture → correct ICPSpec with domain='child_nutrition'."""
        spec = parse_icp_spec(MARKDOWN_ICP)
        assert isinstance(spec, ICPSpec)
        assert spec.domain == "child_nutrition"
        assert "urban Indian parents" in spec.target_segment.lower() or "urban indian parents" in spec.target_segment.lower()
        assert spec.geography is not None
        assert spec.category == "CPG"

    def test_parse_markdown_anchor_traits(self):
        """Markdown anchor traits bullet list parses to exactly the right list."""
        spec = parse_icp_spec(MARKDOWN_ICP)
        assert spec.anchor_traits == [
            "pediatrician_trust",
            "clean_label_preference",
            "child_acceptance_concern",
        ]

    def test_parse_markdown_missing_required_raises(self):
        """Markdown without '## Business Problem' raises ValueError."""
        with pytest.raises(ValueError, match="business_problem"):
            parse_icp_spec(MARKDOWN_MISSING_PROBLEM)

    def test_empty_anchor_traits(self):
        """Markdown without an '## Anchor Traits' section produces anchor_traits == []."""
        spec = parse_icp_spec(MARKDOWN_NO_ANCHOR_TRAITS)
        assert spec.anchor_traits == []

    # --- Path input ---

    def test_parse_path_json(self):
        """parse_icp_spec(Path(...)) reads a JSON file and returns correct ICPSpec."""
        data = {
            "domain": "cpg",
            "business_problem": "Understand purchase deferral.",
            "target_segment": "Urban parents.",
            "anchor_traits": ["pediatrician_trust"],
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            tmp_path = Path(f.name)

        try:
            spec = parse_icp_spec(tmp_path)
            assert spec.domain == "cpg"
            assert spec.anchor_traits == ["pediatrician_trust"]
        finally:
            tmp_path.unlink(missing_ok=True)
