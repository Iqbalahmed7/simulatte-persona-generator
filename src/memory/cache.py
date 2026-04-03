"""src/memory/cache.py — Process-scoped core memory string cache.

Core memory is immutable per session and injected into every LLM call.
Re-assembling the same string block on every call wastes CPU and makes
prompt construction harder to reason about. This module provides a
simple dict-based cache keyed on persona_id.

The cache is process-scoped (in-memory only, never persisted).
It stores the pre-assembled text strings returned by the core memory
assembly helpers in perceive.py, reflect.py, and decide.py.

Usage:
    from src.memory.cache import _GLOBAL_CACHE

    block = _GLOBAL_CACHE.get(persona.persona_id)
    if block is None:
        block = _assemble_block(persona)
        _GLOBAL_CACHE.set(persona.persona_id, block)
    # use block
"""
from __future__ import annotations


class CoreMemoryCache:
    """Simple in-memory dict cache for pre-assembled core memory strings.

    Keyed on persona_id (str). Values are the text blocks injected into
    LLM prompts. The cache is process-scoped — it lives for the lifetime
    of the Python process and is never written to disk.

    Thread safety: this class is not thread-safe by design. Simulatte's
    async cognitive loop runs in a single event loop; concurrent access
    from multiple threads is not a supported use case.
    """

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, persona_id: str) -> str | None:
        """Return the cached core memory block, or None on a miss."""
        return self._store.get(persona_id)

    def set(self, persona_id: str, block: str) -> None:
        """Store a core memory block under persona_id."""
        self._store[persona_id] = block

    def invalidate(self, persona_id: str) -> None:
        """Remove the cached block for persona_id (no-op if not present)."""
        self._store.pop(persona_id, None)

    def clear(self) -> None:
        """Evict all entries from the cache."""
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)


# ---------------------------------------------------------------------------
# Module-level singleton — shared across all cognition calls in this process
# ---------------------------------------------------------------------------

_GLOBAL_CACHE: CoreMemoryCache = CoreMemoryCache()
