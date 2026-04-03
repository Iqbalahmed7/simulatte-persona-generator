"""src/memory/hierarchical_retrieval.py

Cross-tier retrieval for hierarchical memory archival (Sprint 25).

Applies tier-specific decay weights on top of the standard retrieval formula:
    score = (α·recency + β·importance + γ·relevance) × tier_decay

Active tier has decay=1.0 so the standard path is identical when archival_index
is None — HierarchicalRetriever degrades to WorkingMemoryManager.retrieve_top_k().

Spec ref: Master Spec §8 (Retrieve formula), §14A S7 (tier decay as multiplier).
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Union

from src.memory.archive import ArchiveTier, ArchiveEntry, ArchivalIndex
from src.schema.persona import WorkingMemory, Observation, Reflection

# ---------------------------------------------------------------------------
# Tier decay weights — applied as score multipliers (S7)
# ---------------------------------------------------------------------------

TIER_DECAY: dict[ArchiveTier, float] = {
    ArchiveTier.ACTIVE: 1.0,
    ArchiveTier.WORKING_ARCHIVE: 0.7,
    ArchiveTier.DEEP_ARCHIVE: 0.3,
}

DEFAULT_ARCHIVE_BUDGET_FRACTION: float = 0.40  # max 40% of returned K from archive

_STOPWORDS: set[str] = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "of",
    "and", "or", "but", "for", "with", "this", "that", "was", "are",
}


def _tokenise(text: str) -> set[str]:
    tokens = re.findall(r"[a-zA-Z0-9']+", text.lower())
    return {t for t in tokens if t not in _STOPWORDS}


def _keyword_relevance(query: str, content: str) -> float:
    q_tokens = _tokenise(query)
    if not q_tokens:
        return 0.0
    c_tokens = _tokenise(content)
    return len(q_tokens & c_tokens) / len(q_tokens)


class HierarchicalRetriever:
    """Retrieve top-K candidates across active and archived tiers.

    When archival_index is None (or memory is a plain WorkingMemory),
    delegates to WorkingMemoryManager.retrieve_top_k() and returns its output
    unchanged — ensuring the standard path is completely unaffected.
    """

    def retrieve_top_k(
        self,
        memory: Union["WorkingMemoryExtended", WorkingMemory],  # noqa: F821
        query: str,
        k: int = 10,
        alpha: float = 0.5,
        beta: float = 0.3,
        gamma: float = 0.2,
        context_budget_archive_fraction: float = DEFAULT_ARCHIVE_BUDGET_FRACTION,
    ) -> list[dict]:
        """Return top-K memory candidates across all tiers as dicts.

        Graceful fallback: if archival_index is None or memory has no
        archival_index attribute, delegates to WorkingMemoryManager and
        wraps its output as active dicts so the caller always receives
        a uniform list[dict].

        Parameters
        ----------
        memory:
            WorkingMemoryExtended (with archival_index) or plain WorkingMemory.
        query:
            The query string for relevance scoring.
        k:
            Number of candidates to return.
        alpha / beta / gamma:
            Recency / importance / relevance weights.
        context_budget_archive_fraction:
            Maximum fraction of returned K that may be archived entries.
        """
        archival_index = getattr(memory, "archival_index", None)

        if archival_index is None:
            # Standard path — delegate and wrap
            from src.memory.working_memory import WorkingMemoryManager
            manager = WorkingMemoryManager()
            standard_results = manager.retrieve_top_k(memory, query=query, k=k)
            return [self._obs_to_dict(entry) for entry in standard_results]

        now = datetime.now(timezone.utc)

        # ------------------------------------------------------------------
        # 1. Collect all candidates with their raw timestamps for normalisation
        # ------------------------------------------------------------------
        all_timestamps: list[datetime] = []

        active_obs: list[Observation] = list(memory.observations)
        for obs in active_obs:
            ts = obs.last_accessed if hasattr(obs, "last_accessed") else obs.timestamp
            all_timestamps.append(ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc))

        working_entries: list[ArchiveEntry] = list(archival_index.working_archive)
        deep_entries: list[ArchiveEntry] = list(archival_index.deep_archive)

        for entry in working_entries + deep_entries:
            ts = entry.latest_timestamp
            all_timestamps.append(ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc))

        # ------------------------------------------------------------------
        # 2. Compute global min/max for recency normalisation
        # ------------------------------------------------------------------
        if not all_timestamps:
            return []

        min_ts = min(all_timestamps)
        max_ts = max(all_timestamps)
        ts_range = (max_ts - min_ts).total_seconds()

        def _recency(ts: datetime) -> float:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts_range == 0:
                return 1.0
            return (ts - min_ts).total_seconds() / ts_range

        # ------------------------------------------------------------------
        # 3. Score active observations
        # ------------------------------------------------------------------
        candidates: list[dict] = []

        for obs in active_obs:
            ts = obs.last_accessed if hasattr(obs, "last_accessed") else obs.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            rec = _recency(ts)
            imp = obs.importance / 10.0
            rel = _keyword_relevance(query, obs.content)
            raw_score = alpha * rec + beta * imp + gamma * rel
            score = raw_score * TIER_DECAY[ArchiveTier.ACTIVE]

            candidates.append({
                "type": "active",
                "tier": ArchiveTier.ACTIVE.value,
                "id": obs.id,
                "content": obs.content,
                "importance": obs.importance,
                "score": score,
                "source": "working_memory",
                "_obs": obs,  # kept for downstream compatibility; not exposed in spec
            })

        # ------------------------------------------------------------------
        # 4. Score archived entries
        # ------------------------------------------------------------------
        for entry in working_entries + deep_entries:
            ts = entry.latest_timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            rec = _recency(ts)
            imp = entry.mean_importance / 10.0
            content_for_relevance = entry.summary_content or ""
            rel = _keyword_relevance(query, content_for_relevance)
            raw_score = alpha * rec + beta * imp + gamma * rel
            score = raw_score * TIER_DECAY[entry.tier]

            candidates.append({
                "type": "archived",
                "tier": entry.tier.value,
                "id": entry.id,
                "summary": entry.summary_content,
                "original_observation_ids": entry.original_observation_ids,
                "mean_importance": entry.mean_importance,
                "score": score,
                "source": "archive",
            })

        # ------------------------------------------------------------------
        # 5. Sort descending, enforce archive budget
        # ------------------------------------------------------------------
        candidates.sort(key=lambda c: c["score"], reverse=True)

        max_archive = max(1, round(k * context_budget_archive_fraction))
        results: list[dict] = []
        archived_count = 0

        for candidate in candidates:
            if len(results) >= k:
                break
            if candidate["type"] == "archived":
                if archived_count >= max_archive:
                    continue
                archived_count += 1
            results.append(candidate)

        return results

    @staticmethod
    def _obs_to_dict(entry: Union[Observation, Reflection]) -> dict:
        """Wrap a standard Observation/Reflection in an active-tier dict."""
        return {
            "type": "active",
            "tier": ArchiveTier.ACTIVE.value,
            "id": entry.id,
            "content": entry.content,
            "importance": entry.importance,
            "score": 0.0,  # score not computed in fallback path
            "source": "working_memory",
            "_obs": entry,
        }

    def retrieve_active_only(
        self,
        memory: Union["WorkingMemoryExtended", WorkingMemory],  # noqa: F821
        query: str,
        k: int = 10,
    ) -> list[Observation | Reflection]:
        """Convenience method: return only active-tier Observation/Reflection objects.

        Used by loop.py reflect path which requires Observation objects, not dicts.
        Falls back to WorkingMemoryManager.retrieve_top_k() when no archival_index.
        """
        from src.memory.working_memory import WorkingMemoryManager

        archival_index = getattr(memory, "archival_index", None)
        if archival_index is None:
            return WorkingMemoryManager().retrieve_top_k(memory, query=query, k=k)

        results = self.retrieve_top_k(memory, query=query, k=k)
        # Extract only active entries and recover the original _obs object
        active = [r["_obs"] for r in results if r["type"] == "active" and "_obs" in r]
        return active
