# Sprint 26 Review — Domain Onboarding: Template Library + Auto-Selection

**Sprint lead:** Tech Lead (Claude)
**Date:** 2026-04-03
**Status:** COMPLETE ✅

---

## Goal

Complete the 6-template domain library (CPG and SaaS existed; add 4 more). Add keyword-based auto-selection and collision detection for ICP anchor traits.

## What Was Built

| Engineer | File | Rating |
|---|---|---|
| Cursor | `src/taxonomy/domain_templates/financial_services.py` — 41 attributes | 20/20 |
| Cursor | `src/taxonomy/domain_templates/healthcare_wellness.py` — 37 attributes | 20/20 |
| Codex | `src/taxonomy/domain_templates/ecommerce.py` — 46 attributes | 20/20 |
| Codex | `src/taxonomy/domain_templates/education.py` — 36 attributes | 20/20 |
| Goose | `src/taxonomy/template_selector.py` — keyword auto-selection, LOW_CONFIDENCE_THRESHOLD=0.30 | 20/20 |
| OpenCode | `src/taxonomy/collision_detector.py` — exact/near-duplicate/template collision; CollisionReport | 20/20 |
| OpenCode | `src/taxonomy/icp_spec_parser.py` — wired collision detection after parse | 20/20 |
| Antigravity | `tests/test_template_library.py` — 32 tests, 0 bugs | 20/20 |

## Test Suite

- **753 tests passing, 0 failures** (up from 693)
- 60 new tests (28 Sprint 25 + 32 Sprint 26)

## Key Technical Findings

1. **P8 violation found and fixed** — `health_anxiety` appeared in both `healthcare_wellness.py` and `BASE_TAXONOMY`. Constitution P8 requires domain attributes to stay in Layer 2 only. Renamed to `medical_consultation_anxiety` in the domain template (description scoped to medical consultation frequency, not general worry).
2. **`alternative_medicine_openness` naming conflict** — Cursor found that `health_wellness.py` (Sprint 12) already owns this name. Healthcare template uses `complementary_medicine_openness` instead (clinical context: integrating complementary therapies alongside conventional medicine).
3. **icp_spec.py TYPE_CHECKING bug** — S26-OpenCode's wiring used `TYPE_CHECKING` guard for `CollisionReport`, which broke Pydantic v2 at runtime. Fixed in Sprint 25 to direct import (no circular dependency risk — `collision_detector.py` imports only stdlib).
4. **All 6 templates now present** — cpg, saas (existing) + financial_services, healthcare_wellness, ecommerce, education (new).

## Spec Alignment

Full alignment check in `SPEC_ALIGNMENT_CHECK.md`.
