"""tests/test_core_memory_cache.py — CoreMemoryCache unit tests.

No LLM calls. Tests the cache class directly and the wired behaviour
in perceive/reflect/decide core-memory block functions.
"""
from __future__ import annotations

import pytest

from src.memory.cache import CoreMemoryCache, _GLOBAL_CACHE


# ---------------------------------------------------------------------------
# CoreMemoryCache unit tests
# ---------------------------------------------------------------------------

class TestCorMemoryCacheBasic:
    def setup_method(self):
        self.cache = CoreMemoryCache()

    def test_miss_returns_none(self):
        assert self.cache.get("pg-test-001") is None

    def test_set_then_get_returns_value(self):
        self.cache.set("pg-test-001", "block text")
        assert self.cache.get("pg-test-001") == "block text"

    def test_second_call_returns_same_string(self):
        """Second call with same persona_id must return cached string (no re-assembly)."""
        self.cache.set("pg-test-002", "original block")
        first = self.cache.get("pg-test-002")
        second = self.cache.get("pg-test-002")
        assert first == second == "original block"

    def test_invalidate_forces_miss(self):
        """invalidate() must cause the next get() to return None."""
        self.cache.set("pg-test-003", "some block")
        assert self.cache.get("pg-test-003") == "some block"
        self.cache.invalidate("pg-test-003")
        assert self.cache.get("pg-test-003") is None

    def test_invalidate_nonexistent_is_noop(self):
        self.cache.invalidate("pg-nonexistent-999")  # must not raise

    def test_clear_evicts_all(self):
        self.cache.set("pg-a-001", "block a")
        self.cache.set("pg-b-002", "block b")
        self.cache.clear()
        assert self.cache.get("pg-a-001") is None
        assert self.cache.get("pg-b-002") is None
        assert len(self.cache) == 0

    def test_len_tracks_entries(self):
        assert len(self.cache) == 0
        self.cache.set("pg-x-001", "block")
        assert len(self.cache) == 1
        self.cache.set("pg-x-002", "block2")
        assert len(self.cache) == 2
        self.cache.invalidate("pg-x-001")
        assert len(self.cache) == 1


class TestCacheIsolationBetweenPersonas:
    def setup_method(self):
        self.cache = CoreMemoryCache()

    def test_two_personas_do_not_collide(self):
        """Cache must correctly handle two different persona_ids without collision."""
        self.cache.set("pg-alice-001", "Alice's block")
        self.cache.set("pg-bob-002", "Bob's block")

        assert self.cache.get("pg-alice-001") == "Alice's block"
        assert self.cache.get("pg-bob-002") == "Bob's block"

        # Invalidate one — the other must be unaffected
        self.cache.invalidate("pg-alice-001")
        assert self.cache.get("pg-alice-001") is None
        assert self.cache.get("pg-bob-002") == "Bob's block"

    def test_decide_cache_key_separate_from_perceive_reflect_key(self):
        """decide uses '<persona_id>:decide' — must not collide with base key."""
        base_key = "pg-test-010"
        decide_key = "pg-test-010:decide"

        self.cache.set(base_key, "perceive/reflect block")
        self.cache.set(decide_key, "decide block with constraints")

        assert self.cache.get(base_key) == "perceive/reflect block"
        assert self.cache.get(decide_key) == "decide block with constraints"

        self.cache.invalidate(base_key)
        assert self.cache.get(base_key) is None
        assert self.cache.get(decide_key) == "decide block with constraints"


# ---------------------------------------------------------------------------
# Integration: wired cache in perceive._core_memory_block
# ---------------------------------------------------------------------------

class TestCacheWiredInCognitiveModules:
    """Verify the perceive/reflect core_memory_block function uses the global cache."""

    def setup_method(self):
        # Clear global cache before each test so we start from a clean slate
        _GLOBAL_CACHE.clear()

    def teardown_method(self):
        _GLOBAL_CACHE.clear()

    def _make_minimal_persona(self, persona_id: str):
        """Build a minimal PersonaRecord-like object sufficient for _core_memory_block."""
        from unittest.mock import MagicMock
        persona = MagicMock()
        persona.persona_id = persona_id
        persona.memory.core.identity_statement = "I am a test persona."
        persona.memory.core.key_values = ["value1", "value2", "value3"]
        persona.memory.core.tendency_summary = "Tends to prefer quality over price."
        return persona

    def test_perceive_cache_hit_on_second_call(self):
        from src.cognition.perceive import _core_memory_block as perceive_block
        persona = self._make_minimal_persona("pg-cache-test-001")

        # First call — cache miss, builds and stores
        block1 = perceive_block(persona)
        assert _GLOBAL_CACHE.get("pg-cache-test-001") == block1

        # Second call — cache hit, must return same string
        block2 = perceive_block(persona)
        assert block1 == block2

    def test_reflect_cache_hit_on_second_call(self):
        from src.cognition.reflect import _core_memory_block as reflect_block
        persona = self._make_minimal_persona("pg-cache-test-002")

        block1 = reflect_block(persona)
        block2 = reflect_block(persona)
        assert block1 == block2
        assert _GLOBAL_CACHE.get("pg-cache-test-002") == block1

    def test_invalidate_forces_re_assembly(self):
        from src.cognition.perceive import _core_memory_block as perceive_block
        persona = self._make_minimal_persona("pg-cache-test-003")

        block1 = perceive_block(persona)
        _GLOBAL_CACHE.invalidate("pg-cache-test-003")

        # Mutate persona's core — simulates a promotion that updated tendency_summary
        persona.memory.core.tendency_summary = "Updated tendency after promotion."
        block2 = perceive_block(persona)

        assert block1 != block2
        assert "Updated tendency" in block2

    def test_two_personas_cache_independently(self):
        from src.cognition.perceive import _core_memory_block as perceive_block
        p1 = self._make_minimal_persona("pg-alpha-001")
        p2 = self._make_minimal_persona("pg-beta-002")
        p2.memory.core.identity_statement = "I am a different persona."

        b1 = perceive_block(p1)
        b2 = perceive_block(p2)

        assert b1 != b2
        assert _GLOBAL_CACHE.get("pg-alpha-001") == b1
        assert _GLOBAL_CACHE.get("pg-beta-002") == b2
