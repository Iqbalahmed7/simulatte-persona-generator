# SPRINT 3 BRIEF — GOOSE
**Role:** Working Memory + Retrieval Engineer
**Sprint:** 3 — Memory Architecture
**Spec check:** Master Spec §8 (Memory Architecture — all subsections), §14A S3 (core/working split settled), S17 (promotion rules settled), S18 (experiment isolation settled)
**Previous rating:** 20/20 — Perfect Sprint 2. Zero LLM calls, all formulas correct.

---

## Your Job This Sprint

You own the working memory runtime: the write/retrieve/evict operations and the retrieval formula. This is the memory system that accumulates observations and reflections during simulation.

Two files.

---

## File 1: `src/memory/working_memory.py`

### What It Does

Implements all CRUD operations on `WorkingMemory`: write observations, write reflections, retrieve top-K entries by the retrieval formula, evict lowest-importance entries, and reset for experiment isolation.

### Interface

```python
from src.schema.persona import (
    WorkingMemory, Observation, Reflection, SimulationState
)
from datetime import datetime
from typing import Any
import uuid

class WorkingMemoryManager:

    def write_observation(
        self,
        memory: WorkingMemory,
        content: str,
        importance: int,           # 1–10, LLM-assigned at perception time
        emotional_valence: float,  # -1.0 to 1.0
        source_stimulus_id: str | None = None,
    ) -> tuple[WorkingMemory, Observation]:
        """
        Creates a new Observation entry and appends to memory.observations.
        Generates a unique id (uuid4), sets timestamp=now, last_accessed=now.
        Returns updated memory and the new observation.
        Triggers eviction if len(observations) > 1000 after write.
        """
        ...

    def write_reflection(
        self,
        memory: WorkingMemory,
        content: str,
        importance: int,
        source_observation_ids: list[str],  # must be ≥ 2 — validated
    ) -> tuple[WorkingMemory, Reflection]:
        """
        Creates a new Reflection entry and appends to memory.reflections.
        Raises ValueError if len(source_observation_ids) < 2.
        Updates simulation_state.reflection_count += 1.
        Resets simulation_state.importance_accumulator to 0.0 after reflection.
        Returns updated memory and the new reflection.
        """
        ...

    def retrieve_top_k(
        self,
        memory: WorkingMemory,
        query_embedding_or_text: str,   # text used for relevance scoring
        k: int = 10,
        now: datetime | None = None,
    ) -> list[Observation | Reflection]:
        """
        Returns top-K memory entries by retrieval score.
        Retrieval formula: score = α·recency + β·importance + γ·relevance
        Default α=β=γ=1/3 (equal weighting, normalised to sum to 1).
        Updates last_accessed on all returned entries.
        See retrieval.py for formula implementation.
        """
        ...

    def evict(
        self,
        memory: WorkingMemory,
        target_size: int = 900,   # evict until len(observations) ≤ target_size
    ) -> tuple[WorkingMemory, int]:
        """
        Evicts lowest-scoring entries from memory.observations.
        Eviction score = importance × recency_score (NOT relevance — no query at evict time).
        Removes bottom 10% by eviction score, or until target_size is reached.
        Never evicts reflections.
        Returns updated memory and count of evicted entries.
        """
        ...

    def reset(
        self,
        memory: WorkingMemory,
    ) -> WorkingMemory:
        """
        Resets working memory for a new experiment.
        Clears: observations, reflections, plans, brand_memories, simulation_state.
        Returns a fresh WorkingMemory with empty state.
        Core memory is NOT touched — this method does not receive it.
        Idempotent: calling twice produces same result as calling once.
        """
        ...

    def increment_accumulator(
        self,
        memory: WorkingMemory,
        importance: int,
    ) -> WorkingMemory:
        """
        Adds importance to simulation_state.importance_accumulator.
        Called after every perceive() in the cognitive loop (Sprint 4).
        Returns updated memory.
        """
        ...

    def should_reflect(
        self,
        memory: WorkingMemory,
        threshold: float = 50.0,
    ) -> bool:
        """
        Returns True if importance_accumulator > threshold.
        Default threshold = 50 (open question O5 — subject to empirical validation).
        """
        return memory.simulation_state.importance_accumulator > threshold
```

---

## File 2: `src/memory/retrieval.py`

### What It Does

Implements the retrieval formula from Master Spec §8 and Generative Agents (Park et al.). Used by `working_memory.py` and directly by the cognitive loop in Sprint 4.

### The Formula

```
score(entry) = α·recency(entry) + β·importance(entry) + γ·relevance(entry, query)

Where:
  α = β = γ = 1/3  (equal weighting — Open Question O6)

  recency(entry)    = exp(-λ · hours_since_last_access)
                      λ = 0.01  (slow decay — Open Question O7)
                      hours_since_last_access = (now - entry.last_accessed).total_seconds() / 3600

  importance(entry) = entry.importance / 10.0   # normalise 1–10 to 0.0–1.0

  relevance(entry, query) = keyword_overlap_score(entry.content, query)
                            # Simple: len(query_words ∩ content_words) / len(query_words)
                            # query_words = set of lowercased, stopword-stripped tokens
                            # Sprint 4 may upgrade to embedding similarity — this is the v1 stub
```

### Interface

```python
from src.schema.persona import Observation, Reflection
from datetime import datetime

# Tunable weights (Open Questions O6, O7 — set defaults, allow override)
DEFAULT_ALPHA = 1/3
DEFAULT_BETA  = 1/3
DEFAULT_GAMMA = 1/3
DEFAULT_DECAY_LAMBDA = 0.01

def score_entry(
    entry: Observation | Reflection,
    query: str,
    now: datetime,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    gamma: float = DEFAULT_GAMMA,
    decay_lambda: float = DEFAULT_DECAY_LAMBDA,
) -> float:
    """Compute retrieval score for a single memory entry."""
    ...

def retrieve_top_k(
    entries: list[Observation | Reflection],
    query: str,
    k: int,
    now: datetime | None = None,
) -> list[Observation | Reflection]:
    """
    Score all entries, return top-K sorted descending by score.
    Does NOT update last_accessed — that is WorkingMemoryManager's responsibility.
    """
    ...

def recency_score(entry: Observation | Reflection, now: datetime, decay_lambda: float) -> float:
    """exp(-λ · hours_since_last_access)"""
    ...

def importance_score(entry: Observation | Reflection) -> float:
    """entry.importance / 10.0"""
    ...

def relevance_score(entry: Observation | Reflection, query: str) -> float:
    """Keyword overlap: len(query_words ∩ content_words) / max(len(query_words), 1)"""
    ...
```

### Stopword List

Use a minimal inline stopword set — no NLTK dependency:
```python
_STOPWORDS = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "of",
    "and", "or", "but", "for", "with", "this", "that", "was", "are",
    "be", "been", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "not", "no", "i", "my", "you", "your",
    "they", "their", "we", "our", "he", "she", "his", "her",
}
```

---

## Integration Contract

- **Called by Sprint 4 cognitive loop:** `WorkingMemoryManager.write_observation()`, `retrieve_top_k()`, `increment_accumulator()`, `should_reflect()`, `write_reflection()`
- **Called by Sprint 5 experiment modality:** `WorkingMemoryManager.reset()`
- **Exports:** `WorkingMemoryManager` from `src.memory.working_memory`, all functions from `src.memory.retrieval`
- **No LLM calls** in either file — purely deterministic

---

## Constraints

- Cap at 1,000 observations. Evict when exceeded. Reflections are never evicted.
- `reset()` must be idempotent — calling it twice must produce the same result as once.
- Core memory is never touched by any method in these files.
- All timestamps use `datetime.now(timezone.utc)`.
- `WorkingMemory` is a Pydantic model — use `.model_copy(update={...})` for immutable updates, or work with mutable copies. Do not mutate in place if the caller holds a reference.

---

## Outcome File

When done, write `sprints/outcome_goose.md` with:
1. Files created (line counts)
2. Retrieval formula — show a worked example with sample values
3. Eviction logic — describe the scoring and order
4. `should_reflect` threshold — note it as Open Question O5 and the default you used
5. Any deviations from the spec interface
6. Known gaps
