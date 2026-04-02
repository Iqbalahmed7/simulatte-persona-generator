# SPRINT 3 BRIEF — CODEX
**Role:** Idle
**Sprint:** 3 — Memory Architecture
**Previous rating:** 19/20

---

## Your Job This Sprint

Codex is idle this sprint.

Use this time to prepare for Sprint 4 (Cognitive Loop), where you own the three prompt-heavy LLM components: `perceive.py`, `reflect.py`, and `decide.py`.

Read:
1. **Master Spec §9** — Cognitive Loop. Study the full prompt structures specified there, especially:
   - `perceive()`: Haiku call, scores importance (1–10) + valence (-1 to 1) through the persona's lens
   - `reflect()`: Sonnet call, synthesises 2–3 insights from top-20 observations, must cite ≥ 2 source_observation_ids
   - `decide()`: Sonnet call, 5-step reasoning chain (gut → information → constraints → social → decision), tendency_summary always in context
2. **`src/schema/persona.py`** — Observation, Reflection schemas
3. **`src/generation/tendency_estimator.py`** — understand `reasoning_prompt` structure, as it is injected into every decide() call

In Sprint 4 you will write all three prompt templates and LLM calls. The quality of `decide()` is the most critical output of the whole system.

No deliverable this sprint.
