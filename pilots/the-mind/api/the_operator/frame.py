"""the_operator/frame.py — frame scoring: run a message through the Twin's decision filter."""
from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from the_operator.config import FRAME_MAX_TOKENS, FRAME_MODEL
from the_operator.errors import synthesis_failed
from the_operator.prompts import FRAME_SYSTEM, FRAME_USER

logger = logging.getLogger("the_operator")

# ── Frame score output schema (forced tool-use) ───────────────────────────

_FRAME_SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "annotations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "segment":  {"type": "string"},
                    "score":    {"type": "number"},
                    "reads_as": {"type": "string"},
                    "risk":     {"oneOf": [{"type": "string"}, {"type": "null"}]},
                },
                "required": ["segment", "score", "reads_as"],
            },
        },
        "overall_score":            {"type": "number"},
        "reply_probability":        {"type": "string", "enum": ["high", "medium", "low"]},
        "weakest_point":            {
            "type": "object",
            "properties": {"segment": {"type": "string"}, "issue": {"type": "string"}},
            "required": ["segment", "issue"],
        },
        "strongest_point":          {
            "type": "object",
            "properties": {"segment": {"type": "string"}, "reason": {"type": "string"}},
            "required": ["segment", "reason"],
        },
        "single_change_to_improve": {"type": "string"},
    },
    "required": [
        "annotations", "overall_score", "reply_probability",
        "weakest_point", "strongest_point", "single_change_to_improve",
    ],
}

_SUBMIT_TOOL = {
    "name": "submit_frame_score",
    "description": "Submit the completed frame score analysis as structured JSON.",
    "input_schema": _FRAME_SCORE_SCHEMA,
}


async def score_frame(
    full_name: str,
    title: str | None,
    company: str | None,
    profile: dict,
    message: str,
    client: anthropic.AsyncAnthropic,
) -> dict[str, Any]:
    """Score a message against the Twin's decision filter. Returns parsed score dict."""
    system = FRAME_SYSTEM.format(
        full_name=full_name,
        title=title or "Executive",
        company=company or "their company",
        profile_json=json.dumps(profile, indent=2)[:6_000],
    )
    user_msg = FRAME_USER.format(full_name=full_name, message=message)

    for attempt in range(2):
        try:
            response = await client.messages.create(
                model=FRAME_MODEL,
                system=system,
                messages=[{"role": "user", "content": user_msg}],
                tools=[_SUBMIT_TOOL],
                tool_choice={"type": "tool", "name": "submit_frame_score"},
                max_tokens=FRAME_MAX_TOKENS,
            )

            logger.info(
                "[operator] frame_score name=%s tokens_in=%d tokens_out=%d",
                full_name,
                response.usage.input_tokens,
                response.usage.output_tokens,
            )

            for block in response.content:
                if hasattr(block, "type") and block.type == "tool_use":
                    result = block.input
                    # Clamp reply_probability from score if model ignores enum
                    score = result.get("overall_score", 0)
                    if "reply_probability" not in result or result["reply_probability"] not in ("high", "medium", "low"):
                        result["reply_probability"] = (
                            "high" if score >= 8.5 else "medium" if score >= 6.5 else "low"
                        )
                    return result

            raise ValueError("No tool_use block in frame response")

        except Exception as exc:
            logger.warning("[operator] frame score attempt %d failed: %s", attempt + 1, exc)
            if attempt == 1:
                raise synthesis_failed()

    raise synthesis_failed()
