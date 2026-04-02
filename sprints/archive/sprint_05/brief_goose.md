# SPRINT 5 BRIEF — GOOSE
**Role:** Idle — Preparing Sprint 6 Survey Runner
**Sprint:** 5 — Cohort Assembly + Experiment Modularity
**Previous rating:** 20/20

---

## Your Job This Sprint

Goose is idle this sprint.

Use this time to prepare for Sprint 6 (One-Time Survey Modality), where you own the end-to-end test.

Read:
1. **Master Spec §1** — The four product modalities; focus on one-time survey (core memory only, working memory empty at start and discarded after).
2. **`src/cognition/decide.py`** — Your survey runner will call `decide()` for each question. Understand the `DecisionOutput` dataclass.
3. **`src/cognition/loop.py`** — The survey modality uses a simplified loop: perceive the question, decide the response. No accumulation across questions (working memory is ephemeral).
4. **Validity Protocol BV4** — Interview realism; applies to surveys too. ≥3/5 responses must cite life story detail.
5. **Validity Protocol BV5** — Adjacent persona distinction. Two Pragmatist-type personas must produce <50% shared language in responses.

In Sprint 6 you will write:
- `tests/test_survey_e2e.py` — end-to-end test: ICP Spec → 5-persona cohort → 5-question survey → report

No deliverable this sprint.
