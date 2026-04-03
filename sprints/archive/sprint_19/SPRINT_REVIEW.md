# Sprint 19 Review — Four Engine Improvements

**Sprint lead:** Tech Lead (Claude)
**Date:** 2026-04-03
**Status:** COMPLETE

---

## Goal

Add decision noise injection, core memory caching, longitudinal persona aging, and tiered simulation to the engine. Deploy to the LittleJoys pipeline.

## What Was Built

| Improvement | Files | Tests | Status |
|---|---|---|---|
| Decision noise injection | `src/cognition/decide.py` | 15 | ✅ |
| Core memory embedding cache | `src/memory/cache.py`, wired into perceive/reflect/decide | 13 | ✅ |
| Longitudinal persona aging | `src/memory/aging.py`, CLI `age-persona` | 15 | ✅ |
| Tiered simulation (DEEP/SIGNAL/VOLUME) | `src/experiment/session.py`, `src/cognition/loop.py`, `src/cli.py` | 18 | ✅ |
| LittleJoys pipeline deployment | `pilots/littlejoys/regenerate_pipeline.py` — `--tier`, `--simulate` flags | — | ✅ |

## Key Design Decisions

- **Noise ranges:** ±5 (consistency ≥ 75), ±12 (50–74), ±20 (< 50) — only confidence perturbed, never reasoning/drivers/objections
- **Cache keys:** Base key for perceive/reflect; `f"{persona_id}:decide"` richer key (includes constraints) for decide
- **Aging threshold:** Scans at importance ≥ 8, promotes only at ≥ 9 + no-demographic content
- **SIGNAL tier:** Haiku perceive+reflect, Sonnet decide — best cost/quality for pipeline re-runs

## Outcome

- 400 tests passing, 0 failures
- LittleJoys cohort re-run at tier=signal: 194/200 (97.0%) parity maintained
- Sprint 19 features recorded in cohort calibration notes

---

*Sprint 19 was tech-lead-only — no engineer briefs were issued.*
