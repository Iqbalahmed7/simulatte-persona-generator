"""services/benchmark/chat.py — Drive a simulated conversation turn against a persona.

Uses claude-haiku-4-5 (cheap) for conversation turns.
Returns (reply_text, input_tokens, output_tokens).
"""
from __future__ import annotations

import os
from typing import List, Tuple

import anthropic

_HAIKU = "claude-haiku-4-5"
_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


async def chat_turn(
    system_prompt: str,
    history: List[dict],
    user_message: str,
    max_tokens: int = 400,
) -> Tuple[str, int, int]:
    """
    Send one conversation turn.

    Args:
        system_prompt: full persona system prompt
        history: list of {"role": "user"|"assistant", "content": str}
        user_message: the new user message to send
        max_tokens: max tokens for the reply

    Returns:
        (reply_text, input_tokens, output_tokens)
    """
    messages = history + [{"role": "user", "content": user_message}]
    client = _get_client()
    resp = await client.messages.create(
        model=_HAIKU,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages,
    )
    reply = resp.content[0].text if resp.content else ""
    return reply, resp.usage.input_tokens, resp.usage.output_tokens


async def run_conversation(
    system_prompt: str,
    turns: List[str],
    max_tokens_per_turn: int = 400,
) -> Tuple[List[dict], int, int]:
    """
    Drive a full scripted conversation.

    Args:
        system_prompt: persona system prompt
        turns: list of user messages to send in sequence
        max_tokens_per_turn: reply length cap

    Returns:
        (full_history, total_input_tokens, total_output_tokens)
    """
    history: List[dict] = []
    total_in = total_out = 0
    for msg in turns:
        reply, tok_in, tok_out = await chat_turn(
            system_prompt, history, msg, max_tokens_per_turn
        )
        history.append({"role": "user", "content": msg})
        history.append({"role": "assistant", "content": reply})
        total_in += tok_in
        total_out += tok_out
    return history, total_in, total_out


# ── Token cost helpers ────────────────────────────────────────────────────────
# Haiku pricing (as of 2025): $0.25/M input, $1.25/M output
HAIKU_COST_PER_M_IN = 0.25
HAIKU_COST_PER_M_OUT = 1.25


def haiku_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000) * HAIKU_COST_PER_M_IN + \
           (output_tokens / 1_000_000) * HAIKU_COST_PER_M_OUT
