# Sprint 18 Review — LittleJoys Full Population Regeneration + Sarvam Integration

**Sprint lead:** Tech Lead (Claude)
**Date:** 2026-04-03
**Status:** COMPLETE

---

## Goal

Migrate all 200 LittleJoys personas from the legacy engine into the Simulatte v1 schema, enrich via Sarvam, and validate at quality parity.

## What Was Built

| Component | Status | Notes |
|---|---|---|
| `pilots/littlejoys/convert_to_simulatte.py` | ✅ | Pure data mapping, zero LLM calls, 200 personas converted |
| `pilots/littlejoys/extract_signals.py` | ✅ | 2,010 signals extracted for grounding |
| `pilots/littlejoys/regenerate_pipeline.py` | ✅ | 5-stage orchestration: load → ground → sarvam → seed → validate+save |
| G5 negation-context detection (`_phrase_is_negated()`) | ✅ | 40-char lookback window, false positive rate 7% → 3% |
| Sarvam Stage 3: 200/200 enriched | ✅ | Fixed `record.skipped` → `not record.enrichment_applied` bug |

## Issues Fixed

- `SarvamEnrichmentRecord` had no `skipped` attribute — corrected to `not record.enrichment_applied`
- G5 false positives: "rarely makes impulsive decisions" triggered risk-embracing flag — fixed with negation prefix detection
- Stale test assertion: `persona_id.startswith("lj-")` updated to `startswith("pg-lj-")`

## Outcome

- 200/200 personas in Simulatte schema
- 194/200 (97.0%) at quality parity
- 6 edge cases accepted (4 past-context "impulsive" uses, 2 HC4 source-data artifacts)

---

*Sprints 13–17 archive is in sprints/archive/sprint_13 through sprint_17.*
*Sprint 18 was tech-lead-only — no engineer briefs were issued.*
