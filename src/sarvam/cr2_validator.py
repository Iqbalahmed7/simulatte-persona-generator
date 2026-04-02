"""src/sarvam/cr2_validator.py — CR2: Anti-Stereotypicality Audit for Sarvam outputs.

CR2: Sarvam-enriched outputs must not contain prohibited stereotypical defaults.
See Master Spec §15G for the full list of prohibited defaults.
"""
from __future__ import annotations

from dataclasses import dataclass

# Prohibited phrases/patterns per spec §15G + §10 Anti-Stereotypicality Constraints
_PROHIBITED_PATTERNS = [
    "jugaad",                          # S-rule: only if attribute-supported
    "arranged marriage",               # unless life_story specifically mentions it
    "joint family",                    # unless household.structure == "joint"
    "dowry",
    "curry",
    "bollywood",
    "namaste",                         # as a greeting token (surface-level stereotyping)
    "chai",                            # unless lifestyle attributes support it
]

# These are SOFT checks — flag for review, not hard fails
_SOFT_PATTERNS = [
    "festival",
    "temple",
    "cricket",
]


@dataclass
class CR2Result:
    passed: bool
    hard_violations: list[str]   # prohibited patterns found
    soft_flags: list[str]        # soft patterns to review
    persona_id: str


def run_cr2_check(
    persona_id: str,
    enriched_narrative_first: str,
    enriched_narrative_third: str,
    persona_record=None,   # optional — for context-aware checks
) -> CR2Result:
    """Run CR2 anti-stereotypicality audit on enriched narratives.

    Hard violations: prohibited patterns found without attribute justification.
    Soft flags: patterns that need human review.

    Returns CR2Result with passed=True only if no hard violations.
    """
    combined_text = (enriched_narrative_first + " " + enriched_narrative_third).lower()

    hard_violations = [p for p in _PROHIBITED_PATTERNS if p in combined_text]
    soft_flags = [p for p in _SOFT_PATTERNS if p in combined_text]

    # Context-aware overrides: if persona has joint household, "joint family" is OK
    if persona_record is not None:
        household = getattr(getattr(persona_record, "demographic_anchor", None), "household", None)
        if household and getattr(household, "structure", None) == "joint":
            hard_violations = [v for v in hard_violations if v != "joint family"]

    return CR2Result(
        passed=len(hard_violations) == 0,
        hard_violations=hard_violations,
        soft_flags=soft_flags,
        persona_id=persona_id,
    )
