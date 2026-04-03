"""src/memory/rematerialisation.py

Convert an ArchiveEntry into a context-window dict for injection into
decide() or reflect() prompts.

Read-only — never appends to observations, never mutates ArchiveEntry.

Spec ref: Sprint 25 — rematerialisation layer for cross-tier retrieval.
"""

from __future__ import annotations

from src.memory.archive import ArchiveEntry


def rematerialise(entry: ArchiveEntry, persona_id: str) -> dict:
    """Convert an ArchiveEntry to a context-window dict.

    Parameters
    ----------
    entry:
        The archived memory entry to rematerialise.
    persona_id:
        The owning persona's ID — included in the signature for future
        logging and tracing; not included in the output dict.

    Returns
    -------
    dict with exactly 6 keys:
        "type"            : "archived_memory"
        "tier"            : entry.tier.value  (e.g. "working_archive")
        "period"          : "YYYY-MM-DD to YYYY-MM-DD"
        "summary"         : entry.summary_content  (may be empty string)
        "original_count"  : len(entry.original_observation_ids)
        "mean_importance" : entry.mean_importance

    The function is pure — the entry is never modified.
    """
    period = (
        f"{entry.earliest_timestamp.strftime('%Y-%m-%d')} to "
        f"{entry.latest_timestamp.strftime('%Y-%m-%d')}"
    )
    return {
        "type": "archived_memory",
        "tier": entry.tier.value,
        "period": period,
        "summary": entry.summary_content,
        "original_count": len(entry.original_observation_ids),
        "mean_importance": entry.mean_importance,
    }
