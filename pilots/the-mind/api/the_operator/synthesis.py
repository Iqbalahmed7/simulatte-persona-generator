"""the_operator/synthesis.py — Twin profile synthesis using forced tool-use output.

Takes the structured recon intermediate + optional enrichment text and produces
the final synthesised Twin profile JSON via submit_twin_profile tool call.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from the_operator.config import SYNTHESIS_MAX_TOKENS, SYNTHESIS_MODEL
from the_operator.errors import synthesis_failed
from the_operator.prompts import (
    SYNTHESIS_ENRICHMENT_SECTION,
    SYNTHESIS_SYSTEM,
    SYNTHESIS_USER,
)

logger = logging.getLogger("the_operator")

# ── Twin profile JSON schema (forced tool output) ─────────────────────────

_PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "identity_snapshot": {"type": "string"},
        "decision_architecture": {
            "type": "object",
            "properties": {
                "first_filter":           {"type": "string"},
                "trust_signal":           {"type": "string"},
                "rejection_trigger":      {"type": "string"},
                "engagement_threshold":   {"type": "string"},
            },
            "required": ["first_filter", "trust_signal", "rejection_trigger", "engagement_threshold"],
        },
        "professional_register": {
            "type": "object",
            "properties": {
                "vocabulary_used":    {"type": "array", "items": {"type": "string"}},
                "vocabulary_avoided": {"type": "array", "items": {"type": "string"}},
                "tone":               {"type": "string"},
                "already_knows":      {"type": "array", "items": {"type": "string"}},
            },
            "required": ["vocabulary_used", "vocabulary_avoided", "tone", "already_knows"],
        },
        "personal_signal_layer": {
            "oneOf": [{"type": "null"}, {"type": "string"}]
        },
        "trigger_map": {
            "type": "object",
            "properties": {
                "leans_in":   {"type": "array", "items": {"type": "string"}},
                "disengages": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["leans_in", "disengages"],
        },
        "objection_anticipator": {
            "type": "object",
            "properties": {
                "first_contact": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "objection": {"type": "string"},
                            "preempt":   {"type": "string"},
                        },
                        "required": ["objection", "preempt"],
                    },
                },
                "first_call": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "objection": {"type": "string"},
                            "response":  {"type": "string"},
                        },
                        "required": ["objection", "response"],
                    },
                },
            },
            "required": ["first_contact", "first_call"],
        },
        "message_frame_recommendations": {
            "type": "object",
            "properties": {
                "lead_with":           {"type": "string"},
                "open_format":         {"type": "string"},
                "subject_register":    {"type": "string"},
                "optimal_length_words": {"type": "integer"},
                "withhold_for_call":   {"type": "string"},
            },
            "required": ["lead_with", "open_format", "subject_register", "optimal_length_words", "withhold_for_call"],
        },
        "call_prep": {
            "type": "object",
            "properties": {
                "have_ready":   {"type": "array", "items": {"type": "string"}},
                "do_not_say":   {"type": "array", "items": {"type": "string"}},
            },
            "required": ["have_ready", "do_not_say"],
        },
        "confidence":       {"type": "string", "enum": ["high", "medium", "low"]},
        "gaps":             {"type": "string"},
    },
    "required": [
        "identity_snapshot", "decision_architecture", "professional_register",
        "trigger_map", "objection_anticipator", "message_frame_recommendations",
        "call_prep", "confidence", "gaps",
    ],
}

_SUBMIT_TOOL = {
    "name": "submit_twin_profile",
    "description": "Submit the completed Twin profile as structured JSON.",
    "input_schema": _PROFILE_SCHEMA,
}


async def synthesise_twin(
    full_name: str,
    company: str | None,
    title: str | None,
    recon_data: dict,
    enrichment_text: str | None,
    client: anthropic.AsyncAnthropic,
) -> dict[str, Any]:
    """Run synthesis LLM call. Returns parsed profile dict.

    Attempts twice on JSON failure; raises synthesis_failed() on second miss.
    """
    company_str = company or "their company"
    title_str   = title   or "their role"

    enrichment_section = (
        SYNTHESIS_ENRICHMENT_SECTION.format(enrichment_text=enrichment_text)
        if enrichment_text
        else ""
    )

    user_msg = SYNTHESIS_USER.format(
        full_name=full_name,
        title=title_str,
        company=company_str,
        recon_json=json.dumps(recon_data, indent=2)[:12_000],
        enrichment_section=enrichment_section,
    )

    for attempt in range(2):
        try:
            response = await client.messages.create(
                model=SYNTHESIS_MODEL,
                system=SYNTHESIS_SYSTEM,
                messages=[{"role": "user", "content": user_msg}],
                tools=[_SUBMIT_TOOL],
                tool_choice={"type": "tool", "name": "submit_twin_profile"},
                max_tokens=SYNTHESIS_MAX_TOKENS,
            )

            logger.info(
                "[operator] synthesis tokens_in=%d tokens_out=%d attempt=%d",
                response.usage.input_tokens,
                response.usage.output_tokens,
                attempt + 1,
            )

            # Extract tool_use block
            for block in response.content:
                if hasattr(block, "type") and block.type == "tool_use":
                    return block.input   # already parsed dict

            raise ValueError("No tool_use block in response")

        except Exception as exc:
            logger.warning("[operator] synthesis attempt %d failed: %s", attempt + 1, exc)
            if attempt == 1:
                raise synthesis_failed()

    raise synthesis_failed()  # unreachable but satisfies type checker
