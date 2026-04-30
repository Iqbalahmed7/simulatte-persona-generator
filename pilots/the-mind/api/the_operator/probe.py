"""the_operator/probe.py — probe session management and streaming response.

Two-call structure per turn:
  1. In-character Twin reply (collected via streaming SDK)
  2. Out-of-character Operator note (non-streaming, short)

The router is responsible for SSE emission. probe.py provides coroutines.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import anthropic

from the_operator.config import (
    PROBE_IDLE_MINUTES,
    PROBE_NOTE_MAX_TOKENS,
    PROBE_REPLY_MAX_TOKENS,
    PROBE_MODEL,
)
from the_operator.prompts import (
    PROBE_NOTE_SYSTEM,
    PROBE_NOTE_USER,
    PROBE_SYSTEM,
)

logger = logging.getLogger("the_operator")


def build_probe_system(full_name: str, title: str | None, company: str | None, profile: dict) -> str:
    """Build the system prompt for in-character Twin responses."""
    first_name = full_name.split()[0]
    return PROBE_SYSTEM.format(
        full_name=full_name,
        first_name=first_name,
        title=title or "Executive",
        company=company or "their company",
        profile_json=json.dumps(profile, indent=2)[:6_000],
    )


async def collect_twin_reply(
    full_name: str,
    title: str | None,
    company: str | None,
    profile: dict,
    conversation_history: list[dict],
    user_message: str,
    client: anthropic.AsyncAnthropic,
    token_callback=None,
) -> tuple[str, int, int]:
    """Collect the full Twin in-character reply.

    If token_callback is provided, calls it with each text chunk (for SSE forwarding).
    Returns (full_text, tokens_in, tokens_out).
    """
    system = build_probe_system(full_name, title, company, profile)
    messages = _history_to_messages(conversation_history) + [
        {"role": "user", "content": user_message}
    ]

    full_text = ""

    async with client.messages.stream(
        model=PROBE_MODEL,
        system=system,
        messages=messages,
        max_tokens=PROBE_REPLY_MAX_TOKENS,
    ) as stream:
        async for text in stream.text_stream:
            full_text += text
            if token_callback:
                await token_callback(text)

        final_msg = await stream.get_final_message()

    tokens_in  = final_msg.usage.input_tokens
    tokens_out = final_msg.usage.output_tokens

    logger.info(
        "[operator] probe_reply name=%s tokens_in=%d tokens_out=%d",
        full_name, tokens_in, tokens_out,
    )
    return full_text, tokens_in, tokens_out


async def generate_operator_note(
    full_name: str,
    profile: dict,
    user_message: str,
    twin_response: str,
    client: anthropic.AsyncAnthropic,
) -> str:
    """Generate the out-of-character analyst note (non-streaming, 2-4 sentences)."""
    profile_summary = _profile_summary(profile)

    response = await client.messages.create(
        model=PROBE_MODEL,
        system=PROBE_NOTE_SYSTEM.format(full_name=full_name),
        messages=[{
            "role": "user",
            "content": PROBE_NOTE_USER.format(
                user_message=user_message,
                full_name=full_name,
                twin_response=twin_response,
                profile_summary=profile_summary,
            ),
        }],
        max_tokens=PROBE_NOTE_MAX_TOKENS,
    )

    return "".join(b.text for b in response.content if hasattr(b, "text"))


def session_is_idle(last_message_at: datetime) -> bool:
    """Return True if the session has been idle past PROBE_IDLE_MINUTES."""
    age_minutes = (datetime.now(timezone.utc) - last_message_at).total_seconds() / 60
    return age_minutes > PROBE_IDLE_MINUTES


def _history_to_messages(history: list[dict]) -> list[dict]:
    """Convert stored message rows to Anthropic messages format.

    Excludes operator_note rows — meta-commentary, not part of the Twin conversation.
    Maps 'twin' → 'assistant'.
    """
    messages = []
    for msg in history:
        role = msg.get("role", "")
        if role == "operator_note":
            continue
        messages.append({
            "role": "assistant" if role == "twin" else "user",
            "content": msg["content"],
        })
    return messages


def _profile_summary(profile: dict) -> str:
    da = profile.get("decision_architecture", {})
    pr = profile.get("professional_register", {})
    return (
        f"First filter: {da.get('first_filter', 'unknown')}\n"
        f"Trust signal: {da.get('trust_signal', 'unknown')}\n"
        f"Rejection trigger: {da.get('rejection_trigger', 'unknown')}\n"
        f"Tone they respond to: {pr.get('tone', 'unknown')}\n"
        f"Vocabulary avoided: {', '.join(pr.get('vocabulary_avoided', [])[:3])}"
    )
