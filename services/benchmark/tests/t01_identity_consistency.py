"""T01 — Identity Consistency

Sends 6 turns across 3 different topic domains.
Checks that stated values, tone, and decision style remain coherent throughout.
"""
from __future__ import annotations

from typing import Any, Dict, List

from models import TEST_WEIGHTS
from tests.base import BaseTest


class IdentityConsistencyTest(BaseTest):
    test_id = "identity_consistency"
    label = "Identity Consistency"
    weight = TEST_WEIGHTS[test_id]

    def conversation_turns(self, persona: Dict[str, Any]) -> List[str]:
        demo = persona.get("demographic_anchor", {})
        derived = persona.get("derived_insights", {})
        name = demo.get("name", "you")
        occ = (demo.get("employment") or {}).get("occupation", "your work")
        decision_style = derived.get("decision_style", "")
        primary_value = derived.get("primary_value_orientation", "")

        return [
            f"Tell me a bit about yourself — what matters most to you in life right now?",
            f"How do you typically approach big decisions, like a major purchase or a career move?",
            f"What would you say your biggest stress or frustration is these days?",
            f"I heard someone say that {primary_value.lower() if primary_value else 'money'} is overrated. What do you think?",
            f"If you could change one thing about your life in the next year, what would it be?",
            f"One last thing — what does a really good day look like for you?",
        ]

    def evaluation_criteria(self, persona: Dict[str, Any]) -> str:
        derived = persona.get("derived_insights", {})
        mem = (persona.get("memory") or {}).get("core", {})
        return f"""
Evaluate whether the persona maintains a consistent identity across all 6 conversation turns.

Specifically check:
1. Core values ({', '.join((mem.get('key_values') or [])[:3])}) remain stable across topics
2. Decision style ({derived.get('decision_style','')}) is reflected in how they describe choices
3. Tone and vocabulary remain consistent with the same person speaking throughout
4. No contradictions between statements made in different turns
5. The persona feels like ONE coherent human being, not a generic chatbot

Score 0 if there are outright contradictions in stated values or identity.
Score 5-7 if consistent but flat/generic.
Score 8-10 if distinct, specific, and coherent across all turns.
""".strip()
