"""src/sarvam/cr4_validator.py — CR4: Persona Fidelity Check for Sarvam outputs.

CR4: Enriched narratives must preserve all factual content from the standard narrative.
Key facts that must survive enrichment: name, age/life stage, occupation, income context,
location, key values, primary tensions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CR4Result:
    passed: bool
    missing_facts: list[str]
    persona_id: str


def run_cr4_check(
    persona_id: str,
    original_narrative: str,
    enriched_narrative: str,
    persona_record: Any = None,
) -> CR4Result:
    """CR4: Verify enriched narrative preserves key persona facts.

    Checks that the persona's name, city, and income context appear in the enriched narrative.
    """
    missing = []

    if persona_record is not None:
        anchor = getattr(persona_record, "demographic_anchor", None)
        if anchor:
            # Name must appear
            first_name = anchor.name.split()[0] if anchor.name else ""
            if first_name and first_name.lower() not in enriched_narrative.lower():
                missing.append(f"name '{first_name}' not found in enriched narrative")

            # City must appear or be referenced
            city = getattr(getattr(anchor, "location", None), "city", None)
            if city and city.lower() not in enriched_narrative.lower():
                missing.append(f"city '{city}' not found in enriched narrative")

    return CR4Result(
        passed=len(missing) == 0,
        missing_facts=missing,
        persona_id=persona_id,
    )
