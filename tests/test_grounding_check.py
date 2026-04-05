"""tests/test_grounding_check.py — Unit tests for the G12 Grounding Check module.

Tests the three contamination types:
  T1 — Injected product facts (unsourced numbers/claims in the product frame)
  T2 — Impossible persona attributes (forbidden touchpoints, offline channels)
  T3 — Quote leakage (numbers in verbatim quotes not in the product frame)

No LLM calls. All inputs are constructed inline.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.validation.grounding_check import (
    GroundingIssue,
    GroundingReport,
    load_market_facts,
    run_grounding_check,
)


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_LUMIO_PRODUCT_FRAME = (
    "Lumio Vision 7 is a 43-inch Smart TV priced at ₹29,999. "
    "It offers 2x faster boot speed and 2x faster Netflix loading vs competition. "
    "Available exclusively on Amazon.in. Rated 4.4/5 with 200+ reviews."
)

_LUMIO_MARKET_FACTS = {
    "client": "Lumio",
    "distribution": {
        "model": "Amazon-only",
        "channels": ["Amazon.in"],
        "offline_retail": False,
        "forbidden_touchpoints": [
            "Croma",
            "Reliance Digital",
            "Vijay Sales",
            "offline store",
            "in-store demo",
            "retail store",
            "physical store",
            "showroom",
        ],
        "notes": "Amazon-only, no physical retail.",
    },
    "brand_facts": {
        "category": "Smart TV",
        "verified_claims": {
            "vision_7_price": 29999,
            "speed_claim": "2x faster boot, 2x faster Netflix loading",
        },
    },
}


def _clean_persona(persona_id: str = "P01") -> dict:
    """Return a persona dict with no grounding issues."""
    return {
        "persona_id": persona_id,
        "prior_exposure": "I came across the Lumio Vision 7 on Amazon while searching for budget TVs.",
        "backstory": "Ravi is a software engineer in Pune who shops primarily online.",
        "quotes": [
            "I liked the 2x faster boot claim, that's exactly what I was looking for.",
            "The price of ₹29,999 feels reasonable for a 43-inch TV.",
        ],
        "channel_usage": "Amazon, Flipkart",
    }


def _persona_with_croma(persona_id: str = "P02") -> dict:
    """Return a persona with a forbidden Croma touchpoint."""
    return {
        "persona_id": persona_id,
        "prior_exposure": "I first saw the Lumio TV at Croma last month and was impressed.",
        "backstory": "Priya saw Lumio at the Croma store in Bangalore.",
        "quotes": [
            "The 2x speed claim checks out from what I saw in the Croma demo.",
        ],
        "channel_usage": "Amazon",
    }


def _persona_with_leaked_number(persona_id: str = "P03") -> dict:
    """Return a persona whose quote contains a number not in the product frame."""
    return {
        "persona_id": persona_id,
        "prior_exposure": "Found Lumio on Amazon and it looked good.",
        "backstory": "Tech-savvy buyer in Delhi.",
        "quotes": [
            "Netflix loads in 4 seconds on Lumio vs 22 seconds on my old Xiaomi TV — that blew my mind.",
        ],
        "channel_usage": "Amazon",
    }


# ---------------------------------------------------------------------------
# T2 Tests
# ---------------------------------------------------------------------------


class TestT2ForbiddenTouchpoints:
    def test_t2_forbidden_touchpoint_detected(self):
        """Persona quote containing 'Croma' for Lumio client must flag T2 CRITICAL."""
        persona = _persona_with_croma("P02")
        report = run_grounding_check(
            product_frame=_LUMIO_PRODUCT_FRAME,
            market_facts=_LUMIO_MARKET_FACTS,
            persona_outputs=[persona],
        )
        t2_issues = [i for i in report.issues if i.issue_type == "T2"]
        assert len(t2_issues) >= 1, "Expected at least one T2 issue"
        critical_issues = [i for i in t2_issues if i.severity == "CRITICAL"]
        assert len(critical_issues) >= 1, "Expected at least one T2 CRITICAL issue"
        # Verify the flagged text relates to Croma
        assert any("Croma" in i.contaminated_text for i in critical_issues)

    def test_t2_clean_passes(self):
        """Clean persona with no forbidden touchpoints must produce zero T2 issues."""
        persona = _clean_persona("P01")
        report = run_grounding_check(
            product_frame=_LUMIO_PRODUCT_FRAME,
            market_facts=_LUMIO_MARKET_FACTS,
            persona_outputs=[persona],
        )
        t2_issues = [i for i in report.issues if i.issue_type == "T2"]
        assert len(t2_issues) == 0

    def test_t2_persona_id_captured(self):
        """T2 issue must record the correct persona_id."""
        persona = _persona_with_croma("P99")
        report = run_grounding_check(
            product_frame=_LUMIO_PRODUCT_FRAME,
            market_facts=_LUMIO_MARKET_FACTS,
            persona_outputs=[persona],
        )
        t2_issues = [i for i in report.issues if i.issue_type == "T2"]
        assert any(i.persona_id == "P99" for i in t2_issues)

    def test_t2_offline_channel_usage_flagged_high(self):
        """Persona with 'in-store' in channel_usage for Amazon-only brand => T2 HIGH."""
        persona = {
            "persona_id": "P05",
            "prior_exposure": "I found it on Amazon.",
            "quotes": ["₹29,999 is reasonable."],
            "channel_usage": "in-store, Amazon",
        }
        report = run_grounding_check(
            product_frame=_LUMIO_PRODUCT_FRAME,
            market_facts=_LUMIO_MARKET_FACTS,
            persona_outputs=[persona],
        )
        t2_high = [
            i for i in report.issues
            if i.issue_type == "T2" and i.severity == "HIGH"
        ]
        assert len(t2_high) >= 1


# ---------------------------------------------------------------------------
# T3 Tests
# ---------------------------------------------------------------------------


class TestT3QuoteLeakage:
    def test_t3_number_not_in_frame_flagged(self):
        """Quote with '4 seconds' when product frame only says '2x faster' => T3 HIGH."""
        persona = _persona_with_leaked_number("P03")
        report = run_grounding_check(
            product_frame=_LUMIO_PRODUCT_FRAME,
            market_facts=_LUMIO_MARKET_FACTS,
            persona_outputs=[persona],
        )
        t3_issues = [i for i in report.issues if i.issue_type == "T3"]
        assert len(t3_issues) >= 1, "Expected at least one T3 issue"
        high_issues = [i for i in t3_issues if i.severity == "HIGH"]
        assert len(high_issues) >= 1

    def test_t3_number_in_frame_passes(self):
        """Quote with '₹29,999' when product frame states '₹29,999' must not flag T3."""
        persona = {
            "persona_id": "P04",
            "prior_exposure": "Found it on Amazon.",
            "quotes": ["I paid ₹29,999 for the Vision 7 and I'm very happy with it."],
            "channel_usage": "Amazon",
        }
        report = run_grounding_check(
            product_frame=_LUMIO_PRODUCT_FRAME,
            market_facts=_LUMIO_MARKET_FACTS,
            persona_outputs=[persona],
        )
        # There may be T1 issues but no T3 for this persona's quote
        t3_for_p04 = [
            i for i in report.issues
            if i.issue_type == "T3" and i.persona_id == "P04"
        ]
        assert len(t3_for_p04) == 0

    def test_t3_persona_id_captured(self):
        """T3 issue must record the correct persona_id."""
        persona = _persona_with_leaked_number("P77")
        report = run_grounding_check(
            product_frame=_LUMIO_PRODUCT_FRAME,
            market_facts=_LUMIO_MARKET_FACTS,
            persona_outputs=[persona],
        )
        t3_issues = [i for i in report.issues if i.issue_type == "T3"]
        assert any(i.persona_id == "P77" for i in t3_issues)


# ---------------------------------------------------------------------------
# GroundingReport.passed tests
# ---------------------------------------------------------------------------


class TestGroundingReportPassed:
    def test_report_fails_on_critical(self):
        """GroundingReport.passed must be False when a CRITICAL issue exists."""
        persona = _persona_with_croma("P02")
        report = run_grounding_check(
            product_frame=_LUMIO_PRODUCT_FRAME,
            market_facts=_LUMIO_MARKET_FACTS,
            persona_outputs=[persona],
        )
        # Croma triggers T2 CRITICAL
        assert report.passed is False

    def test_report_fails_on_high(self):
        """GroundingReport.passed must be False when a HIGH issue exists."""
        persona = _persona_with_leaked_number("P03")
        report = run_grounding_check(
            product_frame=_LUMIO_PRODUCT_FRAME,
            market_facts=_LUMIO_MARKET_FACTS,
            persona_outputs=[persona],
        )
        # Quote leakage => T3 HIGH => not passed
        assert report.passed is False

    def test_report_passes_when_clean(self):
        """GroundingReport.passed must be True when no CRITICAL or HIGH issues."""
        # Use a persona whose quotes only reference numbers and model names that
        # appear in the product frame, so T3 does not fire.
        clean_frame = (
            "Lumio Vision 7 is a 43-inch Smart TV priced at ₹29,999. "
            "Available exclusively on Amazon.in with a 3-year warranty. "
            "It offers 2x faster boot speed vs competition."
        )
        persona = {
            "persona_id": "P01",
            "prior_exposure": "I came across the Lumio Vision 7 on Amazon.",
            "backstory": "Ravi shops primarily online.",
            "quotes": [
                "The 2x faster boot claim is what convinced me.",
                "The price of ₹29,999 feels reasonable for a 43-inch TV.",
            ],
            "channel_usage": "Amazon",
        }
        market_facts_no_forbidden = {
            "client": "Test",
            "distribution": {
                "model": "Amazon-only",
                "channels": ["Amazon.in"],
                "offline_retail": False,
                "forbidden_touchpoints": [],
            },
            "brand_facts": {},
        }
        # Pass source documents so that T1 can verify the price claim.
        source_docs = ["Lumio Vision 7 official price: ₹29,999. Screen: 43-inch."]
        report = run_grounding_check(
            product_frame=clean_frame,
            market_facts=market_facts_no_forbidden,
            persona_outputs=[persona],
            source_documents=source_docs,
        )
        blocking = [i for i in report.issues if i.severity in ("CRITICAL", "HIGH")]
        assert len(blocking) == 0
        assert report.passed is True

    def test_report_passed_field_is_bool(self):
        """GroundingReport.passed must be a bool."""
        report = run_grounding_check(
            product_frame="A product.",
            market_facts={"distribution": {"forbidden_touchpoints": []}, "brand_facts": {}},
            persona_outputs=[],
        )
        assert isinstance(report.passed, bool)

    def test_report_issues_is_list(self):
        """GroundingReport.issues must be a list."""
        report = run_grounding_check(
            product_frame="A product.",
            market_facts={"distribution": {"forbidden_touchpoints": []}, "brand_facts": {}},
            persona_outputs=[],
        )
        assert isinstance(report.issues, list)


# ---------------------------------------------------------------------------
# load_market_facts tests
# ---------------------------------------------------------------------------


class TestLoadMarketFacts:
    def test_load_market_facts_lumio(self):
        """Successfully loads lumio.json and returns a dict with expected keys."""
        facts = load_market_facts("lumio")
        assert isinstance(facts, dict)
        assert facts.get("client") == "Lumio"
        assert "distribution" in facts
        assert "forbidden_touchpoints" in facts["distribution"]

    def test_load_market_facts_lo_foods(self):
        """Successfully loads lo_foods.json."""
        facts = load_market_facts("lo_foods")
        assert isinstance(facts, dict)
        assert "distribution" in facts

    def test_load_market_facts_littlejoys(self):
        """Successfully loads littlejoys.json."""
        facts = load_market_facts("littlejoys")
        assert isinstance(facts, dict)
        assert facts.get("client") == "LittleJoys"

    def test_load_market_facts_unknown_client_raises(self):
        """Loading a non-existent client raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_market_facts("nonexistent_client_xyz")

    def test_lumio_forbidden_touchpoints_contains_croma(self):
        """Lumio market facts must list Croma as a forbidden touchpoint."""
        facts = load_market_facts("lumio")
        forbidden = facts["distribution"]["forbidden_touchpoints"]
        assert "Croma" in forbidden

    def test_lumio_distribution_model_is_amazon_only(self):
        """Lumio distribution model must be 'Amazon-only'."""
        facts = load_market_facts("lumio")
        assert facts["distribution"]["model"] == "Amazon-only"


# ---------------------------------------------------------------------------
# summary() format tests
# ---------------------------------------------------------------------------


class TestSummaryFormat:
    def test_summary_format_non_empty_string(self):
        """summary() must return a non-empty formatted string."""
        persona = _persona_with_croma("P02")
        report = run_grounding_check(
            product_frame=_LUMIO_PRODUCT_FRAME,
            market_facts=_LUMIO_MARKET_FACTS,
            persona_outputs=[persona],
        )
        summary = report.summary()
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_summary_contains_gate_header(self):
        """summary() must include the G12 gate header."""
        report = run_grounding_check(
            product_frame="A product.",
            market_facts={"distribution": {"forbidden_touchpoints": []}, "brand_facts": {}},
            persona_outputs=[],
        )
        assert "G12" in report.summary()

    def test_summary_shows_pass_when_clean(self):
        """summary() must show PASS when report.passed is True."""
        clean_frame = "Lumio is available on Amazon with a warranty."
        facts = {
            "distribution": {
                "model": "Amazon-only",
                "offline_retail": False,
                "forbidden_touchpoints": [],
            },
            "brand_facts": {},
        }
        report = run_grounding_check(
            product_frame=clean_frame,
            market_facts=facts,
            persona_outputs=[],
        )
        assert "PASS" in report.summary()

    def test_summary_shows_fail_when_critical_issue(self):
        """summary() must show FAIL when there is a CRITICAL issue."""
        persona = _persona_with_croma("P02")
        report = run_grounding_check(
            product_frame=_LUMIO_PRODUCT_FRAME,
            market_facts=_LUMIO_MARKET_FACTS,
            persona_outputs=[persona],
        )
        assert "FAIL" in report.summary()

    def test_summary_contains_issue_type_label(self):
        """summary() must include the issue type (T2) when issues exist."""
        persona = _persona_with_croma("P02")
        report = run_grounding_check(
            product_frame=_LUMIO_PRODUCT_FRAME,
            market_facts=_LUMIO_MARKET_FACTS,
            persona_outputs=[persona],
        )
        assert "T2" in report.summary()

    def test_summary_includes_clean_count(self):
        """summary() must report a clean element count."""
        report = run_grounding_check(
            product_frame="A product.",
            market_facts={"distribution": {"forbidden_touchpoints": []}, "brand_facts": {}},
            persona_outputs=[],
        )
        assert "Clean" in report.summary()


# ---------------------------------------------------------------------------
# GroundingIssue dataclass tests
# ---------------------------------------------------------------------------


class TestGroundingIssueDataclass:
    def test_grounding_issue_fields(self):
        """GroundingIssue must accept all required fields."""
        issue = GroundingIssue(
            issue_type="T2",
            severity="CRITICAL",
            persona_id="P01",
            location="prior_exposure field",
            contaminated_text="I saw it at Croma",
            reason="Croma is a forbidden touchpoint for this Amazon-only brand.",
            suggested_fix="Replace with an online discovery path.",
        )
        assert issue.issue_type == "T2"
        assert issue.severity == "CRITICAL"
        assert issue.persona_id == "P01"

    def test_grounding_issue_none_persona_id(self):
        """GroundingIssue persona_id may be None (used for T1 product frame issues)."""
        issue = GroundingIssue(
            issue_type="T1",
            severity="HIGH",
            persona_id=None,
            location="product_frame (price claim)",
            contaminated_text="₹4,000",
            reason="Price not in source documents.",
            suggested_fix="Remove or cite the price.",
        )
        assert issue.persona_id is None
