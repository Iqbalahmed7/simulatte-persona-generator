# SPRINT 4 BRIEF — OPENCODE
**Role:** Idle
**Sprint:** 4 — Cognitive Loop
**Previous rating:** 18/20

---

## Your Job This Sprint

OpenCode is idle this sprint.

Use this time to prepare for Sprint 5 (Cohort Assembly + Experiment Modularity), where you own diversity checking and distinctiveness enforcement.

Read:
1. **Master Spec §11** — Distinctiveness Enforcement. Study the G7 cosine-distance gate and resampling trigger.
2. **`src/generation/stratification.py`** — understand how 5:3:2 stratification already works (Antigravity Sprint 1); your distinctiveness.py builds on top of this.
3. **Validity Protocol G6, G7, G8** — the three gates you'll implement:
   - G6: Distribution checks (no city > 20%, no age bracket > 40%)
   - G7: Mean pairwise cosine distance on 8 core attributes > 0.35
   - G8: Type coverage rules for cohort sizes N=3, 5, 10

In Sprint 5 you will write:
- `src/cohort/diversity_checker.py` — G6 distribution checks
- `src/cohort/distinctiveness.py` — G7 cosine distance enforcement + resampling trigger

No deliverable this sprint.
