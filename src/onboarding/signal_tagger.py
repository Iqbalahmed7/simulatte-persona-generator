"""src/onboarding/signal_tagger.py

Batch Haiku signal tagging for client review data.
Tags each consumer signal with one of 6 categories derived from Master Spec §7
trigger verbs.

LLM model: claude-haiku-4-5-20251001 (high volume, low cost).
Spec ref: Sprint 27, Master Spec §7 (trigger verb taxonomy).
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import anthropic

from src.utils.retry import api_call_with_retry

logger = logging.getLogger(__name__)

_HAIKU_MODEL = "claude-haiku-4-5-20251001"

# ---------------------------------------------------------------------------
# Signal taxonomy
# ---------------------------------------------------------------------------

SIGNAL_TAGS = [
    "purchase_trigger",
    "rejection",
    "switching",
    "trust_citation",
    "price_mention",
    "neutral",
]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TaggedSignal:
    text: str
    tag: str          # one of SIGNAL_TAGS
    confidence: float  # 0.0–1.0


@dataclass
class TaggedCorpus:
    signals: list[TaggedSignal]
    tag_distribution: dict[str, int]   # {tag: count}
    n_decision_signals: int            # count of non-neutral signals


# ---------------------------------------------------------------------------
# Prompt constants
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a consumer research signal classifier. "
    "Classify each signal into exactly one category."
)

_USER_TEMPLATE = (
    "Classify each of the following {n} consumer signals into exactly one of these categories:\n"
    "- purchase_trigger: what prompted a purchase\n"
    "- rejection: why a product was rejected or avoided\n"
    "- switching: switching from one product/brand to another\n"
    "- trust_citation: citing a trusted source (doctor, friend, review, certification)\n"
    "- price_mention: mentioning price, cost, value, discount, or affordability\n"
    "- neutral: does not clearly fit any of the above\n"
    "\n"
    "Signals:\n"
    "{numbered_list}\n"
    "\n"
    "Reply with a JSON array of {n} objects, one per signal, in order:\n"
    '[{{"tag": "...", "confidence": 0.0-1.0}}, ...]\n'
    "\n"
    "Rules:\n"
    "- confidence < 0.40 means you are unsure; the system will override to \"neutral\"\n"
    "- Reply with ONLY the JSON array, no other text"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_numbered_list(signals: list[str]) -> str:
    return "\n".join(f"{i + 1}. {s}" for i, s in enumerate(signals))


def _build_user_message(signals: list[str]) -> str:
    return _USER_TEMPLATE.format(
        n=len(signals),
        numbered_list=_build_numbered_list(signals),
    )


def _strip_markdown_fence(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrapper if present."""
    stripped = text.strip()
    if stripped.startswith("```"):
        # Drop opening fence line
        lines = stripped.splitlines()
        # First line is ```json or ```, last line is ```
        inner_lines = lines[1:] if lines[-1].strip() == "```" else lines[1:]
        if inner_lines and inner_lines[-1].strip() == "```":
            inner_lines = inner_lines[:-1]
        stripped = "\n".join(inner_lines)
    return stripped


def _neutral_fallback(signals: list[str]) -> list[TaggedSignal]:
    """Return a list of neutral/0.0 TaggedSignals for a batch that failed to parse."""
    return [TaggedSignal(text=s, tag="neutral", confidence=0.0) for s in signals]


def _parse_batch_response(raw_text: str, signals: list[str]) -> list[TaggedSignal]:
    """Parse Haiku JSON response for one batch.

    Returns a list of TaggedSignal objects aligned to ``signals``.
    Falls back to neutral/0.0 for the whole batch on any parse failure.
    """
    try:
        cleaned = _strip_markdown_fence(raw_text)
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning(
            "_parse_batch_response(): JSON parse failed (%s) — falling back to neutral for "
            "%d signals",
            exc,
            len(signals),
        )
        return _neutral_fallback(signals)

    if not isinstance(parsed, list):
        logger.warning(
            "_parse_batch_response(): expected a JSON array, got %s — falling back to neutral",
            type(parsed).__name__,
        )
        return _neutral_fallback(signals)

    tagged: list[TaggedSignal] = []
    for i, signal_text in enumerate(signals):
        # If the model returned fewer items than expected, use neutral for the rest
        if i >= len(parsed):
            logger.warning(
                "_parse_batch_response(): model returned %d items for %d signals — "
                "padding with neutral",
                len(parsed),
                len(signals),
            )
            tagged.append(TaggedSignal(text=signal_text, tag="neutral", confidence=0.0))
            continue

        item = parsed[i]
        try:
            tag = str(item.get("tag", "neutral")).lower()
            confidence = float(item.get("confidence", 0.0))
        except (AttributeError, TypeError, ValueError) as exc:
            logger.warning(
                "_parse_batch_response(): could not read item %d (%s) — using neutral",
                i,
                exc,
            )
            tagged.append(TaggedSignal(text=signal_text, tag="neutral", confidence=0.0))
            continue

        # Validate tag; fall back to neutral for unrecognised values
        if tag not in SIGNAL_TAGS:
            logger.warning(
                "_parse_batch_response(): unrecognised tag %r at index %d — using neutral",
                tag,
                i,
            )
            tag = "neutral"

        # Confidence threshold override
        if confidence < 0.40:
            tag = "neutral"

        tagged.append(TaggedSignal(text=signal_text, tag=tag, confidence=confidence))

    return tagged


def _build_tagged_corpus(all_tagged: list[TaggedSignal]) -> TaggedCorpus:
    """Assemble final TaggedCorpus from a flat list of TaggedSignals."""
    distribution: dict[str, int] = {t: 0 for t in SIGNAL_TAGS}
    for ts in all_tagged:
        distribution[ts.tag] = distribution.get(ts.tag, 0) + 1

    n_decision = sum(1 for ts in all_tagged if ts.tag != "neutral")

    return TaggedCorpus(
        signals=all_tagged,
        tag_distribution=distribution,
        n_decision_signals=n_decision,
    )


# ---------------------------------------------------------------------------
# Async core
# ---------------------------------------------------------------------------


async def tag_signals_async(
    signals: list[str],
    llm_client: Any = None,
    batch_size: int = 50,
) -> TaggedCorpus:
    """Tag each signal with one of 6 categories using Haiku.

    Processing:
    1. Split signals into batches of batch_size.
    2. For each batch, send a single Haiku call asking it to tag each signal.
    3. Parse JSON response: list of {"tag": "...", "confidence": N}.
    4. If confidence < 0.40 → override tag to "neutral".
    5. If parsing fails for any signal → tag as "neutral", confidence=0.0.
    6. Build TaggedCorpus with tag_distribution and n_decision_signals.
    """
    if not signals:
        return TaggedCorpus(
            signals=[],
            tag_distribution={t: 0 for t in SIGNAL_TAGS},
            n_decision_signals=0,
        )

    client = anthropic.AsyncAnthropic()
    all_tagged: list[TaggedSignal] = []

    for batch_start in range(0, len(signals), batch_size):
        batch = signals[batch_start : batch_start + batch_size]
        logger.debug(
            "tag_signals_async(): tagging batch of %d signals (indices %d–%d)",
            len(batch),
            batch_start,
            batch_start + len(batch) - 1,
        )

        messages = [{"role": "user", "content": _build_user_message(batch)}]

        try:
            if llm_client is not None and hasattr(llm_client, "complete"):
                raw_text: str = await llm_client.complete(
                    system=_SYSTEM_PROMPT,
                    messages=messages,
                    max_tokens=1024,
                    model=_HAIKU_MODEL,
                )
            else:
                response = await api_call_with_retry(
                    client.messages.create,
                    model=_HAIKU_MODEL,
                    max_tokens=1024,
                    system=_SYSTEM_PROMPT,
                    messages=messages,
                )
                raw_text = response.content[0].text
        except Exception as exc:
            logger.warning(
                "tag_signals_async(): LLM call failed for batch starting at index %d (%s) "
                "— falling back to neutral for %d signals",
                batch_start,
                exc,
                len(batch),
            )
            all_tagged.extend(_neutral_fallback(batch))
            continue

        batch_tagged = _parse_batch_response(raw_text, batch)
        all_tagged.extend(batch_tagged)

    return _build_tagged_corpus(all_tagged)


# ---------------------------------------------------------------------------
# Sync wrapper
# ---------------------------------------------------------------------------


def tag_signals(
    signals: list[str],
    llm_client: Any = None,
    batch_size: int = 50,
) -> TaggedCorpus:
    """Synchronous wrapper around tag_signals_async. Uses asyncio.run()."""
    return asyncio.run(
        tag_signals_async(signals, llm_client=llm_client, batch_size=batch_size)
    )
