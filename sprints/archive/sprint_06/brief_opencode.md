# SPRINT 6 BRIEF — OPENCODE
**Role:** Idle — Preparing Sprint 7 Simulation Report + Quality Gates
**Sprint:** 6 — One-Time Survey Modality
**Previous rating:** 19/20

---

## Your Job This Sprint

OpenCode is idle this sprint.

Use this time to prepare for Sprint 7, where you own the simulation report and S1–S4 quality gates.

Read:
1. **Master Spec §12** — Simulation Quality Gates S1–S4:
   - S1: 5-persona trial run completes without error
   - S2: No single decision > 90% of cohort
   - S3: Driver coherence (top drivers are category-relevant — manual review equivalent)
   - S4: Temporal consistency check (BV3)
2. **BV1–BV6** — understand the full behavioural validity suite; you'll implement S1–S4 checks.
3. **`src/modalities/survey_report.py`** (Sprint 6, Codex) — understand the report pattern you'll mirror for simulation.
4. **`src/cognition/loop.py`** — understand `LoopResult` structure (observation, reflections, decision, reflected, decided).

In Sprint 7 you will write:
- `src/modalities/simulation_report.py` — per-turn decision log, attitude evolution, cohort summary
- `tests/test_simulation_e2e.py` → S1, S2 quality gate assertions (structural)

No deliverable this sprint.
