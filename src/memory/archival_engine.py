"""src/memory/archival_engine.py

Promotion logic for hierarchical memory archival.
Moves observations from active working memory to archive tiers based on age + importance.
Deterministic — no LLM calls.
Backward compatible: no-op when len(observations) <= 1000 and archival_index is None.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.schema.memory_extended import WorkingMemoryExtended
from src.memory.archive import ArchiveTier, ArchiveEntry, ArchivalIndex


class ArchivalEngine:
    """
    Deterministic promotion engine for hierarchical memory archival.

    Two promotion paths:
      1. Active → Working Archive  (promote_to_working_archive)
      2. Working Archive → Deep Archive  (promote_to_deep_archive)

    Archival and eviction are strictly separate paths.  This class NEVER calls
    WorkingMemoryManager.evict().  Eviction remains owned by WorkingMemoryManager
    and is triggered only on write (hard-cap 1,000).

    All mutations follow the immutable-update pattern: a new WorkingMemoryExtended
    is returned via model_copy(); the passed-in object is never modified.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def promote_to_working_archive(
        self,
        memory: WorkingMemoryExtended,
        age_threshold_hours: int = 24,
        importance_threshold: float = 4.0,
    ) -> WorkingMemoryExtended:
        """
        Scan memory.observations for entries that qualify for working-archive
        promotion, move them out of active memory, and record ArchiveEntry
        objects in memory.archival_index.working_archive.

        Qualification criteria (both must be true):
          - age   > age_threshold_hours  (based on observation.timestamp)
          - importance < importance_threshold  (observation.importance, int 1-10)

        Backward compat guard:
          If len(memory.observations) <= 1000 AND memory.archival_index is None,
          return memory unchanged immediately (no-op).

        Parameters
        ----------
        memory : WorkingMemoryExtended
            The current memory state.
        age_threshold_hours : int
            Observations older than this many hours are candidates for promotion.
            Default 24 hours.
        importance_threshold : float
            Observations with importance strictly less than this value are
            candidates for promotion.  Default 4.0.

        Returns
        -------
        WorkingMemoryExtended
            Updated memory with qualifying observations removed from
            .observations and added to .archival_index.working_archive.
        """
        # Backward compat guard — no-op for standard working memory in short sims
        if len(memory.observations) <= 1000 and memory.archival_index is None:
            return memory

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=age_threshold_hours)

        qualifying = []
        remaining = []

        for obs in memory.observations:
            obs_ts = obs.timestamp
            # Ensure comparison is timezone-aware
            if obs_ts.tzinfo is None:
                obs_ts = obs_ts.replace(tzinfo=timezone.utc)

            if obs_ts < cutoff and obs.importance < importance_threshold:
                qualifying.append(obs)
            else:
                remaining.append(obs)

        if not qualifying:
            # Nothing to promote — return as-is (still init index if needed)
            return memory

        # Build ArchiveEntry for each qualifying observation
        new_entries: list[ArchiveEntry] = []
        for obs in qualifying:
            obs_ts = obs.timestamp
            if obs_ts.tzinfo is None:
                obs_ts = obs_ts.replace(tzinfo=timezone.utc)

            entry = ArchiveEntry(
                id=str(uuid4()),
                tier=ArchiveTier.WORKING_ARCHIVE,
                original_observation_ids=[obs.id],
                summary_content="",
                mean_importance=float(obs.importance),
                earliest_timestamp=obs_ts,
                latest_timestamp=obs_ts,
                last_accessed=now,
                citation_count=0,
            )
            new_entries.append(entry)

        # Build updated ArchivalIndex
        existing_index = memory.archival_index
        if existing_index is None:
            existing_index = ArchivalIndex()

        existing_working = list(existing_index.working_archive) if existing_index.working_archive else []
        existing_deep = list(existing_index.deep_archive) if existing_index.deep_archive else []

        updated_index = existing_index.model_copy(
            update={
                "working_archive": existing_working + new_entries,
                "deep_archive": existing_deep,
                "total_compressed": (existing_index.total_compressed or 0) + len(new_entries),
                "last_archival_run": now,
            }
        )

        return memory.model_copy(
            update={
                "observations": remaining,
                "archival_index": updated_index,
            }
        )

    def promote_to_deep_archive(
        self,
        memory: WorkingMemoryExtended,
        age_threshold_days: int = 7,
    ) -> WorkingMemoryExtended:
        """
        Scan memory.archival_index.working_archive for ArchiveEntry objects
        whose latest_timestamp is older than age_threshold_days, and move
        them to memory.archival_index.deep_archive.

        No-op conditions:
          - memory.archival_index is None  (nothing to promote)
          - working_archive is empty

        Parameters
        ----------
        memory : WorkingMemoryExtended
            The current memory state.
        age_threshold_days : int
            Working-archive entries older than this many days (by latest_timestamp)
            are promoted to deep archive.  Default 7 days.

        Returns
        -------
        WorkingMemoryExtended
            Updated memory with qualifying working-archive entries moved to
            deep_archive (tier updated to DEEP_ARCHIVE) and removed from
            working_archive.
        """
        index = memory.archival_index

        # No-op: archival never initialised
        if index is None:
            return memory

        working_archive = list(index.working_archive) if index.working_archive else []

        if not working_archive:
            return memory

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=age_threshold_days)

        staying_in_working: list[ArchiveEntry] = []
        promoting_to_deep: list[ArchiveEntry] = []

        for entry in working_archive:
            ts = entry.latest_timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            if ts < cutoff:
                promoting_to_deep.append(entry)
            else:
                staying_in_working.append(entry)

        if not promoting_to_deep:
            return memory

        # Re-stamp tier on each promoted entry
        promoted_entries: list[ArchiveEntry] = []
        for entry in promoting_to_deep:
            import dataclasses
            promoted = dataclasses.replace(entry, tier=ArchiveTier.DEEP_ARCHIVE)
            promoted_entries.append(promoted)

        existing_deep = list(index.deep_archive) if index.deep_archive else []

        updated_index = index.model_copy(
            update={
                "working_archive": staying_in_working,
                "deep_archive": existing_deep + promoted_entries,
                "last_archival_run": now,
            }
        )

        return memory.model_copy(
            update={"archival_index": updated_index}
        )
