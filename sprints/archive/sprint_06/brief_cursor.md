# SPRINT 6 BRIEF — CURSOR
**Role:** Idle — Preparing Sprint 7 Simulation Runner
**Sprint:** 6 — One-Time Survey Modality
**Previous rating:** 19/20

---

## Your Job This Sprint

Cursor is idle this sprint.

Use this time to prepare for Sprint 7 (Temporal Simulation Modality), where you own the simulation runner.

Read:
1. **Master Spec §1** — temporal simulation modality: core + working memory, accumulates across turns.
2. **`src/cognition/loop.py`** — your simulation runner wraps `run_loop()` for a sequence of stimuli. Understand the `LoopResult` structure.
3. **`src/experiment/session.py`** — `ExperimentSession` is the input to your simulation runner.
4. **BV3** — Temporal consistency: confidence/trust should increase across positive stimulus arc.
5. **BV6** — Believable override: persona should depart from tendency in override scenarios.

In Sprint 7 you will write:
- `src/modalities/simulation.py` — simulation runner: takes ExperimentSession → runs stimuli through `run_loop()` → returns SimulationResult with per-turn log

No deliverable this sprint.
