"""Engine compat shim — lightweight Q&A simulation against a cohort.

Used by simulatte-engine's /simulation/run forwarder, which posts a
question + multiple-choice options to PG /simulate. PG fans out per-persona
Q&A calls in bounded parallel and returns a distribution + headline.

This is intentionally light-weight (single Sonnet call per persona, no
multi-round cognition loop) — it's a direct probe, not a full simulation.
The legacy /simulate route (cohort_id + scenario + rounds) still routes to
src.cli._run_simulation as before.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

# Match the codebase default Sonnet model used in src/cognition/decide.py
_SONNET_MODEL = "claude-sonnet-4-6"
_MAX_CONCURRENCY = 5
_MAX_TOKENS = 256


def _persona_brief(p: dict) -> tuple[str, str]:
    """Pull (name, bio_blob) from a persona record dict, defensively."""
    anchor = p.get("demographic_anchor", {}) or {}
    name = anchor.get("name") or p.get("name") or p.get("persona_id") or "Respondent"

    bits: list[str] = []
    for key in ("first_person_narrative", "narrative", "summary", "bio"):
        v = p.get(key)
        if v:
            bits.append(str(v))
            break
    # Add a few demographic / psychographic hooks if present
    if anchor:
        loc = anchor.get("location", {}) or {}
        loc_str = ", ".join(str(x) for x in (loc.get("city"), loc.get("country")) if x)
        demo_bits = [
            f"age {anchor.get('age')}" if anchor.get("age") else None,
            f"{anchor.get('gender')}" if anchor.get("gender") else None,
            f"in {loc_str}" if loc_str else None,
            f"occupation {anchor.get('occupation')}" if anchor.get("occupation") else None,
        ]
        demo = ", ".join(b for b in demo_bits if b)
        if demo:
            bits.insert(0, demo)
    return name, " ".join(bits)[:2000]


def _parse_answer(raw: str, valid_ids: list[str]) -> tuple[str | None, str]:
    """Pull option_id + rationale from model output. Tolerant to non-JSON."""
    # Try strict JSON first
    m = re.search(r"\{[^}]*\}", raw, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(0))
            oid = str(parsed.get("option_id", "")).strip()
            rat = str(parsed.get("rationale", "")).strip()
            if oid in valid_ids:
                return oid, rat
            # case-insensitive match
            for vid in valid_ids:
                if vid.lower() == oid.lower():
                    return vid, rat
        except Exception:  # noqa: BLE001
            pass
    # Fallback: scan for any option id token
    for vid in valid_ids:
        if re.search(rf"\b{re.escape(vid)}\b", raw, re.IGNORECASE):
            return vid, raw.strip()[:300]
    return None, raw.strip()[:300]


async def _ask_persona(
    client,
    persona: dict,
    question: str,
    context: str,
    options: list[dict],
) -> dict | None:
    """Single Sonnet Q&A call. Returns persona_response dict or None on failure."""
    name, bio = _persona_brief(persona)
    valid_ids = [str(o.get("id")) for o in options if o.get("id")]
    opt_lines = "\n".join(
        f"  - {o.get('id')}: {o.get('name', o.get('label', o.get('id')))}" for o in options
    )
    sys_prompt = (
        f"You are {name}. Background: {bio}\n"
        "Answer in character. Pick exactly one option ID."
    )
    user_prompt = (
        (f"Context: {context}\n\n" if context else "")
        + f"Question: {question}\n\nOptions:\n{opt_lines}\n\n"
        + f"Reply with strict JSON only: {{\"option_id\": \"<one of {','.join(valid_ids)}>\", "
          "\"rationale\": \"<one sentence>\"}}"
    )
    try:
        msg = await client.messages.create(
            model=_SONNET_MODEL,
            max_tokens=_MAX_TOKENS,
            system=sys_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = "".join(
            block.text for block in msg.content if getattr(block, "type", None) == "text"
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("simulate_qna persona %s failed: %s", name, exc)
        return None

    option_id, rationale = _parse_answer(raw, valid_ids)
    if option_id is None:
        logger.warning("simulate_qna persona %s gave unparseable answer", name)
        return None
    return {
        "persona_id": persona.get("persona_id") or name,
        "persona_name": name,
        "option_id": option_id,
        "rationale": rationale,
    }


async def run_qna_simulation(
    cohort_data: dict,
    question: str,
    context: str,
    options: list[dict],
    n_personas: int = 5,
) -> dict[str, Any]:
    """Fan out Q&A across `n_personas` from the cohort, aggregate the result."""
    import anthropic

    personas = (cohort_data.get("personas") or [])[: max(1, n_personas)]
    if not personas:
        return {
            "ok": False,
            "error": "cohort has no personas",
            "headline": None,
            "confidence_score": 0.0,
            "distribution": [],
            "persona_responses": [],
        }

    client = anthropic.AsyncAnthropic()
    sem = asyncio.Semaphore(_MAX_CONCURRENCY)

    async def _bounded(p):
        async with sem:
            return await _ask_persona(client, p, question, context, options)

    raw_results = await asyncio.gather(*[_bounded(p) for p in personas])
    persona_responses = [r for r in raw_results if r is not None]

    if not persona_responses:
        return {
            "ok": False,
            "error": "all persona Q&A calls failed",
            "headline": None,
            "confidence_score": 0.0,
            "distribution": [],
            "persona_responses": [],
        }

    counts = Counter(r["option_id"] for r in persona_responses)
    total = sum(counts.values())
    id_to_label = {str(o.get("id")): o.get("name", o.get("label", o.get("id"))) for o in options}
    distribution = [
        {
            "option_id": oid,
            "option_name": id_to_label.get(oid, oid),
            "count": cnt,
            "percentage": round(100.0 * cnt / total, 1),
        }
        for oid, cnt in counts.most_common()
    ]
    top_oid, top_cnt = counts.most_common(1)[0]
    top_label = id_to_label.get(top_oid, top_oid)
    headline = (
        f"{round(100.0 * top_cnt / total)}% of {total} personas chose "
        f"\"{top_label}\""
    )
    confidence = round(top_cnt / total, 3)

    return {
        "ok": True,
        "headline": headline,
        "confidence_score": confidence,
        "strategic_implication": None,
        "distribution": distribution,
        "persona_responses": persona_responses,
    }
