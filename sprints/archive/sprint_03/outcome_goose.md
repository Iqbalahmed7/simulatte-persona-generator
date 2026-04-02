# SPRINT 3 OUTCOME — GOOSE
**Engineer:** Goose
**Role:** Working Memory + Retrieval Engineer
**Sprint:** 3 — Memory Architecture
**Date:** 2026-04-02
**Status:** COMPLETE

---

## 1. Files Created

| File | Lines | Description |
|------|-------|-------------|
| `src/memory/retrieval.py` | 143 | Deterministic retrieval formula: recency × importance × relevance |
| `src/memory/working_memory.py` | 310 | `WorkingMemoryManager` — all CRUD on `WorkingMemory` |

Zero LLM calls in either file. All computation is deterministic.

---

## 2. Retrieval Formula — Worked Example

Formula: `score = α·recency + β·importance + γ·relevance`
Default weights: α = β = γ = 1/3

**Sample entry:**
- `content`: "brand loyalty coffee purchase morning routine"
- `importance`: 8
- `last_accessed`: 1 hour ago
- `query`: "coffee morning brand"

**Component scores:**

| Component | Formula | Value |
|-----------|---------|-------|
| recency | exp(−0.01 × 1.0 hour) | 0.990050 |
| importance | 8 / 10 | 0.800000 |
| relevance | \|{coffee, morning, brand} ∩ {brand, loyalty, coffee, purchase, morning, routine}\| / 3 = 3/3 | 1.000000 |
| **score** | (0.990050 + 0.800000 + 1.000000) / 3 | **0.930017** |

A second entry "price discount sale supermarket" with importance=3 and last_accessed=now scored 0.434 — correctly ranked below.

**Relevance tokenisation:** lowercase, split on `[a-zA-Z0-9']+`, strip from the 37-word `_STOPWORDS` set. Division by `max(len(query_words), 1)` guards against empty queries.

---

## 3. Eviction Logic

**When eviction triggers:** `write_observation` triggers eviction automatically when `len(observations) > 1000` after the write, targeting `target_size=900`.

**Eviction score per observation:** `importance × recency_score(entry, now, λ=0.01)`
Relevance is excluded — there is no query at eviction time.

**Order of removal:**
1. Score all observations ascending (lowest eviction score = least important + most stale = first to go).
2. Compute `bottom_10pct = max(1, int(total * 0.10))`.
3. Compute `must_remove = current_size − target_size`.
4. Remove `max(bottom_10pct, must_remove)` entries from the bottom of the sorted list.

Reflections are never evicted.

---

## 4. `should_reflect` Threshold — Open Question O5

Default threshold = **50.0**.

`should_reflect` returns `True` when `simulation_state.importance_accumulator > 50.0`.

The accumulator is incremented by the raw `importance` integer (1–10) after each `perceive()` call, and reset to 0.0 after each `write_reflection()`. At a threshold of 50, roughly 5–10 high-importance perceptions are needed before a reflection is triggered. This is a starting point pending empirical validation in Sprint 4/5 (Open Question O5).

---

## 5. Deviations from Spec Interface

**`retrieve_top_k` — side-effect on memory object**

The spec says "Updates last_accessed on all returned entries." The `WorkingMemory` Pydantic model does not support in-place mutation through the normal `.observations[i].last_accessed = now` path. The implementation uses `object.__setattr__` to replace the `observations` and `reflections` lists with updated copies (each returned entry gets a new `last_accessed`). The returned list also contains the updated objects.

This is the minimal approach that satisfies the spec without requiring the caller to hold an updated memory copy — the same memory object is mutated as a side-effect, consistent with how `retrieve_top_k` is documented ("Updates last_accessed on all returned entries").

No other deviations from the spec interface.

---

## 6. Known Gaps

- **`src/memory/__init__.py`** was pre-existing and imports `core_memory` and `seed_memory` modules that do not yet exist (from a different sprint). Neither new file depends on this init being importable as a package, so the two deliverables work correctly in isolation.

- **Relevance scoring is v1 keyword overlap.** The spec explicitly notes "Sprint 4 may upgrade to embedding similarity." The `relevance_score` function signature is compatible with that upgrade — callers only pass `entry` and `query: str`.

- **`retrieve_top_k` on `WorkingMemoryManager`** uses `object.__setattr__` to update `last_accessed` on the mutable Pydantic model lists. If Pydantic v2 model config is set to `frozen=True` in future this would break. Current schema uses `extra="forbid"` but not `frozen`, so this works correctly today.

- **Eviction score tie-breaking** is deterministic (Python's `sorted` is stable) but not explicitly specified in the brief. Entries with identical eviction scores are removed in their original list order (earliest first).
