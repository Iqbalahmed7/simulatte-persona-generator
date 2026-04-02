# SPRINT 3 OUTCOME — ANTIGRAVITY
**Engineer:** Antigravity
**Sprint:** 3 — Memory Architecture
**Date:** 2026-04-02

---

## 1. Files Created / Modified

| File | Status | Description |
|------|--------|-------------|
| `src/schema/validators.py` | Modified | Added `g10_seed_memory_count`, updated `validate_all` signature |
| `tests/test_memory.py` | Created | 24 tests (23 pass, 1 skip) |
| `src/memory/__init__.py` | Already present (OpenCode) | Not overwritten; contents verified |

`src/memory/__init__.py` was already created by OpenCode with eager imports from `core_memory` and `seed_memory`. Those modules exist (Goose delivered `retrieval.py`; working_memory, seed_memory, core_memory are present), so the package is importable. The brief instruction "create if OpenCode hasn't already" was satisfied — the file exists and was left intact.

---

## 2. G10 Implementation — Exact Checks

`g10_seed_memory_count(self, memory: WorkingMemory) -> ValidationResult` in `PersonaValidator`:

**Check 1 — Minimum count:**
`len(memory.observations) >= 3`
Failure message includes the actual count and the minimum of 3.

**Check 2 — Valid id per entry:**
For each observation at index `i`: `isinstance(entry.id, str) and entry.id.strip()` must be truthy.
Catches empty strings and whitespace-only strings.

**Check 3 — Importance range per entry:**
`1 <= entry.importance <= 10` (belt-and-suspenders; Pydantic `Field(ge=1, le=10)` enforces this at construction).

**Check 4 — Emotional valence range per entry:**
`-1.0 <= entry.emotional_valence <= 1.0` (belt-and-suspenders; Pydantic `Field(ge=-1.0, le=1.0)` enforces this at construction).

**Check 5 — No duplicate ids:**
Iterates `memory.observations`, accumulates a `seen` set. Each id that appears a second time produces a failure message naming the duplicate id.

All failures are collected before returning — the validator does not short-circuit on the first failure.

**`validate_all` signature change (backward-compatible):**
```python
def validate_all(
    self,
    persona: PersonaRecord,
    include_narrative: bool = False,
    include_memory: bool = False,
) -> list[ValidationResult]:
```
`include_memory` defaults to `False`. All existing callers that omit it receive the same G1/G2/G3 results as before. When `include_memory=True`, the method calls `self.g10_seed_memory_count(persona.memory.working)` and appends the result.

---

## 3. Test Results

**Run command:** `python3 -m pytest tests/test_memory.py -v`

**Result: 23 passed, 1 skipped**

| Test | Status | Notes |
|------|--------|-------|
| `TestObservationSchema::test_write_observation` | PASS | Schema fields set correctly |
| `TestObservationSchema::test_write_reflection_requires_two_sources` | PASS | Pydantic ValidationError raised for < 2 sources |
| `TestObservationSchema::test_observation_importance_bounds` | PASS | Importance 0 and 11 both rejected |
| `TestObservationSchema::test_observation_emotional_valence_bounds` | PASS | -1.1 and 1.1 both rejected |
| `TestG10SeedMemoryGate::test_g10_passes_with_three_observations` | PASS | Exactly 3 valid observations → passes |
| `TestG10SeedMemoryGate::test_g10_passes_with_more_than_three` | PASS | 10 observations → passes |
| `TestG10SeedMemoryGate::test_g10_fails_on_empty_working_memory` | PASS | 0 observations → fails with count in message |
| `TestG10SeedMemoryGate::test_g10_fails_with_one_observation` | PASS | 1 observation → fails |
| `TestG10SeedMemoryGate::test_g10_fails_with_two_observations` | PASS | 2 observations → fails |
| `TestG10SeedMemoryGate::test_g10_detects_duplicate_ids` | PASS | 3 observations with 2 sharing an id → fails |
| `TestG10SeedMemoryGate::test_g10_result_has_no_failures_on_pass` | PASS | Passing result has empty failures list |
| `TestG10SeedMemoryGate::test_g10_to_dict_shape` | PASS | to_dict() returns {passed, gate, failures, warnings} |
| `TestPromotionGuard::test_promotion_guard` | SKIP | `src.memory.reflection_store` not yet delivered (see §4) |
| `TestWorkingMemoryManager::test_write_observation_via_manager` | PASS | All fields set; id is non-empty uuid |
| `TestWorkingMemoryManager::test_write_reflection_via_manager_requires_two_sources` | PASS | ValueError raised for < 2 source ids |
| `TestWorkingMemoryManager::test_eviction_at_cap` | PASS | 1001 writes → len(observations) <= 1000 |
| `TestWorkingMemoryManager::test_eviction_order` | PASS | importance=10 entries retained; importance=1 entries evicted |
| `TestWorkingMemoryManager::test_reset_clears_working_memory` | PASS | All working fields cleared; idempotent |
| `TestWorkingMemoryManager::test_retrieval_top_k` | PASS | Top-5 contains >= 3 "quality"-relevant observations |
| `TestWorkingMemoryManager::test_importance_accumulator` | PASS | Accumulator increments correctly; threshold detection; reset on reflection |
| `TestSeedMemory::test_g10_seed_memory_gate_via_bootstrap` | PASS | bootstrap_seed_memories → >= 3 obs; G10 passes |
| `TestSeedMemory::test_seed_observations_are_valid_type` | PASS | All seeded entries have type="observation" |
| `TestSeedMemory::test_seed_observations_have_unique_ids` | PASS | No duplicate ids in bootstrap output |
| `TestSeedMemory::test_seed_observations_have_high_importance` | PASS | All seed observations have importance >= 7 |

**Note on `TestWorkingMemoryManager` and `TestSeedMemory` passing:** Goose's `working_memory.py` and OpenCode's `seed_memory.py` were present at test time, so the `try/except ImportError` guards resolved to `_HAS_WORKING_MEMORY = True` and `_HAS_SEED_MEMORY = True`. The `skipif` markers on those classes therefore did not trigger. If those files are removed or their imports fail, those 11 tests skip gracefully.

---

## 4. Promotion Guard Test — §14A S17 Confirmation

**Settled rule set from §14A S17:**

Promotion fires when ALL three conditions are simultaneously true:
1. `importance >= 9` — just above the seed memory default of 8
2. `citation_count >= 3` — entry has been referenced by at least 3 reflections
3. `no_contradiction = True` — no contradicting entry exists in core or working memory

**Never promotes demographics** — the identity layer (CoreMemory) is immutable.

**Test status:** `test_promotion_guard` is **SKIPPED** because `src.memory.reflection_store` does not yet exist. The `can_promote` function is OpenCode's Sprint 3 deliverable alongside `core_memory.py` and `seed_memory.py`, but was not present in the delivered files at test time.

The test is fully implemented and ready to execute the moment `reflection_store.py` is delivered. It tests:
- `can_promote(importance=8, citation_count=5, no_contradiction=True)` → False (importance below threshold)
- `can_promote(importance=9, citation_count=3, no_contradiction=True)` → True (all conditions met)
- `can_promote(importance=9, citation_count=2, no_contradiction=True)` → False (citation_count below threshold)
- `can_promote(importance=9, citation_count=3, no_contradiction=False)` → False (contradiction present)

The test uses synthetic `Observation` objects directly from the schema — no LLM calls, no side effects.

---

## 5. Known Gaps

- **`src/memory/__init__.py` contains eager imports:** The existing `__init__.py` (written by OpenCode) imports `assemble_core_memory` and `bootstrap_seed_memories` at module load time. If `core_memory.py` or `seed_memory.py` are removed or fail to import, `import src.memory` will fail entirely. The test file uses `try/except ImportError` on each submodule individually to avoid this cascading failure, but any code that does `import src.memory` (not the submodules) will break if those files are absent.

- **Promotion guard test blocked by missing `reflection_store.py`:** `can_promote` was expected from OpenCode but was not delivered. The test is written and waiting; it will execute automatically once the file exists.

- **G10 does not validate reflections:** The gate currently only checks `memory.observations`. If seed memory were ever bootstrapped as reflections (which the spec prohibits — seeds must be type="observation"), G10 would not catch it. This is by design; the Observation type field and the Pydantic Literal enforce type="observation" at construction.

- **G10 belt-and-suspenders checks (importance, emotional_valence) are redundant in practice:** Pydantic enforces these at object construction. They are included in G10 to make the gate self-contained for audit purposes and to catch any bypass attempts (e.g., objects constructed with `model_construct` skipping validation).

- **`test_retrieval_top_k` is probabilistic:** The assertion `quality_in_results >= 3` (not 5) is intentional — the retrieval formula includes recency and importance, so a very recently written low-importance "quality" observation could be outscored by an older high-importance "weather" observation in edge cases. The `>= 3` threshold gives the formula room to apply all three scoring components while still verifying relevance drives results.
