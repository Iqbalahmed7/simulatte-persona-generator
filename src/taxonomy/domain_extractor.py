"""src/taxonomy/domain_extractor.py

MiroFish-style domain attribute extraction.

Takes a raw signal corpus (reviews, forum posts, transcripts, ICP spec)
and uses an LLM to extract the domain-specific attribute set (Layer 2).

Spec ref: Master Spec §6 — "Seed-document-to-ontology via LLM: Adopt the principle,
modify the scope. Used for domain taxonomy extension (Layer 2) only."
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import anthropic

from src.utils.retry import api_call_with_retry

if TYPE_CHECKING:
    from src.schema.icp_spec import ICPSpec

logger = logging.getLogger(__name__)

_SONNET_MODEL = "claude-sonnet-4-6"
_SIGNALS_IN_PROMPT = 100
_MIN_CORPUS_SIZE = 200


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------


@dataclass
class DomainAttribute:
    name: str               # snake_case — e.g. "pediatrician_trust"
    description: str        # 1-2 sentences defining what this attribute captures
    valid_range: str        # "0.0-1.0" | "low|medium|high" | "categorical: [a, b, c]"
    example_values: list[str] = field(default_factory=list)  # 3 concrete examples from corpus
    signal_count: int = 0   # how many signals from the corpus mention this attribute
    extraction_source: str = "corpus"  # "corpus" | "icp_anchor" | "template_fallback"


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """
You are analyzing consumer research data for a domain taxonomy extraction task.

Domain: {domain}
Business problem: {business_problem}

Here is a sample of {signal_count} consumer signals from this domain:
{signals_block}

{anchor_block}

Your task: Identify up to {max_attributes} distinct PSYCHOLOGICAL and BEHAVIOURAL attributes
that differentiate how people in this domain make decisions. Focus on attributes that:
- Directly affect purchase, usage, or loyalty decisions
- Vary meaningfully across consumers (not universal)
- Can be scored on a 0.0-1.0 scale or as a categorical value

DO NOT include demographic attributes (age, income, location).
DO NOT include product features.

Return a JSON array only (no other text):
[
  {{"name": "snake_case_name", "description": "1-2 sentences", "valid_range": "0.0-1.0 OR low|medium|high OR categorical: [...]", "example_values": ["low example", "mid example", "high example"], "signal_count": <int>}},
  ...
]
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_signals_block(corpus: list[str]) -> str:
    """Format the first _SIGNALS_IN_PROMPT signals as a numbered list."""
    signals = corpus[:_SIGNALS_IN_PROMPT]
    return "\n".join(f"{i + 1}. {s}" for i, s in enumerate(signals))


def _build_anchor_block(icp_spec: "ICPSpec | None") -> str:
    """If icp_spec has anchor_traits, build a 'must-include' instruction block."""
    if icp_spec is None or not icp_spec.anchor_traits:
        return ""
    traits = ", ".join(icp_spec.anchor_traits)
    return (
        f"MUST-INCLUDE attributes (from ICP Spec anchor traits — always include these "
        f"in your output regardless of signal frequency): {traits}"
    )


def _build_prompt(
    corpus: list[str],
    icp_spec: "ICPSpec | None",
    max_attributes: int,
) -> str:
    """Assemble the full extraction prompt."""
    domain = icp_spec.domain if icp_spec else "Unknown domain"
    business_problem = icp_spec.business_problem if icp_spec else "General consumer research"

    signals_used = corpus[:_SIGNALS_IN_PROMPT]
    signals_block = _build_signals_block(corpus)
    anchor_block = _build_anchor_block(icp_spec)

    return _EXTRACTION_PROMPT.format(
        domain=domain,
        business_problem=business_problem,
        signal_count=len(signals_used),
        signals_block=signals_block,
        anchor_block=anchor_block,
        max_attributes=max_attributes,
    )


def _parse_json_array(raw: str) -> list[dict] | None:
    """Extract a JSON array from an LLM response string.

    Strips markdown code fences if present, then tries to parse the full string.
    Falls back to bracket-boundary extraction if direct parse fails.
    Returns a list of dicts, or None if parsing fails entirely.
    """
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Bracket boundary extraction
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


def _anchor_trait_names(icp_spec: "ICPSpec | None") -> set[str]:
    """Return the set of anchor trait names (lowercased) from the ICP spec."""
    if icp_spec is None or not icp_spec.anchor_traits:
        return set()
    return {t.lower().strip() for t in icp_spec.anchor_traits}


def _assemble_attributes(
    parsed: list[dict],
    icp_spec: "ICPSpec | None",
) -> list[DomainAttribute]:
    """Convert a list of raw parsed dicts into DomainAttribute objects.

    Sets extraction_source to "icp_anchor" if name matches an anchor trait,
    otherwise "corpus".
    """
    anchors = _anchor_trait_names(icp_spec)
    results: list[DomainAttribute] = []

    for item in parsed:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue

        source = "icp_anchor" if name.lower() in anchors else "corpus"

        example_values_raw = item.get("example_values", [])
        example_values = (
            [str(v) for v in example_values_raw]
            if isinstance(example_values_raw, list)
            else []
        )

        signal_count_raw = item.get("signal_count", 0)
        try:
            signal_count = int(signal_count_raw)
        except (TypeError, ValueError):
            signal_count = 0

        results.append(
            DomainAttribute(
                name=name,
                description=str(item.get("description", "")).strip(),
                valid_range=str(item.get("valid_range", "0.0-1.0")).strip(),
                example_values=example_values,
                signal_count=signal_count,
                extraction_source=source,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Core async function
# ---------------------------------------------------------------------------


async def extract_domain_attributes(
    corpus: list[str],
    icp_spec: "ICPSpec | None" = None,
    llm_client: Any = None,
    max_attributes: int = 80,
) -> list[DomainAttribute]:
    """Extract domain-specific psychological/behavioural attributes from a signal corpus.

    Args:
        corpus: List of raw consumer signal strings (reviews, transcripts, posts).
        icp_spec: Optional ICPSpec — provides domain, business_problem, anchor_traits.
        llm_client: Optional test double. Must have a `complete()` async method
            matching the signature used in decide.py. If None, uses AsyncAnthropic.
        max_attributes: Maximum number of attributes to request from the LLM.

    Returns:
        List of DomainAttribute objects. Returns [] if corpus is too small or if
        JSON parsing fails on both attempts.
    """
    if len(corpus) < _MIN_CORPUS_SIZE:
        logger.warning(
            "extract_domain_attributes(): corpus has %d signals (minimum %d). "
            "Skipping LLM extraction — returning empty list. Caller should apply "
            "template_fallback.",
            len(corpus),
            _MIN_CORPUS_SIZE,
        )
        return []

    prompt = _build_prompt(corpus, icp_spec, max_attributes)
    messages = [{"role": "user", "content": prompt}]

    async def _call_llm() -> str:
        if llm_client is not None and hasattr(llm_client, "complete"):
            return await llm_client.complete(
                messages=messages,
                max_tokens=4096,
                model=_SONNET_MODEL,
            )
        client = anthropic.AsyncAnthropic()
        response = await api_call_with_retry(
            client.messages.create,
            model=_SONNET_MODEL,
            max_tokens=4096,
            messages=messages,
        )
        return response.content[0].text

    # Attempt 1
    raw_text = await _call_llm()
    parsed = _parse_json_array(raw_text)

    if parsed is None:
        logger.warning(
            "extract_domain_attributes(): JSON parse failed on attempt 1 — retrying"
        )
        # Attempt 2
        raw_text = await _call_llm()
        parsed = _parse_json_array(raw_text)

    if parsed is None:
        logger.error(
            "extract_domain_attributes(): JSON parse failed on both attempts — "
            "returning empty list"
        )
        return []

    attributes = _assemble_attributes(parsed, icp_spec)
    logger.info(
        "extract_domain_attributes(): extracted %d attributes (%d from icp_anchor, "
        "%d from corpus)",
        len(attributes),
        sum(1 for a in attributes if a.extraction_source == "icp_anchor"),
        sum(1 for a in attributes if a.extraction_source == "corpus"),
    )
    return attributes


# ---------------------------------------------------------------------------
# Sync wrapper
# ---------------------------------------------------------------------------


def extract_domain_attributes_sync(
    corpus: list[str],
    icp_spec: "ICPSpec | None" = None,
    llm_client: Any = None,
    max_attributes: int = 80,
) -> list[DomainAttribute]:
    """Synchronous wrapper around extract_domain_attributes() for non-async callers.

    Uses asyncio.run() — do not call from within an already-running event loop.
    """
    return asyncio.run(
        extract_domain_attributes(corpus, icp_spec, llm_client, max_attributes)
    )
