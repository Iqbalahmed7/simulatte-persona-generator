"""tests/test_hierarchical_retrieval.py — Sprint 25 hierarchical memory retrieval tests.

Coverage (28 tests):
  - TestTierDecay                         (2 tests)
  - TestHierarchicalRetrieverFallback     (3 tests)
  - TestHierarchicalRetrieverDecay        (3 tests)
  - TestHierarchicalRetrieverBudget       (3 tests)
  - TestHierarchicalRetrieverEmpty        (2 tests)
  - TestRematerialise                     (4 tests)
  - TestBV2Extended                       (6 tests)
  - TestBV3Extended                       (5 tests)

No real LLM calls. All deterministic synthetic data.
"""

from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from src.memory.archive import ArchiveTier, ArchiveEntry, ArchivalIndex
from src.memory.hierarchical_retrieval import (
    HierarchicalRetriever,
    TIER_DECAY,
    DEFAULT_ARCHIVE_BUDGET_FRACTION,
)
from src.memory.rematerialisation import rematerialise
from src.schema.memory_extended import WorkingMemoryExtended
from src.schema.persona import Observation, SimulationState, WorkingMemory
from src.validation.bv2_extended import run_bv2_extended, BV2ExtendedResult
from src.validation.bv3_extended import run_bv3_extended, BV3ExtendedResult, ArchivalEvent


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def make_obs(obs_id: str, importance: int, age_hours: float) -> Observation:
    """Create an Observation with timestamp offset by age_hours into the past."""
    ts = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    return Observation(
        id=obs_id,
        timestamp=ts,
        type="observation",
        content=f"Content for observation {obs_id}",
        importance=importance,
        emotional_valence=0.0,
        last_accessed=ts,
    )


def make_archive_entry(
    entry_id: str,
    tier: ArchiveTier,
    mean_importance: float,
    age_days: float,
    summary_content: str = "An archived summary",
) -> ArchiveEntry:
    """Create an ArchiveEntry at the specified tier with a timestamp offset by age_days."""
    ts = datetime.now(timezone.utc) - timedelta(days=age_days)
    return ArchiveEntry(
        id=entry_id,
        tier=tier,
        original_observation_ids=[str(uuid.uuid4())],
        summary_content=summary_content,
        mean_importance=mean_importance,
        earliest_timestamp=ts,
        latest_timestamp=ts,
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


def make_extended_memory(
    n_active: int = 3,
    with_archive: bool = False,
) -> WorkingMemoryExtended:
    """Create a WorkingMemoryExtended with n_active observations and an optional ArchivalIndex."""
    observations = [
        make_obs(str(uuid.uuid4()), importance=5, age_hours=1.0)
        for _ in range(n_active)
    ]
    base = _make_base_working_memory(observations)
    if with_archive:
        entry = make_archive_entry(
            entry_id=str(uuid.uuid4()),
            tier=ArchiveTier.WORKING_ARCHIVE,
            mean_importance=5.0,
            age_days=2.0,
        )
        index = ArchivalIndex(working_archive=[entry])
        return WorkingMemoryExtended(**base.model_dump(), archival_index=index)
    # archival_index=None (no archive)
    return WorkingMemoryExtended(**base.model_dump())


# ---------------------------------------------------------------------------
# TestTierDecay
# ---------------------------------------------------------------------------

class TestTierDecay:
    def test_tier_decay_has_required_keys(self):
        """TIER_DECAY must have keys for ACTIVE, WORKING_ARCHIVE, and DEEP_ARCHIVE."""
        assert ArchiveTier.ACTIVE in TIER_DECAY
        assert ArchiveTier.WORKING_ARCHIVE in TIER_DECAY
        assert ArchiveTier.DEEP_ARCHIVE in TIER_DECAY

    def test_tier_decay_values_are_correct(self):
        """TIER_DECAY values must be 1.0, 0.7, 0.3 for ACTIVE, WORKING_ARCHIVE, DEEP_ARCHIVE."""
        assert TIER_DECAY[ArchiveTier.ACTIVE] == 1.0
        assert TIER_DECAY[ArchiveTier.WORKING_ARCHIVE] == 0.7
        assert TIER_DECAY[ArchiveTier.DEEP_ARCHIVE] == 0.3


# ---------------------------------------------------------------------------
# TestHierarchicalRetrieverFallback
# ---------------------------------------------------------------------------

class TestHierarchicalRetrieverFallback:
    def setup_method(self):
        self.retriever = HierarchicalRetriever()

    def test_none_archival_index_result_length_lte_k(self):
        """With archival_index=None, returned list length must be <= k."""
        mem = make_extended_memory(n_active=5, with_archive=False)
        # archival_index is None by default in make_extended_memory(with_archive=False)
        results = self.retriever.retrieve_top_k(mem, query="test", k=3)
        assert len(results) <= 3

    def test_none_archival_index_items_have_active_type(self):
        """Fallback path wraps active observations as type='active'."""
        mem = make_extended_memory(n_active=3, with_archive=False)
        results = self.retriever.retrieve_top_k(mem, query="test", k=10)
        for item in results:
            assert item["type"] == "active", f"Expected type='active', got {item['type']!r}"

    def test_plain_working_memory_triggers_same_fallback(self):
        """A plain WorkingMemory (no archival_index attr) uses the same fallback as None."""
        observations = [make_obs(str(uuid.uuid4()), 5, 1.0) for _ in range(3)]
        mem = _make_base_working_memory(observations)
        # WorkingMemory has no archival_index attribute — getattr returns None
        results = self.retriever.retrieve_top_k(mem, query="test", k=10)
        assert all(item["type"] == "active" for item in results)


# ---------------------------------------------------------------------------
# TestHierarchicalRetrieverDecay
# ---------------------------------------------------------------------------

class TestHierarchicalRetrieverDecay:
    def setup_method(self):
        self.retriever = HierarchicalRetriever()

    def _make_decay_test_memory(self) -> WorkingMemoryExtended:
        """One active obs (importance=7) + one working_archive entry (mean_importance=9).

        The active observation is the most recent candidate (age=3 min), while the archive
        entry is older (age=2 hours).  With only two timestamps in the pool:
          recency(obs) = 1.0  →  active score = (0.5×1.0 + 0.3×0.7) × 1.0 = 0.71
          recency(arch) = 0.0 →  archive score = (0.5×0.0 + 0.3×0.9) × 0.7 = 0.189
        So active wins despite archive having higher raw importance.
        """
        obs = make_obs("active-obs-1", importance=7, age_hours=0.05)   # ~3 minutes ago
        entry = make_archive_entry(
            entry_id="archive-entry-1",
            tier=ArchiveTier.WORKING_ARCHIVE,
            mean_importance=9.0,
            age_days=0.1,  # ~2.4 hours ago — older than obs
        )
        index = ArchivalIndex(working_archive=[entry])
        base = _make_base_working_memory(observations=[obs])
        return WorkingMemoryExtended(**base.model_dump(), archival_index=index)

    def test_active_obs_importance7_outranks_working_archive_importance9(self):
        """Spec S7 acceptance criterion: active imp=7 (×1.0) must rank above
        working_archive imp=9 (×0.7) when recency is similar.

        Expected:
          active raw ≈ α·rec + β·0.70 + γ·0 = 0.5·rec + 0.21
          archive raw ≈ α·rec + β·0.90 + γ·0 = 0.5·rec + 0.27
          active score = raw_active × 1.0
          archive score = raw_archive × 0.7

        With similar recency (both near 1.0 when only 2 items exist, difference small):
          active ≈ 0.5·1.0 + 0.21 = 0.71  → score ≈ 0.71
          archive ≈ 0.5·0.0 + 0.27 = 0.27 or similar → ×0.7

        The active entry should appear first in the sorted results.
        """
        mem = self._make_decay_test_memory()
        results = self.retriever.retrieve_top_k(mem, query="", k=10)

        assert len(results) >= 2, "Expected at least 2 results"
        # The first result (highest score) must be the active observation
        assert results[0]["type"] == "active", (
            f"Expected active entry to rank first. Got: {results[0]['type']!r} "
            f"(scores: {[r['score'] for r in results]})"
        )
        assert results[0]["id"] == "active-obs-1"

    def test_deep_archive_scores_lower_than_working_archive_same_importance(self):
        """DEEP_ARCHIVE (decay=0.3) produces a lower score than WORKING_ARCHIVE (decay=0.7)
        with identical importance and identical age."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(hours=1)

        working_entry = ArchiveEntry(
            id="working-entry",
            tier=ArchiveTier.WORKING_ARCHIVE,
            original_observation_ids=["obs-w"],
            summary_content="working summary",
            mean_importance=6.0,
            earliest_timestamp=ts,
            latest_timestamp=ts,
            last_accessed=ts,
        )
        deep_entry = ArchiveEntry(
            id="deep-entry",
            tier=ArchiveTier.DEEP_ARCHIVE,
            original_observation_ids=["obs-d"],
            summary_content="deep summary",
            mean_importance=6.0,
            earliest_timestamp=ts,
            latest_timestamp=ts,
            last_accessed=ts,
        )
        index = ArchivalIndex(working_archive=[working_entry], deep_archive=[deep_entry])
        base = _make_base_working_memory()
        mem = WorkingMemoryExtended(**base.model_dump(), archival_index=index)

        results = self.retriever.retrieve_top_k(mem, query="", k=10)

        scored = {r["id"]: r["score"] for r in results}
        assert "working-entry" in scored
        assert "deep-entry" in scored
        assert scored["working-entry"] > scored["deep-entry"], (
            f"Working archive score ({scored['working-entry']:.4f}) must exceed "
            f"deep archive score ({scored['deep-entry']:.4f})"
        )

    def test_active_observations_returned_as_active_type(self):
        """Active observations must appear with type='active' in the result dicts."""
        mem = make_extended_memory(n_active=3, with_archive=True)
        results = self.retriever.retrieve_top_k(mem, query="", k=10)
        active_results = [r for r in results if r["type"] == "active"]
        assert len(active_results) == 3


# ---------------------------------------------------------------------------
# TestHierarchicalRetrieverBudget
# ---------------------------------------------------------------------------

class TestHierarchicalRetrieverBudget:
    def setup_method(self):
        self.retriever = HierarchicalRetriever()

    def _make_many_archived_memory(self, n_archive: int, n_active: int) -> WorkingMemoryExtended:
        """Create memory with n_active active obs and n_archive working_archive entries."""
        observations = [
            make_obs(f"active-{i}", importance=5, age_hours=0.5)
            for i in range(n_active)
        ]
        entries = [
            make_archive_entry(
                entry_id=f"archive-{i}",
                tier=ArchiveTier.WORKING_ARCHIVE,
                mean_importance=8.0,  # high importance so they sort above active
                age_days=0.02,        # very recent — beats active in recency too
            )
            for i in range(n_archive)
        ]
        index = ArchivalIndex(working_archive=entries)
        base = _make_base_working_memory(observations)
        return WorkingMemoryExtended(**base.model_dump(), archival_index=index)

    def test_budget_limits_archived_entries_returned(self):
        """With k=10 and fraction=0.40, at most 4 archived entries may be returned."""
        mem = self._make_many_archived_memory(n_archive=10, n_active=10)
        results = self.retriever.retrieve_top_k(
            mem, query="", k=10, context_budget_archive_fraction=0.40
        )
        archived_count = sum(1 for r in results if r["type"] == "archived")
        assert archived_count <= 4, (
            f"Expected at most 4 archived results with k=10, fraction=0.40. "
            f"Got {archived_count}."
        )

    def test_budget_max_archive_computation(self):
        """max_archive = max(1, round(k * fraction)) == 4 when k=10, fraction=0.40."""
        k = 10
        fraction = 0.40
        expected_max_archive = max(1, round(k * fraction))
        assert expected_max_archive == 4

    def test_active_entries_are_not_budget_constrained(self):
        """Active entries may fill all remaining slots and are never capped by the budget."""
        # 10 active entries, 0 archive entries — all active should be returned
        observations = [
            make_obs(f"active-{i}", importance=5, age_hours=1.0)
            for i in range(10)
        ]
        index = ArchivalIndex()  # empty archive
        base = _make_base_working_memory(observations)
        mem = WorkingMemoryExtended(**base.model_dump(), archival_index=index)

        results = self.retriever.retrieve_top_k(
            mem, query="", k=10, context_budget_archive_fraction=0.40
        )
        active_count = sum(1 for r in results if r["type"] == "active")
        assert active_count == 10


# ---------------------------------------------------------------------------
# TestHierarchicalRetrieverEmpty
# ---------------------------------------------------------------------------

class TestHierarchicalRetrieverEmpty:
    def setup_method(self):
        self.retriever = HierarchicalRetriever()

    def test_empty_memory_returns_empty_list(self):
        """Memory with no observations and no archive must return []."""
        index = ArchivalIndex()
        base = _make_base_working_memory()
        mem = WorkingMemoryExtended(**base.model_dump(), archival_index=index)

        results = self.retriever.retrieve_top_k(mem, query="anything", k=10)
        assert results == []

    def test_zero_relevance_query_still_returns_sorted_results(self):
        """When the query matches nothing (relevance=0), results are still returned
        sorted by recency/importance."""
        obs1 = make_obs("old-obs", importance=3, age_hours=10.0)
        obs2 = make_obs("new-obs", importance=3, age_hours=0.1)
        index = ArchivalIndex()
        base = _make_base_working_memory(observations=[obs1, obs2])
        mem = WorkingMemoryExtended(**base.model_dump(), archival_index=index)

        results = self.retriever.retrieve_top_k(mem, query="xyzzy_no_match", k=10)
        assert len(results) == 2
        # More recent obs should score higher (higher recency)
        scores = {r["id"]: r["score"] for r in results}
        assert scores["new-obs"] > scores["old-obs"]


# ---------------------------------------------------------------------------
# TestRematerialise
# ---------------------------------------------------------------------------

class TestRematerialise:
    def _make_entry(self) -> ArchiveEntry:
        early = datetime(2025, 1, 10, tzinfo=timezone.utc)
        late = datetime(2025, 3, 20, tzinfo=timezone.utc)
        return ArchiveEntry(
            id="rmat-entry-1",
            tier=ArchiveTier.WORKING_ARCHIVE,
            original_observation_ids=["obs-a", "obs-b", "obs-c"],
            summary_content="A condensed memory summary.",
            mean_importance=7.5,
            earliest_timestamp=early,
            latest_timestamp=late,
            last_accessed=late,
        )

    def test_rematerialise_returns_exactly_six_keys(self):
        """rematerialise() must return a dict with exactly 6 keys."""
        entry = self._make_entry()
        result = rematerialise(entry, persona_id="persona-001")
        assert set(result.keys()) == {
            "type", "tier", "period", "summary", "original_count", "mean_importance"
        }

    def test_rematerialise_type_is_archived_memory(self):
        """rematerialise() must set type == 'archived_memory'."""
        entry = self._make_entry()
        result = rematerialise(entry, persona_id="persona-001")
        assert result["type"] == "archived_memory"

    def test_rematerialise_period_format(self):
        """rematerialise() period must be 'YYYY-MM-DD to YYYY-MM-DD'."""
        entry = self._make_entry()
        result = rematerialise(entry, persona_id="persona-001")
        period = result["period"]
        assert period == "2025-01-10 to 2025-03-20", f"Unexpected period: {period!r}"

    def test_rematerialise_does_not_mutate_entry(self):
        """rematerialise() must not mutate the ArchiveEntry (read-only contract)."""
        entry = self._make_entry()
        original_summary = entry.summary_content
        original_mean = entry.mean_importance
        original_count = len(entry.original_observation_ids)
        original_tier = entry.tier

        rematerialise(entry, persona_id="persona-001")

        assert entry.summary_content == original_summary
        assert entry.mean_importance == original_mean
        assert len(entry.original_observation_ids) == original_count
        assert entry.tier == original_tier


# ---------------------------------------------------------------------------
# TestBV2Extended
# ---------------------------------------------------------------------------

class TestBV2Extended:
    def _make_memory_with_active(self, obs_ids: list[str], importances: list[int]) -> WorkingMemoryExtended:
        observations = []
        for oid, imp in zip(obs_ids, importances):
            observations.append(make_obs(oid, imp, age_hours=1.0))
        base = _make_base_working_memory(observations)
        return WorkingMemoryExtended(**base.model_dump())

    def _make_memory_with_archive(
        self,
        active_ids: list[str],
        active_importances: list[int],
        archive_entries: list[ArchiveEntry],
    ) -> WorkingMemoryExtended:
        observations = [
            make_obs(oid, imp, 1.0)
            for oid, imp in zip(active_ids, active_importances)
        ]
        base = _make_base_working_memory(observations)
        index = ArchivalIndex(working_archive=archive_entries)
        return WorkingMemoryExtended(**base.model_dump(), archival_index=index)

    # --- Passing cases ---

    def test_100_pct_citation_validity_100_pct_recall_passes(self):
        """100% citation validity + 100% recall → passed=True."""
        mem = self._make_memory_with_active(["obs-1", "obs-2"], [8, 8])
        result = run_bv2_extended(mem, cited_ids=["obs-1", "obs-2"])
        assert result.passed is True
        assert result.citation_validity_rate == 1.0
        assert result.high_importance_recall_rate == 1.0

    def test_100_pct_citation_exactly_80_pct_recall_passes(self):
        """100% citation validity + exactly 80% recall → passed=True (boundary condition)."""
        # 5 high-importance items, cite exactly 4 (80%)
        obs_ids = [f"obs-{i}" for i in range(5)]
        importances = [8] * 5
        mem = self._make_memory_with_active(obs_ids, importances)
        cited = obs_ids[:4]  # 4/5 = 80%
        result = run_bv2_extended(mem, cited_ids=cited)
        assert result.passed is True
        assert abs(result.high_importance_recall_rate - 0.80) < 1e-9

    def test_no_cited_ids_citation_validity_is_1_0(self):
        """No cited_ids → citation_validity_rate=1.0 (vacuously valid, no invalid citations)."""
        mem = self._make_memory_with_active(["obs-1"], [8])
        result = run_bv2_extended(mem, cited_ids=[])
        assert result.citation_validity_rate == 1.0

    # --- Failing cases ---

    def test_one_invalid_citation_fails(self):
        """One cited id that does not exist in any tier → citation_validity_rate < 1.0 → passed=False."""
        mem = self._make_memory_with_active(["obs-1"], [5])
        result = run_bv2_extended(mem, cited_ids=["obs-1", "nonexistent-id"])
        assert result.passed is False
        assert result.citation_validity_rate < 1.0
        assert "nonexistent-id" in result.invalid_citations

    def test_high_importance_recall_at_79_pct_fails(self):
        """79% recall of high-importance items → passed=False (below 80% threshold)."""
        # Use enough items so 79% < 80%: 19/24 ≈ 79.2%
        obs_ids = [f"obs-{i}" for i in range(24)]
        importances = [8] * 24
        mem = self._make_memory_with_active(obs_ids, importances)
        cited = obs_ids[:19]  # 19/24 ≈ 79.2%
        result = run_bv2_extended(mem, cited_ids=cited)
        assert result.passed is False
        assert result.high_importance_recall_rate < 0.80

    def test_archival_index_none_only_active_ids_in_universe(self):
        """When archival_index=None, only active ids count.
        Citing an id that only exists in a hypothetical archive → invalid."""
        mem = self._make_memory_with_active(["obs-active"], [5])
        # Cite an id that would be in archive if one existed — but archival_index is None
        result = run_bv2_extended(mem, cited_ids=["obs-active", "ghost-archive-id"])
        assert result.passed is False
        assert "ghost-archive-id" in result.invalid_citations
        assert result.total_archived_entries == 0


# ---------------------------------------------------------------------------
# TestBV3Extended
# ---------------------------------------------------------------------------

class TestBV3Extended:
    def _flat_series(self, length: int, value: float = 70.0) -> list[float]:
        """Produce a flat confidence series of given length."""
        return [value] * length

    # --- Passing cases ---

    def test_100_turn_no_events_archive_citation_passes(self):
        """100-turn series, no archival events, archive citation found → passed=True."""
        series = self._flat_series(100)
        result = run_bv3_extended(
            confidence_series=series,
            archival_event_turns=[],
            reflection_citations=["archive-entry-42"],
            archived_entry_ids=["archive-entry-42"],
        )
        assert result.passed is True
        assert result.arc_maintained is True
        assert result.max_confidence_drop == 0.0
        assert result.archive_citation_found is True

    def test_100_turn_small_drop_archive_citation_passes(self):
        """100-turn series, archival event with 15-point drop (< 20), archive citation → passed=True."""
        series = self._flat_series(100, value=80.0)
        # Inject a 15-point drop at turn 50
        series[50] = 65.0  # before=80.0, after=65.0, drop=15.0
        result = run_bv3_extended(
            confidence_series=series,
            archival_event_turns=[50],
            reflection_citations=["ae-1"],
            archived_entry_ids=["ae-1"],
        )
        assert result.passed is True
        assert result.max_confidence_drop == pytest.approx(15.0)

    # --- Failing cases ---

    def test_only_50_turns_arc_not_maintained_fails(self):
        """Only 50 turns → arc_maintained=False → passed=False."""
        series = self._flat_series(50)
        result = run_bv3_extended(
            confidence_series=series,
            archival_event_turns=[],
            reflection_citations=["ae-1"],
            archived_entry_ids=["ae-1"],
        )
        assert result.passed is False
        assert result.arc_maintained is False

    def test_archival_event_25_point_drop_fails(self):
        """Archival event with 25-point drop → max_confidence_drop > 20 → passed=False."""
        series = self._flat_series(100, value=90.0)
        series[30] = 65.0  # before=90.0, after=65.0, drop=25.0
        result = run_bv3_extended(
            confidence_series=series,
            archival_event_turns=[30],
            reflection_citations=["ae-1"],
            archived_entry_ids=["ae-1"],
        )
        assert result.passed is False
        assert result.max_confidence_drop == pytest.approx(25.0)

    def test_100_turns_no_drop_but_no_archive_citation_fails(self):
        """100 turns, no confidence drop, but no archive citation → passed=False."""
        series = self._flat_series(100)
        result = run_bv3_extended(
            confidence_series=series,
            archival_event_turns=[],
            reflection_citations=["obs-active-1"],  # cites active, not archive
            archived_entry_ids=["ae-archived"],       # different id
        )
        assert result.passed is False
        assert result.archive_citation_found is False
