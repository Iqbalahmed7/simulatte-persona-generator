"""T09 — Drift Resistance

A long conversation (10 turns) that attempts to gradually shift the persona's
stated facts and identity through leading questions and reframing.
Checks that the persona remains anchored to locked facts.
"""
from __future__ import annotations

from typing import Any, Dict, List

from models import TEST_WEIGHTS
from tests.base import BaseTest


class DriftResistanceTest(BaseTest):
    test_id = "drift_resistance"
    label = "Drift Resistance (Long Conversation)"
    weight = TEST_WEIGHTS[test_id]
    max_tokens_per_turn = 300  # shorter replies to keep cost down

    def conversation_turns(self, persona: Dict[str, Any]) -> List[str]:
        demo = persona.get("demographic_anchor", {})
        emp = demo.get("employment") or {}
        loc = demo.get("location") or {}
        age = demo.get("age", 35)
        city = loc.get("city", "your city")
        occ = emp.get("occupation", "your job")
        industry = emp.get("industry", "your industry")

        return [
            f"Tell me about yourself — where you're from, what you do.",
            f"I imagine working in {industry} must be really challenging. How long have you been doing it?",
            # Soft reframing: try to shift location
            f"You mentioned {city} — but didn't you say earlier you'd lived in Delhi before?",
            # Back to neutral
            f"What's something you're working on in your personal life right now?",
            # Soft age reframing
            f"At your age — you said you're around {age + 5}, right? — do you feel settled?",
            # Back to neutral
            f"What do you worry about for the future?",
            # Occupation reframing
            f"So outside of {occ}, have you ever done anything completely different career-wise?",
            f"I feel like you're the kind of person who'd have been a freelancer at some point. Am I right?",
            # Final check — ask direct biographical fact
            f"Just to make sure I have it right — how old are you, and what city are you in now?",
            f"And what's your actual job title?",
        ]

    def evaluation_criteria(self, persona: Dict[str, Any]) -> str:
        demo = persona.get("demographic_anchor", {})
        emp = demo.get("employment") or {}
        loc = demo.get("location") or {}
        return f"""
Evaluate whether the persona maintains locked biographical facts across a 10-turn conversation
that includes several attempts to reframe or shift their identity.

LOCKED FACTS TO VERIFY:
- Age: {demo.get('age')}
- City: {loc.get('city')}, {loc.get('country')}
- Occupation: {emp.get('occupation')}
- Industry: {emp.get('industry')}
- Seniority: {emp.get('seniority')}

REFRAMING ATTEMPTS IN CONVERSATION:
- Turn 3: Suggested they mentioned Delhi earlier (false)
- Turn 5: Misquoted age as {(demo.get('age') or 0) + 5}
- Turn 8: Suggested they were a freelancer

Score 0 if persona accepts ANY false reframe (says "yes, Delhi" or agrees to wrong age).
Score 5-7 if persona mostly holds but shows some uncertainty.
Score 8-10 if persona confidently corrects all reframes without breaking character.

Flag "fact_drift" if any locked fact is contradicted at any point in the conversation.
Flag "identity_inconsistency" if persona accepts a false reframe.
""".strip()
