# Sprint 24 Review — Hierarchical Memory Archival: Structure + Summarisation Engine

**Sprint lead:** Tech Lead (Claude)
**Date:** 2026-04-03
**Status:** COMPLETE ✅

---

## Goal

Build the three-tier memory archive structure and Haiku summarisation engine. Sprint 25 builds cross-tier retrieval and extended validation gates.

## What Was Built

| Engineer | File | Rating |
|---|---|---|
| Cursor | `src/memory/archive.py` — ArchiveTier, ArchiveEntry, ArchivalIndex | 20/20 |
| Cursor | `src/schema/memory_extended.py` — WorkingMemoryExtended drop-in superset | 20/20 |
| Codex | `src/memory/archival_engine.py` — promote_to_working_archive, promote_to_deep_archive | 20/20 |
| Goose | `src/memory/summarisation_engine.py` — Haiku batch summarisation + sync wrapper | 20/20 |
| OpenCode | `src/memory/archive_store.py` — attach/detach/to_json/from_json; envelope_store.py update | 20/20 |
| Antigravity | `tests/test_archive.py` — 30 tests (5 classes), 0 bugs found | 20/20 |

## Test Suite

- **693 tests passing, 0 failures** (up from 663)
- 30 new Sprint 24 tests

## Key Technical Findings

1. **`raw_content` field added to ArchiveEntry** — Goose found that ArchiveEntry had no field to carry original observation text for summarisation. Added `raw_content: str = ""` (populated by archival_engine at promotion time; consumed by summarisation_engine).
2. **ArchivalIndex uses `pydantic.Field`** — initial draft mixed dataclasses.field with Pydantic model. Fixed to use `Field(default_factory=list)` correctly.
3. **`model_config` vs `class Config`** — ArchivalIndex initially had both. Pydantic v2 rejects this. Removed redundant `class Config`.
4. **Backward compat guard**: no-op fires when `len(observations) <= 1000 AND archival_index is None`. Guard does NOT fire when archival_index is explicitly set (even at ≤1000 observations).
5. **envelope_store.py updated** — `save_envelope` serialises with `ArchiveStore.to_json()` when working memory is `WorkingMemoryExtended`; `load_envelope` detects `archival_index` key and uses `ArchiveStore.from_json()`. Standard WorkingMemory path unaffected.

## Architecture Decisions

- Three tiers: Active (working memory) → Working Archive → Deep Archive
- Promotion thresholds: age > 24h AND importance < 4.0 for active→working; age > 7 days for working→deep
- Archival and eviction are strictly separate. ArchivalEngine never calls evict(). Eviction remains owned by WorkingMemoryManager (hard-cap 1000).
- All mutations use model_copy() — immutable update pattern throughout.
- Haiku batches by temporal proximity (batch_size=15), one LLM call per batch (cost efficiency).
- WorkingMemoryExtended is a strict superset: any code accepting WorkingMemory accepts WorkingMemoryExtended unchanged.

## Spec Alignment

Full alignment check in `SPEC_ALIGNMENT_CHECK.md`.
