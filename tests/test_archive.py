"""tests/test_archive.py — Sprint 24 hierarchical memory archival system tests.

Coverage:
  - ArchiveTier / ArchiveEntry / ArchivalIndex  (5 tests)
  - WorkingMemoryExtended                        (3 tests)
  - ArchivalEngine.promote_to_working_archive()  (6 tests)
  - ArchivalEngine.promote_to_deep_archive()     (4 tests)
  - ArchiveStore                                 (5 tests)
  - SummarisationEngine                          (4 tests)

No LLM calls.  All deterministic synthetic data.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.memory.archive import ArchiveTier, ArchiveEntry, ArchivalIndex
from src.schema.memory_extended import WorkingMemoryExtended
from src.schema.persona import (
    Observation,
    SimulationState,
    WorkingMemory,
)
from src.memory.archival_engine import ArchivalEngine
from src.memory.archive_store import ArchiveStore
from src.memory.summarisation_engine import SummarisationEngine, summarise_working_archive_sync


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def make_observation(obs_id: str, importance: int, age_hours: float) -> Observation:
    """Construct a minimal Observation with a timestamp offset by age_hours into the past."""
    ts = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    return Observation(
        id=obs_id,
        timestamp=ts,
        type="observation",
        content=f"Observation {obs_id}",
        importance=importance,
        emotional_valence=0.0,
        last_accessed=ts,
    )


def _make_simulation_state() -> SimulationState:
    return SimulationState(
        current_turn=0,
        importance_accumulator=0.0,
        reflection_count=0,
        awareness_set={},
        consideration_set=[],
        last_decision=None,
    )


def _make_base_working_memory(observations: list[Observation] | None = None) -> WorkingMemory:
    return WorkingMemory(
        observations=observations or [],
        reflections=[],
        plans=[],
        brand_memories={},
        simulation_state=_make_simulation_state(),
    )


def make_working_memory_extended(
    n_obs: int = 1,
    age_hours: float = 1.0,
    importance: int = 5,
) -> WorkingMemoryExtended:
    """Construct a WorkingMemoryExtended with archival_index already initialised via attach_index."""
    observations = [
        make_observation(str(uuid.uuid4()), importance, age_hours)
        for _ in range(n_obs)
    ]
    base = _make_base_working_memory(observations)
    return ArchiveStore.attach_index(base)


def _make_archive_entry(
    age_days: float = 0.0,
    summary_content: str = "",
    tier: ArchiveTier = ArchiveTier.WORKING_ARCHIVE,
) -> ArchiveEntry:
    ts = datetime.now(timezone.utc) - timedelta(days=age_days)
    return ArchiveEntry(
        id=str(uuid.uuid4()),
        tier=tier,
        original_observation_ids=[str(uuid.uuid4())],
        summary_content=summary_content,
        mean_importance=5.0,
        earliest_timestamp=ts,
        latest_timestamp=ts,
        last_accessed=ts,
    )


# ---------------------------------------------------------------------------
# TestArchiveTier / TestArchiveEntry / TestArchivalIndex
# ---------------------------------------------------------------------------

class TestArchiveTier:
    def test_enum_has_active_value(self):
        assert ArchiveTier.ACTIVE == "active"

    def test_enum_has_working_archive_value(self):
        assert ArchiveTier.WORKING_ARCHIVE == "working_archive"

    def test_enum_has_deep_archive_value(self):
        assert ArchiveTier.DEEP_ARCHIVE == "deep_archive"


class TestArchiveEntry:
    def test_construction_with_required_fields(self):
        now = datetime.now(timezone.utc)
        entry = ArchiveEntry(
            id="entry-1",
            tier=ArchiveTier.WORKING_ARCHIVE,
            original_observation_ids=["obs-1"],
            summary_content="",
            mean_importance=3.5,
            earliest_timestamp=now,
            latest_timestamp=now,
            last_accessed=now,
        )
        assert entry.id == "entry-1"
        assert entry.tier == ArchiveTier.WORKING_ARCHIVE

    def test_citation_count_defaults_to_zero(self):
        now = datetime.now(timezone.utc)
        entry = ArchiveEntry(
            id="entry-2",
            tier=ArchiveTier.ACTIVE,
            original_observation_ids=["obs-2"],
            summary_content="",
            mean_importance=5.0,
            earliest_timestamp=now,
            latest_timestamp=now,
            last_accessed=now,
        )
        assert entry.citation_count == 0


class TestArchivalIndex:
    def test_instantiates_with_empty_lists(self):
        index = ArchivalIndex()
        assert index.working_archive == []
        assert index.deep_archive == []

    def test_total_compressed_defaults_to_zero(self):
        index = ArchivalIndex()
        assert index.total_compressed == 0

    def test_last_archival_run_defaults_to_none(self):
        index = ArchivalIndex()
        assert index.last_archival_run is None


# ---------------------------------------------------------------------------
# TestWorkingMemoryExtended
# ---------------------------------------------------------------------------

class TestWorkingMemoryExtended:
    def test_is_working_memory_subclass(self):
        mem = make_working_memory_extended()
        assert isinstance(mem, WorkingMemory)

    def test_archival_index_defaults_to_none(self):
        base = _make_base_working_memory()
        ext = WorkingMemoryExtended(**base.model_dump())
        assert ext.archival_index is None

    def test_none_archival_index_passes_working_memory_validation(self):
        base = _make_base_working_memory()
        ext = WorkingMemoryExtended(**base.model_dump(), archival_index=None)
        # Pydantic would raise on construction if validation failed
        assert ext.archival_index is None
        assert ext.observations == []
        assert ext.reflections == []


# ---------------------------------------------------------------------------
# TestArchivalEnginePromoteToWorkingArchive
# ---------------------------------------------------------------------------

class TestArchivalEnginePromoteToWorkingArchive:
    def setup_method(self):
        self.engine = ArchivalEngine()

    def test_backward_compat_guard_small_memory_no_index(self):
        """Memory with <=1000 obs and archival_index=None is returned unchanged."""
        base = _make_base_working_memory(
            observations=[make_observation(str(uuid.uuid4()), 2, 48)]
        )
        ext = WorkingMemoryExtended(**base.model_dump())  # archival_index=None
        result = self.engine.promote_to_working_archive(ext)
        assert result is ext or result == ext

    def test_backward_compat_does_not_trigger_when_index_set(self):
        """Backward compat guard must NOT fire when archival_index is not None, even with <=1000 obs."""
        obs = make_observation("obs-1", 2, 48)  # old, low importance
        base = _make_base_working_memory(observations=[obs])
        ext = ArchiveStore.attach_index(base)  # archival_index initialised
        result = self.engine.promote_to_working_archive(ext)
        # obs should have been promoted into working_archive
        promoted_ids = [
            oid
            for entry in result.archival_index.working_archive
            for oid in entry.original_observation_ids
        ]
        assert "obs-1" in promoted_ids

    def test_old_low_importance_obs_is_promoted(self):
        """Observation with age=25h and importance=2 qualifies for promotion."""
        obs = make_observation("old-low", 2, 25)
        base = _make_base_working_memory(observations=[obs])
        ext = ArchiveStore.attach_index(base)
        result = self.engine.promote_to_working_archive(ext)
        remaining_ids = [o.id for o in result.observations]
        assert "old-low" not in remaining_ids
        promoted_ids = [
            oid
            for entry in result.archival_index.working_archive
            for oid in entry.original_observation_ids
        ]
        assert "old-low" in promoted_ids

    def test_recent_obs_stays_active_despite_low_importance(self):
        """Recent observation (age=1h, importance=2) must NOT be promoted."""
        obs = make_observation("recent-low", 2, 1)
        base = _make_base_working_memory(observations=[obs])
        ext = ArchiveStore.attach_index(base)
        result = self.engine.promote_to_working_archive(ext)
        remaining_ids = [o.id for o in result.observations]
        assert "recent-low" in remaining_ids

    def test_high_importance_old_obs_stays_active(self):
        """High-importance observation (age=25h, importance=8) must stay active."""
        obs = make_observation("old-high", 8, 25)
        base = _make_base_working_memory(observations=[obs])
        ext = ArchiveStore.attach_index(base)
        result = self.engine.promote_to_working_archive(ext)
        remaining_ids = [o.id for o in result.observations]
        assert "old-high" in remaining_ids

    def test_original_memory_is_not_mutated(self):
        """promote_to_working_archive must follow the immutable-update pattern."""
        obs = make_observation("mut-test", 2, 48)
        base = _make_base_working_memory(observations=[obs])
        ext = ArchiveStore.attach_index(base)
        original_obs_count = len(ext.observations)
        original_working_archive_len = len(ext.archival_index.working_archive)

        _ = self.engine.promote_to_working_archive(ext)

        # ext must be untouched
        assert len(ext.observations) == original_obs_count
        assert len(ext.archival_index.working_archive) == original_working_archive_len


# ---------------------------------------------------------------------------
# TestArchivalEnginePromoteToDeepArchive
# ---------------------------------------------------------------------------

class TestArchivalEnginePromoteToDeepArchive:
    def setup_method(self):
        self.engine = ArchivalEngine()

    def _memory_with_working_entry(self, age_days: float) -> WorkingMemoryExtended:
        entry = _make_archive_entry(age_days=age_days)
        index = ArchivalIndex(working_archive=[entry])
        base = _make_base_working_memory()
        ext = WorkingMemoryExtended(**base.model_dump(), archival_index=index)
        return ext

    def test_old_entry_moves_to_deep_archive(self):
        """Entry older than 7 days in working_archive must be moved to deep_archive."""
        ext = self._memory_with_working_entry(age_days=8)
        result = self.engine.promote_to_deep_archive(ext)
        assert len(result.archival_index.working_archive) == 0
        assert len(result.archival_index.deep_archive) == 1

    def test_recent_entry_stays_in_working_archive(self):
        """Entry newer than 7 days must remain in working_archive."""
        ext = self._memory_with_working_entry(age_days=3)
        result = self.engine.promote_to_deep_archive(ext)
        assert len(result.archival_index.working_archive) == 1
        assert len(result.archival_index.deep_archive) == 0

    def test_noop_when_archival_index_is_none(self):
        """promote_to_deep_archive must return memory unchanged when archival_index is None."""
        base = _make_base_working_memory()
        ext = WorkingMemoryExtended(**base.model_dump())
        result = self.engine.promote_to_deep_archive(ext)
        assert result is ext

    def test_promoted_entry_tier_updated_to_deep_archive(self):
        """Promoted entry must have tier == ArchiveTier.DEEP_ARCHIVE."""
        ext = self._memory_with_working_entry(age_days=10)
        result = self.engine.promote_to_deep_archive(ext)
        promoted = result.archival_index.deep_archive[0]
        assert promoted.tier == ArchiveTier.DEEP_ARCHIVE


# ---------------------------------------------------------------------------
# TestArchiveStore
# ---------------------------------------------------------------------------

class TestArchiveStore:
    def test_attach_index_returns_working_memory_extended(self):
        """attach_index() must wrap WorkingMemory into WorkingMemoryExtended with empty ArchivalIndex."""
        base = _make_base_working_memory()
        ext = ArchiveStore.attach_index(base)
        assert isinstance(ext, WorkingMemoryExtended)
        assert isinstance(ext.archival_index, ArchivalIndex)
        assert ext.archival_index.working_archive == []
        assert ext.archival_index.deep_archive == []

    def test_detach_index_returns_base_and_index_tuple(self):
        """detach_index() must return (WorkingMemory, ArchivalIndex | None) with base fields preserved."""
        obs = make_observation("detach-obs", 5, 1)
        base = _make_base_working_memory(observations=[obs])
        ext = ArchiveStore.attach_index(base)
        wm, index = ArchiveStore.detach_index(ext)
        assert isinstance(wm, WorkingMemory)
        assert isinstance(index, ArchivalIndex)
        assert len(wm.observations) == 1
        assert wm.observations[0].id == "detach-obs"

    def test_to_json_from_json_round_trip(self):
        """WorkingMemoryExtended with ArchiveEntry objects must survive a to_json/from_json round-trip."""
        entry = _make_archive_entry(age_days=1, summary_content="A summary")
        index = ArchivalIndex(working_archive=[entry], total_compressed=1)
        base = _make_base_working_memory()
        ext = WorkingMemoryExtended(**base.model_dump(), archival_index=index)

        data = ArchiveStore.to_json(ext)
        restored = ArchiveStore.from_json(data)

        assert isinstance(restored, WorkingMemoryExtended)
        assert restored.archival_index is not None
        assert len(restored.archival_index.working_archive) == 1
        assert restored.archival_index.working_archive[0].summary_content == "A summary"
        assert restored.archival_index.total_compressed == 1

    def test_from_json_backward_compat_missing_key(self):
        """Legacy dict without 'archival_index' key must deserialise with archival_index=None."""
        base = _make_base_working_memory()
        data = base.model_dump(mode="json")
        # Ensure the key is absent (legacy format)
        assert "archival_index" not in data

        restored = ArchiveStore.from_json(data)
        assert isinstance(restored, WorkingMemoryExtended)
        assert restored.archival_index is None

    def test_from_json_with_explicit_none_archival_index(self):
        """Dict with archival_index=None must deserialise with archival_index=None."""
        base = _make_base_working_memory()
        data = base.model_dump(mode="json")
        data["archival_index"] = None

        restored = ArchiveStore.from_json(data)
        assert restored.archival_index is None


# ---------------------------------------------------------------------------
# TestSummarisationEngine
# ---------------------------------------------------------------------------

class TestSummarisationEngine:
    def test_no_op_when_archival_index_is_none(self):
        """summarise_working_archive_sync must return memory unchanged when archival_index is None."""
        base = _make_base_working_memory()
        ext = WorkingMemoryExtended(**base.model_dump())
        result = summarise_working_archive_sync(ext)
        assert result is ext

    def test_no_op_when_all_entries_already_summarised(self):
        """summarise_working_archive_sync must skip entries that already have summary_content set."""
        entry = _make_archive_entry(summary_content="Already summarised")
        index = ArchivalIndex(working_archive=[entry])
        base = _make_base_working_memory()
        ext = WorkingMemoryExtended(**base.model_dump(), archival_index=index)
        result = summarise_working_archive_sync(ext)
        # Returned unchanged (same archival_index content)
        assert result.archival_index.working_archive[0].summary_content == "Already summarised"

    def test_only_processes_unsummarised_entries(self):
        """summarise_working_archive_sync must only call the LLM for entries where summary_content == ''."""

        class _StubLLMClient:
            def __init__(self):
                self.calls = 0

            async def complete(self, **kwargs: Any) -> str:
                self.calls += 1
                return "Stub summary"

        summarised_entry = _make_archive_entry(summary_content="Already done")
        unsummarised_entry = _make_archive_entry(summary_content="")
        index = ArchivalIndex(working_archive=[summarised_entry, unsummarised_entry])
        base = _make_base_working_memory()
        ext = WorkingMemoryExtended(**base.model_dump(), archival_index=index)

        stub = _StubLLMClient()
        result = summarise_working_archive_sync(ext, llm_client=stub)

        # Exactly one LLM call should have been made (one batch for the single unsummarised entry)
        assert stub.calls == 1
        # The pre-summarised entry must not be overwritten
        result_entries = {e.id: e for e in result.archival_index.working_archive}
        assert result_entries[summarised_entry.id].summary_content == "Already done"

    def test_mock_llm_sets_summary_content(self):
        """Stub llm_client.complete() returning 'Test summary' must be written to entry.summary_content."""

        class _StubLLMClient:
            async def complete(self, **kwargs: Any) -> str:
                return "Test summary"

        entry = _make_archive_entry(summary_content="")
        index = ArchivalIndex(working_archive=[entry])
        base = _make_base_working_memory()
        ext = WorkingMemoryExtended(**base.model_dump(), archival_index=index)

        stub = _StubLLMClient()
        result = summarise_working_archive_sync(ext, llm_client=stub)

        updated_entry = result.archival_index.working_archive[0]
        assert updated_entry.summary_content == "Test summary"
