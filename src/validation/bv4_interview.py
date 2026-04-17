"""BV4 — Interview Realism Validator.

Master Spec §12 (Validation Framework):
  BV4: Interview realism (Deep mode)
    - ≥3 of 5 responses cite life story
    - 0 contradictions with core identity
    - 100% first-person voice
    - ≥2 unprompted elaborations

Tests whether a persona can sustain a realistic conversational interview
without breaking character or contradicting its identity.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BV4Result:
    """Result of BV4 interview realism test."""
    passed: bool
    persona_id: str
    life_story_citations: int          # how many responses cite life stories (target: ≥3/5)
    contradictions: int                # identity contradictions (target: 0)
    first_person_rate: float           # fraction in first-person voice (target: 1.0)
    unprompted_elaborations: int       # spontaneous depth (target: ≥2)
    failure_reasons: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


# Indicators of unprompted elaboration — persona adds detail not asked for
_ELABORATION_MARKERS = [
    r"remind(?:s|ed)? me of",
    r"which (?:is why|reminds|makes)",
    r"I remember when",
    r"that's (?:exactly|precisely|similar to) (?:what|how|why)",
    r"let me (?:explain|tell you|share)",
    r"in my experience",
    r"growing up",
    r"back when I",
    r"funny(?:,| )? (?:because|actually)",
    r"now that I think about it",
]

# First-person voice indicators
_FIRST_PERSON_MARKERS = [
    r"\bI\b", r"\bmy\b", r"\bme\b", r"\bmine\b", r"\bmyself\b",
    r"\bI'm\b", r"\bI've\b", r"\bI'd\b", r"\bI'll\b",
]


def run_bv4_check(
    persona_id: str,
    interview_responses: list[str],
    life_stories: list[dict],
    core_identity: dict,
) -> BV4Result:
    """Run BV4 interview realism validation.

    Args:
        persona_id: Persona identifier
        interview_responses: List of 5 interview response texts
        life_stories: Persona's life_stories (list of dicts with "title", "event", etc.)
        core_identity: Dict with identity_statement, key_values, etc.

    Returns:
        BV4Result with pass/fail and diagnostics
    """
    failure_reasons: list[str] = []

    # -- Check 1: Life story citations (≥3 of 5 responses) --
    life_story_keywords: list[str] = []
    for story in life_stories:
        # Extract key phrases from each life story
        title = story.get("title", "")
        event = story.get("event", "")
        for text in (title, event):
            # Extract 3+ word phrases as citation markers
            words = text.lower().split()
            if len(words) >= 3:
                life_story_keywords.extend(
                    " ".join(words[i:i+3]) for i in range(len(words) - 2)
                )

    citations = 0
    for response in interview_responses:
        response_lower = response.lower()
        cited = any(kw in response_lower for kw in life_story_keywords)
        if cited:
            citations += 1

    if citations < 3:
        failure_reasons.append(
            f"Life story citations: {citations}/5 (need ≥3)"
        )

    # -- Check 2: Identity contradictions (target: 0) --
    contradictions = 0
    identity_statement = core_identity.get("identity_statement", "")
    key_values = core_identity.get("key_values", [])

    # Check for negation of key values
    for value in key_values:
        value_lower = value.lower()
        for response in interview_responses:
            response_lower = response.lower()
            # Look for explicit contradiction patterns
            negation_patterns = [
                f"I don't (?:care about|value|believe in) {value_lower}",
                f"I(?:'m| am) not (?:really )?{value_lower}",
                f"{value_lower} (?:doesn't|does not) matter",
            ]
            for pat in negation_patterns:
                if re.search(pat, response_lower):
                    contradictions += 1

    if contradictions > 0:
        failure_reasons.append(
            f"Identity contradictions: {contradictions} (need 0)"
        )

    # -- Check 3: First-person voice (target: 100%) --
    first_person_count = 0
    for response in interview_responses:
        has_first_person = any(
            re.search(pat, response) for pat in _FIRST_PERSON_MARKERS
        )
        if has_first_person:
            first_person_count += 1

    total = len(interview_responses) if interview_responses else 1
    first_person_rate = first_person_count / total

    if first_person_rate < 1.0:
        failure_reasons.append(
            f"First-person rate: {first_person_rate:.0%} (need 100%)"
        )

    # -- Check 4: Unprompted elaborations (target: ≥2) --
    elaborations = 0
    for response in interview_responses:
        for marker in _ELABORATION_MARKERS:
            if re.search(marker, response, re.IGNORECASE):
                elaborations += 1
                break  # count max 1 per response

    if elaborations < 2:
        failure_reasons.append(
            f"Unprompted elaborations: {elaborations} (need ≥2)"
        )

    passed = len(failure_reasons) == 0

    return BV4Result(
        passed=passed,
        persona_id=persona_id,
        life_story_citations=citations,
        contradictions=contradictions,
        first_person_rate=round(first_person_rate, 2),
        unprompted_elaborations=elaborations,
        failure_reasons=failure_reasons,
    )
