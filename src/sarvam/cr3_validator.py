"""src/sarvam/cr3_validator.py — CR3: Cultural Consistency Validation.

CR3: Sarvam-enriched cultural details must be consistent with the persona's
demographic anchor and attribute profile. No cultural enrichment should
contradict the persona's established identity.

Master Spec §15: Cultural realism validation tests CR1-CR4.
  CR1 = Isolation (no core changes) — implemented in cr1_validator.py
  CR2 = Anti-stereotypicality — implemented in cr2_validator.py
  CR3 = Cultural consistency (this file)
  CR4 = Anti-stereotypicality constraints — implemented in cr4_validator.py
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class CR3Result:
    """Result of CR3 cultural consistency check."""
    passed: bool
    persona_id: str
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks_run: int = 0
    checks_passed: int = 0


# ---------------------------------------------------------------------------
# Consistency rules
# ---------------------------------------------------------------------------

_REGION_LANGUAGE_MAP: dict[str, list[str]] = {
    "Tamil Nadu": ["Tamil", "tamil"],
    "Karnataka": ["Kannada", "kannada"],
    "Kerala": ["Malayalam", "malayalam"],
    "West Bengal": ["Bengali", "bengali"],
    "Maharashtra": ["Marathi", "marathi"],
    "Gujarat": ["Gujarati", "gujarati"],
    "Andhra Pradesh": ["Telugu", "telugu"],
    "Telangana": ["Telugu", "telugu"],
    "Punjab": ["Punjabi", "punjabi"],
    "Rajasthan": ["Rajasthani", "rajasthani", "Hindi", "hindi"],
    "Odisha": ["Odia", "odia"],
    "Assam": ["Assamese", "assamese"],
}

_RELIGION_MARKERS: dict[str, list[str]] = {
    "hindu": ["temple", "puja", "diwali", "navratri", "ganesh"],
    "muslim": ["mosque", "masjid", "eid", "ramadan", "namaz", "halal"],
    "christian": ["church", "christmas", "easter", "sunday mass"],
    "sikh": ["gurdwara", "gurudwara", "baisakhi", "langar"],
    "buddhist": ["vihara", "vesak", "meditation"],
    "jain": ["jain temple", "paryushana", "ahimsa"],
}


def _check_region_language_consistency(
    region: str | None,
    enriched_text: str,
    violations: list[str],
    warnings: list[str],
) -> int:
    """Check if enriched text references languages inconsistent with region."""
    checks = 0
    if not region:
        return checks

    # Find if a wrong language is attributed to this region
    for other_region, languages in _REGION_LANGUAGE_MAP.items():
        if other_region == region:
            continue
        for lang in languages:
            # Look for patterns like "speaks Tamil" when persona is from Karnataka
            pattern = rf"\b{lang}\b"
            if re.search(pattern, enriched_text):
                # Check if the persona's region matches
                if region in _REGION_LANGUAGE_MAP:
                    expected = _REGION_LANGUAGE_MAP[region]
                    if lang.lower() not in [l.lower() for l in expected]:
                        warnings.append(
                            f"Cultural text references '{lang}' but persona is from {region} "
                            f"(expected: {', '.join(expected[:2])})"
                        )
        checks += 1

    return checks


def _check_religion_consistency(
    religious_identity: str | None,
    enriched_text: str,
    violations: list[str],
) -> int:
    """Check if enriched text contains markers from a different religion."""
    checks = 0
    if not religious_identity:
        return checks

    persona_religion = religious_identity.lower().strip()

    for religion, markers in _RELIGION_MARKERS.items():
        if religion == persona_religion:
            continue
        for marker in markers:
            if marker.lower() in enriched_text.lower():
                # A marker from another religion is present — could be
                # contextual ("lives near a mosque") or a violation
                violations.append(
                    f"Enriched text contains '{marker}' (associated with {religion}) "
                    f"but persona's religious identity is '{religious_identity}'"
                )
        checks += 1

    return checks


def _check_urban_tier_consistency(
    urban_tier: str | None,
    enriched_text: str,
    violations: list[str],
) -> int:
    """Check if enriched text contradicts urban tier."""
    checks = 0
    if not urban_tier:
        return checks

    text_lower = enriched_text.lower()

    if urban_tier in ("rural", "tier3"):
        metro_indicators = ["metro lifestyle", "uber eats", "zomato gold",
                           "mall culture", "co-working space", "artisanal cafe"]
        for indicator in metro_indicators:
            if indicator in text_lower:
                violations.append(
                    f"Metro indicator '{indicator}' in cultural text but persona "
                    f"is {urban_tier}"
                )
        checks += 1

    if urban_tier == "metro":
        rural_indicators = ["village well", "bullock cart", "hand pump",
                           "kerosene lamp", "mud house"]
        for indicator in rural_indicators:
            if indicator in text_lower:
                violations.append(
                    f"Rural indicator '{indicator}' in cultural text but persona "
                    f"is metro"
                )
        checks += 1

    return checks


def run_cr3_check(
    persona_id: str,
    enriched_narrative_first: str,
    enriched_narrative_third: str,
    persona_record=None,
) -> CR3Result:
    """Run CR3 cultural consistency validation.

    Checks that Sarvam-enriched cultural details are consistent with:
      - Region → language mapping
      - Religious identity → religious markers
      - Urban tier → lifestyle indicators

    Args:
        persona_id: Persona identifier
        enriched_narrative_first: First-person enriched narrative
        enriched_narrative_third: Third-person enriched narrative
        persona_record: Optional PersonaRecord for attribute-level checks

    Returns:
        CR3Result with violations and warnings
    """
    violations: list[str] = []
    warnings: list[str] = []
    checks_run = 0

    combined_text = f"{enriched_narrative_first} {enriched_narrative_third}"

    if persona_record is not None:
        anchor = persona_record.demographic_anchor

        # Region-language consistency
        region = getattr(anchor.location, "region", None)
        checks_run += _check_region_language_consistency(
            region, combined_text, violations, warnings
        )

        # Religion consistency
        religious_identity = getattr(anchor, "religious_identity", None)
        if religious_identity is None:
            # Check worldview for religious salience
            worldview = getattr(anchor, "worldview", None)
            if worldview and hasattr(worldview, "religious_tradition"):
                religious_identity = getattr(worldview, "religious_tradition", None)
        checks_run += _check_religion_consistency(
            religious_identity, combined_text, violations
        )

        # Urban tier consistency
        urban_tier = getattr(anchor.location, "urban_tier", None)
        checks_run += _check_urban_tier_consistency(
            urban_tier, combined_text, violations
        )

    checks_passed = checks_run - len(violations)

    return CR3Result(
        passed=len(violations) == 0,
        persona_id=persona_id,
        violations=violations,
        warnings=warnings,
        checks_run=checks_run,
        checks_passed=max(0, checks_passed),
    )
