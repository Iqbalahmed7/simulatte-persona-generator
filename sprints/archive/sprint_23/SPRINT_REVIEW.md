# Sprint 23 Review — LittleJoys App Integration

**Sprint lead:** Tech Lead (Claude)
**Date:** 2026-04-03
**Status:** COMPLETE ✅

---

## Goal

Wire the Simulatte cognitive engine into the LittleJoys Streamlit app. Replace legacy persona loading and batch runner. Add Sprint 19–22 feature UI (tier selector, confidence display, memory panel, calibration badge).

## What Was Built

| Engineer | File | Rating |
|---|---|---|
| Cursor | `pilots/littlejoys/app_adapter.py` — CohortEnvelope → LJ display dict adapter | 20/20 |
| Codex | `pilots/littlejoys/simulatte_batch_runner.py` — JourneyConfig → run_loop with tier support | 20/20 |
| Goose | `streamlit_app.py` updates — 4 surgical changes (data source, calibration banner, tier selector, batch runner swap) | 20/20 |
| OpenCode | `components/confidence_display.py`, `components/memory_state_viewer.py`, `components/calibration_badge.py` | 20/20 |
| Antigravity | `tests/test_app_adapter.py` — 16 tests (13 unit + 3 cohort-disk), 0 bugs found | 20/20 |

## Test Suite

- **663 tests passing, 0 failures** (up from 647)
- 16 new Sprint 23 tests

## Key Technical Findings

1. **`demographic_anchor` not `core`** — PersonaRecord's top-level identity block is `demographic_anchor`. The adapter maps from `p.demographic_anchor.name`, `p.demographic_anchor.location.city`, etc.
2. **`SimulationTier` in `src.experiment.session`** — Sprint plan referenced `src.cognition.tiering` but the real module is `src.experiment.session`. Codex found this by reading `loop.py` imports.
3. **`child_ages` not in PersonaRecord** — No per-child age array in the Simulatte schema. Adapter returns `[]`. LJ app's age-band filter degrades gracefully.
4. **Backward compatibility preserved** — All 4 streamlit_app.py changes use try/except fallback to legacy `run_batch`/`personas_generated.json`. The app continues working even if the cohort file moves.

## Changes to LittleJoys App

All changes documented in `pilots/littlejoys/LJ_UI_CHANGES.md`:

1. **Data source** — `load_all_personas()` now loads `simulatte_cohort_final.json` via `app_adapter` (with legacy fallback)
2. **Calibration badge** — Sidebar shows green/amber/red badge from `cohort.calibration_state.status`
3. **Tier selector** — SIGNAL/DEEP/VOLUME radio on Run Scenario page
4. **Simulatte batch runner** — `run_simulatte_batch` called first; falls back to `run_batch` on error
5. **Confidence display component** — `render_confidence(confidence, noise_applied)` — colored badge
6. **Memory state viewer component** — `render_memory_state(observations, reflections, last_reflection)`
7. **Calibration badge component** — `render_calibration_badge(status)`

## Spec Alignment

Full alignment check in `SPEC_ALIGNMENT_CHECK.md`.
