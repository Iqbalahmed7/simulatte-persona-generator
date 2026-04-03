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

## Sprint 18 — Full Population Regeneration + Sarvam Integration

**Goal:** Rebuild all 200 LittleJoys personas in the Simulatte v1 schema, enriched via Sarvam, and validated at parity.

### What was built

| Component | Status |
|---|---|
| `pilots/littlejoys/convert_to_simulatte.py` — raw → PersonaRecord converter | ✅ |
| `pilots/littlejoys/extract_signals.py` — signal extractor for grounding pipeline | ✅ |
| `pilots/littlejoys/regenerate_pipeline.py` — 5-stage orchestration script | ✅ |
| Stage 3 Sarvam enrichment — 200/200 India personas enriched | ✅ |
| G5 negation-context fix (`_phrase_is_negated()`) — false positive rate 7% → 3% | ✅ |
| Quality parity: 194/200 (97.0%) at par | ✅ |

### Issues encountered

- **Stage 3 `record.skipped` AttributeError** — `SarvamEnrichmentRecord` has no `skipped` field; correct check is `not record.enrichment_applied`. Fixed in regenerate_pipeline.py.
- **G5 false positives** — "rarely makes impulsive decisions" triggered G5 (risk-embracing phrase). Fixed by adding 40-char lookback negation detection in `src/schema/validators.py`.
- **Stale test assertion** — `persona_id.startswith("lj-")` changed to `startswith("pg-lj-")` after converter format update.

### Sprint 18 outcome

- 200/200 personas in Simulatte schema
- 200/200 Sarvam enriched
- 194/200 (97.0%) at quality parity
- 6 known below-par edge cases accepted (4 past-context "impulsive" uses, 2 HC4 source-data artifacts)

---

## Sprint 19 — Four Engine Improvements

**Goal:** Add noise injection, core memory caching, persona aging, and tiered simulation to the Simulatte engine. Deploy to the LittleJoys pipeline.

### What was built

| Component | File | Tests |
|---|---|---|
| Decision noise injection — calibrated ±5/±12/±20 by `consistency_score`; `noise_applied` field | `src/cognition/decide.py` | 15 |
| Core memory embedding cache — process-scoped `CoreMemoryCache`; perceive/reflect/decide cache-aware | `src/memory/cache.py` | 13 |
| Longitudinal persona aging — `run_annual_review()`, token-overlap clustering, promotion gate | `src/memory/aging.py` | 15 |
| Tiered simulation — `SimulationTier` enum (DEEP/SIGNAL/VOLUME), `tier_models()`, `--tier` CLI flag | `src/experiment/session.py`, `src/cognition/loop.py`, `src/cli.py` | 18 |
| Pipeline deployment — `--tier` and `--simulate` flags in `regenerate_pipeline.py`; Stage 6 simulation pass | `pilots/littlejoys/regenerate_pipeline.py` | — |

### Sprint 19 outcome

- 400 tests passing, 0 failures
- LittleJoys cohort re-run at tier=signal: 200/200 enriched, 194/200 (97.0%) parity
- Cohort calibration notes now record tier + Sprint 19 feature set
- Stage 6 simulation pass available via `--simulate` flag

---

## Pending

- Run `--simulate` pass on full cohort (3 LJ stimuli + purchase decision, report decision distribution)
- Multi-tick simulation (30 days of stimuli, brand trust evolution)
- Calibration — move cohort from `uncalibrated` to `calibrated` against LJ purchase data
- Competitive scenario (LittleJoys vs Horlicks vs Complan)
- Segment report (auto-cluster by decision outcome, surface differentiators)
- **WOM propagation — UNBLOCKED (Sprints SA/SB/SC, 2026-04-03).** Multi-agent social simulation is now shipped. Use `run_social_loop()` with FULL_MESH or RANDOM_ENCOUNTER topology at MODERATE level. Recommended starting point: 10–20 representative personas from the 200-persona cohort (use registry lookup from Sprint 31 to assemble). WOM + competitive scenario can be combined: seed some personas with Horlicks/Complan loyalty, observe peer influence on LittleJoys consideration. CLI: `simulate --social-level moderate --social-topology full_mesh`.
