# Sprint Log — LittleJoys Pilot

Quick reference of what was built sprint by sprint.

---

## Sprint 28 — Infrastructure

**Goal:** Build the cognitive simulation engine on top of the existing persona schema.

### What was built

| Component | Engineer | Status |
|---|---|---|
| MemoryManager (episodic store, retrieval, brand memory) | Cursor | ✅ |
| EmbeddingCache (sentence-transformers + TF-IDF fallback) | Cursor | ✅ |
| CognitiveAgent.perceive() — importance scoring via LLM | Codex | ✅ |
| CognitiveAgent.decide() — 5-step reasoning chain | Goose | ✅ |
| DecisionResult dataclass | Goose | ✅ (fixed by Tech Lead — HTML entities) |
| ConstraintChecker — 30 rules across 5 categories | Goose | ✅ (fixed by Tech Lead — HTML entities + field paths) |
| Test suite: test_memory.py, test_agent.py, test_constraint_checker.py | Antigravity | ✅ |
| scripts/validate_personas.py | OpenCode | ✅ |
| scripts/run_perception_sample.py | OpenCode | ✅ |

### Issues encountered

- **Goose HTML entity bug** — `decision_result.py` and `constraint_checker.py` had `\"` and `&lt;` throughout. Required full file rewrite by Tech Lead.
- **`__init__.py` conflict** — Codex and Goose both wrote it; Goose's version dropped Codex's exports. Fixed by manual merge.
- **4 field path errors in briefs** — `household_structure`, `daily_routine.digital_payment_comfort`, `"single-parent"`, `parent_name` were all wrong. Antigravity caught them in tests. Fixed in constraint_checker.py.
- **70 CAT2-R009 violations** — `work_hours_per_week` defaults to 0 for full-time employees. Patched with `scripts/patch_work_hours.py`.

### Sprint 28 outcome

- 200/200 personas validated
- Clean: 131 | Hard violations: 35 | Soft: remaining
- ConstraintChecker with 30 rules operational
- Engine ready for simulation (perceive + decide working)

---

## Sprint 29 — Simulation + Thesis Proof

**Goal:** Prove the v1 thesis: memory-backed personas are more distinct than naive LLM sampling.

### What was built

| Component | Engineer | Status |
|---|---|---|
| ReflectionEngine — Generative Agents reflection mechanism | Cursor | ✅ |
| Tier1Generator.enforce_hard_constraints() — post-sample enforcement | Cursor | ✅ |
| CognitiveAgent.reflect() — delegates to ReflectionEngine | Codex | ✅ |
| scripts/ab_test_baseline.py — memory-backed vs naive comparison | Codex | ✅ |
| scripts/run_scenario_batch.py — full population scenario runner | Goose | ✅ (fixed by Tech Lead — HTML entities in f-strings) |
| app/streamlit_app.py — 2-page debug UI | OpenCode | ✅ |
| ReflectionEngine/ReflectionInsight exports in `__init__.py` | OpenCode | ✅ |
| tests/test_reflection.py (15 tests) | Antigravity | ✅ |
| tests/test_schema_coherence.py (21 tests) | Antigravity | ✅ |
| test_agent.py updates (reflect tests + decide test) | Antigravity | ✅ |

### Issues encountered

- **Goose HTML entity bug (again)** — `print_summary()` f-strings broken: `summary[&#39;total_personas&#39;]`, `{decision:&lt;15}`. Import check passed; runtime would have failed. Fixed by Tech Lead.
- **model `claude-haiku-3-5` not found** — Model name invalid on this API key. Correct: `claude-haiku-4-5`. Updated `agent.py` and `ab_test_baseline.py`.
- **`max_tokens=512` too low for decide()** — The 5-step reasoning trace requires ~1500 tokens. JSON was being truncated mid-response causing parse failure. Fixed: `max_tokens=2048` for decide().
- **`pytest_plugins` in conftest.py** — Antigravity added a line registering an unrelated test module with missing `structlog` dep, blocking the entire test runner. Removed by Tech Lead.

### Sprint 29 outcome

- **Thesis: PASS** — 607.6% more distinct than naive baseline
- 165/165 clean personas ran to completion — 0 errors
- Decision distribution: 62.4% buy, 15.8% research_more, 11.5% trial, 9.1% defer, 1.2% reject
- Test suite: 109 tests, 0.64s
- Engine fully operational: perceive + memory + reflect + decide

---

## Pending (Sprint 30+)

- Regenerate 35 hard-violation personas
- Multi-tick simulation (30 days of stimuli, brand trust evolution)
- Competitive scenario (LittleJoys vs Horlicks vs Complan)
- Segment report (auto-cluster by decision outcome, surface differentiators)
- WOM propagation (persona-to-persona influence)
- Formalise as Claude skill (see `skill/SKILL_SPEC.md`)
