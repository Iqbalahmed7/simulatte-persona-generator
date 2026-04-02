# SPRINT 11 REVIEW — Production Entry Point + Technical Debt Clearance
**Tech Lead:** Claude
**Date:** 2026-04-02
**Status:** COMPLETE — ARCHIVED

---

## Summary

Sprint 11 delivered the CLI entry point and closed 5 carry-forwards that had been outstanding since Sprint 1–5. Full suite: **186 passed, 10 skipped** (was 155 entering the sprint — +31 new tests). All 31 tests pass, zero failures.

---

## Test Results

| File | Tests | Pass | Skip |
|------|-------|------|------|
| test_cli.py | 5 | 5 | 0 |
| test_assembler_debt.py | 5 | 5 | 0 |
| test_memory_promotion.py | 6 | 6 | 0 |
| test_smoke.py | 7 | 7 | 0 |
| test_sprint11_gates.py | 8 | 8 | 0 |
| **TOTAL NEW** | **31** | **31** | **0** |

**Full suite:** 186 passed, 10 skipped
**Previous:** 155 passed, 10 skipped

---

## Carry-Forwards Closed This Sprint

| Gap | Status | Carried Since |
|-----|--------|--------------|
| `health_supplement_belief` missing from taxonomy (HC3 blocked) | ✅ CLOSED — added to psychology category | Sprint 1 |
| `distinctiveness_score` hardcoded 0.0 | ✅ CLOSED — `check_distinctiveness()` now called from assembler | Sprint 5 |
| `business_problem` hardcoded empty string | ✅ CLOSED — parameter added to `assemble_cohort()` | Sprint 5 |
| `icp_spec_hash` hardcoded empty string | ✅ CLOSED — SHA-256 fingerprint from domain + persona IDs | Sprint 5 |
| Memory promotion executor not wired | ✅ CLOSED — `run_promotion_pass()` called in loop Step 4b | Sprint 3 |
| No CLI entry point | ✅ CLOSED — `src/cli.py` with `generate` command | — |

---

## Engineer Ratings

### Cursor — 20/20
**Spec adherence: 5/5** — CLI matches brief exactly: `generate` command, all 6 options, `_run_generation` async at module level (importable), Sarvam flag.
**Completeness: 5/5** — `src/cli.py`, `main.py`, `tests/test_cli.py` all delivered.
**Code quality: 5/5** — Correctly diagnosed that `click` wasn't installed and installed it. Applied `from __future__ import annotations` for Python 3.9 `list | None` compatibility — good defensive instinct.
**Acceptance criteria: 5/5** — 5/5 tests pass.

### Codex — 19/20
**Spec adherence: 5/5** — All three fixes implemented correctly: distinctiveness wiring (lazy import + try/except), `business_problem` parameter (backward-compatible default), `icp_spec_hash` (SHA-256 16-char hex).
**Completeness: 5/5** — assembler.py patched, schema/cohort.py updated for the new TaxonomyMeta fields, test_assembler_debt.py (5 tests).
**Code quality: 4/5** — One schema placement note: `icp_spec_hash` ended up as a top-level field on `CohortEnvelope` rather than inside `TaxonomyMeta` per the brief. Antigravity adapted its tests accordingly and everything works — but the brief was clear it should live in TaxonomyMeta. Minor deviation.
**Acceptance criteria: 5/5** — 5/5 tests pass.

### Goose — 20/20
**Spec adherence: 5/5** — promotion_executor.py implements all three functions exactly as specified. loop.py Step 4b wired correctly with lazy import, model_copy (no mutation), promoted_ids threaded to LoopResult.
**Completeness: 5/5** — promotion_executor.py, loop.py modified, test_memory_promotion.py (6 tests).
**Code quality: 5/5** — Correctly discovered that actual schema field names differ from the brief pseudocode (`obs.id` not `observation_id`, `core.tendency_summary` as promotion target, `plans=[]` and `brand_memories={}` required for WorkingMemory). Adapted code to match the real schema rather than blindly copying the brief.
**Acceptance criteria: 5/5** — 6/6 tests pass.

### OpenCode — 20/20
**Spec adherence: 5/5** — `health_supplement_belief` added to psychology category (correct — constraint_checker reads from psychology). Also correctly updated `_validate_taxonomy()` count from 30→31 to prevent the taxonomy size validator from failing on import.
**Completeness: 5/5** — base_taxonomy.py updated, test_smoke.py (7 tests).
**Code quality: 5/5** — Correctly adapted tests for actual schema field names (`attr_type` not `type`, `source="sampled"` not `source="proxy"`). Previously mislabelled outcome file (Sprint 9 vs 10) — this sprint the outcome file is correctly labelled. Full recovery.
**Acceptance criteria: 5/5** — 7/7 tests pass.

### Antigravity — 20/20
**Spec adherence: 5/5** — 8 gate tests exactly as specified. All dependency checks in place.
**Completeness: 5/5** — test_sprint11_gates.py (156 lines, 8 tests).
**Code quality: 5/5** — Correctly adapted to the real schema (`source="sampled"`, `v.constraint_id` attribute on HardConstraintViolation, `icp_spec_hash` location on CohortEnvelope). The `test_full_pipeline_structural` test is a genuine end-to-end structural smoke test.
**Acceptance criteria: 5/5** — 8/8 pass.

---

## Spec Alignment Check

SPEC ALIGNMENT CHECK — Sprint 11 END
======================================

GOVERNING SECTIONS REVIEWED:
✓ Master Spec §14C (v1 required components)
✓ Master Spec §8 (Memory Architecture — promotion rules §14A S17)
✓ Master Spec §6 (Taxonomy — HC3 constraint)
✓ Master Spec §11 (Distinctiveness)

SETTLED DECISIONS CHECKED:
✓ S17: Promotion gate (importance ≥ 9, ≥ 3 citations, no contradiction) implemented exactly
✓ S17: Demographics never promoted — keyword guard in promote_to_core()
✓ S17: Core memory updated via model_copy() — no mutation
✓ HC3: health_supplement_belief in psychology category (matches constraint_checker read path)

ANTI-PATTERNS CHECKED:
✓ No coefficient creep — no new numerical weights introduced
✓ Memory promotion is a no-op when no reflections present (fast path)
✓ CLI never bypasses gate validation — assemble_cohort() called normally

RESULT: ✓ ALIGNED

---

## Remaining Carry-Forwards Into Sprint 12

1. **`icp_spec_hash` placement** — landed as top-level on `CohortEnvelope` rather than inside `TaxonomyMeta` (Codex deviation from brief). Functionally fine; schema alignment note for future cleanup.
2. **CR2/CR3/CR4 not automated** — Sarvam validation statuses remain manual/human-evaluated.
3. **Integration tests not live-run** — all LLM-gated tests (BV1-BV6, simulation e2e, survey e2e, enricher) still skipped pending `ANTHROPIC_API_KEY`.
4. **CLI `generate` not end-to-end tested live** — `_run_generation()` tested structurally; a live run requires API key.
5. **Persona persistence** — no database or file-based storage for generated personas.
6. **Domain template library** — CPG and SaaS templates exist; no additional verticals.

---

## Sprint 12 Target

**Live Integration Run + Persona Persistence**
- Run `python -m src.cli generate --spec spec.json --count 3 --domain cpg` with real API key
- Write `src/persistence/` — JSON file storage for PersonaEnvelope (load/save)
- Wire persistence into CLI: `--output` saves envelope + separate `load` command
- Run integration test suite with `--integration` flag to validate BV1-BV6
