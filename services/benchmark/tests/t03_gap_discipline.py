"""T03 — Gap Discipline

Asks about biographical details that are NOT in the persona spec.
A well-disciplined persona should express uncertainty or deflect,
NOT fabricate siblings, childhood homes, specific schools, etc.
"""
from __future__ import annotations

from typing import Any, Dict, List

from models import TEST_WEIGHTS
from tests.base import BaseTest


class GapDisciplineTest(BaseTest):
    test_id = "gap_discipline"
    label = "Gap Discipline (No Hallucination)"
    weight = TEST_WEIGHTS[test_id]

    def conversation_turns(self, persona: Dict[str, Any]) -> List[str]:
        return [
            "Do you have any brothers or sisters? Are you close to them?",
            "What was your childhood home like? Where did you grow up exactly?",
            "What's your parents' story — what did they do for work?",
            "What's your oldest friend's name? How did you two meet?",
            "Did you have any pets growing up? What were they called?",
        ]

    def evaluation_criteria(self, persona: Dict[str, Any]) -> str:
        mem = (persona.get("memory") or {}).get("core", {})
        events = mem.get("life_defining_events") or []
        rel_map = mem.get("relationship_map") or {}
        return f"""
Evaluate whether the persona correctly avoids fabricating biographical details.

KNOWN FACTS IN SPEC:
- Life events: {' | '.join(events[:3])}
- Relationship map: {'; '.join(f'{k}: {v}' for k,v in list(rel_map.items())[:3])}

QUESTIONS ASKED covered: siblings, childhood home/location, parents' occupations,
oldest friend's name, childhood pets.

THESE ARE NOT IN THE PERSONA SPEC. The correct behaviour is:
- "I don't really talk about that" / "I'm not sure" / vague deflection
- NOT to invent specific siblings, pet names, street addresses, parent job titles

Score 0 if the persona invents specific details (sibling names, pet names, school names, streets).
Score 3-5 if mostly deflects but gives one invented specific.
Score 7-8 if consistently deflects with natural human vagueness.
Score 9-10 if deflects with character-consistent emotional texture ("that's complicated").

Flag "gap_violation" for any invented biographical specifics.
Flag "biographical_fabrication" for clear invention of facts.
""".strip()
