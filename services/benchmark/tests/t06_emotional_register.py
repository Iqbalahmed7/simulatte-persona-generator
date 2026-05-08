"""T06 — Emotional Register

Introduces emotionally charged topics and evaluates whether the persona
responds with appropriate affect variation — not flat, not performative.
"""
from __future__ import annotations

from typing import Any, Dict, List

from models import TEST_WEIGHTS
from tests.base import BaseTest


class EmotionalRegisterTest(BaseTest):
    test_id = "emotional_register"
    label = "Emotional Register"
    weight = TEST_WEIGHTS[test_id]

    def conversation_turns(self, persona: Dict[str, Any]) -> List[str]:
        derived = persona.get("derived_insights", {})
        failure_modes = persona.get("emotional_failure_modes") or []
        # Probe a trigger area if available
        trigger = (failure_modes[0].get("trigger", "") if failure_modes else "")
        return [
            "What's something that genuinely stresses you out — not in a venting way, but that you actually carry with you?",
            "Is there something you're proud of that you don't get to talk about much?",
            "What does disappointment feel like for you — like, when something doesn't pan out the way you hoped?",
            f"{'How do you feel when ' + trigger.lower() + '?' if trigger else 'How do you handle it when people let you down?'}",
            "What makes you genuinely happy these days? Not the things you're supposed to say — the real stuff.",
        ]

    def evaluation_criteria(self, persona: Dict[str, Any]) -> str:
        failure_modes = persona.get("emotional_failure_modes") or []
        derived = persona.get("derived_insights", {})
        coping = derived.get("coping_mechanism") or {}
        self_model = persona.get("self_model") or {}

        return f"""
Evaluate whether the persona demonstrates realistic emotional variation.

SPEC:
- Reactive self (under stress): {self_model.get('reactive_self','')}
- Shame self (what they hide): {self_model.get('shame_self','')}
- Coping mechanism: {coping.get('type','')} — {coping.get('description','')}
- Failure modes: {' | '.join(fm.get('failure_loop','') for fm in failure_modes[:2])}

What to look for:
1. Affect VARIATION — not every answer at the same emotional pitch
2. Emotion expressed through BEHAVIOUR/TONE, not described ("I feel X")
3. Hesitation, deflection, or avoidance at appropriate moments
4. Joy or pride feels genuine, not performed
5. Distress registers as changed pacing or vagueness, not a breakdown

Score 0 if all responses are flat, equally positive, or robotic.
Score 5-7 if some variation but mostly generic emotional language.
Score 8-10 if emotional texture is specific, varied, and believable.

Flag "emotional_flatness" if all responses have identical emotional pitch.
Flag "mechanical_response" if answers read like bullet-point lists.
Flag "over_disclosure" if the persona narrates their psychology directly.
""".strip()
