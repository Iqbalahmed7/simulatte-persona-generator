# Sprint 30 Review — Persona Registry

**Sprint lead:** Tech Lead (Claude)
**Date:** 2026-04-03
**Status:** COMPLETE ✅

---

## Goal

Build the central persona registry infrastructure from PERSONA_REUSE_MODALITIES.md: persistent file store, demographic query index, domain layer swap utility, cohort manifest format, and CLI registry commands. After this sprint, personas can be stored, retrieved, queried by demographics, re-grounded for new domains, and referenced via cohort manifests.

## What Was Built

| Engineer | File | Rating |
|---|---|---|
| Cursor | `src/registry/__init__.py` — package marker | 20/20 |
| Cursor | `src/registry/persona_registry.py` — PersonaRegistry: add/get/find/list_all/sync_from_json; RegistryEntry dataclass | 20/20 |
| Codex | `src/registry/registry_index.py` — age_band, build_demographics_index, query_index, domain_history, personas_by_domain | 20/20 |
| Goose | `src/registry/persona_regrounder.py` — reground_for_domain; _downgrade_sources; Layer A preserved, Layer B sources → "estimated" | 20/20 |
| OpenCode | `src/registry/cohort_manifest.py` — CohortManifest dataclass; save_manifest, load_manifest, make_manifest | 20/20 |
| OpenCode | `src/cli.py` — `registry` command group: get, find, export, sync | 20/20 |
| Antigravity | `tests/test_persona_registry.py` — 75 tests, 0 failures | 20/20 |

## Test Suite

- **943 tests passing, 0 failures** (up from 868)
- 75 new Sprint 30 tests

## Key Technical Findings

1. **File store layout** — personas stored at `data/registry/personas/{persona_id}.json` (full PersonaRecord JSON), index at `data/registry/index/registry_index.json` (list of RegistryEntry dicts). Directories created on first use; no pre-existing setup required.
2. **add() idempotency** — PersonaRegistry.add() replaces an existing index entry (matched by persona_id) rather than duplicating, ensuring the index stays consistent across repeated calls.
3. **Pydantic v2 model_copy pattern in regrounder** — All three source fields (price_sensitivity, trust_orientation, switching_propensity) are downgraded via `model_copy(update={"source": "estimated"})` at each level. No mutation of input objects; verified by Antigravity.
4. **ISO string sort for domain_history** — Codex used string-sort on ISO-8601 `registered_at` for chronological ordering; this is correct because ISO-8601 dates sort lexicographically.
5. **RegistryEntry import guard in registry_index.py** — Guarded with try/except to support parallel development; import resolves correctly when both files are present.
6. **75 tests from Antigravity** — Exceeded 30-test target. Thorough coverage including edge cases: age band boundaries (0, 80), combined AND filters, case-insensitivity in query_index, domain_history deduplication, manifest parent-dir creation.

## Acceptance Criteria

- PersonaRegistry: add/get/find/list_all/sync_from_json all work ✅
- add() is idempotent ✅
- find() AND logic across age, gender, city_tier, domain ✅
- reground_for_domain: domain updated, all tendency sources → "estimated", Layer A preserved ✅
- original persona not mutated after reground ✅
- CohortManifest: save/load round-trip correct ✅
- CLI: `simulatte registry get/find/export/sync` commands registered ✅
- All 75 tests pass ✅

## From PERSONA_REUSE_MODALITIES.md — Implementation Status

| Feature | Priority | Status |
|---|---|---|
| Central persona registry (file store + index) | HIGH | ✅ DONE |
| Persona versioning (version field in RegistryEntry) | MEDIUM | ✅ DONE |
| Domain layer swap utility (persona_regrounder.py) | MEDIUM | ✅ DONE |
| Registry CLI commands (get/find/export/sync) | MEDIUM | ✅ DONE |
| Cohort manifest format | LOW | ✅ DONE |
| Registry lookup before generation (assembler.py hook) | HIGH | Sprint 31 |
| ICP drift detection | LOW | Sprint 31+ |
