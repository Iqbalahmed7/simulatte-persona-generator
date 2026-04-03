# Sprint SA Review — Multi-Agent Social Simulation: Schema + InfluenceEngine + NetworkBuilder

**Sprint lead:** Tech Lead (Claude)
**Date:** 2026-04-03
**Status:** COMPLETE ✅

---

## Goal

Build the foundational layer of the multi-agent social simulation system: data structures (schema.py), influence computation engine (influence_engine.py), network topology builders (network_builder.py), and ExperimentSession extension with social fields.

## What Was Built

| Engineer | File | Rating |
|---|---|---|
| Cursor | `src/social/__init__.py` — package marker | 20/20 |
| Cursor | `src/social/schema.py` — SocialSimulationLevel, LEVEL_WEIGHTS, NetworkTopology, SocialNetworkEdge, SocialNetwork, InfluenceVector, SocialInfluenceEvent, TendencyShiftRecord, SocialSimulationTrace | 20/20 |
| Cursor | `src/experiment/session.py` — added social_simulation_level (default ISOLATED) + social_network (default None) to ExperimentSession | 20/20 |
| Codex | `src/social/influence_engine.py` — compute_susceptibility, compute_signal_strength, compute_gated_importance, format_as_stimulus, generate_influence_events, check_tendency_drift | 20/20 |
| Goose | `src/social/network_builder.py` — build_full_mesh, build_random_encounter, build_directed_graph | 20/20 |
| Antigravity | `tests/test_social/test_schema.py` (22), `test_influence_engine.py` (27), `test_network_builder.py` (21) — 70 tests, 0 failures | 20/20 |

## Test Suite

- **1074 tests passing, 0 failures** (up from 1004)
- 70 new Sprint SA tests

## Key Technical Findings

1. **ISOLATED short-circuit in generate_influence_events** — returns [] immediately when level==ISOLATED, before any edge iteration. Zero overhead at the default level. All existing behaviour unchanged.
2. **prior_decisions=None → observation events** — when no prior_decisions dict is provided, the engine generates influence events with source_output_type="observation" (using placeholder expressed positions). When the dict is provided but a transmitter is absent, that edge is skipped. This distinction was discovered and tested by Antigravity.
3. **Social attribute fallback** — compute_susceptibility falls back to 0.5 for `social_proof_bias` and `wom_receiver_openness` if the "social" attribute category doesn't exist on the persona (most personas in the system don't have it yet).
4. **Antigravity fixture fixes** — three Pydantic validation errors caught: `primary_value_orientation="community"` (invalid) → `"convenience"`; `severity="blocker"` (invalid) → `"friction"`; key_values lists needed ≥3 items.
5. **build_random_encounter deduplication** — uses a `seen` set to prevent the same directed pair being emitted twice across multiple persona iterations. Reproducible with seed via `random.Random(seed)`.
6. **check_tendency_drift is detection-only** — produces TendencyShiftRecord objects with `description_after="[PENDING DRIFT REVIEW — N social reflections]"` sentinel. Actual application of drift is Sprint SB's `tendency_drift.py`.

## Acceptance Criteria

- ISOLATED level always returns [] from generate_influence_events ✅
- susceptibility in [0.0, 1.0] ✅
- gated_importance in [1, 10] for non-ISOLATED levels ✅
- ExperimentSession default is ISOLATED ✅
- ExperimentSession social_network defaults to None ✅
- Existing tests pass unchanged (0 regressions) ✅
- All 70 Sprint SA tests pass ✅
