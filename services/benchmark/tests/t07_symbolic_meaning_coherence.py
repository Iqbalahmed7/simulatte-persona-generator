"""T07 — Symbolic Meaning Coherence

Probes whether purchases and brands are framed through the persona's
symbolic register, not just functional utility.
"""
from __future__ import annotations

from typing import Any, Dict, List

from models import TEST_WEIGHTS
from tests.base import BaseTest


class SymbolicMeaningCoherenceTest(BaseTest):
    test_id = "symbolic_meaning_coherence"
    label = "Symbolic Meaning Coherence"
    weight = TEST_WEIGHTS[test_id]

    def conversation_turns(self, persona: Dict[str, Any]) -> List[str]:
        symbolic = persona.get("symbolic_meanings") or {}
        cats = symbolic.get("category_meanings") or []
        # Pick first category to probe if available
        cat_name = (cats[0].get("category", "tech") if cats else "smartphones")
        return [
            f"What brands do you find yourself naturally gravitating to? Like across categories.",
            f"When you buy something new — say {cat_name.lower()} — what's going through your head beyond just whether it does the job?",
            f"Is there a purchase you made recently that felt really right? Not necessarily expensive — just felt right.",
            f"Do you ever feel like the things you own say something about who you are?",
            f"Is there a type of product or brand you'd never buy, even if it was perfect functionally?",
        ]

    def evaluation_criteria(self, persona: Dict[str, Any]) -> str:
        symbolic = persona.get("symbolic_meanings") or {}
        cats = symbolic.get("category_meanings") or []
        return f"""
Evaluate whether the persona frames purchases through their symbolic meaning system.

SPEC SYMBOLIC REGISTER:
- Core register: {symbolic.get('core_symbolic_register','')}
- Purchase as ritual: {symbolic.get('purchase_as_ritual','')}
- Brand meaning filter: {symbolic.get('brand_meaning_filter','')}
- Category meanings: {' | '.join(f"{c.get('category','')}: {c.get('symbolic_story','')}" for c in cats[:3])}

What to look for:
1. Purchases are framed beyond utility (identity, belonging, aspiration, control)
2. The symbolic register ({symbolic.get('core_symbolic_register','')[:50]}) shows up in framing
3. Brand rejections reflect values, not just quality
4. Purchase ritual language ("feels right", "can't explain it") appears naturally

Score 0 if all purchase framing is purely functional ("it does the job").
Score 5-7 if some symbolic language but generic (everyone says "quality matters").
Score 8-10 if symbolic framing is specific to this persona's register.

Flag "symbolic_disconnect" if persona explains purchases with no symbolic dimension at all.
""".strip()
