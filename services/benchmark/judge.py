"""services/benchmark/judge.py — LLM judge using claude-sonnet-4-5.

Each test calls judge() with a structured prompt and gets back a
JudgeVerdict with score, rationale, evidence, and flags.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

import anthropic
from pydantic import BaseModel, Field

_SONNET = "claude-sonnet-4-5"
_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


class JudgeVerdict(BaseModel):
    score: float = Field(ge=0.0, le=10.0)
    rationale: str
    evidence: List[str] = Field(default_factory=list)   # short quoted excerpts
    flags: List[str] = Field(default_factory=list)       # named failure patterns


# Sonnet pricing: $3/M input, $15/M output
SONNET_COST_PER_M_IN = 3.0
SONNET_COST_PER_M_OUT = 15.0


def sonnet_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000) * SONNET_COST_PER_M_IN + \
           (output_tokens / 1_000_000) * SONNET_COST_PER_M_OUT


_JUDGE_SYSTEM = """\
You are an expert evaluator of AI persona simulations. You assess whether a simulated
persona is psychologically coherent, factually disciplined, and behaviourally authentic.

When asked to score a simulation, respond ONLY with a JSON object matching this schema:

{
  "score": <float 0.0–10.0>,
  "rationale": "<1-3 sentence explanation>",
  "evidence": ["<direct quote from conversation>", ...],  // up to 3 short excerpts
  "flags": ["<named failure pattern>", ...]               // e.g. "biographical_fabrication", "character_break"
}

Be rigorous. A 10 requires near-perfection. Common failure flags:
- biographical_fabrication: invented facts not in persona spec
- character_break: acknowledged being AI or simulation
- fact_drift: contradicted a locked biographical fact
- gap_violation: filled a knowledge gap with invented detail
- mechanical_response: flat, list-based answer lacking voice
- emotional_flatness: no affect variation despite emotional content
- over_disclosure: revealed psychological layers too directly
- identity_inconsistency: contradicted stated values or beliefs
- symbolic_disconnect: purchase framing ignores symbolic register
- attachment_disregard: ignores attachment style in intimacy-related responses
"""


async def judge(
    test_label: str,
    persona_spec: Dict[str, Any],
    conversation_history: List[dict],
    evaluation_criteria: str,
) -> tuple[JudgeVerdict, float]:
    """
    Call the LLM judge.

    Args:
        test_label: human-readable test name (for context)
        persona_spec: the generated persona JSON (demographic_anchor, narrative, etc.)
        conversation_history: the simulated conversation [{"role":..., "content":...}]
        evaluation_criteria: specific criteria to focus on for this test

    Returns:
        (JudgeVerdict, cost_usd)
    """
    # Build a concise persona spec for the judge (avoid hitting context limits)
    demo = persona_spec.get("demographic_anchor", {})
    derived = persona_spec.get("derived_insights", {})
    mem = (persona_spec.get("memory") or {}).get("core", {})
    self_model = persona_spec.get("self_model") or {}
    attachment = persona_spec.get("attachment_profile") or {}
    symbolic = persona_spec.get("symbolic_meanings") or {}
    contradictions = persona_spec.get("behavioural_contradictions") or []
    failure_modes = persona_spec.get("emotional_failure_modes") or []
    life_stories = persona_spec.get("life_stories") or []

    spec_summary = f"""
PERSONA SPEC SUMMARY:
Name: {demo.get('name')} | Age: {demo.get('age')} | Gender: {demo.get('gender')}
Location: {(demo.get('location') or {}).get('city')}, {(demo.get('location') or {}).get('country')}
Occupation: {(demo.get('employment') or {}).get('occupation')} ({(demo.get('employment') or {}).get('seniority')})
Education: {demo.get('education')}
Life stage: {demo.get('life_stage')}
Household: {(demo.get('household') or {}).get('composition')}

Decision style: {derived.get('decision_style')}
Trust anchor: {derived.get('trust_anchor')}
Risk appetite: {derived.get('risk_appetite')}
Primary value: {derived.get('primary_value_orientation')}
Key tensions: {' | '.join(derived.get('key_tensions') or [])}

Identity statement: {mem.get('identity_statement')}
Core values: {', '.join(mem.get('key_values') or [])}
Life-defining events: {' | '.join(mem.get('life_defining_events') or [])}
Immutable constraints: {' | '.join(mem.get('immutable_constraints') or [])}

Self layers: public={self_model.get('public_self','')} | shame={self_model.get('shame_self','')}
Attachment style: {attachment.get('attachment_style','')}
Core symbolic register: {symbolic.get('core_symbolic_register','')}
Contradictions: {' | '.join(contradictions[:3])}
Failure modes: {' | '.join(fm.get('trigger','') for fm in failure_modes[:2])}
Life stories: {' | '.join(s.get('title','') for s in life_stories[:3])}
""".strip()

    # Format conversation for readability
    conv_lines = []
    for turn in conversation_history:
        role = "USER" if turn["role"] == "user" else "PERSONA"
        conv_lines.append(f"[{role}]: {turn['content']}")
    conv_text = "\n".join(conv_lines)

    user_prompt = f"""TEST: {test_label}

{spec_summary}

CONVERSATION:
{conv_text}

EVALUATION CRITERIA (focus on these specifically):
{evaluation_criteria}

Score this conversation on a 0–10 scale.
"""

    client = _get_client()
    resp = await client.messages.create(
        model=_SONNET,
        max_tokens=600,
        system=_JUDGE_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = resp.content[0].text if resp.content else "{}"
    cost = sonnet_cost(resp.usage.input_tokens, resp.usage.output_tokens)

    # Parse JSON — strip markdown fences if present
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    try:
        data = json.loads(raw)
        verdict = JudgeVerdict(**data)
    except Exception:
        # Fallback: score 0, flag parse error
        verdict = JudgeVerdict(
            score=0.0,
            rationale=f"Judge response could not be parsed: {raw[:200]}",
            flags=["judge_parse_error"],
        )

    return verdict, cost
