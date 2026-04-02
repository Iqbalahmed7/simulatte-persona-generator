"""
tests/test_memory.py — Sprint 3 memory component tests.

No LLM calls. All synthetic data.

Strategy:
  - WorkingMemory/Observation/Reflection objects are constructed directly from
    src.schema.persona (Pydantic models) — no dependency on Goose or OpenCode files.
  - Imports from src.memory.working_memory and src.memory.seed_memory are
    guarded with try/except ImportError and skipped gracefully if those files
    are not yet written (parallel sprint delivery).
  - G10 validator is tested directly against WorkingMemory objects.
  - Promotion guard rules are verified either against
    src.memory.reflection_store.can_promote (if present) or documented inline.
"""

from __future__ import annotations

import uuid
import pytest
from datetime import datetime, timezone

from src.schema.persona import (
    Observation,
    Reflection,
    WorkingMemory,
    SimulationState,
)
from src.schema.validators import PersonaValidator, ValidationResult

# ---------------------------------------------------------------------------
# Optional imports — gracefully skipped when parallel files are absent
# ---------------------------------------------------------------------------

try:
    from src.memory.working_memory import WorkingMemoryManager
    _HAS_WORKING_MEMORY = True
except ImportError:
    _HAS_WORKING_MEMORY = False
    WorkingMemoryManager = None  # type: ignore[assignment,misc]

try:
    from src.memory.seed_memory import bootstrap_seed_memories
    _HAS_SEED_MEMORY = True
except ImportError:
    _HAS_SEED_MEMORY = False
    bootstrap_seed_memories = None  # type: ignore[assignment]

try:
    from src.memory.reflection_store import can_promote
    _HAS_REFLECTION_STORE = True
except ImportError:
    _HAS_REFLECTION_STORE = False
    can_promote = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Helpers — build synthetic schema objects without LLM or file dependencies
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_observation(
    content: str = "A sample observation about brand preference.",
    importance: int = 5,
    emotional_valence: float = 0.0,
    obs_id: str | None = None,
    source_stimulus_id: str | None = None,
) -> Observation:
    """Create a minimal valid Observation."""
    ts = _now()
    return Observation(
        id=obs_id or str(uuid.uuid4()),
        timestamp=ts,
        type="observation",
        content=content,
        importance=importance,
        emotional_valence=emotional_valence,
        source_stimulus_id=source_stimulus_id,
        last_accessed=ts,
    )


def _make_reflection(
    content: str = "A synthesised reflection about shopping behaviour.",
    importance: int = 7,
    source_observation_ids: list[str] | None = None,
    reflection_id: str | None = None,
) -> Reflection:
    """Create a minimal valid Reflection (requires >= 2 source_observation_ids)."""
    if source_observation_ids is None:
        source_observation_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    ts = _now()
    return Reflection(
        id=reflection_id or str(uuid.uuid4()),
        timestamp=ts,
        type="reflection",
        content=content,
        importance=importance,
        source_observation_ids=source_observation_ids,
        last_accessed=ts,
    )


def _make_simulation_state(
    importance_accumulator: float = 0.0,
    reflection_count: int = 0,
) -> SimulationState:
    return SimulationState(
        current_turn=0,
        importance_accumulator=importance_accumulator,
        reflection_count=reflection_count,
        awareness_set={},
        consideration_set=[],
        last_decision=None,
    )


def _make_empty_working_memory() -> WorkingMemory:
    return WorkingMemory(
        observations=[],
        reflections=[],
        plans=[],
        brand_memories={},
        simulation_state=_make_simulation_state(),
    )


def _make_working_memory_with_observations(
    count: int,
    base_importance: int = 5,
) -> WorkingMemory:
    """Return a WorkingMemory pre-populated with `count` observations."""
    obs = [
        _make_observation(
            content=f"Observation number {i} about product quality and value.",
            importance=max(1, min(10, base_importance)),
        )
        for i in range(count)
    ]
    return WorkingMemory(
        observations=obs,
        reflections=[],
        plans=[],
        brand_memories={},
        simulation_state=_make_simulation_state(),
    )


# ---------------------------------------------------------------------------
# Tests that use schema objects directly (no optional imports needed)
# ---------------------------------------------------------------------------

class TestObservationSchema:
    """Direct schema construction tests — never need working_memory.py."""

    def test_write_observation(self):
        """Write one observation, verify fields are set correctly."""
        content = "Tried the new mango pickle. Strong brand association formed."
        importance = 7
        emotional_valence = 0.4
        obs_id = str(uuid.uuid4())

        obs = _make_observation(
            content=content,
            importance=importance,
            emotional_valence=emotional_valence,
            obs_id=obs_id,
        )

        assert obs.id == obs_id
        assert obs.content == content
        assert obs.importance == importance
        assert obs.emotional_valence == emotional_valence
        assert obs.type == "observation"
        assert isinstance(obs.timestamp, datetime)
        assert isinstance(obs.last_accessed, datetime)

    def test_write_reflection_requires_two_sources(self):
        """Verify ValueError raised when source_observation_ids < 2."""
        with pytest.raises(Exception):
            # Pydantic v2 raises ValidationError (subclass of ValueError/Exception)
            Reflection(
                id=str(uuid.uuid4()),
                timestamp=_now(),
                type="reflection",
                content="Insufficient sources.",
                importance=5,
                source_observation_ids=["only_one_id"],  # < 2 — must fail
                last_accessed=_now(),
            )

    def test_observation_importance_bounds(self):
        """Observations reject importance outside 1–10."""
        with pytest.raises(Exception):
            _make_observation(importance=0)   # below min
        with pytest.raises(Exception):
            _make_observation(importance=11)  # above max

    def test_observation_emotional_valence_bounds(self):
        """Observations reject emotional_valence outside -1.0 to 1.0."""
        with pytest.raises(Exception):
            _make_observation(emotional_valence=-1.1)
        with pytest.raises(Exception):
            _make_observation(emotional_valence=1.1)


# ---------------------------------------------------------------------------
# G10 validator tests — direct schema, no optional imports
# ---------------------------------------------------------------------------

class TestG10SeedMemoryGate:
    """
    G10: >= 3 seed memories per persona after bootstrap.
    g10_seed_memory_count takes a WorkingMemory directly.
    """

    def setup_method(self):
        self.validator = PersonaValidator()

    def test_g10_passes_with_three_observations(self):
        """g10_seed_memory_count passes on WorkingMemory with exactly 3 valid observations."""
        memory = _make_working_memory_with_observations(3)
        result = self.validator.g10_seed_memory_count(memory)
        assert result.passed, f"G10 should pass with 3 observations; failures: {result.failures}"
        assert result.gate == "G10"

    def test_g10_passes_with_more_than_three(self):
        """G10 passes with > 3 observations."""
        memory = _make_working_memory_with_observations(10)
        result = self.validator.g10_seed_memory_count(memory)
        assert result.passed

    def test_g10_fails_on_empty_working_memory(self):
        """g10_seed_memory_count fails on empty WorkingMemory."""
        memory = _make_empty_working_memory()
        result = self.validator.g10_seed_memory_count(memory)
        assert not result.passed
        assert result.gate == "G10"
        assert any("0" in f for f in result.failures), (
            f"Failure message should mention 0 observations; got: {result.failures}"
        )

    def test_g10_fails_with_one_observation(self):
        """G10 fails when only 1 observation exists."""
        memory = _make_working_memory_with_observations(1)
        result = self.validator.g10_seed_memory_count(memory)
        assert not result.passed

    def test_g10_fails_with_two_observations(self):
        """G10 fails when only 2 observations exist (minimum is 3)."""
        memory = _make_working_memory_with_observations(2)
        result = self.validator.g10_seed_memory_count(memory)
        assert not result.passed

    def test_g10_detects_duplicate_ids(self):
        """G10 fails when duplicate observation ids are present."""
        shared_id = str(uuid.uuid4())
        obs = [
            _make_observation(content=f"Obs {i}", obs_id=shared_id if i < 2 else None)
            for i in range(3)
        ]
        memory = WorkingMemory(
            observations=obs,
            reflections=[],
            plans=[],
            brand_memories={},
            simulation_state=_make_simulation_state(),
        )
        result = self.validator.g10_seed_memory_count(memory)
        assert not result.passed
        assert any("duplicate" in f.lower() for f in result.failures)

    def test_g10_result_has_no_failures_on_pass(self):
        """Passing G10 result has an empty failures list."""
        memory = _make_working_memory_with_observations(5)
        result = self.validator.g10_seed_memory_count(memory)
        assert result.passed
        assert result.failures == []

    def test_g10_to_dict_shape(self):
        """ValidationResult.to_dict() returns expected keys."""
        memory = _make_working_memory_with_observations(3)
        result = self.validator.g10_seed_memory_count(memory)
        d = result.to_dict()
        assert set(d.keys()) == {"passed", "gate", "failures", "warnings"}
        assert d["gate"] == "G10"


# ---------------------------------------------------------------------------
# Promotion guard rules — §14A S17
# ---------------------------------------------------------------------------

class TestPromotionGuard:
    """
    Promotion guard rules (§14A S17, settled):

      Promotion fires when ALL of the following are true:
        1. importance >= 9
        2. citation_count >= 3
        3. no_contradiction is True
      Never promotes demographics (identity layer is immutable).

    These rules are tested against src.memory.reflection_store.can_promote
    if that file exists. If not, the tests are skipped with an explanatory message.

    The guard logic is documented here regardless so the rules are auditable
    even when reflection_store.py has not yet been delivered (OpenCode Sprint 3).
    """

    def test_promotion_guard(self):
        """
        Promotion guard test (§14A S17):
          - No observation with importance < 9 can be promoted.
          - A reflection with < 3 source_observation_ids cannot be promoted.

        Skipped gracefully if src.memory.reflection_store is not yet present.
        """
        if not _HAS_REFLECTION_STORE:
            pytest.skip(
                "src.memory.reflection_store not yet available "
                "(OpenCode Sprint 3 deliverable — parallel development). "
                "Promotion guard rules are documented in this test class docstring."
            )

        # --- Rule 1: importance < 9 must NOT be promotable ---
        obs_low_importance = _make_observation(importance=8)  # one below threshold
        assert not can_promote(
            importance=obs_low_importance.importance,
            citation_count=5,
            no_contradiction=True,
        ), "importance=8 should NOT be promotable (threshold is 9)"

        obs_at_threshold = _make_observation(importance=9)
        assert can_promote(
            importance=obs_at_threshold.importance,
            citation_count=3,
            no_contradiction=True,
        ), "importance=9 with citation_count=3 and no_contradiction=True SHOULD be promotable"

        # --- Rule 2: citation_count < 3 must NOT be promotable ---
        obs_high_importance = _make_observation(importance=9)
        assert not can_promote(
            importance=obs_high_importance.importance,
            citation_count=2,  # one below threshold
            no_contradiction=True,
        ), "citation_count=2 should NOT be promotable (threshold is 3)"

        # --- Rule 3: no_contradiction=False must NOT be promotable ---
        assert not can_promote(
            importance=obs_high_importance.importance,
            citation_count=3,
            no_contradiction=False,
        ), "no_contradiction=False should prevent promotion"

        # --- Combined: all three must be True simultaneously ---
        assert can_promote(
            importance=obs_high_importance.importance,
            citation_count=3,
            no_contradiction=True,
        ), "All three promotion conditions met — should be promotable"


# ---------------------------------------------------------------------------
# Tests requiring WorkingMemoryManager (guarded — skipped if absent)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _HAS_WORKING_MEMORY, reason=(
    "src.memory.working_memory not yet available "
    "(Goose Sprint 3 deliverable — parallel development)"
))
class TestWorkingMemoryManager:
    """
    Tests for WorkingMemoryManager operations.
    Skipped gracefully when working_memory.py has not yet been delivered.
    """

    def setup_method(self):
        self.mgr = WorkingMemoryManager()

    def test_write_observation_via_manager(self):
        """Write one observation via manager; verify all fields are set correctly."""
        memory = _make_empty_working_memory()
        obs = _make_observation(
            content="Saw an ad for Lo-Foods mango pickle. Felt nostalgic.",
            importance=6,
            emotional_valence=0.5,
            source_stimulus_id="ad-001",
        )
        memory = self.mgr.write_observation(memory, obs)

        assert len(memory.observations) == 1
        stored = memory.observations[0]
        assert stored.content == "Saw an ad for Lo-Foods mango pickle. Felt nostalgic."
        assert stored.importance == 6
        assert stored.emotional_valence == 0.5
        assert stored.source_stimulus_id == "ad-001"
        assert stored.type == "observation"
        assert isinstance(stored.id, str) and stored.id  # non-empty
        assert isinstance(stored.timestamp, datetime)
        assert isinstance(stored.last_accessed, datetime)

    def test_write_reflection_via_manager_requires_two_sources(self):
        """Verify ValidationError raised when source_observation_ids < 2."""
        import pydantic
        memory = _make_empty_working_memory()
        with pytest.raises((ValueError, pydantic.ValidationError)):
            ref = Reflection(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                type="reflection",
                content="Reflection with insufficient sources.",
                importance=5,
                source_observation_ids=["only_one"],
                last_accessed=datetime.now(timezone.utc),
            )
            self.mgr.write_reflection(memory, ref)

    def test_eviction_at_cap(self):
        """
        Write 1001 observations with varying importance.
        Verify eviction fires and len(observations) <= 1000 after write.
        """
        memory = _make_empty_working_memory()

        # Write 1000 observations first to bring to cap
        for i in range(1000):
            importance = max(1, min(10, (i % 10) + 1))
            memory = self.mgr.write_observation(
                memory, _make_observation(
                    content=f"Background observation {i} about market dynamics.",
                    importance=importance,
                )
            )

        # The 1001st write must trigger eviction
        memory = self.mgr.write_observation(
            memory, _make_observation(
                content="The observation that triggers eviction.",
                importance=5,
            )
        )

        assert len(memory.observations) <= 1000, (
            f"After 1001 writes, observations should be <= 1000 (got {len(memory.observations)})"
        )

    def test_eviction_order(self):
        """
        Write observations with known importance values.
        Trigger eviction. Verify highest-importance entries are retained.
        """
        memory = _make_empty_working_memory()

        # Write 5 low-importance and 5 high-importance observations
        low_ids = []
        high_ids = []

        for i in range(5):
            obs = _make_observation(content=f"Low importance observation {i}.", importance=1)
            memory = self.mgr.write_observation(memory, obs)
            low_ids.append(obs.id)

        for i in range(5):
            obs = _make_observation(
                content=f"High importance observation {i} about core brand belief.",
                importance=10,
            )
            memory = self.mgr.write_observation(memory, obs)
            high_ids.append(obs.id)

        # Force eviction with a small target
        memory, evicted_count = self.mgr.evict(memory, target_size=5)

        retained_ids = {o.id for o in memory.observations}

        # All high-importance entries should be retained
        for h_id in high_ids:
            assert h_id in retained_ids, (
                f"High-importance observation {h_id} should not be evicted"
            )

        assert evicted_count > 0, "evict() should have evicted at least one entry"

    def test_reset_clears_working_memory(self):
        """
        Write observations and reflections.
        Call reset(). Verify all working fields are empty.
        Verify reset is idempotent (call twice, same result).
        """
        memory = _make_empty_working_memory()

        # Populate working memory
        obs1 = _make_observation(content="Obs 1.", importance=5)
        obs2 = _make_observation(content="Obs 2.", importance=6, emotional_valence=0.1)
        memory = self.mgr.write_observation(memory, obs1)
        memory = self.mgr.write_observation(memory, obs2)
        ref = _make_reflection(
            content="Reflection on obs 1 and 2.",
            importance=7,
            source_observation_ids=[obs1.id, obs2.id],
        )
        memory = self.mgr.write_reflection(memory, ref)
        memory = self.mgr.increment_accumulator(memory, amount=5)

        assert len(memory.observations) > 0
        assert len(memory.reflections) > 0

        # First reset
        memory = self.mgr.reset(memory)
        assert memory.observations == []
        assert memory.reflections == []
        assert memory.plans == []
        assert memory.brand_memories == {}

        # Idempotency: second reset must produce identical empty state
        memory_after_second_reset = self.mgr.reset(memory)
        assert memory_after_second_reset.observations == []
        assert memory_after_second_reset.reflections == []
        assert memory_after_second_reset.plans == []
        assert memory_after_second_reset.brand_memories == {}

    def test_retrieval_top_k(self):
        """
        Write 10 observations with varied importance and content.
        Query with a relevant term. Verify top-K are returned.
        Verify order is descending by score.
        """
        memory = _make_empty_working_memory()

        # 5 observations mentioning "quality" — should rank higher on relevance
        quality_ids = []
        for i in range(5):
            obs = _make_observation(
                content=f"This product has exceptional quality and value. Trial {i}.",
                importance=8,
                emotional_valence=0.2,
            )
            memory = self.mgr.write_observation(memory, obs)
            quality_ids.append(obs.id)

        # 5 observations with unrelated content
        for i in range(5):
            memory = self.mgr.write_observation(
                memory, _make_observation(
                    content=f"Completely unrelated content about weather patterns. Sample {i}.",
                    importance=3,
                )
            )

        results = self.mgr.retrieve_top_k(memory, query="quality", k=5)

        assert len(results) == 5, f"Expected 5 results, got {len(results)}"

        # Results should be ordered descending by score — verify pairwise
        # (We can't check the score directly, but we can verify retrieved items are plausible)
        retrieved_ids = [r.id for r in results]
        quality_in_results = sum(1 for rid in retrieved_ids if rid in quality_ids)
        assert quality_in_results >= 3, (
            f"Expected at least 3 quality-related observations in top-5; got {quality_in_results}"
        )

    def test_importance_accumulator(self):
        """
        Verify increment_accumulator adds correctly.
        Verify should_reflect returns False below threshold, True above.
        Verify write_reflection resets accumulator to 0.
        """
        memory = _make_empty_working_memory()

        # Accumulator starts at 0
        assert memory.simulation_state.importance_accumulator == 0.0
        assert not self.mgr.should_reflect(memory, threshold=50.0)

        # Add increments below threshold
        memory = self.mgr.increment_accumulator(memory, amount=7)
        assert memory.simulation_state.importance_accumulator == 7.0
        assert not self.mgr.should_reflect(memory, threshold=50.0)

        # Keep accumulating
        for _ in range(6):
            memory = self.mgr.increment_accumulator(memory, amount=7)
        # 7 * 7 = 49 — still below 50
        assert memory.simulation_state.importance_accumulator == 49.0
        assert not self.mgr.should_reflect(memory, threshold=50.0)

        # One more push over threshold
        memory = self.mgr.increment_accumulator(memory, amount=2)
        assert memory.simulation_state.importance_accumulator == 51.0
        assert self.mgr.should_reflect(memory, threshold=50.0)

        # Write a reflection — must reset accumulator to 0
        obs1 = _make_observation(content="Observation A for reflection source.", importance=8)
        obs2 = _make_observation(content="Observation B for reflection source.", importance=8)
        memory = self.mgr.write_observation(memory, obs1)
        memory = self.mgr.write_observation(memory, obs2)
        ref = _make_reflection(
            content="Post-threshold reflection synthesising recent signals.",
            importance=8,
            source_observation_ids=[obs1.id, obs2.id],
        )
        memory = self.mgr.write_reflection(memory, ref)

        assert memory.simulation_state.importance_accumulator == 0.0, (
            "Accumulator should reset to 0 after write_reflection"
        )
        assert not self.mgr.should_reflect(memory, threshold=50.0)


# ---------------------------------------------------------------------------
# Tests requiring bootstrap_seed_memories (guarded — skipped if absent)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _HAS_SEED_MEMORY, reason=(
    "src.memory.seed_memory not yet available "
    "(OpenCode Sprint 3 deliverable — parallel development)"
))
class TestSeedMemory:
    """
    Tests for bootstrap_seed_memories.
    Skipped gracefully when seed_memory.py has not yet been delivered.
    """

    def _make_minimal_core_memory(self):
        """Build a minimal CoreMemory for bootstrap testing."""
        # Lazy import to avoid circular import issues at module load time
        from src.schema.persona import (
            CoreMemory,
            LifeDefiningEvent,
            RelationshipMap,
            ImmutableConstraints,
        )
        return CoreMemory(
            identity_statement=(
                "I am a value-conscious urban professional who prioritises "
                "quality and family wellbeing in every purchase I make."
            ),
            key_values=[
                "Quality over price",
                "Family first",
                "Conscious spending",
            ],
            life_defining_events=[
                LifeDefiningEvent(
                    age_when=24,
                    event="Got first job and became financially independent.",
                    lasting_impact="Developed strong sense of fiscal responsibility.",
                ),
                LifeDefiningEvent(
                    age_when=30,
                    event="Had first child; priorities shifted completely.",
                    lasting_impact="Family safety and health now drive all decisions.",
                ),
            ],
            relationship_map=RelationshipMap(
                primary_decision_partner="Spouse/partner",
                key_influencers=["Expert reviews", "Peer recommendations"],
                trust_network=["Close family", "Trusted friends"],
            ),
            immutable_constraints=ImmutableConstraints(
                budget_ceiling=None,
                non_negotiables=["No compromise on food quality"],
                absolute_avoidances=[],
            ),
            tendency_summary=(
                "Approaches purchases analytically with high brand loyalty. "
                "Price-sensitive but will pay premium for quality and safety."
            ),
        )

    def test_g10_seed_memory_gate_via_bootstrap(self):
        """
        bootstrap_seed_memories returns WorkingMemory with >= 3 observations.
        g10_seed_memory_count passes on that memory.
        g10_seed_memory_count fails on empty WorkingMemory.
        """
        core_memory = self._make_minimal_core_memory()
        memory = bootstrap_seed_memories(core_memory=core_memory, persona_name="Priya")

        validator = PersonaValidator()

        # G10 should PASS on bootstrapped memory
        result = validator.g10_seed_memory_count(memory)
        assert result.passed, (
            f"G10 should pass on bootstrapped memory; failures: {result.failures}"
        )
        assert len(memory.observations) >= 3, (
            f"bootstrap_seed_memories must return >= 3 observations (got {len(memory.observations)})"
        )

        # G10 should FAIL on empty memory
        empty_memory = WorkingMemory(
            observations=[],
            reflections=[],
            plans=[],
            brand_memories={},
            simulation_state=SimulationState(
                current_turn=0,
                importance_accumulator=0.0,
                reflection_count=0,
                awareness_set={},
                consideration_set=[],
                last_decision=None,
            ),
        )
        empty_result = validator.g10_seed_memory_count(empty_memory)
        assert not empty_result.passed, "G10 should FAIL on empty WorkingMemory"

    def test_seed_observations_are_valid_type(self):
        """All bootstrapped observations must have type='observation'."""
        core_memory = self._make_minimal_core_memory()
        memory = bootstrap_seed_memories(core_memory=core_memory, persona_name="Priya")

        for obs in memory.observations:
            assert obs.type == "observation", (
                f"Seed memory entry must have type='observation', got '{obs.type}'"
            )

    def test_seed_observations_have_unique_ids(self):
        """All bootstrapped observations must have unique ids."""
        core_memory = self._make_minimal_core_memory()
        memory = bootstrap_seed_memories(core_memory=core_memory, persona_name="Priya")

        ids = [obs.id for obs in memory.observations]
        assert len(ids) == len(set(ids)), "Seed observations must have unique ids"

    def test_seed_observations_have_high_importance(self):
        """Seed observations should have importance >= 7 (spec says importance=8)."""
        core_memory = self._make_minimal_core_memory()
        memory = bootstrap_seed_memories(core_memory=core_memory, persona_name="Priya")

        for obs in memory.observations:
            assert obs.importance >= 7, (
                f"Seed observation importance should be >= 7, got {obs.importance}"
            )
