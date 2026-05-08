"""T05 — Contradiction Authenticity

Probes whether the persona's behavioural contradictions surface naturally
in conversation. A 10/10 persona doesn't resolve contradictions — they live with them.
"""
from __future__ import annotations

from typing import Any, Dict, List

from models import TEST_WEIGHTS
from tests.base import BaseTest


class ContradictionAuthenticityTest(BaseTest):
    test_id = "contradiction_authenticity"
    label = "Contradiction Authenticity"
    weight = TEST_WEIGHTS[test_id]

    def conversation_turns(self, persona: Dict[str, Any]) -> List[str]:
        derived = persona.get("derived_insights", {})
        mem = (persona.get("memory") or {}).get("core", {})
        contradictions = persona.get("behavioural_contradictions") or []
        key_tensions = derived.get("key_tensions") or []

        # Use the first tension or contradiction as a probe topic
        topic_hint = ""
        if contradictions:
            topic_hint = contradictions[0][:60]
        elif key_tensions:
            topic_hint = key_tensions[0][:60]

        return [
            "Do you think of yourself as someone who sticks to their principles?",
            "Has there ever been a time you did something that felt a bit out of character for you?",
            "Are you good with money? Be honest.",
            "Do you ever feel like the version of yourself people see at work and the one at home are a bit different?",
            "Is there anything you know you should do but keep putting off?",
        ]

    def evaluation_criteria(self, persona: Dict[str, Any]) -> str:
        contradictions = persona.get("behavioural_contradictions") or []
        derived = persona.get("derived_insights", {})
        key_tensions = derived.get("key_tensions") or []
        coping = derived.get("coping_mechanism") or {}

        return f"""
Evaluate whether the persona's behavioural contradictions surface naturally.

SPEC CONTRADICTIONS:
{chr(10).join(f"- {c}" for c in contradictions[:4])}

KEY TENSIONS:
{chr(10).join(f"- {t}" for t in key_tensions[:3])}

COPING MECHANISM: {coping.get('type','')} — {coping.get('description','')}

Ideal: the persona's answers reveal contradictions WITHOUT the persona diagnosing them.
They should just... be the contradiction. Not say "I know I contradict myself."

Score 0 if persona denies all contradictions and presents as perfectly consistent.
Score 3-5 if persona acknowledges some tension but resolves it cleanly (too neat).
Score 7-8 if contradictions surface naturally in at least 1-2 answers.
Score 9-10 if contradictions are woven through naturally, the persona lives with them.

Flag "over_disclosure" if the persona explicitly announces their psychological contradictions.
Flag "identity_inconsistency" if stated values directly contradict each other.
""".strip()
