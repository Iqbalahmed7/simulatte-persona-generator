"""src/cognition/perceive.py — Stimulus perception through a persona's psychological lens.

Sprint 4 — Codex (Cognitive Loop)

Spec: §9 (Cognitive Loop), §14A S1, Constitution P1/P2/P4
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import anthropic

from src.cognition.errors import PerceiveError
from src.schema.persona import Observation, PersonaRecord
from src.utils.retry import api_call_with_retry

logger = logging.getLogger(__name__)

_HAIKU_MODEL = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Core memory block
# ---------------------------------------------------------------------------


def _core_memory_block(persona: PersonaRecord) -> str:
    """Assemble the core memory block injected into the system prompt.

    tendency_summary is injected as natural language only — never as
    numerical weights (Constitution P4).
    """
    core = persona.memory.core
    return (
        f"You know yourself: {core.identity_statement} "
        f"What matters most to you: {', '.join(core.key_values[:3])}. "
        f"{core.tendency_summary}"
    )


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

_PERCEIVE_SYSTEM_TEMPLATE = "You are {name}. {core_memory}"

_PERCEIVE_USER_TEMPLATE = (
    "You just encountered: {stimulus}\n\n"
    "Given who you are, your values, and your past experiences:\n"
    "1. What stands out to you about this?\n"
    "2. How important is this to you? (1-10)\n"
    "3. How does it make you feel? (-1.0 to 1.0, negative to positive)\n\n"
    "Respond in first person, in character.\n"
    'Reply in JSON: {{"content": "...", "importance": N, "emotional_valence": F}}'
)

_PERCEIVE_RETRY_USER_TEMPLATE = (
    "You just encountered: {stimulus}\n\n"
    "Given who you are, your values, and your past experiences:\n"
    "1. What stands out to you about this?\n"
    "2. How important is this to you? (1-10)\n"
    "3. How does it make you feel? (-1.0 to 1.0, negative to positive)\n\n"
    "Respond in first person, in character.\n"
    "IMPORTANT: You MUST reply with valid JSON only — no prose, no markdown fences.\n"
    'Reply in JSON: {{"content": "...", "importance": N, "emotional_valence": F}}'
)


def _build_perceive_messages(
    stimulus: str,
    persona: PersonaRecord,
    retry: bool = False,
) -> tuple[str, list[dict]]:
    """Return (system_prompt, messages_list) for the perceive call."""
    system_prompt = _PERCEIVE_SYSTEM_TEMPLATE.format(
        name=persona.demographic_anchor.name,
        core_memory=_core_memory_block(persona),
    )
    user_template = _PERCEIVE_RETRY_USER_TEMPLATE if retry else _PERCEIVE_USER_TEMPLATE
    user_content = user_template.format(stimulus=stimulus)
    messages = [{"role": "user", "content": user_content}]
    return system_prompt, messages


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_perceive_response(raw: str) -> dict | None:
    """Extract and validate the JSON object from the LLM response.

    Returns a dict with keys 'content', 'importance', 'emotional_valence',
    or None on failure.
    """
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    # Try direct parse
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # Try to extract JSON object substring
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(cleaned[start : end + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    return None


def _clamp_int(value: int | float, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(round(value))))


def _clamp_float(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _build_observation(
    parsed: dict,
    stimulus_id: str | None,
) -> Observation:
    """Construct an Observation from a validated parse result."""
    content = str(parsed.get("content", "")).strip()
    importance = _clamp_int(parsed.get("importance", 5), 1, 10)
    emotional_valence = _clamp_float(parsed.get("emotional_valence", 0.0), -1.0, 1.0)

    now = datetime.now(tz=timezone.utc)
    return Observation(
        id=str(uuid.uuid4()),
        timestamp=now,
        type="observation",
        content=content,
        importance=importance,
        emotional_valence=emotional_valence,
        source_stimulus_id=stimulus_id,
        last_accessed=now,
    )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


async def perceive(
    stimulus: str,
    persona: PersonaRecord,
    stimulus_id: str | None = None,
    llm_client: Any = None,
) -> Observation:
    """Process a stimulus through the persona's psychological lens.

    Makes one Haiku call. Returns an Observation with:
    - content: first-person description of what stood out
    - importance: int 1-10
    - emotional_valence: float -1.0 to 1.0
    - source_stimulus_id: stimulus_id if provided
    - type: "observation"
    - id: uuid4
    - timestamp: now (UTC)
    - last_accessed: now (UTC)

    Core memory is ALWAYS in context (§14A S11).
    tendency_summary is injected as natural language only (P4).
    Retries once on JSON parse failure; raises PerceiveError on second failure.
    """
    client = anthropic.AsyncAnthropic()

    # Attempt 1
    system_prompt, messages = _build_perceive_messages(stimulus, persona, retry=False)
    if llm_client is not None and hasattr(llm_client, 'complete'):
        raw_text = await llm_client.complete(
            system=system_prompt,
            messages=messages,
            max_tokens=512,
            model=_HAIKU_MODEL,
        )
    else:
        response = await api_call_with_retry(
            client.messages.create,
            model=_HAIKU_MODEL,
            max_tokens=512,
            system=system_prompt,
            messages=messages,
        )
        raw_text = response.content[0].text
    parsed = _parse_perceive_response(raw_text)

    if parsed is None:
        logger.warning("perceive(): JSON parse failed on attempt 1 — retrying with stricter prompt")
        # Attempt 2 — stricter prompt
        system_prompt, messages = _build_perceive_messages(stimulus, persona, retry=True)
        if llm_client is not None and hasattr(llm_client, 'complete'):
            raw_text = await llm_client.complete(
                system=system_prompt,
                messages=messages,
                max_tokens=512,
                model=_HAIKU_MODEL,
            )
        else:
            response = await api_call_with_retry(
                client.messages.create,
                model=_HAIKU_MODEL,
                max_tokens=512,
                system=system_prompt,
                messages=messages,
            )
            raw_text = response.content[0].text
        parsed = _parse_perceive_response(raw_text)

        if parsed is None:
            raise PerceiveError(
                f"perceive() failed to parse a valid JSON response after 2 attempts. "
                f"Last raw response: {raw_text!r}"
            )

    return _build_observation(parsed, stimulus_id)
