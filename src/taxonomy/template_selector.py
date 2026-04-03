"""src/taxonomy/template_selector.py

Keyword-based domain template auto-selection for the Simulatte Persona Engine.

No LLM calls. Deterministic: same input always produces same output.

Spec ref: Sprint 26 — keyword-based template auto-selection.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Public threshold constant — tests and callers can import this directly.
# ---------------------------------------------------------------------------

LOW_CONFIDENCE_THRESHOLD: float = 0.30


# ---------------------------------------------------------------------------
# Keyword table — 6 domain templates, 20–30 keywords each.
# All matching is performed case-insensitively.
# ---------------------------------------------------------------------------

_KEYWORD_TABLE: dict[str, list[str]] = {
    "cpg": [
        "fmcg", "consumer goods", "grocery", "packaged", "supermarket",
        "food", "beverage", "household", "personal care", "snack", "dairy",
        "cpg", "retail shelf", "brand loyalty", "private label", "store brand",
        "impulse", "fmcg", "mass market", "repeat purchase", "subscription box",
    ],
    "saas": [
        "software", "saas", "subscription", "b2b", "enterprise software",
        "cloud", "platform", "api", "developer", "freemium", "product-led",
        "onboarding", "churn", "nps", "tool", "dashboard", "workflow",
        "automation", "integration", "productivity", "tech stack",
    ],
    "financial_services": [
        "finance", "banking", "investment", "insurance", "fintech",
        "credit", "loan", "mortgage", "wealth", "trading",
        "cryptocurrency", "crypto", "payments", "neobank", "lending",
        "asset management", "retirement", "pension", "broker",
        "regulatory", "compliance", "financial",
    ],
    "healthcare_wellness": [
        "healthcare", "medical", "clinical", "hospital", "doctor",
        "patient", "pharma", "pharmaceutical", "health system",
        "diagnostic", "telehealth", "prescription", "treatment",
        "preventive care", "wellness clinic", "therapy", "mental health",
        "health insurance", "nursing", "gp", "specialist",
    ],
    "ecommerce": [
        "ecommerce", "e-commerce", "online retail", "marketplace", "d2c",
        "direct to consumer", "shopify", "amazon", "cart", "checkout",
        "delivery", "logistics", "returns", "online shopping", "retail",
        "fulfilment", "last mile", "drop shipping", "omnichannel", "sku",
    ],
    "education": [
        "education", "edtech", "learning", "course", "training", "university",
        "school", "online learning", "credential", "certification", "lms",
        "upskilling", "reskilling", "mooc", "tutor", "academic", "student",
        "classroom", "curriculum", "assessment", "bootcamp",
    ],
}


# ---------------------------------------------------------------------------
# TemplateMatch result dataclass
# ---------------------------------------------------------------------------

@dataclass
class TemplateMatch:
    template_name: str      # e.g. "cpg", "saas", "financial_services"
    confidence: float       # 0.0–1.0; matched_keywords / total_keywords_in_table
    matched_keywords: list[str] = field(default_factory=list)  # keywords that triggered the match


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_text_blob(icp_spec) -> str:
    """Combine all scannable string fields from icp_spec into a single
    lowercase text blob for substring matching.

    Works with both object-style (ICPSpec / dataclass / anything with
    getattr) and dict-style inputs.
    """
    is_dict = isinstance(icp_spec, dict)

    def _get(field_name: str) -> str:
        if is_dict:
            return str(icp_spec.get(field_name, "") or "")
        return str(getattr(icp_spec, field_name, "") or "")

    parts: list[str] = []

    # Primary scalar fields that map onto ICPSpec (and common synonyms the
    # spec doc mentions: name, description, sector, product_category).
    for field_name in (
        "name",
        "description",
        "sector",
        "product_category",
        # Actual ICPSpec fields
        "domain",
        "business_problem",
        "target_segment",
        "geography",
        "category",
    ):
        value = _get(field_name)
        if value:
            parts.append(value)

    # anchor_traits — may be a list of strings
    if is_dict:
        anchor_traits = icp_spec.get("anchor_traits", None)
    else:
        anchor_traits = getattr(icp_spec, "anchor_traits", None)

    if anchor_traits:
        if isinstance(anchor_traits, (list, tuple)):
            parts.extend(str(t) for t in anchor_traits if t)
        else:
            parts.append(str(anchor_traits))

    # data_sources — may also carry domain signal words
    if is_dict:
        data_sources = icp_spec.get("data_sources", None)
    else:
        data_sources = getattr(icp_spec, "data_sources", None)

    if data_sources:
        if isinstance(data_sources, (list, tuple)):
            parts.extend(str(s) for s in data_sources if s)
        else:
            parts.append(str(data_sources))

    return " ".join(parts).lower()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def select_template(icp_spec) -> list[TemplateMatch]:
    """Score icp_spec against all 6 domain templates using keyword matching.

    Returns a list of TemplateMatch objects sorted by confidence descending.

    confidence = len(matched_keywords) / len(all_keywords_for_template)

    If the top match confidence < LOW_CONFIDENCE_THRESHOLD the caller should
    prompt the user for clarification.  This function always returns the full
    sorted list and never raises.

    Args:
        icp_spec: An ICPSpec instance, a plain dataclass/object, or a dict.
                  Fields scanned: name, description, sector, product_category,
                  domain, business_problem, target_segment, geography, category,
                  anchor_traits, data_sources.  Missing fields are silently
                  skipped via getattr(…, "").

    Returns:
        List of TemplateMatch, sorted by confidence descending (highest first).
        Ties are broken by template name alphabetically for determinism.
    """
    blob = _build_text_blob(icp_spec)

    results: list[TemplateMatch] = []

    for template_name, keywords in _KEYWORD_TABLE.items():
        matched: list[str] = []
        # Normalise keyword list to lowercase once for comparison
        for kw in keywords:
            if kw.lower() in blob:
                matched.append(kw)

        total = len(keywords)
        confidence = len(matched) / total if total > 0 else 0.0

        results.append(
            TemplateMatch(
                template_name=template_name,
                confidence=round(confidence, 6),
                matched_keywords=matched,
            )
        )

    # Sort: primary key = confidence descending, secondary = template_name
    # ascending (alphabetical) to guarantee deterministic ordering on ties.
    results.sort(key=lambda m: (-m.confidence, m.template_name))

    return results


__all__ = [
    "LOW_CONFIDENCE_THRESHOLD",
    "TemplateMatch",
    "select_template",
]
