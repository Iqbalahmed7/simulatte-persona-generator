# Simulatte Defensibility Roadmap

> Ground-truth planning document for raising Simulatte's category position. Reframed in v2.0 around the **four-block platform model** (Persona Generator → PopScale → Morpheus → Niobe), with the L1–L5 view kept as a category-positioning lens.

**Version:** 2.0
**Created:** 2026-05-01
**Last revised:** 2026-05-01
**Owner:** Iqbal
**Status:** Living document. Update at the close of every phase.

## Changelog

- **v2.0 (2026-05-01):** Reframed around the four-block model after reviewing the Simulatte Research Agent platform architecture. Morpheus v2 is now an explicit high-priority track, not buried in L5. L4 simulation work is reframed as supporting Morpheus counterfactual generation, not as the primary moat. L1 substitute updated: the Morpheus knowledge graph is the compounding substrate; calibration corpus is the bridge until engagements feed it. New phases added: Morpheus v2 Foundation, Niobe v2 Build. Status table now includes built-vs-spec'd honesty.
- **v1.1 (2026-05-01):** Re-anchored to credibility-program numbers (12 studies above the 91% Iyengar ceiling). Phase 0 baseline pivot. Phase 4A frontloaded.
- **v1.0 (2026-05-01):** Initial roadmap.

---

## Table of Contents

1. [Two Views: Category Position and Execution Architecture](#1-two-views-category-position-and-execution-architecture)
2. [Where Simulatte Sits Today](#2-where-simulatte-sits-today)
3. [Known Risks and Defenses](#3-known-risks-and-defenses)
4. [Reading Guide](#4-reading-guide)
5. [Phase 0 — Baseline Anchor](#phase-0--baseline-anchor-week-1)
6. [Phase 1 — Persona Generator Hardening](#phase-1--persona-generator-hardening-weeks-28)
7. [Phase 2 — Calibration Corpus Interface](#phase-2--calibration-corpus-interface-weeks-410)
8. [Phase 3 — L3 Cognition Constraints](#phase-3--l3-cognition-constraints-weeks-914)
9. [Phase 4 — Morpheus v2 Foundation](#phase-4--morpheus-v2-foundation-weeks-836-the-largest-bet)
10. [Phase 5 — Multi-Agent Simulation Substrate](#phase-5--multi-agent-simulation-substrate-weeks-1224)
11. [Phase 6 — RAG-as-Prior for Holdout Robustness](#phase-6--rag-as-prior-for-holdout-robustness-weeks-1624)
12. [Phase 7 — Niobe v2 Build](#phase-7--niobe-v2-build-weeks-2034)
13. [Phase 8 — Audit-Grade Output (G13 Grounding)](#phase-8--audit-grade-output-g13-grounding-weeks-2032)
14. [Phase 9 — Public Proof Harness Extensions](#phase-9--public-proof-harness-extensions-weeks-2436)
15. [Phase 10 — Constrained Generation](#phase-10--constrained-generation-months-1014)
16. [Tooling Recommendation](#tooling-recommendation-cursor-vs-sonnet)
17. [Impact Matrix](#impact-matrix-across-existing-features)
18. [Proof Harness](#proof-harness--test-suite)
19. [Path to SubPOP-Level Robustness](#path-to-subpop-level-robustness)
20. [What to Do This Week](#what-to-do-this-week)

---

## 1. Two Views: Category Position and Execution Architecture

Two complementary lenses, both useful, neither sufficient on its own.

### Category position view (L1–L5)

The Predictive Decision Intelligence stack. Useful when positioning Simulatte against Synthetic Users, Evidenza, panel survey vendors, or generative AI platforms.

| Layer | Description | Value Accrual |
|---|---|---|
| L1 — Data | First-party behavioural telemetry, closed-loop calibration | Low alone; high with proprietary loop |
| L2 — Persona Generation | Architectural framework for synthetic entities | Moderate; commoditizing |
| L3 — Cognition | Inference engines driving persona behaviour | Heavily taxed by oligopoly |
| L4 — Simulation | Bounded virtual environments where agents interact | Extremely high |
| L5 — Output | Translation of simulation events into strategic insight | Maximum — captures customer relationship |

### Execution architecture view (four blocks)

The platform's actual structure. Useful when planning engineering effort and articulating the moat to enterprise buyers.

| Block | Role | Defensibility tier |
|---|---|---|
| **Substrate (Persona Generator)** | Creates synthetic humans with identity, memory, behavioural tendencies | Visible moat — replicable, but expensive. Public credibility numbers are the proof. |
| **Orchestration (PopScale)** | Runs population-scale simulations: demographic calibration, scenario framing, analytics | Commodity. Anyone can build a sim runner. |
| **Research Brain (Morpheus)** | Decomposes problems, generates hypotheses, designs adaptive probes, runs counterfactuals, accumulates pattern intelligence | **Hidden compounding moat.** Knowledge graph that grows with engagements is genuinely hard to replicate. |
| **Population Validation (Niobe)** | Validates distributions, projects findings to population scale, calibrates against real-world outcomes | **Hidden moat.** Real-world calibration data + outcome-comparison loop. |

### Why both views matter

The L1–L5 view tells investors and prospects where Simulatte sits in the category. The four-block view tells the engineering team what to build.

**The most important strategic statement in this document:** *Persona Generator and PopScale are infrastructure. Morpheus and Niobe are the product.* Substrate-and-orchestration are necessary but not sufficient — competitors can replicate them. Research-Brain-and-Population-Validation are the compounding assets.

---

## 2. Where Simulatte Sits Today

### Four-block status (built vs spec'd)

| Block | Status | Notes |
|---|---|---|
| Substrate (Persona Generator) | **Production. Hardened.** | PR0 + PR1 shipped May 2026. 12 calibrated studies above the 91% human ceiling. |
| Orchestration (PopScale) | **Production.** | Functional sim runner. |
| Research Brain (Morpheus v1) | **Working — limited.** | The `simulatte-research-brain` skill orchestrates Stage 1–4 pipelines. No persistent knowledge graph yet. |
| Research Brain (Morpheus v2) | **Spec phase.** | April 2026 BLUEPRINT + critique + BUILD_SPEC. Sprints 1–5 are planning, not built code. The blueprint critique itself notes the document is a "research process specification wearing an architecture document's clothes." |
| Population Validation (Niobe v1) | **Thin translation layer.** | Today: passes `NiobeStudyRequest` to PopScale. |
| Population Validation (Niobe v2) | **Spec phase.** | Peer-reviewer role specified; not built. |
| Knowledge Graph | **Spec phase.** | Architecture defined (patterns / mechanisms / market_context / engagement_results / calibration). Storage substrate not chosen. |

### L1–L5 evaluation (updated for four-block view)

| Layer | Position | Strengths | Weaknesses |
|---|---|---|---|
| L1 | **Weak today, with a defensible plan.** | The Morpheus knowledge graph is the L1 substrate-in-progress: structural patterns, mechanisms, market-context-feasibility maps, engagement results. Compounds with usage. | Knowledge graph is not built. Compounding requires paying engagements feeding it. Calibration corpus is the bridge. |
| L2 | **Category-leading.** | 12 studies above Iyengar ceiling. Gates G1–G12 enforced in code post-PR0/PR1. WorldviewAnchor 4D system. | Calibration→holdout gap of 10–20pp on most geographies. |
| L3 | Commodity. | SIGNAL/DEEP tier framework. Haiku 4.5 batch API. | Vulnerable to Correct Answer Effect on novel stimuli. |
| L4 | **Median today; potentially category-leading after Morpheus v2 + multi-agent.** | PopScale runs structured sims. Morpheus v1 orchestrates pipelines. | Multi-agent emergent dynamics not built. Morpheus v2 not built. |
| L5 | **Designed for audit-grade — but designed ≠ built.** | Morpheus v2 spec includes G13 grounding gate with claim-lineage tags ([PROBE], [SHAP], [JOURNEY], [META], [CLIENT], [UNVERIFIED]). Receipt-anchored claims model is in the blueprint. | Not in code. Today's deliverables are prose with hedge language. |

### Composite verdict

L2 calibration is essentially solved on opinion data. L4 + L5 + L1-via-knowledge-graph is the next-twelve-months work. The defensibility lever has shifted from persona generation to **research-brain + population-validation**, which is the harder and more valuable build.

---

## 3. Known Risks and Defenses

| Risk | Source | Defense |
|---|---|---|
| **Calibration→holdout gap (10–20pp)** | Calibrated DA uses topic anchors; holdout removes them. | Phase 6 RAG-as-prior. India already proves the gap is closable. |
| **D-suppression / C-concentration** | Documented structural failures on abortion / democracy items. | Tier 5 adversarial regression. Track trend, do not paper over. |
| **Behavioural economics canon untested** | Opinion items proven; cognitive biases untested. | Phase 9 addendum. |
| **Pure prompt-based, no fine-tune** | Acknowledged. Asset for cost; liability for control. | Phase 10 (constrained generation) hedges. |
| **Synthetic Persona Fallacy critique (ACM)** | Category-wide. | Public credibility repo + G13 grounding gate (Phase 8) + retrospective predictive validity (Phase 9). |
| **Morpheus v2 execution risk** | Spec phase only. Blueprint critique flagged real architecture gaps. | Phase 4 starts week 8. Build a thin v2 first; do not skip the architecture decisions the critique surfaced. |
| **Knowledge graph compounding requires engagements** | Theatre without paying clients. | Sequence: PR2 → first paying client → first Morpheus engagement → first knowledge-graph patterns. The flywheel cannot start in isolation. |

---

## 4. Reading Guide

Each phase has Scope, Deliverables, Success Metrics, Tooling, Impact, and Dependencies. A phase blocks the next if metrics don't pass. Don't skip; the metrics compound.

---

## Phase 0 — Baseline Anchor (week 1)

| | |
|---|---|
| **Scope** | Pin the baseline numbers from the credibility program as the durable reference. |
| **Status** | **Complete.** |
| **Anchor numbers (frozen)** | Calibrated DA: USA 95.3%, India 97.61%, Europe mean 92.6%. Holdout DA: USA 81.9%, India 95.87%, Europe mean 74.4%. Reference ceiling: Iyengar Stanford 2023 = 91%. |
| **Deliverables** | `benchmarks/baseline_2026-05.json`, `benchmarks/grounding_extractor_baseline.json` (macro F1 0.946 gold), `benchmarks/budget_envelope.md` (estimated). |

---

## Phase 1 — Persona Generator Hardening (weeks 2–8)

| | |
|---|---|
| **Scope** | Cursor's hardening plan: gate enforcement, regen wiring, fidelity state. |
| **Status** | **PR0 + PR1 shipped.** PR2 pending consumer audit. |

### PR0 — shipped (commit fa1db07)
Strict gate wiring, sequencing fix, orchestrator G1/G2/G3 inference bug, synthetic price_mention removal, docs aligned.

### PR1 — shipped (commit 1fd8a09)
Cohort regeneration wiring, canonical quality report consuming validator output, explicit per-gate status enum (passed / failed / not_run with reasons), all 12 protocol gates emitted.

### PR2 — pending
Fidelity state model. Blocked on consumer audit (White Rabbit, Niobe, Morpheus, Operator, PopScale, Engine).

---

## Phase 2 — Calibration Corpus Interface (weeks 4–10)

| | |
|---|---|
| **Scope** | Wrap the 12 existing credibility studies as a programmatic corpus. Add behavioural econ + adversarial pairs to fill gaps. |
| **Dependencies** | Access to simulatte-credibility repo. |
| **Deliverables** | `calibration_pairs/schema.json` (Opus tier for design). `sources/credibility_program/ingest.py` — ~180 pairs from existing 12 studies. `sources/behavioral_econ/` — 50 manually curated pairs. `sources/adversarial/` — 30 pairs. `bin/score_calibration.py`. 80/20 train/holdout split. |
| **Success Metrics** | ~260 total pairs. Scorecard reproduces credibility numbers within ±2pp on wrapped pairs. Behavioral econ baseline first-time measured. |
| **Tooling** | Sonnet/Claude Code with Opus tier for schema. |
| **Impact** | Net-new module. Credibility repo stays public scorecard; this is internal tooling. |

---

## Phase 3 — L3 Cognition Constraints (weeks 9–14)

| | |
|---|---|
| **Scope** | Persona-conditioned decoding, RAG-from-memory at Decide time, anti-sycophancy probes, tier routing audit. |
| **Dependencies** | PR1 merged. |
| **Deliverables** | Per-persona temperature/top_p map driven by Big Five. Decide retrieves top-3 memories at decision time. 20-item anti-sycophancy probe battery as CI test. Tier routing audit. |
| **Success Metrics** | Cohort entropy on neutral items rises ≥20% vs Phase 0. Anti-sycophancy position shift <15%. Zero DEEP calls on screening operations. Decide cost drops 15–25%. |
| **Tooling** | Sonnet/Claude Code with `claude-api` skill. |
| **Impact** | Higher response variance breaks tests asserting exact distributions; update fixtures. |

---

## Phase 4 — Morpheus v2 Foundation (weeks 8–36, the largest bet)

**The defensibility moat.** Highest engineering priority after Phase 1 hardening lands. Spec is well-developed; build is greenfield. Budget for 6+ months.

### 4A — Knowledge Graph Substrate (weeks 8–14)

| | |
|---|---|
| **Scope** | Choose storage. Define schemas for patterns, mechanisms, market_context, engagement_results, calibration. Build CRUD layer. |
| **Deliverables** | `morpheus/knowledge_graph/` repo. Storage decision: Neo4j vs Postgres+graph extension vs simple relational. CRUD API. Seed with ~30 patterns extracted from past studies (LittleJoys, etc.). |
| **Success Metrics** | Round-trip a pattern: write → query by mechanism feasibility → retrieve. Storage scales to 1000 patterns × 100 mechanisms × 50 contexts in <100ms. |
| **Tooling** | Opus tier for schema/storage decision. Sonnet for implementation. |

### 4B — Phase 0–2 Pipeline (weeks 12–20)

| | |
|---|---|
| **Scope** | Client Context Audit, Problem Decomposition, Adaptive Hypothesis Generation. The "before any probe" stages. |
| **Deliverables** | `morpheus/phase0_audit/`, `morpheus/phase1_decompose/`, `morpheus/phase2_hypothesize/`. Product-stage classifier (Demand Creation / Demand Capture / Competitive Defence). Factor tree generator (macro/meso/micro). Hypothesis tree with confidence priors fed by knowledge graph matches. |
| **Success Metrics** | Run Phase 0–2 on 3 retrospective case studies; outputs match the manually-produced hypothesis registers within reasonable diff. |
| **Tooling** | Sonnet/Claude Code with `simulatte-research-brain` skill as reference. |

### 4C — Phase 3–4 Probing + Mechanism Validation (weeks 18–28)

| | |
|---|---|
| **Scope** | Segment-aware probing with adaptive sequencing. Mechanism validation. The "loop until root cause" engine. |
| **Deliverables** | `morpheus/phase3_probe/`, `morpheus/phase4_mechanism/`. Adaptive sequencing rules (0% diagnose, 90% test scalability, 50–70% find moderating variable). Mechanism feasibility checker against market_context graph. |
| **Success Metrics** | Replicates the LittleJoys B-P3 mechanism analysis end-to-end (driver → 4 candidate mechanisms → ranked feasibility) automatically. |

### 4D — Phase 5–6: Counterfactual + G13 Gate (weeks 24–34)

| | |
|---|---|
| **Scope** | Counterfactual generation engine + G13 grounding gate. The two highest-value modules. |
| **Deliverables** | `morpheus/phase5_counterfactual/` — minor-tweak generator using knowledge graph mechanisms. `morpheus/phase6_g13/` — claim-lineage tagger ([PROBE], [SHAP], [JOURNEY], [META], [CLIENT], [UNVERIFIED]) with delivery-blocking enforcement. |
| **Success Metrics** | On a retrospective case study, Morpheus produces ≥3 counterfactuals at least 1 of which a domain expert flags as "non-obvious, would test." G13 catches and blocks an `[UNVERIFIED]` claim in test fixtures. |

**Hard gate before Phase 4D ships:** at least one paying engagement runs through Phase 0–4 end-to-end, populating the knowledge graph with real patterns.

---

## Phase 5 — Multi-Agent Simulation Substrate (weeks 12–24)

**Reframed in v2.0:** This was the headline L4 work in v1.1. In v2.0 it's reframed as *infrastructure that supports Morpheus Phase 5 counterfactual generation*, not the moat itself.

| | |
|---|---|
| **Scope** | Discrete-event simulation core, social graph between personas, opinion dynamics, market modes (adoption/competition/shock), multi-round memory, macro-metric extraction. |
| **Deliverables** | `src/simulation/des.py`, `social_graph.py`, `opinion_dynamics.py`, `market_modes.py`, `macro_metrics.py`. |
| **Success Metrics** | N=200 cohort: clustering coefficient ±0.05 of empirical norms, 10-round sim <60s, Bass diffusion R²>0.80, Asch conformity emerges, Schelling segregation matches published norm, 10-round persona identity stability >0.85 cosine. |
| **Tooling** | Opus tier for architecture. |
| **Impact** | Existing single-shot sims unchanged. Morpheus Phase 5 counterfactual generator consumes these as the simulation substrate it needs. |

---

## Phase 6 — RAG-as-Prior for Holdout Robustness (weeks 16–24)

| | |
|---|---|
| **Scope** | Use Phase 2 corpus to inject real-distribution priors at decode time when anchoring is OFF. Close the calibration→holdout gap. |
| **Dependencies** | Phase 2 corpus interface. |
| **Deliverables** | `src/calibration/retriever.py`. Holdout protocol re-run on all 12 geographies. |
| **Success Metrics** | Europe holdout 74.4% → ≥82% (population-weighted 76.3% → ≥84%). USA 81.9% → ≥86%. India holds at 95.87%. No demographic cell degrades >3pp. |
| **Tooling** | Sonnet/Claude Code. |
| **Impact** | Re-run all 12 studies with retrieval; publish as v2 credibility scorecard. |

---

## Phase 7 — Niobe v2 Build (weeks 20–34)

| | |
|---|---|
| **Scope** | Promote Niobe from translation layer to peer-reviewer. Post-probe distribution validation, segment representativeness, population-scale projection, real-world outcome comparison. |
| **Deliverables** | Niobe knowledge base (India: NFHS-5, state census, urban/rural; US: ACS, county income). Distribution validator. Projection engine with confidence intervals and demographic skew analysis. Outcome-comparison harness. |
| **Success Metrics** | Run on a Morpheus probe result: outputs population-scale projection with CI, flags demographic concentration, reports POPULATION BIAS warnings against real-world data. |
| **Tooling** | Sonnet/Claude Code. |
| **Impact** | Morpheus deliverables gain second-opinion validation. Engine repo gains the Niobe v2 module. |

---

## Phase 8 — Audit-Grade Output (G13 Grounding) (weeks 20–32)

**Largely subsumed by Phase 4D.** Listed separately because PG/Niobe deliverable templates also need updating to consume G13 lineage tags.

| | |
|---|---|
| **Scope** | Receipt-anchored claims everywhere. Cohort-variance CIs replace prose hedge language. Counterfactual deliverable mode. |
| **Deliverables** | Every deliverable sentence has receipt_id linking to underlying decisions. CI on every percentage. Morpheus `--counterfactual` mode. |
| **Success Metrics** | 100% claim → receipt resolution. 20-claim audit: every receipt supports its claim. |
| **Impact** | Major White Rabbit update (click-to-receipt UX). Morpheus + Niobe template overhaul. |

---

## Phase 9 — Public Proof Harness Extensions (weeks 24–36)

| | |
|---|---|
| **Scope** | Extend the public credibility repo with what's missing. |
| **Deliverables** | (1) Behavioural economics canon study (endowment, loss aversion, anchoring, framing, sunk cost, ultimatum, dictator) published as `studies/behavioral_econ/`. (2) Cross-platform shootout vs Synthetic Users + panel survey (~$5k panel cost). (3) Retrospective predictive validity on 15 historical decisions. |
| **Success Metrics** | Behav econ: 6 of 7 effects within 1σ. Cross-platform: Simulatte beats Synthetic Users on opinion-item DA by ≥10pp. Retrospective: ≥70% directional accuracy. |
| **Impact** | Public credibility repo becomes the most rigorous artifact in the synthetic-population category. |

---

## Phase 10 — Constrained Generation (months 10–14)

| | |
|---|---|
| **Scope** | Per-cell calibration model fitted on corpus. Inference-time rejection sampling for anchor-free robustness. |
| **Dependencies** | Phase 6 complete with measurable improvement. |
| **Success Metrics** | Europe holdout ≥88%. USA ≥90%. Calibration→holdout gap <5pp. Behav econ canon: 7 of 7 effects within 1σ. |
| **Impact** | Generation latency rises 10–20%. Output realism approaches calibrated quality without anchors. |

---

## Tooling Recommendation: Cursor vs Sonnet

**Cursor:** PR0-style surgical edits only.

**Sonnet (via Claude Code):** Everything else. Cross-file refactors, schema migrations, architecture work. The `claude-api`, `simulatte-pipeline`, `simulatte-research-brain`, and `simulatte-niobe` skills are already loaded.

**Opus tier:** Phase 2 schema design, Phase 4A storage decision, Phase 4 architecture decisions, Phase 5 architecture, Phase 8 receipt schema design, retrospective validity study analysis. Everywhere else, Sonnet.

---

## Impact Matrix Across Existing Features

| Feature | Phase 1 | Phase 3 | Phase 4 (Morpheus) | Phase 5 (Multi-agent) | Phase 6 | Phase 7 (Niobe) | Phase 8 | Net |
|---|---|---|---|---|---|---|---|---|
| **White Rabbit dashboard** | Signal counts, fidelity column | Variance indicator | Knowledge graph viz, Morpheus run views | Graph + adoption curves | Generation version label | Population projection viz | Click-to-receipt UX | Major Q4 sprint |
| **Niobe** | Schema additive | Higher variance | Consumes Morpheus probe results | Multi-round mode | Outputs shift | **Major v2 build** | Receipts in deliverables | v2 build phase |
| **Morpheus** | Quality scorecard text shifts | Higher variance | **The major build** | Counterfactual sim substrate | Generation version label | Consumes Niobe second-opinion | Template overhaul | The defensibility build |
| **Operator** | Stricter gates | Same | N/A — single-agent | N/A | Twin shifts | N/A | Receipts in twin reports | Twin-specific fidelity threshold |
| **PopScale** | None | None | Morpheus orchestrates above PopScale | New sim modes | None | Niobe consumes PopScale outputs | None | Mostly passthrough |
| **Engine** | Schema passthrough | None | Knowledge graph runtime | New sim modes | None | Niobe v2 module | None | New module hosting |
| **simulatte-credibility (public)** | None | None | None | None | **v2 scorecard with retrieval** | None | None | Phase 6 + Phase 9 extensions |

---

## Proof Harness — Test Suite

(Unchanged from v1.1.) Tier 1 public benchmark replications, Tier 2 cross-platform shootout, Tier 3 retrospective predictive validity, Tier 4 internal regression, Tier 5 adversarial. Cadence: T1+T4 every release; T2+T3 quarterly; T5 monthly.

---

## Path to SubPOP-Level Robustness

| Stage | When | Method | Target |
|---|---|---|---|
| A — RAG-as-prior | Q2 (Phase 6) | Retrieve nearest pairs at decode time, inject as Bayesian prior; anchoring OFF | Europe holdout 74.4% → ≥82%; USA → ≥86% |
| B — Constrained generation | Q3–Q4 (Phase 10) | Per-cell calibration model, rejection sampling | Europe ≥88%; USA ≥90%; gap <5pp |
| C — Fine-tune | Q4+ | SFT on corpus when Anthropic fine-tune access opens | Holdout matches calibrated |
| D — Active learning via knowledge graph | Post-launch ongoing | Each Morpheus engagement adds patterns + calibration deltas | Bridge to L1 closed-loop moat |

---

## What to Do This Week

1. **PR2 consumer audit** — Niobe, White Rabbit, Engine, Morpheus, Operator, PopScale: enumerate every read of `grounded`. 30–60 minutes per repo.
2. **Phase 4A architecture decision** — choose knowledge graph storage (Neo4j vs Postgres+graph). Use Opus tier. Document the decision before writing code.
3. **Schedule the first paying engagement** — Morpheus v2 only compounds with real client patterns. The flywheel cannot start in isolation.
4. **Don't start Phase 5 (multi-agent) yet** — it's now infrastructure for Morpheus Phase 5, not the headline. Build it when Morpheus Phase 4 needs it.

---

## Document Maintenance

Update at the close of every phase. Bump version on structural change (new phase, removed phase). Patch (2.0 → 2.1) for actuals-only updates.
