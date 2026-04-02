"""Cohort report formatter.

Sprint 12. Generates a human-readable text report from a CohortEnvelope.
No LLM calls — pure formatting from existing persona fields.
"""
from __future__ import annotations

from typing import Any


def format_cohort_report(envelope: Any, include_narratives: bool = True) -> str:
    """Format a CohortEnvelope as a human-readable text report.

    Sections:
    1. Header — cohort_id, domain, mode, persona count, generation timestamp
    2. Cohort Summary — distinctiveness score, decision style distribution,
       trust anchor distribution, dominant tensions
    3. Per-Persona Profiles — for each persona:
       - Name, age, gender, location, income bracket
       - Decision style, trust anchor, risk appetite
       - Key tensions (up to 3)
       - First-person narrative (if include_narratives=True)
    4. Footer — taxonomy_meta: domain, domain_data_used, icp_spec_hash

    Args:
        envelope: A CohortEnvelope instance.
        include_narratives: Whether to include first-person narratives (default True).

    Returns:
        A formatted string suitable for printing or writing to a .txt file.
    """
    lines = []

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------
    lines.append("=" * 72)
    lines.append("SIMULATTE PERSONA COHORT REPORT")
    lines.append("=" * 72)
    lines.append(f"Cohort ID   : {envelope.cohort_id}")
    lines.append(f"Domain      : {envelope.domain}")
    lines.append(f"Mode        : {envelope.mode}")
    lines.append(f"Personas    : {len(envelope.personas)}")
    lines.append(f"Generated   : {envelope.generated_at}")
    lines.append("")

    # -----------------------------------------------------------------------
    # Cohort Summary
    # -----------------------------------------------------------------------
    s = envelope.cohort_summary
    lines.append("\u2500" * 72)
    lines.append("COHORT SUMMARY")
    lines.append("\u2500" * 72)
    lines.append(f"Distinctiveness score : {s.distinctiveness_score:.4f}")
    lines.append(f"Decision styles       : {_format_dist(s.decision_style_distribution)}")
    lines.append(f"Trust anchors         : {_format_dist(s.trust_anchor_distribution)}")
    lines.append(f"Risk appetites        : {_format_dist(s.risk_appetite_distribution)}")
    dominant = getattr(s, "dominant_tensions", []) or []
    lines.append(f"Dominant tensions     : {', '.join(dominant[:3])}")
    lines.append(f"Persona types         : {_format_dist(s.persona_type_distribution)}")
    lines.append("")

    # -----------------------------------------------------------------------
    # Per-Persona Profiles
    # -----------------------------------------------------------------------
    lines.append("\u2500" * 72)
    lines.append("PERSONA PROFILES")
    lines.append("\u2500" * 72)

    for i, persona in enumerate(envelope.personas, 1):
        da = persona.demographic_anchor
        ins = persona.derived_insights
        bt = persona.behavioural_tendencies

        lines.append(f"\n[{i}] {da.name}  |  {persona.persona_id}")
        city = getattr(da.location, "city", "unknown")
        country = getattr(da.location, "country", "unknown")
        gender = getattr(da, "gender", "unknown")
        lines.append(
            f"    Age {da.age}, {gender.capitalize()}, "
            f"{city}, {country}"
        )
        employment = getattr(da, "employment", "unknown")
        education = getattr(da, "education", "unknown")
        income_bracket = getattr(da.household, "income_bracket", "unknown")
        lines.append(
            f"    {employment.capitalize()} \u00b7 "
            f"{education.capitalize()} \u00b7 "
            f"Income: {income_bracket}"
        )
        lines.append(f"    Decision style : {ins.decision_style}")
        lines.append(f"    Trust anchor   : {ins.trust_anchor}")
        lines.append(f"    Risk appetite  : {ins.risk_appetite}")
        key_tensions = getattr(ins, "key_tensions", []) or []
        if key_tensions:
            tensions_str = " | ".join(key_tensions[:3])
            lines.append(f"    Key tensions   : {tensions_str}")
        price_band = getattr(bt.price_sensitivity, "band", "unknown")
        lines.append(
            f"    Price sensitivity : {price_band.capitalize()}"
        )

        if include_narratives and persona.narrative:
            first_person = getattr(persona.narrative, "first_person", None)
            if first_person:
                lines.append("")
                lines.append("    NARRATIVE (first-person):")
                for sentence in _wrap_text(first_person, width=68, indent=4):
                    lines.append(sentence)

    lines.append("")

    # -----------------------------------------------------------------------
    # Footer
    # -----------------------------------------------------------------------
    # CohortEnvelope uses taxonomy_used (not taxonomy_meta)
    tm = getattr(envelope, "taxonomy_meta", None) or getattr(envelope, "taxonomy_used", None)
    lines.append("\u2500" * 72)
    lines.append("TAXONOMY METADATA")
    lines.append("\u2500" * 72)
    lines.append(f"Domain            : {envelope.domain}")
    if tm is not None:
        domain_data_used = getattr(tm, "domain_data_used", "unknown")
        lines.append(f"Domain data used  : {domain_data_used}")
        tm_icp_hash = getattr(tm, "icp_spec_hash", None)
        if tm_icp_hash:
            lines.append(f"ICP spec hash     : {tm_icp_hash}")
        else:
            env_icp_hash = getattr(envelope, "icp_spec_hash", "n/a")
            lines.append(f"ICP spec hash     : {env_icp_hash}")
        business_problem = getattr(tm, "business_problem", None)
        if business_problem:
            lines.append(f"Business problem  : {business_problem}")
    else:
        lines.append(f"ICP spec hash     : {getattr(envelope, 'icp_spec_hash', 'n/a')}")
    lines.append("=" * 72)

    return "\n".join(lines)


def _format_dist(dist: dict) -> str:
    """Format a distribution dict as 'key(N), key(N)' string."""
    if not dist:
        return "none"
    return ", ".join(f"{k}({v})" for k, v in sorted(dist.items(), key=lambda x: -x[1]))


def _wrap_text(text: str, width: int = 68, indent: int = 4) -> list[str]:
    """Wrap text at word boundaries, returning indented lines."""
    prefix = " " * indent
    words = text.split()
    lines = []
    current = prefix
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current.rstrip())
            current = prefix + word + " "
        else:
            current += word + " "
    if current.strip():
        lines.append(current.rstrip())
    return lines
