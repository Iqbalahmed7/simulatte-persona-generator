# Sprint 31 Review — Registry Integration + ICP Drift Detection

**Sprint lead:** Tech Lead (Claude)
**Date:** 2026-04-03
**Status:** COMPLETE ✅

---

## Goal

Wire the persona registry into the generation pipeline: ICP-to-registry demographic matching, drift detection (personas that have aged out of ICP band), full assembly orchestration (lookup → drift filter → reground → gap fill), and `--registry-path` hook on the `generate` CLI command.

## What Was Built

| Engineer | File | Rating |
|---|---|---|
| Cursor | `src/registry/registry_lookup.py` — classify_scenario, plan_reuse, ReuseCandidate, ReusePlan, DOMAIN_TAXONOMY_CLASSES | 20/20 |
| Codex | `src/registry/drift_detector.py` — DriftResult, detect_drift (birthday-style calendar arithmetic), filter_drifted | 20/20 |
| Goose | `src/registry/registry_assembler.py` — RegistryAssemblyResult, assemble_from_registry (4-step orchestration) | 20/20 |
| OpenCode | `src/cli.py` — `--registry-path` option on `generate` command; pre-population from registry + gap generation + post-add | 20/20 |
| Antigravity | `tests/test_registry_integration.py` — 61 tests, 0 failures | 20/20 |

## Test Suite

- **1004 tests passing, 0 failures** (up from 943)
- 61 new Sprint 31 tests

## Key Technical Findings

1. **Leap-year birthday arithmetic in drift_detector.py** — Codex caught a subtle bug: `int(age + delta_days/365.25)` gives 1 instead of 2 on exact anniversary dates crossing a leap year (730 days / 365.25 = 1.998...). Fixed with birthday-style calendar arithmetic (`year_diff - 1 if anniversary hasn't occurred yet`). The `years_elapsed` float field still uses `delta_days / 365.25` for informational display.

2. **Antigravity drift test fixture fix** — First test run had a fixture setting `age=50` in a registry with `icp_age_max=40`. Since `registry.find(age_max=40)` filters by registration age (50 > 40), the persona was excluded before drift detection ran — drift_filtered_count remained 0. Fixed: set registration age=35 (within ICP band), rewind `registered_at` to 2016 so `detect_drift` computes current_age≈45 > 40 → correctly flagged as drifted.

3. **assemble_from_registry lazy imports** — drift_detector and registry_lookup imported inside the function body to avoid circular import risk during parallel development. Clean resolution at runtime.

4. **CLI generate hook: gap_count=0 path** — When registry fully covers demand, the generation loop is wrapped in `if generate_count > 0` so no personas are generated. Combined result is `registry_personas + newly_generated_personas`.

5. **DOMAIN_TAXONOMY_CLASSES covers 22 domain strings** — 6 taxonomy classes (cpg, financial_services, healthcare, ecommerce, education, saas). Unknown domains fall to `"different_domain"` by default.

## Acceptance Criteria

- classify_scenario: same/adjacent/different correctly identified ✅
- plan_reuse: demographics filtered, candidates capped, gap_count correct ✅
- detect_drift: birthday arithmetic, is_drifted flag, DriftResult fields ✅
- filter_drifted: valid/drifted split correct ✅
- assemble_from_registry: 4-step orchestration; same-domain preserved, different-domain regrounded ✅
- generate --registry-path: pre-populates from registry, generates gap only, adds new to registry ✅
- All 61 tests pass ✅
- Existing 943 tests still pass (0 regressions) ✅

## PERSONA_REUSE_MODALITIES.md — Implementation Status (Updated)

| Feature | Priority | Status |
|---|---|---|
| Central persona registry (file store + index) | HIGH | ✅ Sprint 30 |
| Registry lookup before generation | HIGH | ✅ Sprint 31 |
| Persona versioning | MEDIUM | ✅ Sprint 30 |
| Domain layer swap utility | MEDIUM | ✅ Sprint 30 |
| Registry CLI commands | MEDIUM | ✅ Sprint 30 |
| Cohort manifest format | LOW | ✅ Sprint 30 |
| ICP drift detection | LOW | ✅ Sprint 31 |

**All 7 features from PERSONA_REUSE_MODALITIES.md §11 are now implemented.**
