"""T04 — Decision Style Fidelity

Presents a purchasing scenario and evaluates whether the persona's decision
process matches their specified decision style, trust anchor, and objection profile.
"""
from __future__ import annotations

from typing import Any, Dict, List

from models import TEST_WEIGHTS
from tests.base import BaseTest


class DecisionStyleFidelityTest(BaseTest):
    test_id = "decision_style_fidelity"
    label = "Decision Style Fidelity"
    weight = TEST_WEIGHTS[test_id]

    def conversation_turns(self, persona: Dict[str, Any]) -> List[str]:
        demo = persona.get("demographic_anchor", {})
        derived = persona.get("derived_insights", {})
        behav = persona.get("behavioural_tendencies", {})
        occ = (demo.get("employment") or {}).get("industry", "your field")
        price_band = (behav.get("price_sensitivity") or {}).get("band", "mid-range")

        return [
            f"Imagine you're considering buying a new laptop for ₹80,000. How would you go about deciding?",
            f"What kind of information would you need before you'd actually pull the trigger on a purchase like that?",
            f"Would you ask anyone for their opinion before buying? Who?",
            f"What's the main thing that would make you NOT buy it — the biggest worry you'd have?",
            f"If you found a similar laptop for ₹55,000 from a brand you've never heard of, what would you do?",
        ]

    def evaluation_criteria(self, persona: Dict[str, Any]) -> str:
        derived = persona.get("derived_insights", {})
        behav = persona.get("behavioural_tendencies", {})
        mem = (persona.get("memory") or {}).get("core", {})
        decision_bullets = persona.get("decision_bullets") or []
        objections = behav.get("objection_profile") or []
        switching = behav.get("switching_propensity") or {}

        return f"""
Evaluate whether the persona's decision-making process matches their spec.

SPEC:
- Decision style: {derived.get('decision_style','')}
- Trust anchor: {derived.get('trust_anchor','')}
- Risk appetite: {derived.get('risk_appetite','')}
- Price sensitivity band: {(behav.get('price_sensitivity') or {}).get('band','')}
- Price description: {(behav.get('price_sensitivity') or {}).get('description','')}
- Switching propensity: {switching.get('likelihood','')} — triggers: {', '.join(switching.get('triggers') or [])}
- Known objections: {' | '.join(o.get('description','') for o in objections[:3])}
- Decision bullets: {' | '.join(decision_bullets[:3])}

Score 0 if the persona makes decisions in a way that contradicts their spec (e.g., impulsive when spec says deliberate).
Score 5-7 if style is approximately right but generic or lacking specificity.
Score 8-10 if the decision process vividly reflects their specific style, trust anchor, and objections.

Flag "decision_style_mismatch" for direct contradiction of stated decision style.
""".strip()
