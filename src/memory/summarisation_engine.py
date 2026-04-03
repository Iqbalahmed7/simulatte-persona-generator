"""src/memory/summarisation_engine.py

Batch Haiku summarisation of archived observations.
Groups observations into temporal batches and compresses each batch into a
SummaryReflection stored in the ArchiveEntry.summary_content field.

LLM model: claude-haiku-4-5 (high volume, low cost).
Spec ref: Sprint 24, Master Spec §8 (memory cap extension).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import anthropic

from src.memory.archive import ArchiveEntry
from src.schema.memory_extended import WorkingMemoryExtended
from src.utils.retry import api_call_with_retry

logger = logging.getLogger(__name__)

_HAIKU_MODEL = "claude-haiku-4-5-20251001"

_FALLBACK_PERSONA_CONTEXT = "A synthetic consumer persona"

# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

_SYSTEM_TEMPLATE = (
    "You are a memory summarisation assistant for a consumer research simulation. "
    "You compress archived observations about a persona into concise summaries that "
    "preserve decision-relevant signals. Be precise and factual — do not invent details."
)

_USER_TEMPLATE = (
    "Persona context: {persona_context}\n\n"
    "The following {entry_count} archived observation(s) span the period "
    "{period_start} to {period_end}.\n\n"
    "{entries_block}\n\n"
    "Write a 3–5 sentence summary of this set of experiences. Cover:\n"
    "1. The key theme or topic\n"
    "2. The dominant emotion or attitude expressed\n"
    "3. Any decision-relevant signals (purchase intent, objections, brand reactions)\n\n"
    "Reply in plain text only — no JSON, no bullet points, no headers."
)


def _build_entries_block(entries: list[ArchiveEntry]) -> str:
    """Format a batch of ArchiveEntry objects for injection into the prompt."""
    lines = []
    for i, entry in enumerate(entries, start=1):
        obs_ids_preview = ", ".join(entry.original_observation_ids[:3])
        if len(entry.original_observation_ids) > 3:
            obs_ids_preview += f" … (+{len(entry.original_observation_ids) - 3} more)"
        content_text = entry.raw_content.strip() if entry.raw_content else "(no raw content stored)"
        lines.append(
            f"[{i}] obs_ids=[{obs_ids_preview}] importance={entry.mean_importance:.1f}\n"
            f"    {content_text}"
        )
    return "\n".join(lines)


def _build_messages(
    batch: list[ArchiveEntry],
    persona_context: str,
) -> list[dict]:
    """Return messages list for the Haiku call."""
    period_start = min(e.earliest_timestamp for e in batch).strftime("%Y-%m-%d %H:%M")
    period_end = max(e.latest_timestamp for e in batch).strftime("%Y-%m-%d %H:%M")
    entries_block = _build_entries_block(batch)

    user_content = _USER_TEMPLATE.format(
        persona_context=persona_context,
        entry_count=len(batch),
        period_start=period_start,
        period_end=period_end,
        entries_block=entries_block,
    )
    return [{"role": "user", "content": user_content}]


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------


class SummarisationEngine:
    """Batch Haiku summarisation of unsummarised working-archive entries."""

    async def summarise_working_archive(
        self,
        memory: WorkingMemoryExtended,
        llm_client: Any = None,
        batch_size: int = 15,
    ) -> WorkingMemoryExtended:
        """Summarise all unsummarised ArchiveEntry objects in working_archive.

        Steps:
        1. Collect entries where summary_content == "" (unsummarised).
        2. Sort by earliest_timestamp (chronological order).
        3. Group into batches of batch_size.
        4. For each batch, call Haiku with persona context + entry contents.
        5. Set entry.summary_content = Haiku response text.
        6. Return updated WorkingMemoryExtended via model_copy.

        Returns the original memory unchanged if archival_index is None or
        there are no unsummarised entries.
        """
        if memory.archival_index is None:
            logger.debug("summarise_working_archive(): archival_index is None — no-op")
            return memory

        unsummarised: list[ArchiveEntry] = [
            e for e in memory.archival_index.working_archive
            if e.summary_content == ""
        ]

        if not unsummarised:
            logger.debug("summarise_working_archive(): no unsummarised entries — no-op")
            return memory

        # Sort chronologically
        unsummarised.sort(key=lambda e: e.earliest_timestamp)

        # Resolve persona context from CoreMemory tendency_summary
        persona_context: str = _FALLBACK_PERSONA_CONTEXT
        if hasattr(memory, "core") and memory.core is not None:  # type: ignore[attr-defined]
            ts = getattr(memory.core, "tendency_summary", None)  # type: ignore[attr-defined]
            if ts and ts.strip():
                persona_context = ts.strip()
        # WorkingMemoryExtended does not carry CoreMemory directly — it lives on
        # PersonaRecord.memory.core. Callers should inject tendency_summary via a
        # subclass or pass a pre-built context string. We apply the fallback here
        # so the engine is always safe to call standalone.

        # Build an id→entry lookup for in-place mutation
        entry_map: dict[str, ArchiveEntry] = {
            e.id: e for e in memory.archival_index.working_archive
        }

        client = anthropic.AsyncAnthropic()

        # Process in batches
        for batch_start in range(0, len(unsummarised), batch_size):
            batch = unsummarised[batch_start : batch_start + batch_size]
            logger.debug(
                "summarise_working_archive(): summarising batch of %d entries "
                "(indices %d–%d)",
                len(batch),
                batch_start,
                batch_start + len(batch) - 1,
            )

            messages = _build_messages(batch, persona_context)

            if llm_client is not None and hasattr(llm_client, "complete"):
                raw_text: str = await llm_client.complete(
                    system=_SYSTEM_TEMPLATE,
                    messages=messages,
                    max_tokens=512,
                    model=_HAIKU_MODEL,
                )
            else:
                response = await api_call_with_retry(
                    client.messages.create,
                    model=_HAIKU_MODEL,
                    max_tokens=512,
                    system=_SYSTEM_TEMPLATE,
                    messages=messages,
                )
                raw_text = response.content[0].text

            summary_text = raw_text.strip()
            if not summary_text:
                logger.warning(
                    "summarise_working_archive(): Haiku returned empty text for batch "
                    "starting at index %d — skipping",
                    batch_start,
                )
                continue

            # Apply summary to every entry in the batch
            for entry in batch:
                if entry.id in entry_map:
                    entry_map[entry.id].summary_content = summary_text
                    logger.debug(
                        "summarise_working_archive(): set summary_content on entry %s",
                        entry.id,
                    )

        # Rebuild the updated working_archive list preserving original order
        updated_archive = [entry_map.get(e.id, e) for e in memory.archival_index.working_archive]
        updated_index = memory.archival_index.model_copy(
            update={"working_archive": updated_archive}
        )
        return memory.model_copy(update={"archival_index": updated_index})


# ---------------------------------------------------------------------------
# Sync wrapper
# ---------------------------------------------------------------------------


def summarise_working_archive_sync(
    memory: WorkingMemoryExtended,
    llm_client: Any = None,
    batch_size: int = 15,
) -> WorkingMemoryExtended:
    """Synchronous wrapper around SummarisationEngine.summarise_working_archive.

    Uses asyncio.run() — do not call from within an already-running event loop.
    """
    engine = SummarisationEngine()
    return asyncio.run(
        engine.summarise_working_archive(memory, llm_client=llm_client, batch_size=batch_size)
    )
