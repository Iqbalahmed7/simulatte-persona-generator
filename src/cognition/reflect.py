"""src/cognition/reflect.py — Higher-order reflection synthesis.

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

from src.cognition.errors import ReflectError
from src.memory.cache import _GLOBAL_CACHE
from src.schema.cognition_outputs import ReflectOutput
from src.schema.persona import Observation, PersonaRecord, Reflection
from src.utils.retry import api_call_with_retry
from src.utils.structured import extract_tool_input, get_text_from_response

logger = logging.getLogger(__name__)

_SONNET_MODEL = "claude-sonnet-4-6"
_HAIKU_MODEL = "claude-haiku-4-5-20251001"

_MIN_OBSERVATIONS = 5
_MAX_OBSERVATIONS = 20

# ---------------------------------------------------------------------------
# Tool-use definition (module-level singleton — constructed once, not per call)
# ---------------------------------------------------------------------------

_REFLECT_TOOL = {
    "name": "emit_reflections",
    "description": "Emit a list of structured reflections synthesised from recent observations.",
    "input_schema": ReflectOutput.model_json_schema(),
}
_REFLECT_TOOL_CHOICE = {"type": "tool", "name": "emit_reflections"}


# ---------------------------------------------------------------------------
# Core memory block (with cache)
# ---------------------------------------------------------------------------


def _core_memory_block(persona: PersonaRecord) -> str:
    """Return the pre-assembled core memory block for a persona.

    Checks _GLOBAL_CACHE first. On a miss, assembles the block and stores it.
    tendency_summary is injected as natural language only (P4).
    """
    cached = _GLOBAL_CACHE.get(persona.persona_id)
    cache_hit = cached is not None
    logger.debug("reflect(): core memory cache %s for %s", "HIT" if cache_hit else "MISS", persona.persona_id)
    if cache_hit:
        return cached  # type: ignore[return-value]

    core = persona.memory.core
    block = (
        f"You know yourself: {core.identity_statement} "
        f"What matters most to you: {', '.join(core.key_values[:3])}. "
        f"{core.tendency_summary}"
    )
    _GLOBAL_CACHE.set(persona.persona_id, block)
    return block


# ---------------------------------------------------------------------------
# Observations block
# ---------------------------------------------------------------------------


def _observations_block(observations: list[Observation]) -> str:
    """Format observations for injection into the prompt."""
    lines = []
    for obs in observations:
        lines.append(f"[{obs.id[:8]}] {obs.content} (importance: {obs.importance})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

_REFLECT_SYSTEM_TEMPLATE = "You are {name}. {core_memory}"

_REFLECT_USER_TEMPLATE = (
    "Here are your recent experiences:\n"
    "{observations_block}\n\n"
    "Step back and think about what patterns you're noticing.\n"
    "What 2-3 insights or realizations are forming?\n"
    "These should be about YOUR evolving views — not summaries of events.\n\n"
    "For each insight, cite which specific experience IDs led to it.\n\n"
    "Reply in JSON:\n"
    "[\n"
    "  {{\n"
    '    "content": "...",\n'
    '    "importance": N,\n'
    '    "emotional_valence": F,\n'
    '    "source_observation_ids": ["id1", "id2"]\n'
    "  }},\n"
    "  ...\n"
    "]"
)


def _build_reflect_messages(
    observations: list[Observation],
    persona: PersonaRecord,
) -> tuple[list[dict], list[dict]]:
    """Return (system_blocks, messages_list) for the reflect call.

    The persona identity block carries cache_control. Its content is identical
    to perceive's cached block, so a warm perceive cache is a reflect cache hit
    for the same persona (for non-India personas without a cultural preamble).
    """
    system_text = _REFLECT_SYSTEM_TEMPLATE.format(
        name=persona.demographic_anchor.name,
        core_memory=_core_memory_block(persona),
    )
    system_blocks = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]
    obs_block = _observations_block(observations)
    user_content = _REFLECT_USER_TEMPLATE.format(observations_block=obs_block)
    messages = [{"role": "user", "content": user_content}]
    return system_blocks, messages


# ---------------------------------------------------------------------------
# Response parsing + validation
# ---------------------------------------------------------------------------


def _parse_reflect_response(raw: str) -> list[dict] | None:
    """Extract the JSON array from the LLM response.

    Returns a list of dicts or None on failure.
    """
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(cleaned[start : end + 1])
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    return None


def _clamp_int(value: int | float, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(round(value))))


def _clamp_float(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _validate_and_build_reflection(item: dict) -> Reflection | None:
    """Attempt to build a validated Reflection from a parsed dict.

    Rules (from spec):
    - source_observation_ids MUST have >= 2 entries (drop silently, log warning)
    - importance clamped to [1, 10]
    - emotional_valence clamped to [-1.0, 1.0]
    - content must be a non-empty string
    """
    if not isinstance(item, dict):
        return None

    content = str(item.get("content", "")).strip()
    if not content:
        logger.warning("reflect(): dropping item with empty content")
        return None

    raw_ids = item.get("source_observation_ids", [])
    if not isinstance(raw_ids, list) or len(raw_ids) < 2:
        logger.warning(
            "reflect(): dropping reflection with fewer than 2 source_observation_ids: %r",
            raw_ids,
        )
        return None

    source_ids = [str(sid) for sid in raw_ids]

    importance_raw = item.get("importance", 5)
    try:
        importance = _clamp_int(importance_raw, 1, 10)
    except (TypeError, ValueError):
        importance = 5

    # Reflection schema does not include emotional_valence directly but we
    # accept it from the LLM and discard (schema only has the listed fields).
    # The spec prompt asks for it for depth of reasoning; it is not stored.

    now = datetime.now(tz=timezone.utc)
    try:
        return Reflection(
            id=str(uuid.uuid4()),
            timestamp=now,
            type="reflection",
            content=content,
            importance=importance,
            source_observation_ids=source_ids,
            last_accessed=now,
        )
    except Exception as exc:
        logger.warning("reflect(): Reflection construction failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


async def reflect(
    observations: list[Observation],
    persona: PersonaRecord,
    llm_client: Any = None,
    model: str | None = None,
) -> list[Reflection]:
    """Synthesise 2-3 insights from recent observations.

    model: override the LLM model (used by SimulationTier routing). Defaults
      to _SONNET_MODEL when None. Pass _HAIKU_MODEL for SIGNAL/VOLUME tiers.

    Makes one Sonnet (or overridden model) call. Returns a list of Reflection objects.
    Each reflection MUST cite >= 2 source_observation_ids.
    Raises ReflectError if fewer than 5 observations provided (insufficient context).
    Raises ReflectError if all reflections fail validation after the call.

    Observations are capped at 20, ordered chronologically (oldest first).
    Core memory is ALWAYS in context.
    tendency_summary is injected as natural language only (P4).
    """
    if len(observations) < _MIN_OBSERVATIONS:
        raise ReflectError(
            f"reflect() requires at least {_MIN_OBSERVATIONS} observations; "
            f"got {len(observations)}."
        )

    # Sort chronologically (oldest first) and cap at 20
    sorted_obs = sorted(observations, key=lambda o: o.timestamp)[:_MAX_OBSERVATIONS]

    _model = model or _SONNET_MODEL
    client = anthropic.AsyncAnthropic()
    system_blocks, messages = _build_reflect_messages(sorted_obs, persona)

    if llm_client is not None and hasattr(llm_client, 'complete'):
        # Test path — llm_client.complete expects a plain string
        system_str = " ".join(b["text"] for b in system_blocks)
        raw_text = await llm_client.complete(
            system=system_str,
            messages=messages,
            max_tokens=1024,
            model=_model,
        )
        parsed = _parse_reflect_response(raw_text)
    else:
        response = await api_call_with_retry(
            client.messages.create,
            model=_model,
            max_tokens=2048,
            system=system_blocks,
            messages=messages,
            tools=[_REFLECT_TOOL],
            tool_choice=_REFLECT_TOOL_CHOICE,
        )
        # Primary path: tool_use block → extract items list
        tool_input = extract_tool_input(response)
        if tool_input is not None:
            # Unwrap the wrapper: {"items": [...]} → list of dicts
            parsed = tool_input.get("items")
            if not isinstance(parsed, list):
                logger.warning(
                    "reflect(): tool_use block missing 'items' list — falling back to text parser"
                )
                parsed = None
        else:
            # Fallback: API returned text instead of tool_use (rare)
            raw_text = get_text_from_response(response)
            parsed = _parse_reflect_response(raw_text)

    if parsed is None:
        raise ReflectError(
            f"reflect() failed to parse a valid JSON list from LLM response."
        )

    reflections: list[Reflection] = []
    for item in parsed:
        reflection = _validate_and_build_reflection(item)
        if reflection is not None:
            reflections.append(reflection)

    if not reflections:
        raise ReflectError(
            "reflect(): all reflections failed validation — no valid reflections produced."
        )

    return reflections
