"""the_operator/recon.py — 3-pass web reconnaissance pipeline.

Uses Anthropic's web_search tool for all searches.
Outputs a structured ReconResult dict consumed by synthesis.py.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import AsyncIterator

import anthropic

from the_operator.config import (
    RECON_CUMULATIVE_INPUT_CEILING,
    RECON_MAX_TOKENS_PASS,
    RECON_MODEL,
)
from the_operator.errors import recon_budget_exceeded, recon_failed, recon_unavailable
from the_operator.prompts import (
    RECON_EXTRACT_SYSTEM,
    RECON_EXTRACT_USER,
    RECON_PASS_1_USER,
    RECON_PASS_2_USER,
    RECON_PASS_3_USER,
    RECON_SYSTEM,
)
from the_operator.storage import read_recon_cache, write_recon_cache

logger = logging.getLogger("the_operator")

# web_search tool definition (Anthropic server-side built-in).
# `max_uses` lets the server run up to N searches inside a single API call —
# results come back integrated into the assistant response. This is NOT a
# client-side tool: do not echo tool_results back, do not loop on tool_use.
_WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 5,
}


async def run_recon(
    twin_id: str,
    full_name: str,
    company: str | None,
    title: str | None,
    client: anthropic.AsyncAnthropic,
    force: bool = False,
    progress_callback: AsyncIterator | None = None,
) -> dict:
    """Run the full 3-pass reconnaissance pipeline.

    Returns the structured recon intermediate dict.
    Raises HTTPException on hard failures.
    Uses disk cache if available and within TTL (unless force=True).
    """
    # Check disk cache first
    cached = read_recon_cache(twin_id, force=force)
    if cached:
        logger.info("[operator] recon cache hit for twin=%s", twin_id)
        return cached

    company_str = company or "their company"
    title_str   = title   or "their role"

    # Infer industry from company/title for Pass 2 queries
    industry_hint = f"{company_str} industry"

    pass_queries = {
        1: RECON_PASS_1_USER.format(
            full_name=full_name, company=company_str, title=title_str
        ),
        2: RECON_PASS_2_USER.format(
            full_name=full_name, industry=industry_hint
        ),
        3: RECON_PASS_3_USER.format(
            full_name=full_name, company=company_str, industry=industry_hint
        ),
    }

    all_findings: list[str] = []
    cumulative_input = 0
    total_tool_turns = 0

    # Emit a single progress event — all 3 passes run concurrently
    if progress_callback:
        await _emit(progress_callback, "Searching public sources (3 passes in parallel)…")

    # Run all 3 passes simultaneously — they cover independent facets so order doesn't matter
    raw_results = await asyncio.gather(
        _run_search_pass(1, pass_queries[1], client),
        _run_search_pass(2, pass_queries[2], client),
        _run_search_pass(3, pass_queries[3], client),
        return_exceptions=True,
    )

    for pass_num, result in enumerate(raw_results, start=1):
        if isinstance(result, BaseException):
            if isinstance(result, anthropic.APIStatusError) and result.status_code >= 500:
                logger.warning("[operator] recon pass %d server error: %s", pass_num, result)
                raise recon_unavailable()
            raise result

        result_text, tokens_in, turns = result
        cumulative_input += tokens_in
        total_tool_turns += turns
        all_findings.append(f"=== PASS {pass_num} ===\n{result_text}")

        logger.info(
            "[operator] recon pass %d: tokens_in=%d total_turns=%d cumulative=%d",
            pass_num, tokens_in, turns, cumulative_input,
        )

    if cumulative_input > RECON_CUMULATIVE_INPUT_CEILING:
        logger.warning("[operator] recon budget exceeded for twin=%s", twin_id)
        raise recon_budget_exceeded()

    # Extract structured intermediate
    if progress_callback:
        await _emit(progress_callback, "Extracting intelligence signals…")

    combined = "\n\n".join(all_findings)
    structured = await _extract_structured(combined, client)

    # Check if we got any useful signal
    if structured.get("sources_count", 0) == 0 and not structured.get("extracted_facts", {}).get("industry_vertical"):
        structured["confidence_signal"] = "low"
        logger.info("[operator] recon returned low confidence for twin=%s", twin_id)
        # Don't raise — let synthesis proceed with gaps noted

    # Write to disk cache
    write_recon_cache(twin_id, structured)

    logger.info(
        "[operator] recon complete twin=%s sources=%d confidence=%s",
        twin_id,
        structured.get("sources_count", 0),
        structured.get("confidence_signal", "unknown"),
    )

    return structured


async def _run_search_pass(
    pass_num: int,
    user_message: str,
    client: anthropic.AsyncAnthropic,
) -> tuple[str, int, int]:
    """Run one recon pass with the server-side web_search tool.

    Critical: web_search_20250305 is a SERVER-SIDE tool. The model issues
    server_tool_use blocks, Anthropic runs the searches internally (up to
    `max_uses` per call), and results come back as web_search_tool_result
    blocks within the same assistant response. There is no client-side
    handshake — we do NOT echo tool_results, we do NOT loop on tool_use.

    A single messages.create() call performs the full search workflow.

    Returns (text, tokens_in, turns).
    """
    max_cfg = RECON_MAX_TOKENS_PASS[pass_num]

    response = await client.messages.create(
        model=RECON_MODEL,
        system=RECON_SYSTEM,
        messages=[{"role": "user", "content": user_message}],
        tools=[_WEB_SEARCH_TOOL],
        max_tokens=max_cfg["output"],
        timeout=180,  # server-side searches can be slow; cap at 3 min per pass
    )

    text_parts = [b.text for b in response.content if hasattr(b, "text")]
    return "\n".join(text_parts), response.usage.input_tokens, 1


async def _extract_structured(raw_findings: str, client: anthropic.AsyncAnthropic) -> dict:
    """Parse raw recon text into the structured intermediate dict."""
    try:
        response = await client.messages.create(
            model=RECON_MODEL,
            system=RECON_EXTRACT_SYSTEM,
            messages=[{
                "role": "user",
                "content": RECON_EXTRACT_USER.format(raw_findings=raw_findings[:40_000]),
            }],
            max_tokens=2000,
        )
        text = "".join(b.text for b in response.content if hasattr(b, "text"))
        # Strip any accidental markdown fences
        text = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(text)
    except Exception as exc:
        logger.warning("[operator] recon extraction parse failed: %s", exc)
        # Return a minimal valid structure
        return {
            "raw_findings": [{"source_url": None, "snippet": raw_findings[:500], "credibility": "low"}],
            "extracted_facts": {
                "current_role_start": None,
                "prior_companies": [],
                "education": [],
                "public_quotes": [],
                "podcast_appearances": [],
                "conference_talks": [],
                "published_writing": [],
                "industry_vertical": "unknown",
                "company_stage": "unknown",
                "career_pattern": "unknown",
            },
            "sources_count": 0,
            "confidence_signal": "low",
        }


async def _emit(callback, message: str) -> None:
    """Fire progress callback if provided (used by SSE streaming endpoints)."""
    try:
        await callback({"stage": "recon", "message": message})
    except Exception:
        pass
