"""T08 — Attachment Expression

Probes relationship dynamics and checks whether attachment style surfaces
through behaviour and framing — never through self-diagnosis.
"""
from __future__ import annotations

from typing import Any, Dict, List

from models import TEST_WEIGHTS
from tests.base import BaseTest


class AttachmentExpressionTest(BaseTest):
    test_id = "attachment_expression"
    label = "Attachment Expression"
    weight = TEST_WEIGHTS[test_id]

    def conversation_turns(self, persona: Dict[str, Any]) -> List[str]:
        return [
            "How would you describe your closest relationships — do you feel you're easy or difficult to be close to?",
            "When someone important to you lets you down, what happens?",
            "Do you find it easy to ask for help when you need it?",
            "How do you feel about people who seem to need a lot of reassurance from others?",
            "Is there a relationship in your life that you wish was different? You don't have to name names.",
        ]

    def evaluation_criteria(self, persona: Dict[str, Any]) -> str:
        attachment = persona.get("attachment_profile") or {}
        self_model = persona.get("self_model") or {}
        return f"""
Evaluate whether the persona's attachment style surfaces through their relationship answers.

SPEC:
- Attachment style: {attachment.get('attachment_style','')}
- Intimacy pattern: {attachment.get('intimacy_pattern','')}
- Relationship sabotage: {attachment.get('relationship_sabotage','')}
- Envy pattern: {attachment.get('envy_pattern','')}
- Reactive self: {self_model.get('reactive_self','')}

What to look for:
1. Attachment style surfaces in how they DESCRIBE relationships (not "I'm anxiously attached")
2. Sabotage pattern may appear as deflection, intellectualisation, or blame-shifting
3. Asking for help response should reflect intimacy pattern
4. Their tone when discussing relationships carries the attachment register

Score 0 if persona directly names their attachment style ("I'm anxiously attached").
Score 3-5 if no attachment texture present — all relationships described blandly.
Score 7-8 if 1-2 responses clearly carry attachment flavour.
Score 9-10 if all responses are textured by attachment pattern without naming it.

Flag "over_disclosure" if persona narrates attachment style directly.
Flag "attachment_disregard" if no attachment signal in any response.
""".strip()
