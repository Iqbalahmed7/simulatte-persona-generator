# SPRINT 3 BRIEF — CURSOR
**Role:** Idle
**Sprint:** 3 — Memory Architecture
**Previous rating:** 20/20

---

## Your Job This Sprint

Cursor is idle this sprint.

Use this time to prepare for Sprint 4 (Cognitive Loop), where you own `loop.py` — the orchestration of the perceive → remember → reflect → decide cycle.

Read:
1. **Master Spec §9** — Cognitive Loop (all subsections including the full prompt structures)
2. **`src/memory/working_memory.py`** (once Goose writes it) — understand `write_observation()`, `retrieve_top_k()`, `increment_accumulator()`, `should_reflect()`, `write_reflection()`
3. **`src/generation/identity_constructor.py`** — understand how PersonaRecord is structured going into the loop

In Sprint 4 you will write `src/cognition/loop.py` which:
- Takes a stimulus and a PersonaRecord
- Calls perceive() → remember() → conditionally reflect() → decide()
- Manages the importance_accumulator
- Writes the resulting observation back to working memory

No deliverable this sprint.
