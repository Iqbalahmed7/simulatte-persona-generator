# Persona Generator — Master Memory File

**Read this first when context is lost.**

This folder is the persistent memory for the Persona Generator project. It is separate from LittleJoys (which is Pilot 1). Everything here is written to be reusable across any client or product category.

---

## What This Project Is

A **Claude skill** that generates a synthetic population of psychologically grounded personas for any brand or product category — and then simulates how those personas respond to stimuli, campaigns, and purchase scenarios.

Not a profile writer. A behavioural simulation engine.

---

## Folder Structure

```
Persona Generator/
├── README.md                        ← YOU ARE HERE — read this for context
│
├── architecture/
│   ├── COGNITIVE_ARCHITECTURE.md   ← How the engine works (perceive/memory/reflect/decide)
│   ├── SYSTEM_OVERVIEW.md          ← Non-technical: what changed, why it matters
│   └── SCHEMA_PRINCIPLES.md        ← How to design persona schemas for any category
│
├── skill/
│   ├── SKILL_SPEC.md               ← What the Claude skill does, inputs/outputs
│   └── PROMPT_PATTERNS.md          ← Reusable prompts for each engine stage
│
├── learnings/
│   ├── WHAT_WORKS.md               ← Proven patterns and hard-won lessons
│   ├── MULTI_AGENT_PLAYBOOK.md     ← How to orchestrate Cursor/Codex/Goose/Antigravity/OpenCode
│   └── QUALITY_GATES.md            ← Constraint checking, test coverage, validation approach
│
└── pilots/
    └── littlejoys/
        ├── PILOT_RESULTS.md        ← A/B test results, decision distributions, thesis proof
        └── SPRINT_LOG.md           ← What was built sprint by sprint
```

---

## Current Status (as of Sprint 19)

- Engine: **Complete** — perceive, memory, reflect, decide all working
- Population: **200/200** clean personas (Sprint 18 — full regeneration complete)
- Thesis: **PROVED** — 607% more distinct than naive baseline
- Pilot: LittleJoys child nutrition India
- Cohort: regenerated with Sprint 19 features, tier=signal, 97.0% parity

## Sprint 19 Engine Improvements (active)

- **Decision noise injection** — calibrated ±5/±12/±20 confidence perturbation based on `consistency_score`; `noise_applied` field on every decision for traceability
- **Core memory embedding cache** — process-scoped cache in `src/memory/cache.py`; perceive/reflect/decide skip redundant block assembly on repeat calls
- **Longitudinal persona aging** — `run_annual_review()` in `src/memory/aging.py`; clusters reflections by semantic theme, promotes to core at importance ≥ 9; CLI: `age-persona`
- **Tiered simulation mode** — `SimulationTier` enum (DEEP / SIGNAL / VOLUME); controls model routing in loop.py; CLI: `--tier` flag

## What's Next

- Run `--simulate` pass on full cohort (Stage 6 — 3 LJ stimuli + purchase decision)
- Multi-tick simulation (30-day brand journey)
- Calibration — move cohort from `uncalibrated` to `calibrated` against LJ purchase data
- Competitive stimulus sets (LittleJoys vs Horlicks vs Complan)

---

## Key Numbers to Remember

| Metric | Value |
|---|---|
| Population size | 200/200 clean personas |
| Parity | 97.0% (194/200 at par) |
| Thesis result | PASS — 607% more distinct |
| Buy + trial rate | 73.9% after 5-stimulus sequence |
| #1 purchase driver | Pediatrician recommendation (42% of personas) |
| Median WTP | Rs 649 (matches ask price exactly) |
| Test coverage | 400 tests, ~1.9s |
| Model for perceive() | claude-haiku-4-5-20251001 |
| Model for reflect() | claude-sonnet-4-6 (DEEP/SIGNAL) or haiku (VOLUME) |
| Model for decide() | claude-sonnet-4-6 (DEEP) or haiku (VOLUME) |

---

## Quick Reference — The 5 AI Engineers

| Engineer | Model | Role |
|---|---|---|
| Cursor | Auto (Sonnet) | Architecture, complex implementation |
| Codex | GPT-5.3 | Algorithms, backend logic |
| Goose | Grok-4-1-fast | Decision logic, batch scripts |
| Antigravity | Gemini 3 Flash | Tests, schema integrity |
| OpenCode | GPT-5.4 Nano | UI, lightweight tooling, scripts |

**Known issue with Goose:** Output runs through a serialisation layer that produces `\"` and `&lt;` HTML entities. Always verify syntax after Goose delivers. See `learnings/MULTI_AGENT_PLAYBOOK.md` for full detail.
