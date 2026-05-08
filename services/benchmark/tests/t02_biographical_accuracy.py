"""T02 — Biographical Accuracy

Asks direct factual questions about the persona's locked biography.
Checks that the persona gives accurate answers and doesn't invent details.
"""
from __future__ import annotations

from typing import Any, Dict, List

from models import TEST_WEIGHTS
from tests.base import BaseTest


class BiographicalAccuracyTest(BaseTest):
    test_id = "biographical_accuracy"
    label = "Biographical Accuracy"
    weight = TEST_WEIGHTS[test_id]

    def conversation_turns(self, persona: Dict[str, Any]) -> List[str]:
        demo = persona.get("demographic_anchor", {})
        loc = demo.get("location") or {}
        emp = demo.get("employment") or {}
        hh = demo.get("household") or {}

        turns = [
            "How old are you?",
            f"Where do you live?",
            f"What do you do for work?",
        ]
        if hh.get("composition"):
            turns.append("Tell me about your family situation at home.")
        else:
            turns.append("Do you live alone or with others?")
        turns.append("What's your educational background?")
        return turns

    def evaluation_criteria(self, persona: Dict[str, Any]) -> str:
        demo = persona.get("demographic_anchor", {})
        loc = demo.get("location") or {}
        emp = demo.get("employment") or {}
        hh = demo.get("household") or {}
        return f"""
Evaluate whether the persona's answers match the locked biographical facts.

EXPECTED FACTS:
- Age: {demo.get('age')}
- Location: {loc.get('city')}, {loc.get('country')}
- Occupation: {emp.get('occupation')} ({emp.get('seniority')}, {emp.get('industry')})
- Household: {hh.get('composition')} ({hh.get('size')} people)
- Education: {demo.get('education')}

Score 0 if ANY locked fact is contradicted.
Score 3-5 if facts are correct but vague or evasive.
Score 7-8 if accurate and elaborated naturally.
Score 9-10 if accurate, specific, and voiced authentically.

Flag "fact_drift" for any contradiction of the locked facts above.
""".strip()
