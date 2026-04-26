"""src/utils/structured.py — Shared helpers for Anthropic tool-use response extraction.

BRIEF-013: Structured Outputs Migration

Provides extract_tool_input() which pulls the tool_use block from a response
and returns its .input dict. Falls back gracefully when no tool_use block is
present so the text-parser fallback path in each cognition module can run.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def extract_tool_input(response: Any) -> dict | None:
    """Return the .input dict from the first tool_use block in response.content.

    Returns None if no tool_use block is present (triggering text fallback).
    Logs a warning on fallback so the caller can track frequency.
    """
    content_blocks = getattr(response, "content", [])
    tool_block = next(
        (b for b in content_blocks if getattr(b, "type", None) == "tool_use"),
        None,
    )
    if tool_block is not None:
        return tool_block.input  # already a dict — no JSON parsing needed

    # No tool_use block — unexpected; caller will fall back to text parser
    text_block = next(
        (b for b in content_blocks if getattr(b, "type", None) == "text"),
        None,
    )
    text_preview = getattr(text_block, "text", "")[:120] if text_block else "<empty>"
    logger.warning(
        "extract_tool_input(): no tool_use block in response — "
        "falling back to text parser. Text preview: %r",
        text_preview,
    )
    return None


def get_text_from_response(response: Any) -> str:
    """Return the text from the first text block in response.content.

    Used by the fallback path when extract_tool_input() returns None.
    """
    content_blocks = getattr(response, "content", [])
    text_block = next(
        (b for b in content_blocks if getattr(b, "type", None) == "text"),
        None,
    )
    return getattr(text_block, "text", "") if text_block else ""
