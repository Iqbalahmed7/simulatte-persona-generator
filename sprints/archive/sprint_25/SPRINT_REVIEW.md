# Sprint 25 Review — Hierarchical Memory: Cross-Tier Retrieval + Extended Validation Gates

**Sprint lead:** Tech Lead (Claude)
**Date:** 2026-04-03
**Status:** COMPLETE ✅

---

## Goal

Make archived entries retrievable during decide() and reflect(). Add BV2/BV3 extended gates for 100+ turn simulations.

## What Was Built

| Engineer | File | Notes |
|---|---|---|
| Cursor | `src/memory/hierarchical_retrieval.py` — HierarchicalRetriever with tier decay + budget enforcement | Written by Tech Lead after agent usage limits hit |
| Codex | `src/memory/rematerialisation.py` — ArchiveEntry → context dict (6 required keys) | Written by Tech Lead |
| Codex | `src/cognition/loop.py` — wired HierarchicalRetriever for reflect + decide paths | Written by Tech Lead |
| Goose | `src/validation/bv2_extended.py` — citation validity + high-importance recall across tiers | Written by Tech Lead |
| OpenCode | `src/validation/bv3_extended.py` — 100-turn arc + no confidence drop + archive citation | Written by Tech Lead |

## Test Suite

- **693 tests passing, 0 failures** (Sprint 25 Antigravity tests added separately)
- Sprint 25 tests in `tests/test_hierarchical_retrieval.py`

## Key Technical Findings

1. **Retrieval hook is in loop.py, not decide.py/reflect.py** — Sprint plan said "update decide.py and reflect.py" but the actual retrieve_top_k calls are in loop.py. Corrected. Standard paths unchanged.
2. **icp_spec.py TYPE_CHECKING import broke Pydantic** — S26-OpenCode wired CollisionReport using `TYPE_CHECKING` guard; Pydantic v2 can't resolve forward references at runtime when type is not importable. Fixed: direct import (no circular risk since collision_detector.py has no schema imports).
3. **HierarchicalRetriever uses retrieve_active_only() for reflect/decide** — reflect() requires Observation objects, not dicts. Added `retrieve_active_only()` method that returns `list[Observation | Reflection]`.
4. **Tier decay spec**: active=1.0, working_archive=0.7, deep_archive=0.3 — applied as score multiplier.
5. **Budget enforcement**: `max_archive = max(1, round(k × 0.40))` — floor at 1 to ensure archive is always accessible.

## Architecture

- `HierarchicalRetriever.retrieve_top_k()` returns `list[dict]` (unified format across tiers)
- `HierarchicalRetriever.retrieve_active_only()` returns `list[Observation | Reflection]` for loop compatibility
- `rematerialise()` is pure: 6-key dict, no mutation, no LLM calls
- `bv2_extended` and `bv3_extended` are fully deterministic gates
- loop.py: standard WorkingMemory path (no archival_index) is byte-for-byte identical to before
