# SIMULATTE PERSONA GENERATOR — MASTER SPECIFICATION

**Version:** 1.2
**Date:** 2026-04-02
**Status:** CANONICAL — all implementation must reference this document
**Authors:** Simulatte Research & Architecture
**Revision history:**
- v1.0: Initial master spec
- v1.1: Added adopt/modify/reject tables, settled vs open split, behavioural validity tests (BV1-BV6), expanded constitution (10 principles, 10 anti-patterns, 2 checklists), component phase classification
- v1.2: Added Indian Cultural Realism Layer (Sarvam integration — Section 15), anti-stereotypicality constraints, cultural realism validation tests (CR1-CR4), Sarvam-specific anti-drift anti-patterns, settled/open decisions for cultural layer

---

## How to Use This Document

This is the source of truth for the Simulatte Persona Generator. Every sprint, implementation decision, and architecture choice must be traceable to a section of this spec. If a decision contradicts this document, this document wins — or this document must be explicitly updated first.

Read sequentially for full context. Reference by section number for sprint planning.

---

## Table of Contents

1. [Purpose & North Star](#1-purpose--north-star)
2. [Research Synthesis](#2-research-synthesis)
3. [Hybrid Philosophy](#3-hybrid-philosophy)
4. [System Architecture](#4-system-architecture)
5. [Persona Record Structure](#5-persona-record-structure)
6. [Taxonomy Strategy](#6-taxonomy-strategy)
7. [Grounding Strategy](#7-grounding-strategy)
8. [Memory Architecture](#8-memory-architecture)
9. [Cognitive Loop](#9-cognitive-loop)
10. [Constraint System](#10-constraint-system)
11. [Distinctiveness Enforcement](#11-distinctiveness-enforcement)
12. [Validation Framework](#12-validation-framework)
13. [Anti-Drift Guardrails — The Simulatte Constitution](#13-anti-drift-guardrails--the-simulatte-constitution)
14. [Settled Decisions, Open Questions & Build Order](#14-settled-decisions-open-questions--build-order)
15. [Indian Cultural Realism Layer — Sarvam Integration](#15-indian-cultural-realism-layer--sarvam-integration)

---

## 1. Purpose & North Star

### What Simulatte Is

Simulatte is a persistent synthetic population platform. Users create deep synthetic personas anchored to a specific business context. Those personas persist — they have identity, memory, tendencies, and history. They can be reused across multiple experiments without losing who they are.

### The North Star

**A persona is a synthetic person with identity, memory, tendencies, and history — not a segment model with a narrative attached.**

Five properties must hold simultaneously:

| Property | Definition | Test |
|----------|-----------|------|
| **Identity permanence** | Core identity (name, history, values, defining events) is fixed across experiments | Same persona returns consistent identity across sessions |
| **Memory persistence** | Experiences accumulate during simulation; early stimuli influence later decisions | Remove a stimulus from a sequence → subsequent decisions change |
| **Cognitive agency** | The LLM reasons through decisions using the perceive→remember→reflect→decide loop | Disable the loop, give the same profile → decisions are detectably different |
| **Domain grounding** | When data exists, tendencies are anchored to empirical evidence | Compare grounded vs proxy personas on domain-specific questions → grounded are more realistic |
| **Experiment modularity** | Core memory is immutable; working memory resets per experiment | Same persona, two different experiments → core identity is identical, experiment observations are independent |

### What Simulatte Is Not

- A survey response generator (no persistent identity)
- A demographic panel simulator (no cognition, no memory)
- A prompt-augmented chatbot (no structured identity, no working memory separation)
- A clone of a real person (no interview requirement)
- A segment model with narratives (no parametric decision functions replacing reasoning)

### The Four Product Modalities

| Modality | Description | Memory State |
|----------|-------------|-------------|
| **One-time survey** | Present questions, collect responses. No temporal dimension. | Core only. Working memory empty at start, discarded after. |
| **Temporal simulation** | Run a stimulus sequence over simulated time. Observe attitude and decision evolution. | Core + working. Memory accumulates across turns. |
| **Post-event survey** | After a temporal simulation, survey the persona about their experience. | Core + working from prior simulation (preserved). |
| **Deep interview** | Open-ended conversational probing of the persona's reasoning, values, and experiences. | Core + working (if post-simulation) or core only (if standalone). |

---

## 2. Research Synthesis

### Foundational Papers

#### DeepPersona (NeurIPS LAW Workshop 2025)

**Problem solved:** How to construct taxonomy-deep, narrative-complete personas at scale.

**Key mechanisms:** 8,496-node taxonomy from 62K conversations, progressive conditional filling, anchor-first ordering (8 core attributes), 5:3:2 cosine-similarity stratification, population tables for demographics, sparsity prior for long-tail coverage.

**Key results:** 43% KS statistic improvement on WVS alignment, 31.7% deviation reduction, ~200 attributes per persona, ~1MB narrative text.

| Mechanism | Decision | Rationale |
|-----------|----------|-----------|
| 8,496-node taxonomy | **Modify** — use smaller base (~150) + domain extensions | DeepPersona's taxonomy is built for conversation breadth; Simulatte needs decision-relevant depth. ~150 base attributes cover psychology, values, social, lifestyle, identity, decision-making without noise. Domain extensions add 30-80 targeted attributes. |
| Progressive conditional filling | **Adopt directly** | Prevents contradictory attribute assignments. Each attribute conditioned on all prior. Core mechanism, no modification needed. |
| Anchor-first ordering (8 core attributes) | **Adopt directly, modify the specific 8** | Concept is essential — fill high-influence attributes first. DeepPersona's 8 are general; Simulatte's 8 are decision-oriented: personality type, risk tolerance, trust orientation, economic constraints, life stage needs, primary values, social orientation, key tension seed. |
| 5:3:2 stratification | **Adopt directly** | Best documented solution to LLM homogeneity bias. Ratio is empirically validated. No reason to modify. |
| Population tables for demographics | **Adopt directly** | Prevents LLM training-data bias in demographic sampling. Use census/empirical marginals. |
| Sparsity prior | **Adopt directly** | Ensures rare attribute combinations are not zero-probability. Critical for tail representation. |
| LMSYS-Chat mining pipeline | **Reject** | DeepPersona mines chat logs for taxonomy construction. Simulatte builds taxonomy from domain data (when available) or domain template libraries. Different source, same principle. |
| WVS-based evaluation | **Reject for v1** | Survey-response alignment is one validity dimension but not primary. Simulatte prioritizes behavioural validity (decision coherence) over survey-response accuracy. |
| ~200 attributes per persona | **Modify — target ~150-230** | DeepPersona's depth is valuable but some attributes may be noise for decision simulation. Target the range, prune during validation. |

#### Generative Agents (Park et al., UIST 2023 + 1,000 People Extension 2024)

**Problem solved:** How to make LLM personas that behave believably over time.

**Key mechanisms:** Memory stream (observations + reflections + plans), retrieval formula (α·recency + β·importance + γ·relevance), reflection triggers (importance sum > threshold), hierarchical planning, interview-based memory scaffolding.

**Key results:** Cohen's d = 8.16 believability improvement. 85% GSS accuracy, 80% Big Five, 66% economic games. Population-level r = 0.98.

| Mechanism | Decision | Rationale |
|-----------|----------|-----------|
| Memory stream (observations + reflections + plans) | **Adopt directly** | The core architecture. Observations record experience, reflections create depth, plans enable intention. Simulatte uses all three entry types. |
| Retrieval formula: α·recency + β·importance + γ·relevance | **Adopt directly** | Elegant, tunable, proven. Default α=β=γ=1.0. Tunable per experiment if needed. |
| Reflection trigger (importance sum > threshold) | **Adopt, modify threshold** | Park uses ~150 in continuous Smallville. Simulatte's stimulus-based simulations run fewer events. Default threshold = 50 (OPEN — subject to empirical validation, see Section 14A). |
| Hierarchical planning (day → hour → 5-min) | **Reject for v1** | Smallville's continuous time model requires decomposed planning. Simulatte's stimulus-driven model does not. Plans exist as memory entries but are not hierarchically decomposed. Revisit if continuous-time simulation is added. |
| Interview-based memory scaffolding | **Reject** | Requires real human interviews (Simile's approach). Simulatte generates life stories and core memory from taxonomy-grounded profiles. Accepts fidelity tradeoff (~75% vs ~85% GSS) for scalability and domain flexibility. |
| Core/working memory separation | **Adopt and extend** | Park's agents have a single stream. Simulatte splits into immutable core (identity) and resettable working (experiment state). This is an extension of Park's architecture to enable experiment modularity — a capability Park's system does not address. |
| Importance scoring (1-10 LLM-assigned) | **Adopt directly** | Simple, effective. LLM assigns at perception time. No modification needed. |
| Recency decay (exponential) | **Adopt, tune rate** | Park's 0.995/hour is calibrated for continuous time. Simulatte may need event-based decay for irregular stimulus spacing (OPEN — see Section 14A). |
| 1,000-person interview study methodology | **Adopt the insight, reject the method** | The insight: interview-grounded agents dramatically outperform demographic-only. The method: collecting 1,052 interviews is not scalable. Simulatte substitutes taxonomy-depth + domain grounding for interview transcripts. |

#### MiroFish (2024)

**Problem solved:** How to go from a seed document to a running simulation without manual schema configuration.

**Key mechanisms:** Seed-document-to-ontology via LLM, Zep Cloud as unified knowledge graph, temporal edge metadata, OASIS social simulation engine, ReACT report agent with InterviewAgents tool.

| Mechanism | Decision | Rationale |
|-----------|----------|-----------|
| Seed-document-to-ontology via LLM | **Adopt the principle, modify the scope** | MiroFish infers the full ontology from a seed document. Simulatte uses this principle for domain taxonomy extension (Layer 2) only — the base taxonomy (Layer 1) is pre-defined. The ICP Spec + domain data trigger ontology extraction, not a single seed document. |
| Zep Cloud as knowledge graph | **Reject the specific technology, adopt the principle** | Memory should be queryable by recency, importance, relevance, and relationship. But Simulatte's v1 uses JSON-based memory with a retrieval formula, not a graph database. The architecture supports future migration to a knowledge graph without redesign. |
| Temporal edge metadata | **Adopt directly** | Every memory entry carries a timestamp. Reflections carry source_observation_ids (relationship edges). Temporal ordering is fundamental to the retrieval formula. |
| OASIS social simulation engine | **Adopted — implemented Sprints SA/SB/SC (2026-04-03)** | Multi-agent social simulation is now shipped. Architecture: SocialSimulationLevel (ISOLATED default → SATURATED), peer influence via `perceive()` injection, SocialSimulationTrace + SV1–SV5 validity gates. See `docs/MULTI_AGENT_SOCIAL_SIMULATION.md`. |
| ReACT report agent with InterviewAgents tool | **Adopt the concept for Deep Interview modality** | The idea that a report agent can interrogate personas post-simulation maps directly to Simulatte's Deep Interview modality (Phase 4). |
| Zero-configuration aspiration | **Reject** | MiroFish aims for zero manual config. Simulatte requires the ICP Spec — the user must define who they're building personas for and why. Automation applies to taxonomy extension and grounding, not problem definition. |

### Competitive Landscape Summary

| Competitor | Approach | Strengths | Gap vs Simulatte |
|-----------|----------|-----------|-----------------|
| **Simile** ($100M) | Interview-grounded digital twins | Highest fidelity (85% GSS) | Requires real interviews; no self-serve domain flexibility |
| **Fish.Dog/Ditto** | Census-calibrated, live data feeds, 300K personas | Scale, live grounding | No persistent identity, no cognitive loop |
| **Aaru** ($1B val) | Population-level prediction, multi-agent | Scale, predictive claims | Black box; no transparency; no individual persona depth |
| **Synthetic Users** | 4-agent architecture, OCEAN calibration | Multi-agent QA process | Stateless; no temporal simulation |
| **Artificial Societies** (YC W25) | Social graph simulation, 2.5M personas | Network effects, opinion propagation | No deep individual identity; segment-level |
| **SYMAR** | "Synthetic Memories" from CRM data | Memory injection concept | No cognitive loop; memory is static, not accumulated |
| **Toluna** | 79M-panel-grounded, 1M personas | Scale, panel fidelity | No cognition; response generation only |
| **Qualtrics Edge** | 25yr survey data fine-tuned | Embedded in dominant platform | US only; no persistence; segment-level |

**Simulatte's positioning:** The only system that combines taxonomy-deep identity (DeepPersona), memory-persistent cognition (Generative Agents), domain-adaptive grounding (MiroFish), and experiment-modular design. No competitor occupies this intersection.

### Academic Research — Key Findings That Shape This Spec

**On population construction:**
- IPF (Iterative Proportional Fitting) is the standard method for census-calibrated synthetic populations. Use for demographic marginal alignment.
- Population-Aligned Persona Generation (2025): Importance Sampling + Optimal Transport achieves 49.8% error reduction. Standard LLM generation underrepresents low-Extraversion and low-Emotional Stability regions.
- AlphaEvolve-based Persona Generators (2026): Support coverage (spanning what is possible) matters more than density matching for diverse populations.

**On cognitive architecture:**
- CoALA framework: working memory + episodic + semantic + procedural. Perceive→retrieve→reason→act→update cycle. Closest theoretical match to Simulatte's design.
- MemGPT/Letta: hierarchical memory management with explicit memory operators. Relevant for long simulations exceeding context limits.
- BDI + LLMs: Beliefs (worldview), Desires (goals/values), Intentions (commitments). Natural mapping to persona identity and memory.

**On validation:**
- Four validity levels: face (looks real), distributional (population matches), behavioral (decisions match), predictive (forecasts outcomes). Simulatte targets levels 1-3 at launch; level 4 after calibration.
- 76% of marketing experimental findings replicated by LLM personas (Bao et al., 2024). Limitation: complex interactions and embedded biases.
- AgentSociety (2025): 10K agents, 5M interactions. Simulated political polarization and policy impacts aligned with real-world data.

**On known failures to guard against:**
- Homogeneity bias: LLM outputs cluster around modal personalities
- Sycophancy: personas agree with question framing
- Persona drift: character fades over long contexts
- Cultural bias: WEIRD psychology dominates unless explicitly corrected
- Tail underrepresentation: extreme positions and rare trait combinations are systematically absent
- "Too consistent": real humans show more decision noise than LLM personas

---

## 3. Hybrid Philosophy

### The LLM Is the Cognitive Engine

The LLM does not just write stories about personas. It *is* the persona's cognitive machinery. When a persona perceives a stimulus, the LLM processes it through the persona's psychological lens. When a persona reflects, the LLM synthesizes patterns from accumulated experience. When a persona decides, the LLM reasons through the decision using identity, memory, and tendencies.

### Grounding Supports the Simulation — It Does Not Replace It

Behavioural grounding (domain data, proxy estimation, calibration) anchors persona tendencies in empirical evidence. This makes the simulation more realistic. But grounding does NOT:
- Replace LLM reasoning with parametric decision functions
- Reduce personas to coefficient vectors with narrative labels
- Make the decision before the LLM reasons through it
- Defer memory, persistence, or simulation because "calibration comes first"

**Corrected priority order:**
1. Identity and memory make a persona a persona
2. The cognitive loop makes simulation possible
3. Grounding makes the simulation realistic
4. Calibration makes the simulation trustworthy

**Items 1 and 2 are the product. Items 3 and 4 are trust layers.**

### How Tendencies Enter Reasoning

Behavioural tendencies (price sensitivity, trust orientation, switching propensity) are included in the LLM's reasoning context as soft priors — descriptive statements about how the persona tends to think and act:

```
You tend to be quite price-sensitive — cost is usually one of the first things
you notice and evaluate. You're most influenced by what experts and professionals
recommend, less so by advertising. You're generally loyal to brands that have
worked for you and don't switch easily.
```

The LLM reasons with these tendencies as part of the persona's self-understanding. The decision emerges from the reasoning trace. This preserves:
- Situational flexibility (the persona CAN override tendencies when context demands it)
- Internal conflict (a price-sensitive persona might splurge for their child)
- Narrative coherence (the reasoning trace explains the decision in the persona's voice)
- The difference between a persona and a formula

---

## 4. System Architecture

### End-to-End Pipeline

```
                        ICP SPEC (from user)
                              │
                    ┌─────────┴─────────┐
                    │                     │
              Domain Data?          No Domain Data
                    │                     │
            Signal Extraction       Domain Template
                    │               Library Selection
            Feature Construction          │
                    │                     │
            Cluster Derivation            │
                    │                     │
                    └─────────┬───────────┘
                              │
                     TAXONOMY CONSTRUCTION
                     (base + domain extension)
                              │
                     IDENTITY CONSTRUCTION
                     (demographics → core attrs → life stories
                      → extended attrs → derived insights
                      → behavioural tendencies → core memory
                      → narrative)
                              │
                     COHORT ASSEMBLY
                     (diversity enforcement, distinctiveness
                      check, type coverage, tension audit)
                              │
                     VALIDATION
                     (schema, coherence, distribution,
                      narrative alignment)
                              │
                     CALIBRATION (optional)
                     (benchmark anchoring or client feedback)
                              │
                     OUTPUT
                     (persona JSON + summary cards)
                              │
                     ┌────────┴────────┐
                     │                  │
              EXPERIMENT MODE     PERSIST TO STORE
              (survey, simulation,  (for future reuse)
               interview)
```

### Component Responsibilities

| Component | Responsibility | LLM Used |
|-----------|---------------|----------|
| **Taxonomy Engine** | Construct/extend attribute taxonomy for domain | Sonnet (one-time per domain) |
| **Identity Constructor** | Progressive attribute filling, life story generation | Sonnet |
| **Demographic Sampler** | Sample from population tables with empirical marginals | Deterministic (no LLM) |
| **Attribute Filler** | Conditional attribute assignment given growing profile | Sonnet |
| **Tendency Estimator** | Assign behavioural tendencies from clusters or proxies | Deterministic (no LLM) |
| **Narrative Generator** | First-person and third-person summaries | Sonnet |
| **Constraint Checker** | Validate hard/soft constraints, flag violations | Deterministic |
| **Cohort Assembler** | Diversity enforcement, distinctiveness check | Deterministic + Sonnet (for resampling) |
| **Perceive Engine** | Process stimuli through persona's psychological lens | Haiku (high volume) |
| **Memory Manager** | Write observations, retrieve relevant memories | Deterministic (retrieval formula) |
| **Reflection Engine** | Synthesize higher-order insights from observations | Sonnet |
| **Decision Engine** | Reason through decisions using identity + memory + tendencies | Sonnet |
| **Calibration Engine** | Adjust population-level outputs against benchmarks | Deterministic |

### Mode Hierarchy

| Mode | Trigger | What Changes |
|------|---------|-------------|
| **Quick** | Default, ≤ 5 personas | Proxy behavioural tendencies, no calibration, base taxonomy only |
| **Deep** | ≥ 10 personas or domain data provided | Domain-extended taxonomy, grounded tendencies (if data), benchmark calibration |
| **Simulation-Ready** | Any mode + simulation flag | Full memory schema populated, seed memories bootstrapped, cognitive loop enabled |
| **Grounded** | Domain data provided + ≥ 10 personas | Cluster-estimated tendencies, empirical constraint matrix, both calibration methods |

---

## 5. Persona Record Structure

### Top-Level Schema

```json
{
  "persona_id": "pg-[domain_prefix]-[001]",
  "generated_at": "ISO datetime",
  "generator_version": "string",
  "domain": "string",
  "mode": "quick | deep | simulation-ready | grounded",

  "demographic_anchor": { },
  "life_stories": [ ],
  "attributes": { },
  "derived_insights": { },
  "behavioural_tendencies": { },
  "narrative": { },
  "decision_bullets": [ ],
  "memory": {
    "core": { },
    "working": { }
  }
}
```

### demographic_anchor

```json
{
  "name": "string — culturally appropriate, realistic",
  "age": 34,
  "gender": "female | male | non-binary",
  "location": {
    "country": "string",
    "region": "string",
    "city": "string",
    "urban_tier": "metro | tier2 | tier3 | rural"
  },
  "household": {
    "structure": "nuclear | joint | single-parent | couple-no-kids | other",
    "size": 4,
    "income_bracket": "string",
    "dual_income": true
  },
  "life_stage": "string",
  "education": "high-school | undergraduate | postgraduate | doctoral",
  "employment": "full-time | part-time | self-employed | homemaker | student | retired"
}
```

### life_stories

Array of 2-3 vignettes. These are identity-forming, not decorative.

```json
[
  {
    "title": "string",
    "when": "string — age or life period",
    "event": "string — 100-150 words, concrete and specific",
    "lasting_impact": "string — how this shapes current values/behaviour"
  }
]
```

### attributes

Organized by category. All continuous values 0.0-1.0. Categorical values use defined option sets.

```json
{
  "[category_name]": {
    "[attribute_name]": {
      "value": 0.72,
      "type": "continuous | categorical",
      "label": "string — human-readable",
      "source": "sampled | inferred | anchored | domain_data"
    }
  }
}
```

**Mandatory categories (always present):**
- `psychology` — decision biases, risk tolerance, emotional responsiveness
- `values` — what they prioritize (price, quality, relationships, independence)
- `social` — peer influence, authority trust, social proof sensitivity
- `lifestyle` — routines, convenience preferences, time orientation
- `domain_specific` — attributes specific to the business domain

### derived_insights

Computed deterministically from attributes. Never LLM-generated.

```json
{
  "decision_style": "emotional | analytical | habitual | social",
  "decision_style_score": 0.72,
  "trust_anchor": "self | peer | authority | family",
  "risk_appetite": "low | medium | high",
  "primary_value_orientation": "price | quality | brand | convenience | features",
  "coping_mechanism": {
    "type": "string",
    "description": "string"
  },
  "consistency_score": 78,
  "consistency_band": "low | medium | high",
  "key_tensions": ["string — explicit internal contradictions"]
}
```

### behavioural_tendencies

Soft priors that shape LLM reasoning. NOT decision functions.

```json
{
  "behavioural_tendencies": {
    "price_sensitivity": {
      "band": "low | medium | high | extreme",
      "description": "string — natural language tendency statement",
      "source": "grounded | proxy | estimated"
    },
    "trust_orientation": {
      "weights": {
        "expert": 0.72,
        "peer": 0.85,
        "brand": 0.28,
        "ad": 0.12,
        "community": 0.61,
        "influencer": 0.44
      },
      "dominant": "string — highest weight source",
      "description": "string — natural language tendency statement",
      "source": "grounded | proxy | estimated"
    },
    "switching_propensity": {
      "band": "low | medium | high",
      "description": "string",
      "source": "grounded | proxy | estimated"
    },
    "objection_profile": [
      {
        "objection_type": "string — from standard vocabulary",
        "likelihood": "high | medium | low",
        "severity": "blocking | friction | minor"
      }
    ],
    "reasoning_prompt": "string — the paragraph included in LLM context during cognitive operations, assembled from the above fields"
  }
}
```

**Standard objection vocabulary:**
`price_vs_value`, `trust_deficit`, `need_more_information`, `social_proof_gap`, `switching_cost_concern`, `risk_aversion`, `budget_ceiling`, `feature_gap`, `timing_mismatch`

### narrative

```json
{
  "first_person": "string — 100-150 words, in the persona's voice",
  "third_person": "string — 150-200 words, biographical summary",
  "display_name": "string — human-readable identifier"
}
```

### memory

```json
{
  "core": {
    "identity_statement": "string — 25 words, first person",
    "key_values": ["string", "string", "string"],
    "life_defining_events": [
      {
        "age_when": 9,
        "event": "string",
        "lasting_impact": "string"
      }
    ],
    "relationship_map": {
      "primary_decision_partner": "string",
      "key_influencers": ["string"],
      "trust_network": ["string"]
    },
    "immutable_constraints": {
      "budget_ceiling": "string | null",
      "non_negotiables": ["string"],
      "absolute_avoidances": ["string"]
    },
    "tendency_summary": "string — the reasoning_prompt from behavioural_tendencies, included here for context-window injection"
  },
  "working": {
    "observations": [],
    "reflections": [],
    "plans": [],
    "brand_memories": {},
    "simulation_state": {
      "current_turn": 0,
      "importance_accumulator": 0.0,
      "reflection_count": 0,
      "awareness_set": {},
      "consideration_set": [],
      "last_decision": null
    }
  }
}
```

### Observation Entry

```json
{
  "id": "obs-001",
  "timestamp": "ISO datetime",
  "type": "observation",
  "content": "string — natural language description",
  "importance": 7,
  "emotional_valence": 0.3,
  "source_stimulus_id": "string | null",
  "last_accessed": "ISO datetime"
}
```

### Reflection Entry

```json
{
  "id": "ref-001",
  "timestamp": "ISO datetime",
  "type": "reflection",
  "content": "string — synthesized insight",
  "importance": 8,
  "source_observation_ids": ["obs-003", "obs-007", "obs-012"],
  "last_accessed": "ISO datetime"
}
```

### Cohort Envelope

```json
{
  "cohort_id": "cohort-[domain]-[timestamp]",
  "generated_at": "ISO datetime",
  "domain": "string",
  "business_problem": "string",
  "mode": "quick | deep | simulation-ready | grounded",
  "icp_spec_hash": "string — links to the ICP spec that produced this cohort",
  "taxonomy_used": {
    "base_attributes": 150,
    "domain_extension_attributes": 42,
    "total_attributes": 192,
    "domain_data_used": true
  },
  "personas": [],
  "cohort_summary": {
    "decision_style_distribution": {},
    "trust_anchor_distribution": {},
    "risk_appetite_distribution": {},
    "consistency_scores": { "mean": 74, "min": 61, "max": 91 },
    "persona_type_distribution": {},
    "distinctiveness_score": 0.42,
    "coverage_assessment": "string",
    "dominant_tensions": ["string"]
  },
  "grounding_summary": {
    "tendency_source_distribution": {
      "grounded": 0.0,
      "proxy": 1.0,
      "estimated": 0.0
    },
    "domain_data_signals_extracted": 0,
    "clusters_derived": 0
  },
  "calibration_state": {
    "status": "uncalibrated | benchmark_calibrated | client_calibrated | calibration_failed",
    "method_applied": "string | null",
    "last_calibrated": "ISO datetime | null",
    "benchmark_source": "string | null",
    "notes": "string | null"
  }
}
```

---

## 6. Taxonomy Strategy

### Three-Layer Taxonomy

**Layer 1: Domain-Agnostic Base (~150 attributes)**
Shared across all domains. Covers psychology, values, social orientation, lifestyle, decision-making patterns. Built from DeepPersona's taxonomy methodology applied to general human-LLM conversation data.

Categories:
- Psychology (30): decision biases, risk tolerance, emotional responsiveness, cognitive style, information processing
- Values (25): priorities (price, quality, status, relationships, independence, security), moral foundations, identity orientation
- Social (25): peer influence, authority trust, social proof sensitivity, conformity, WOM patterns, community engagement
- Lifestyle (25): routines, time orientation, convenience preferences, health consciousness, technology comfort, media consumption
- Identity (20): self-concept, aspiration gap, life satisfaction, agency, locus of control
- Decision-making (25): analysis depth, speed, delegation patterns, regret sensitivity, satisficing vs maximizing

**Layer 2: Domain Extension (~30-80 attributes)**

When domain data is provided: extracted automatically using MiroFish-style ontology extraction.
```
Input:  reviews, forum posts, transcripts, support tickets
Process: LLM extracts domain-specific attributes mentioned in the data
         (e.g. for child nutrition: "clean label importance", "pediatrician trust",
          "organic preference", "ayurvedic inclination")
Output: domain-specific attribute set with value distributions estimated from data
```

When domain data is unavailable: selected from a domain template library.
```
Template libraries maintained for:
- Consumer packaged goods
- SaaS / B2B software
- Financial services
- Healthcare / wellness
- E-commerce / retail
- Education / edtech
(New templates added as domains are encountered)
```

**Layer 3: User-Specified Anchors (0-10 attributes)**
From the ICP Spec "Anchor Traits" section. These are forced attributes that MUST appear in the taxonomy and are assigned priority in the filling order.

### Filling Order

1. **Demographic anchor** — sampled from population tables (empirical marginals)
2. **8 core attributes** (anchor-first):
   - Personality type (Big Five mapped to decision style)
   - Risk tolerance
   - Trust orientation
   - Economic constraints
   - Life stage needs
   - Primary values
   - Social orientation
   - Key tension seed
3. **User-specified anchors** — forced values from ICP Spec
4. **Extended attributes** — progressively filled, each conditioned on ALL previously assigned
5. **Domain-specific attributes** — filled last, conditioned on full profile

### Progressive Conditioning

Each attribute is filled by providing the LLM with:
- The complete profile so far (all assigned attributes)
- The attribute definition and valid range
- The population distribution for this attribute (if known)
- Any correlation constraints involving this attribute

The LLM returns a value and a brief rationale. The rationale is discarded after validation; only the value is kept.

### 5:3:2 Stratification

For cohorts of 5+ personas:
- **50% (near):** Core attributes within 0.15 cosine distance of the cohort centroid
- **30% (mid):** Core attributes 0.15-0.35 cosine distance from centroid
- **20% (far):** Core attributes > 0.35 cosine distance from centroid

This prevents the homogeneity bias documented across all LLM persona generation research.

---

## 7. Grounding Strategy

### When Grounding Activates

Grounding activates when the user provides domain data in Section 5 of the ICP Spec. The system operates in Grounded Mode. Without domain data, the system operates in Proxy Mode.

### Grounded Mode Pipeline

```
Stage 1: Signal Extraction
  Input:  raw review/forum/transcript text
  Method: Extract sentences with decision-language markers
          Trigger verbs: bought, cancelled, switched, refused, waited, chose, avoided
          Tag by type: purchase_trigger | rejection | switching | trust_citation | price_mention
          Retain metadata: platform, rating, date, category
  Output: labelled signal corpus

Stage 2: Feature Construction
  Input:  labelled signal corpus
  Compute:
    price_salience_index = price_mentions / total_decision_mentions
    trust_source_distribution = proportion by type [expert/peer/brand/ad/community/influencer]
    switching_trigger_taxonomy = [price/feature/service/competitive/life_change]
    objection_cluster_frequencies = relative frequency by semantic group
    purchase_trigger_taxonomy = [need/recommendation/trial/promotion/event]
  Output: feature vectors per review cluster

Stage 3: Behavioural Cluster Derivation
  Input:  feature vectors
  Method: GMM clustering on behavioural features (NOT demographics)
  Output: K behavioural archetypes (typically 3-6), each with:
    - price_sensitivity_band and distribution
    - trust_orientation_weights and distribution
    - switching_propensity_band and distribution
    - primary_objections (ranked)
    - primary_purchase_triggers (ranked)
  Cross-tabulate with demographics to build conditional distributions

Stage 4: Tendency Assignment
  For each persona:
    1. Identify nearest behavioural archetype based on attribute profile
    2. Sample tendencies from that archetype's distribution (not point estimates)
    3. Add controlled noise (±10% of distribution width) for individual variation
    4. Mark source: "grounded"
    5. Run consistency checks (see Section 10)
```

### Proxy Mode (No Domain Data)

When domain data is unavailable:

| Tendency | Proxy Formula | Range |
|----------|--------------|-------|
| price_sensitivity | `budget_consciousness * 0.7 + deal_seeking * 0.3` | [0, 1] → mapped to band |
| trust_orientation.peer | `social_proof_bias * 0.9 + wom_openness * 0.1` | [0, 1] |
| trust_orientation.expert | `authority_bias * 0.85 + domain_expert_trust * 0.15` | [0, 1] |
| trust_orientation.brand | `brand_loyalty * 0.6 + (1 - indie_openness) * 0.4` | [0, 1] |
| trust_orientation.ad | `ad_receptivity * 0.7 + (1 - information_need) * 0.3` | [0, 1] |
| switching_propensity | `(1 - brand_loyalty) * 0.6 + (1 - status_quo_bias) * 0.4` | [0, 1] → mapped to band |

All proxy tendencies are marked `source: "proxy"`.

### Minimum Viable Data Set

For Grounded Mode to produce meaningful clusters:
- **Minimum:** 200 reviews/posts/comments with decision language
- **Recommended:** 500+ for stable cluster estimation
- **Optimal:** 1,000+ spanning multiple platforms and time periods

Below 200: the system warns that clusters may be unstable and offers to fall back to Proxy Mode with domain-specific attribute extensions only.

### What Grounding Does NOT Do

- Does not replace LLM reasoning with parametric functions
- Does not produce point-estimate WTP or conversion probabilities
- Does not make the persona's decision before the LLM reasons through it
- Does not require domain data to produce useful personas

---

## 8. Memory Architecture

### Design Principles

1. **Memory is the mechanism of believability.** Without memory, every LLM call starts from zero. The 8-standard-deviation improvement in Park et al. comes from memory, not from better prompts.
2. **Core memory is identity. Working memory is experience.** The split enables experiment modularity.
3. **Reflection creates depth.** Raw observations are shallow. Reflections synthesize patterns, form opinions, and update self-understanding.
4. **Memory must be cited.** Every reflection must trace back to the observations that produced it. Uncited reflections are unreliable.

### Core Memory

Assembled at persona generation time. Immutable across experiments (with narrow promotion exceptions).

**Contents:**
- Identity statement (25 words, first person)
- Key values (3-5 values that guide decisions)
- Life-defining events (2-3, with age, event, lasting impact)
- Relationship map (decision partner, influencers, trust network)
- Immutable constraints (budget ceiling, non-negotiables, avoidances)
- Tendency summary (natural language paragraph assembled from behavioural_tendencies)

**Always in context window:** Core memory is injected into every LLM call during simulation. It is the persona's persistent self-knowledge.

### Working Memory

Created fresh for each experiment. Accumulates during simulation. Resettable.

**Contents:**
- Observation stream (perceived stimuli with importance, valence, timestamp)
- Reflection journal (synthesized insights with source citations)
- Active plans (current intentions and goals, if applicable)
- Brand/product memories (accumulated brand-specific experiences)
- Simulation state (turn counter, importance accumulator, awareness set, consideration set)

### Memory Operations

**Write (after perceive):**
```
observation = {
  id: auto-generated,
  timestamp: simulation time,
  type: "observation",
  content: LLM-generated interpretation of stimulus through persona's lens,
  importance: LLM-scored 1-10,
  emotional_valence: LLM-scored -1.0 to 1.0,
  source_stimulus_id: reference to the stimulus,
  last_accessed: now
}
→ append to working.observations
→ add importance to working.simulation_state.importance_accumulator
```

**Retrieve (before reflect or decide):**
```
For each candidate memory m:
  recency_score  = decay_function(now - m.timestamp)     // exponential decay, rate 0.995/hour
  importance_score = m.importance / 10.0
  relevance_score  = cosine_similarity(query_embedding, m.content_embedding)
  retrieval_score  = α * recency + β * importance + γ * relevance
  // α = β = γ = 1.0 by default; tunable per experiment

Return top-K memories by retrieval_score (K = 10 default for decide, K = 20 for reflect)
```

**Reflect (triggered by accumulator):**
```
Trigger: working.simulation_state.importance_accumulator > REFLECTION_THRESHOLD
  // REFLECTION_THRESHOLD = 50 default (calibrate per experiment length)

Process:
  1. Retrieve top-20 recent observations
  2. LLM synthesizes 2-3 higher-order insights
  3. Each insight stored as reflection entry with source_observation_ids
  4. Reset importance_accumulator to 0
  5. Increment reflection_count

Validation: reject any reflection without ≥ 2 source_observation_ids
```

**Promote (rare — from working to core):**
```
Conditions (ALL must hold):
  - Reflection importance ≥ 9
  - Reflection has ≥ 3 source citations
  - Content does not contradict existing core memory
  - Promotion target is values, non_negotiables, or relationship_map ONLY

NEVER promote: demographic_anchor, life_defining_events, identity_statement
```

### Memory Cap and Eviction

Working memory observation stream is capped at 1,000 entries. When full:
- Score all observations by `importance * recency_factor`
- Evict the lowest-scoring 10% (100 entries)
- Evicted observations that were cited by reflections are archived (metadata only, full content dropped)

For simulations exceeding 1,000 observations: consider MemGPT-style hierarchical archival (documented as an extension point, not required for v1).

---

## 9. Cognitive Loop

### The Four Operations

```
Stimulus arrives
      │
      ▼
  PERCEIVE — process stimulus through persona's psychological lens
      │         Input: stimulus + core memory + recent working memory
      │         Output: observation (content, importance, valence)
      │         Model: Haiku (fast, cheap — runs per stimulus × persona)
      │
      ▼
  REMEMBER — write observation to working memory
      │         Deterministic: no LLM call
      │         Update importance accumulator
      │
      ▼
  (if importance_accumulator > threshold)
  REFLECT — synthesize patterns from recent observations
      │         Input: top-20 observations + core memory
      │         Output: 2-3 reflections with source citations
      │         Model: Sonnet (reflection needs depth)
      │
      ▼
  (if decision point reached)
  DECIDE — reason through the decision
              Input: scenario + core memory + top-10 relevant memories + tendencies
              Output: decision + confidence + reasoning trace + drivers + objections
              Model: Sonnet, max_tokens=2048
```

### Perceive

The persona does not passively receive stimuli. It processes them through its psychological lens:
- A health-anxious persona amplifies medical claims
- A peer-influence-driven persona attends to social proof
- A price-sensitive persona notices cost signals others ignore

**Prompt structure:**
```
You are [persona name]. [core memory injected]

You just encountered: [stimulus description]

Given who you are, your values, and your past experiences:
1. What stands out to you about this?
2. How important is this to you? (1-10)
3. How does it make you feel? (-1.0 to 1.0, negative to positive)

Respond in first person, in character.
```

### Reflect

Triggered when cumulative importance exceeds threshold. The persona steps back and forms higher-order insights.

**Prompt structure:**
```
You are [persona name]. [core memory injected]

Here are your recent experiences:
[top-20 observations, ordered by time]

Step back and think about what patterns you're noticing.
What 2-3 insights or realizations are forming?
These should be about YOUR evolving views, not summaries of events.

For each insight, cite which specific experiences led you to it.
```

### Decide

The five-step reasoning chain:

**Prompt structure:**
```
You are [persona name]. [core memory injected]
[tendency summary injected as soft context]

You are now facing this decision:
[scenario description]

Here are your relevant memories and experiences:
[top-10 retrieved memories]

Think through this decision step by step:

1. GUT REACTION: What is your immediate, instinctive response?
2. INFORMATION PROCESSING: What information matters most to you here? What are you paying attention to?
3. CONSTRAINT CHECK: Are there hard limits (budget, non-negotiables, absolute avoidances) that apply?
4. SOCIAL SIGNAL CHECK: What would the people you trust think? What would [primary decision partner] say?
5. FINAL DECISION: What do you actually decide to do, and why?

Also state:
- Your confidence in this decision (0-100)
- The top 2-3 factors that drove your decision
- Any objections or hesitations you have
- What would change your mind

Respond in first person, in character.
```

### What Makes This Different From Static Persona Prompting

| Static Persona | Simulatte Cognitive Loop |
|---------------|------------------------|
| Every call starts from zero | Memory persists across stimuli |
| Two stimuli are independent | Early experiences influence later ones |
| Trust is a label | Trust builds or erodes incrementally |
| Decisions are prompt-driven | Decisions are memory-informed |
| No temporal dimension | Reflections change how future stimuli are processed |
| Profile = persona | Profile + memory + accumulated experience = persona |

---

## 10. Constraint System

### Hard Constraints (Never Violate)

These represent economic or psychological impossibilities. If sampling produces a violation, adjust the second value.

| Constraint | Rule |
|-----------|------|
| Income below poverty line + premium preference > 0.85 | Reduce premium preference to ≤ 0.55 |
| Tier 3/rural geography + digital payment comfort > 0.85 | Reduce to ≤ 0.65 |
| Health anxiety < 0.2 + health supplement belief > 0.80 | Raise health anxiety to ≥ 0.45 |
| Age < 25 + brand loyalty > 0.80 | Reduce loyalty to ≤ 0.60 |
| High income (top bracket) + extreme deal seeking > 0.85 | Reduce deal seeking to ≤ 0.60 |
| Risk tolerance > 0.80 + loss aversion > 0.80 | Reduce loss aversion to ≤ 0.50 |

### Soft Constraints (Rare But Possible)

These are statistically uncommon but not impossible. The system flags them as tensions rather than rejecting.

| Combination | Handling |
|------------|---------|
| High income + high deal seeking (0.60-0.85) | Flag as tension: "earns well but hunts for deals" |
| High education + low information need | Flag as tension: "educated but trusts gut over research" |
| Young age + high brand loyalty (0.60-0.80) | Flag as tension: "early commitment to brands" |
| Low social proof bias + high conformity | Flag as tension: "thinks independently but acts conventionally" |

### Correlation Constraints

Directional consistency rules between attributes (from architecture.md Section 1):

| Attribute A | Direction | Attribute B | ρ rule |
|------------|-----------|-------------|--------|
| budget_consciousness → high | → | deal_seeking | ρ ≥ 0.65 |
| social_proof_bias → high | → | wom_receiver_openness | ρ ≥ 0.60 |
| brand_loyalty → high | → | indie_brand_openness | inverse ρ ≤ -0.50 |
| risk_tolerance → low | → | status_quo_bias | ρ ≥ 0.60 |
| information_need → high | → | research_before_purchase | ρ ≥ 0.55 |
| perceived_time_scarcity → high | → | convenience_preference | ρ ≥ 0.60 |

### Tendency-Attribute Consistency

When behavioural tendencies are assigned, they must be directionally consistent with attributes:

| Attribute Condition | Tendency Requirement |
|-------------------|---------------------|
| budget_consciousness > 0.70 | price_sensitivity band ≥ "high" |
| budget_consciousness < 0.35 | price_sensitivity band ≤ "medium" |
| brand_loyalty > 0.70 | switching_propensity band = "low" |
| social_proof_bias > 0.65 | trust_orientation.peer ≥ 0.65 |
| authority_bias > 0.65 | trust_orientation.expert ≥ 0.65 |
| ad_receptivity < 0.30 | trust_orientation.ad ≤ 0.25 |
| information_need > 0.70 | objection_profile must include need_more_information |
| risk_tolerance < 0.30 | objection_profile must include risk_aversion |

Violations are flagged as `TENDENCY_ATTRIBUTE_INCONSISTENCY` and must be resolved before output.

### Narrative Constraints

The narrative must not contradict:
- Behavioural tendencies (describing "brand agnostic" when switching_propensity is "low")
- Demographic anchor (metro lifestyle details for a rural persona)
- Key tensions (omitting the documented tensions)
- Trust orientation (describing trust in ads when trust_orientation.ad < 0.20)

### Anti-Stereotypicality Constraints

These are hard constraints. They apply to all persona generation and to any cultural realism layer (see Section 15). They exist because lazy cultural defaults produce useless personas, not realistic ones.

The following are **prohibited defaults** — they must not be assumed absent explicit support from the persona's attribute profile:

| Prohibited Default | What to Do Instead |
|--------------------|-------------------|
| Joint family assumed for all Indian personas | Derive household structure from `demographic_anchor.household.structure`. A metro professional in their 30s may live alone. |
| Low-income assumed for Indian personas | Derive from `income_bracket`. India has a large and growing affluent segment. Default to the ICP-specified range. |
| Hindi-speaking assumed | Derive from `location.region`. India has 22+ scheduled languages. A Chennai persona is not a Hindi speaker by default. |
| Metro city defaulted when not specified | Respect ICP geography. Tier 2 and Tier 3 cities are valid and common target markets. |
| Traditional / conservative assumed | Derive from `values` and `lifestyle` attributes. Urban professional personas are not inherently traditional. |
| Weddings, festivals, and arranged marriage as default texture | Use only when persona attributes and life stories specifically support it. These are not universal Indian identifiers. |
| "Jugaad" as a universal Indian trait | Jugaad is domain and segment specific. Assigning it universally is a stereotype, not an insight. |
| Single trust pattern for all Indian consumers | Trust patterns vary by education, geography, generation, and category. Derive from `trust_orientation` attributes. |
| India treated as one culture | India is a multi-regional, multi-linguistic, multi-class population. Attributes must reflect the specific segment, not "Indian culture" as a monolith. |
| Class or caste-coded clichés | Persona identity must be derived from attributes and life stories, not from assumed social-group scripts. |

**Enforcement rule:** If a narrative or cultural enrichment output contains any of the above defaults without explicit derivation from the persona's attribute profile, it fails the anti-stereotypicality check and must be regenerated.

This constraint applies with equal force to:
- Standard LLM-generated narratives
- Sarvam-enriched outputs (Section 15)
- Interview dialogue
- Decision reasoning traces

---

## 11. Distinctiveness Enforcement

### Persona Type System

Eight types guide (not dictate) cohort composition:

| Type | Description | Key Signal |
|------|-------------|-----------|
| **The Pragmatist** | Decides on utility and price. Minimizes friction. | Low brand loyalty, high price sensitivity |
| **The Loyalist** | Established habits; resistant to switching. | High consistency, habitual decision style |
| **The Aspirant** | Purchases toward desired identity. | Gap between self-concept and behaviour |
| **The Anxious Optimizer** | Over-researches. Delays decisions. Seeks certainty. | High analytical style, low risk appetite |
| **The Social Validator** | Won't act without peer signal. | Trust anchor: peer, social decision style |
| **The Value Rebel** | Rejects mainstream on principle. | Counter-cultural values, high independence |
| **The Reluctant User** | Uses product but wishes they didn't have to. | Low satisfaction, moderate-high churn risk |
| **The Power User** | Deeply engaged; evangelizes; pushes limits. | High feature orientation, high consistency |

### Cohort Composition Rules

| Cohort Size | Requirement |
|------------|-------------|
| 3 | ≥ 3 distinct types |
| 5 | ≥ 4 distinct types |
| 10 | All 8 types represented |
| 10+ | All 8 types + additional variation within types |

### Diversity Metrics

| Metric | Threshold | Check |
|--------|-----------|-------|
| City concentration | No city > 20% | Distribution check |
| Age bracket concentration | No bracket > 40% | Distribution check |
| Income bracket coverage | ≥ 3 brackets represented | Coverage check |
| Gender balance | Appropriate to category | Domain-specific |
| Decision style distribution | No style > 50% | Distribution check |
| Trust anchor distribution | ≥ 3 anchors represented | Coverage check |

### Distinctiveness Metric

**Mean pairwise cosine distance on 8 core attributes:**
- Threshold: > 0.35
- If below: identify the most similar pair, resample one of them from a different stratification band
- Recheck until threshold met or 3 resample attempts exhausted (then flag and proceed)

### Tension Requirement

Every persona must carry at least one internal contradiction — a value they hold that conflicts with a behaviour they exhibit.

Examples:
- "Wants the absolute best for their child but faces a hard budget ceiling"
- "Values independence and self-reliance but always checks with their mother first"
- "Distrusts big brands on principle but keeps buying from them out of convenience"

Tensions make personas human. A persona without tensions is a stereotype.

---

## 12. Validation Framework

### Gate Progression

```
Gate 1: Schema Validity
  → Every persona parses against schema without error
  → Target: 100% pass rate

Gate 2: Hard Constraint Compliance
  → Hard constraint violation rate
  → Target: < 5%

Gate 3: Tendency-Attribute Consistency
  → Directional consistency checks
  → Target: < 5% violation rate

Gate 4: Narrative Completeness
  → first_person, third_person, display_name present
  → Target: 100%

Gate 5: Narrative Alignment
  → No contradictions between narrative and attributes/tendencies
  → Target: 0 contradictions (automated scan + manual review)

Gate 6: Population Distribution
  → No city >20%, no age bracket >40%, income spans ≥3 brackets
  → Target: all pass

Gate 7: Cohort Distinctiveness
  → Mean pairwise cosine distance on core attributes
  → Target: > 0.35

Gate 8: Persona Type Coverage
  → Unique types represented / required types
  → Target: per cohort size rules above

Gate 9: Tension Completeness
  → Every persona has ≥1 explicit tension
  → Target: 100%

Gate 10: Memory Bootstrap (Simulation-Ready only)
  → Seed memories per persona
  → Target: ≥ 3

Gate 11: Tendency Source Coverage
  → Every tendency has source ≠ null
  → Target: 100%
```

### Behavioural Validity Tests

These go beyond structural checks to test whether personas *behave* like coherent, believable individuals.

#### BV1: Repeated-Run Behavioural Stability

**What it means:** The same persona, given the same stimulus sequence, should produce substantially similar (not identical) decisions across runs. Complete randomness = no identity. Perfect identity = no realism.

**How to test:** Run the same persona through the same 5-stimulus sequence 3 times. Compare decisions at each step.

**v1 threshold:** ≥ 2 of 3 runs produce the same final decision. Reasoning traces share ≥ 60% of cited drivers. Confidence scores within ±15 points.

**Failure looks like:** Decisions flip randomly between runs with no pattern. Or: decisions are byte-identical across runs (no human variability).

#### BV2: Memory-Faithful Recall

**What it means:** When a persona makes a decision, the reasoning trace should reference memories that actually exist in its working memory. The persona should not hallucinate experiences it never had, and should not ignore pivotal experiences it did have.

**How to test:** After a 10-stimulus simulation, present a decision scenario. Check: (a) every memory cited in the reasoning trace exists in working memory, (b) any observation with importance ≥ 8 that is topically relevant appears in retrieved memories.

**v1 threshold:** (a) 100% citation validity — no hallucinated memories. (b) ≥ 80% recall of high-importance relevant observations.

**Failure looks like:** Persona cites "I remember when the doctor recommended..." but no doctor stimulus was ever presented. Or: persona was shown a devastating negative review (importance 9) but doesn't mention it when deciding.

#### BV3: Temporal Consistency Across Multi-Turn Simulation

**What it means:** A persona's attitudes should evolve coherently across a stimulus sequence, not reset or contradict without cause. If stimulus 3 builds trust and stimulus 7 confirms it, the persona should show accumulating confidence — not treat each stimulus as independent.

**How to test:** Run a 10-stimulus sequence designed with a clear trust-building arc (stimuli 1-5 positive, 6-10 mixed). Check that: (a) confidence/trust increases across stimuli 1-5, (b) reflections after stimulus 5 reference the positive trend, (c) mixed stimuli 6-10 produce nuanced responses (not a full trust reset).

**v1 threshold:** (a) Monotonic or near-monotonic confidence increase across the positive arc. (b) At least 1 reflection references the trend. (c) Final decision reasoning cites both positive and mixed experiences.

**Failure looks like:** Persona shows no trust accumulation despite 5 positive stimuli. Or: a single negative stimulus completely overwrites all prior positive experience.

#### BV4: Interview Realism

**What it means:** In Deep Interview modality, the persona should answer open-ended questions in character, referencing its life stories, values, and experiences — not producing generic responses or breaking character.

**How to test:** Present 5 open-ended interview questions (e.g., "Tell me about the last time you made a difficult purchase decision," "What does your spouse think about how you spend money?"). Evaluate: (a) responses reference specific life story elements, (b) responses are consistent with attribute profile, (c) responses maintain first-person voice throughout, (d) persona volunteers information organically rather than just answering the question.

**v1 threshold:** (a) ≥ 3 of 5 responses cite specific life story or core memory details. (b) 0 contradictions with attribute profile. (c) 100% first-person voice. (d) ≥ 2 of 5 responses include unprompted elaboration.

**Failure looks like:** Persona gives generic answers that could apply to anyone ("I try to find the best value"). Or: persona breaks character ("As an AI..."). Or: answers contradict the profile ("I'm very price-sensitive" when budget_consciousness = 0.2).

#### BV5: Resistance to Persona Collapse Under Adjacent Scenarios

**What it means:** Two personas with similar but distinct profiles should produce detectably different responses to the same scenario. The system must not collapse adjacent personas into identical outputs.

**How to test:** Take two personas that share the same persona type but differ in life stories, 2-3 key attributes, and at least 1 tension. Present the same decision scenario. Compare reasoning traces.

**v1 threshold:** (a) Different final decisions OR same decision with ≥ 3 different cited drivers. (b) Reasoning traces share < 50% of verbatim language. (c) At least 1 driver unique to each persona that traces to their specific life story or tension.

**Failure looks like:** Two "Pragmatist" personas produce nearly identical reasoning traces despite different life stories. The system is collapsing to the type label rather than differentiating on identity.

#### BV6: Believable Consistency vs Unrealistic Rigidity

**What it means:** A persona should be consistent with its identity but not robotically so. Real humans sometimes act against their tendencies — a price-sensitive person occasionally splurges, a brand-loyal person sometimes tries something new. The persona should show occasional, motivated departures from type.

**How to test:** Present 10 decision scenarios to a persona, including 2 "override scenarios" designed to trigger departure from tendency (e.g., a price-sensitive persona presented with a health emergency for their child; a brand-loyal persona presented with unignorable evidence of product failure). Check: (a) the persona follows its tendencies in ≥ 7 of 10 scenarios, (b) in override scenarios, the persona departs from tendency with explicit reasoning, (c) departures reference the specific override context, not random drift.

**v1 threshold:** (a) Tendency-consistent in 70-90% of scenarios (not 100%). (b) Override scenarios produce a departure with cited reasoning in ≥ 1 of 2 cases. (c) No persona shows 100% consistency across all 10 scenarios (that's a robot, not a person).

**Failure looks like:** Persona is perfectly consistent in all 10 scenarios including overrides (unrealistic rigidity). Or: persona departs from tendency randomly in 5+ scenarios without override context (no identity coherence).

### Cultural Realism Layer Validation (When Sarvam Is Active)

These tests apply whenever the Indian Cultural Realism Layer (Section 15) is invoked. They must pass before any Sarvam-enriched output is delivered or used in a simulation.

#### CR1: Isolation Test — Core Persona Fidelity

**What it means:** Sarvam enrichment must change texture, not substance. The same persona run through the standard flow and the Sarvam-enriched flow must produce outputs that are recognisably the same person making the same decisions.

**How to test:** Run the same persona through one decision scenario twice — once standard, once with Sarvam enrichment active. Compare:

| Field | Allowed to Differ | Must Not Differ |
|-------|------------------|----------------|
| Narrative phrasing | Yes — cultural texture is expected | — |
| Cultural examples cited | Yes | — |
| Idiomatic style | Yes | — |
| Attributes | — | No change permitted |
| Behavioural tendencies | — | No change permitted |
| Memory entries | — | No change permitted |
| Final decision | — | No material change |
| Top cited drivers | — | Same drivers, possibly expressed differently |
| Reasoning trace structure | — | Same 5-step structure |
| Confidence score | — | Within ±5 points |

**v1 threshold:** Zero attribute/tendency/memory changes. Final decision identical. Confidence within ±5 points. At least 1 cultural reference added to narrative that is not present in standard output.

**Failure looks like:** Sarvam-enriched persona makes a different decision. Or: enrichment removes a tension. Or: enrichment adds an attribute (e.g., silently raises health_anxiety). Or: reasoning trace changes from 5 steps to 3.

#### CR2: Stereotype Audit

**What it means:** Sarvam-enriched outputs must derive Indian context from the persona's attribute profile, not from generic Indian cultural scripts.

**How to test:** For each Sarvam-enriched output, check: (a) every cultural reference or contextual detail can be traced to a specific attribute, life story element, or location in the persona record; (b) none of the prohibited defaults from Section 10 (Anti-Stereotypicality Constraints) appear without derivation.

**v1 threshold:** (a) ≥ 90% of cultural details are traceable to persona attributes. (b) 0 prohibited defaults present without derivation.

**Failure looks like:** A persona from Chennai described consulting her joint family for a SaaS purchase decision when household.structure = "single-person." A tier-2 city persona described using jugaad framing with no lifestyle or values attributes supporting it.

#### CR3: Cultural Realism Audit

**What it means:** Indian personas enriched by Sarvam should read as grounded in actual Indian lived experience — not as Western-default personas with Indian names, and not as caricatures.

**How to test:** Human evaluation by an evaluator with domain knowledge of the target segment. Ask: (a) does this persona feel like a real person in this segment? (b) are the cultural details specific to the geography and demographic, or generic? (c) does the output avoid both "too Western" and "too stereotypically Indian"?

**v1 threshold:** Evaluator rating ≥ 4/5 on "cultural specificity" and "avoidance of caricature." Minimum 2 independent evaluators per domain before Sarvam enrichment is approved for that domain.

**Failure looks like:** Evaluator says "this could be any urban Indian" (too generic) or "this reads like an outsider's idea of India" (caricature) or "this sounds like an American with an Indian name" (Western default bias).

#### CR4: Persona Fidelity Audit

**What it means:** After Sarvam enrichment, the persona must still sound like the same individual — not like a new persona who happens to share the same attributes.

**How to test:** Present the standard narrative and the Sarvam-enriched narrative to an evaluator without labelling which is which. Ask: "Are these two descriptions of the same person?" If the evaluator says no, the enrichment has changed identity, not just texture.

**v1 threshold:** Evaluator confirms same person in ≥ 4 of 5 test pairs.

**Failure looks like:** Standard narrative describes an independent, research-driven buyer; Sarvam-enriched narrative describes a consensus-seeking family-oriented buyer. Different identity, not just different cultural texture.

### Calibration Gates (When Applicable)

| Gate | Check | Threshold |
|------|-------|-----------|
| C1: Status set | calibration_state.status ≠ null | Required for delivery |
| C2: Benchmark applied | For new domains, benchmark anchoring applied | Required first time |
| C3: Conversion plausibility | Simulated conversion within 0.5x-2x of benchmark | Warn if outside |
| C4: Client feedback trigger | If client outcome data available, feedback loop must run | Required |
| C5: Calibration age | Populations > 6 months flagged as stale | Warning |

### Simulation Quality Gates

| Gate | Check | Threshold |
|------|-------|-----------|
| S1: Zero error rate | Run --max 5 first | 100% completion |
| S2: Decision diversity | No single decision > 90% | Warn if violated |
| S3: Driver coherence | Top drivers are category-relevant | Manual review |
| S4: WTP plausibility | Median within ±30% of ask price | Warn if outside |

---

## 13. Anti-Drift Guardrails — The Simulatte Constitution

This section is the constitutional law of the system. It exists because design drift happened once (Sprints A-C collapsed the system into a coefficient model) and must not happen again. Every implementation decision, sprint plan, and code review must be checkable against these guardrails.

### 13A. Ten Non-Negotiable Principles

These are not guidelines. They are axioms. Violating any one is a spec violation that must be corrected before merge.

| # | Principle | Test: You Have Drifted If... |
|---|-----------|------------------------------|
| **P1** | **A persona is a synthetic person, not a segment model.** Personas have identity, memory, history, and cognition. Segments have parameters and labels. | ...you can fully reconstruct a persona from a 10-field vector. |
| **P2** | **The LLM is the cognitive engine.** It perceives, reflects, and decides. It is not a narrator explaining pre-computed outputs. | ...the LLM's only role is generating text after decisions are made by other code. |
| **P3** | **Memory is the product.** Without memory, there is no temporal simulation, no experiment modularity, no persona reuse. Memory is not a "nice to have." | ...memory is "planned for a later sprint" while other features ship. |
| **P4** | **Behavioural tendencies are soft priors, not decision functions.** They shape reasoning. They do not replace it. The decision emerges from the LLM's reasoning trace, not from a formula. | ...you are computing P(purchase) from coefficients and using the LLM to narrate the result. |
| **P5** | **Identity is life stories + values + events + relationships + constraints.** Tendencies are properties of the persona, not the persona itself. Two personas with identical tendencies but different life stories are different people. | ...personas with different life stories but same tendency bands produce identical decisions. |
| **P6** | **Grounding supports the simulation — it does not replace it.** Domain data anchors tendencies in evidence. It does not substitute for LLM reasoning, memory accumulation, or reflection. | ...removing the grounding pipeline causes the cognitive loop to stop functioning. |
| **P7** | **Calibration is a trust layer, not the product.** It makes the simulation credible. It comes after identity, memory, and cognition work. | ...calibration sprints are blocking cognition sprints. |
| **P8** | **The core architecture is domain-agnostic.** Domain-specific knowledge enters through taxonomy extensions and the grounding pipeline. The base schema, memory architecture, cognitive loop, and constraint system must work for any domain. | ...you are adding domain-specific attributes (e.g., `pediatrician_trust`) to the base taxonomy. |
| **P9** | **Every persona carries internal tension.** A persona without contradiction is a stereotype. Real humans hold values that conflict with their behaviours. This is required, not optional. | ...personas pass all constraint checks without a single flagged tension. |
| **P10** | **Transparency over performance.** Every tendency has a source label. Every reflection has citations. Every calibration has documentation. Users must be able to distinguish grounded from estimated from inferred. | ...outputs omit source fields, or tendencies are unlabelled as to their provenance. |

### 13B. Ten Anti-Patterns to Avoid

| # | Anti-Pattern | What It Looks Like | Why It's Dangerous |
|---|-------------|--------------------|--------------------|
| **A1** | **Coefficient creep** | Adding more numerical parameters to the persona model. "Let's add a loyalty_score, a churn_coefficient, a WTP_intercept..." | Transforms personas into statistical models. Every coefficient is a step toward replacing reasoning with formulas. |
| **A2** | **Narrative-last architecture** | Generating the narrative as the final step, after all decisions are made, as a human-readable summary. | Makes the narrative decorative. The narrative should be generated *before* simulation (as part of identity) and *read by the system* (as part of core memory). |
| **A3** | **Memory deferral** | "We'll add memory in Phase 3, after calibration works." | Inverts the priority order. Without memory, you cannot validate temporal simulation, which is the core differentiator. This already happened once. |
| **A4** | **Domain leakage** | Adding category-specific attributes, constraints, or logic to the base system for one client's use case. | Makes the system work perfectly for one domain and break for all others. Domain knowledge belongs in extensions and grounding, not in core. |
| **A5** | **Validation theater** | Reporting high aggregate correlation scores without testing individual-level behavioral validity (BV1-BV6). | Gives false confidence. A population can show 90% aggregate accuracy while every individual persona is stereotypical. |
| **A6** | **Type collapse** | Personas of the same type producing identical outputs. "All Pragmatists say the same thing." | Types are sampling guides, not personality scripts. Life stories, tensions, and specific attribute values must differentiate within types. |
| **A7** | **Grounding absolutism** | Refusing to generate personas without domain data. "We can't produce anything useful without 500 reviews." | The system must work in Proxy Mode. Grounding improves quality; its absence should not block generation. |
| **A8** | **Context window stuffing** | Putting the entire persona record (all 200 attributes, all memories, all tendencies) into every LLM call. | Wastes tokens, dilutes signal, increases cost. Only core memory + relevant working memories + tendency summary should be in context. |
| **A9** | **Platform-first thinking** | Building multi-user infrastructure, database schemas, API layers, and UI before the persona generation and cognitive loop work. | Premature optimization. The platform is meaningless without personas that think and remember. Build the engine, then the chassis. |
| **A10** | **Client-specific optimization** | Tuning the system to produce output that one specific client likes, at the expense of generalizable quality. | Creates a consulting tool, not a product. The system should be domain-agnostic; the domain should be an input, not a hardcoded assumption. |

### 13E. Cultural Layer Anti-Patterns

These specifically guard the Indian Cultural Realism Layer (Section 15) from producing harm or drift. They complement the ten anti-patterns above.

| # | Anti-Pattern | What It Looks Like | Why It's Dangerous |
|---|-------------|--------------------|--------------------|
| **CA1** | **Sarvam as hidden reasoning engine** | Sarvam is invoked during perceive(), reflect(), or decide() — not just narrative enrichment. | Violates the core architecture. Sarvam may only operate post-core, on expression. If it influences reasoning, it changes who the persona is, not how they sound. |
| **CA2** | **India mode becoming mandatory** | The cultural realism layer activates automatically for all Indian personas without client opt-in. | Removes client control. The layer is optional. Mandatory activation makes it part of the core, which it must not be. |
| **CA3** | **Cultural enrichment silently modifying decisions** | A persona chooses a different product after Sarvam enrichment because the cultural context shifted the framing. | Sarvam may change how a decision is narrated. It must not change what decision is made. If enrichment shifts the decision, the layer has leaked into cognition. |
| **CA4** | **Cultural realism as stereotype generation** | Sarvam produces Indian texture by defaulting to generic Indian scripts (joint family, festivals, jugaad) rather than deriving from persona attributes. | Produces the worst version of cultural enrichment — caricature, not realism. Violates Anti-Stereotypicality Constraints (Section 10). |
| **CA5** | **Monolithic India treatment** | The cultural layer applies the same Indian context regardless of whether the persona is from Chennai, Chandigarh, Kolkata, or a Tier 3 town in Maharashtra. | India is not one culture. Regional, linguistic, and socioeconomic specificity is the point. Generic "Indian flavor text" is less accurate than no flavor at all. |
| **CA6** | **Cultural layer extending scope over time** | Sarvam starts with narrative enrichment, then progressively gets used for interview tone, then reasoning priming, then decision framing — scope creeping across releases. | Anti-pattern A1 (coefficient creep) applied to the cultural layer. Every scope expansion must be explicitly approved via spec revision. Sarvam's permitted scope is defined in Section 15C and does not expand by default. |
| **CA7** | **Conflating language with culture** | Using Sarvam for multilingual output (Hindi, Tamil, etc.) without controlling for cultural accuracy per region. | Generating in Hindi for a Tamil Nadu persona is not Indian cultural realism — it is a different error. Multilingual output is an open question (Section 14B) and must not be assumed or silently implemented. |

### 13C. Pre-Implementation Checklist

Before starting any sprint or implementation task, the developer must verify:

```
PRE-IMPLEMENTATION CHECKLIST
=============================

□ 1. Does this work serve identity, memory, or cognition?
     If not, is Phase 1 complete? (If Phase 1 is incomplete, work on Phase 1.)

□ 2. Does this change add any numerical parameters to the persona model?
     If yes: are they soft tendencies (bands + descriptions) or hard coefficients?
     Coefficients are a P4 violation.

□ 3. Does this change touch the base taxonomy or base schema?
     If yes: is the change domain-agnostic?
     Domain-specific changes to core are a P8 violation.

□ 4. Does this change defer or deprioritize memory work?
     If yes: document why and flag for review. Memory deferral is a P3 violation.

□ 5. Does this change introduce a decision that does not go through the
     cognitive loop (perceive → remember → reflect → decide)?
     If yes: is there a documented reason? Bypassing the loop is a P2 violation.

□ 6. Is the change traceable to a section of this master spec?
     If not: the spec must be updated first, then the change implemented.

□ 7. Does this change produce outputs without source labels on tendencies
     or citations on reflections?
     If yes: add provenance tracking. Unlabelled outputs are a P10 violation.

□ 8. Have I checked the Settled Decisions table (14A)?
     Am I contradicting any settled decision?
     If yes: escalate — do not implement without formal spec revision.
```

### 13D. Pre-Release Checklist

Before any population or simulation output is delivered or demonstrated:

```
PRE-RELEASE CHECKLIST
======================

STRUCTURAL QUALITY
□ 1. Schema validity: 100% parse rate (Gate 1)
□ 2. Hard constraint violations: < 5% (Gate 2)
□ 3. Tendency-attribute consistency: < 5% violation rate (Gate 3)
□ 4. Narrative completeness: 100% (Gate 4)
□ 5. Narrative alignment: 0 contradictions (Gate 5)
□ 6. Population distribution checks: all pass (Gate 6)
□ 7. Distinctiveness score: > 0.35 (Gate 7)
□ 8. Persona type coverage: per cohort size rules (Gate 8)
□ 9. Tension completeness: 100% (Gate 9)
□ 10. Tendency source coverage: 100% (Gate 11)

BEHAVIOURAL QUALITY (run on ≥ 3 sample personas)
□ 11. BV1: Repeated-run stability — ≥ 2/3 same decision, ±15 confidence
□ 12. BV2: Memory-faithful recall — 100% citation validity, ≥ 80% high-importance recall
□ 13. BV4: Interview realism — ≥ 3/5 cite life stories, 0 character breaks
□ 14. BV5: Adjacent persona distinction — < 50% shared language in reasoning traces

SIMULATION QUALITY (if simulation mode)
□ 15. BV3: Temporal consistency — confidence trends match stimulus arc
□ 16. BV6: Override test — ≥ 1/2 overrides produce motivated departure
□ 17. S1: Zero error rate on 5-persona trial run
□ 18. S2: No single decision > 90%
□ 19. Memory bootstrap: ≥ 3 seed memories per persona (Gate 10)

PROVENANCE
□ 20. Grounding mode clearly labelled (grounded / proxy / estimated)
□ 21. Calibration state documented (or explicitly "uncalibrated")
□ 22. ICP Spec saved alongside output (versioning)
```

---

## 14. Settled Decisions, Open Questions & Build Order

### 14A. Settled Decisions

These are canonical. They are not defaults — they are the architecture. Changing any requires a formal spec revision with documented rationale.

| # | Decision | Value | Settled Because |
|---|----------|-------|----------------|
| S1 | The LLM is the cognitive engine | LLM runs perceive(), reflect(), decide() | Core philosophy. Course-corrected from parameter-first design. Not negotiable. |
| S2 | Behavioural tendencies are soft priors | Natural language in reasoning context | Parametric functions were tried (Sprints A-C) and rejected. See Section 8 of Research doc. |
| S3 | Core/working memory split | Core immutable, working resettable per experiment | Required for experiment modularity (the product's differentiator). |
| S4 | Anchor-first attribute ordering | 8 core attributes filled first, rest conditioned | From DeepPersona. Prevents incoherent profiles. Proven mechanism. |
| S5 | 5:3:2 stratification ratio | 50% near / 30% mid / 20% far | From DeepPersona. Best documented fix for homogeneity bias. Empirically validated. |
| S6 | Progressive conditional filling | Each attribute conditioned on all prior | From DeepPersona. Prevents contradictory sampling. No alternative considered. |
| S7 | Memory stream with retrieval formula | score = α·recency + β·importance + γ·relevance | From Generative Agents. Cohen's d = 8.16 improvement. Proven mechanism. |
| S8 | Reflections require source citations | ≥ 2 source_observation_ids per reflection | Uncited reflections are untraceable. Memory integrity depends on this. |
| S9 | Domain-agnostic core architecture | Base taxonomy shared; domain enters via extensions only | Prevents domain-locking. Learned from LittleJoys pilot where domain leaked into core. |
| S10 | Every persona has ≥ 1 internal tension | Value-behaviour contradiction required | Tension is what makes personas human, not stereotypes. Non-negotiable quality bar. |
| S11 | Core memory always in context window | Injected into every LLM call during simulation | Identity persistence depends on this. Without it, persona drift is inevitable. |
| S12 | Three-layer taxonomy (base + domain + anchors) | ~150 + 30-80 + 0-10 | Balances depth with manageability. Domain flexibility without noise. |
| S13 | Tendency source must be tracked | Every tendency has source: grounded / proxy / estimated | Provenance enables trust assessment. Users must know what is empirical vs inferred. |
| S14 | Narrative is constrained by attributes and tendencies | Narrative cannot contradict the data model | Prevents "compelling story, wrong persona" failure. |
| S15 | Build order: identity → memory → cognition → grounding → calibration | Phase 1 before Phase 2 before Phase 3 | Course-corrected from calibration-first. Identity and memory are the product. |
| S16 | No interview requirement | Taxonomy + domain data + LLM, not real human interviews | Scalability and domain flexibility over maximum fidelity. Conscious tradeoff. |
| S17 | Promotion mechanism for working → core | Only via importance ≥ 9, ≥ 3 citations, no contradiction | Prevents casual core memory corruption. Demographics and life events never promoted. |
| S18 | Experiment isolation by default | Working memory does not leak between experiments | Required for scientific validity of experiments. |
| S19 | Constraint checker runs before output | Hard violations block output; soft violations flag as tensions | Quality gate, not optional post-processing. |
| S20 | Persona ID is permanent | Once assigned, never reused or changed | Identity permanence extends to the identifier. |
| S21 | Sarvam is optional and off by default | Client must explicitly opt in; no automatic activation | A realism layer that runs without consent is not optional — it is part of core. The opt-in requirement is structural, not a preference. |
| S22 | Sarvam is India-only | Activated only when ICP/market = India | The layer is calibrated for Indian cultural context. Applying it to other geographies would produce incorrect enrichment. |
| S23 | Sarvam is post-core only | Invoked after persona record is fully finalized | Sarvam receives a completed persona as input. It cannot influence what is in that persona — only how it is expressed. |
| S24 | Sarvam operates on expression only | Narrative, dialogue texture, cultural references, contextual examples | Permitted scope is defined exhaustively in Section 15C. Anything not listed there is disallowed by default. |
| S25 | Sarvam must not change the decision | CR1 isolation test must pass — final decision identical with and without enrichment | If enrichment changes the decision, it has leaked into cognition. This is a hard architectural violation. |
| S26 | Anti-stereotypicality constraints apply to Sarvam outputs equally | Section 10 prohibited defaults apply to all outputs including Sarvam-enriched | Cultural enrichment is not a license for stereotyping. |
| S27 | CR1-CR4 validation tests must pass before Sarvam enrichment is approved for any domain | Per-domain evaluation required | Generic approval is not sufficient. Each new domain requires evaluation by human evaluators with domain knowledge. |
| S28 | ISOLATED is the default social simulation level | `ExperimentSession.social_simulation_level = ISOLATED` | Zero overhead at default. Existing single-persona experiments are structurally unaffected by the social simulation layer. |
| S29 | Social influence enters only through perceive() | `format_as_stimulus()` produces stimulus text injected via `run_loop()` | LLM retains full authority to accept, reject, or reframe peer signals. Influence is evidence, not mutation. Upholds P2 and P4. |
| S30 | Tendency band fields never drift | Only description prose may change via `apply_tendency_drift()` | Band, weights, dominant, source are structural anchors. Drift corrupting these would violate identity permanence (S3). |
| S31 | Social simulation calibration confirmed (Sprint SC) | Susceptibility formula: no tuning; signal strength: no tuning; SV3 thresholds (0.60/0.80): confirmed | SVB1 (N=243): mean=0.319, 0 ceiling clamps. SVB2 (N=25): range=[0.10, 0.93]. SVB3: FULL_MESH N=2 scores 0.50, safely below WARN. |

### 14B. Open Research Questions

These have v1 defaults that are functional but not validated. They are subject to empirical testing and may change. Each default is marked with its confidence level.

| # | Question | v1 Default | Confidence | What Would Change It |
|---|----------|-----------|------------|---------------------|
| O1 | Reflection threshold | 50 (importance sum) | Low | Empirical testing across different simulation lengths. May need to be adaptive (shorter sims = lower threshold). Park used ~150 for continuous time. |
| O2 | Memory decay rate | 0.995/hour (exponential) | Low | May need event-based decay instead of time-based for irregular stimulus spacing. Test with simulations where inter-stimulus gaps vary. |
| O3 | Memory cap | 1,000 observations with 10% eviction | Medium | Adequate for most simulations (≤50 turns). For 100+ turn simulations, MemGPT-style hierarchical archival may be needed. |
| O4 | Retrieval K values | K=10 for decide, K=20 for reflect | Medium | May need tuning per simulation complexity. Too few = shallow decisions. Too many = context window pressure. |
| O5 | Base taxonomy size | ~150 attributes | Medium | May be too many (noise) or too few (missing dimensions). Validate by measuring attribute-usage rate in decisions — unused attributes are noise. |
| O6 | Minimum grounding data volume | 200 reviews/posts | Low | Based on GMM stability intuition, not empirical testing. Need systematic cluster stability analysis across data volumes. |
| O7 | Grounding cluster count K | Data-driven (BIC/AIC), min=3, max=8 | Medium | BIC/AIC is standard but may not suit sparse behavioural data. May need domain-specific override. |
| O8 | Model routing | Haiku for perceive, Sonnet for reflect/decide | Medium | Cost-quality tradeoff. Haiku may be too shallow for complex stimuli. Sonnet may be overkill for simple surveys. Test per modality. |
| O9 | Distinctiveness threshold | Mean cosine distance > 0.35 | Low | Arbitrary. Needs calibration against human perception — at what distance do evaluators perceive personas as "different enough"? |
| O10 | Noise injection for realism | None (LLM temperature only) | Low | Real humans show more decision noise than LLM personas. May need explicit noise mechanisms beyond temperature. |
| O11 | Proxy formula coefficients | See Section 7 proxy table | Low | Coefficients (e.g., 0.7, 0.3) are heuristic. Should be validated against grounded-mode outputs when data is available. |
| O12 | Persona type system (8 types) | Fixed set of 8 | Medium | May need expansion for B2B contexts (e.g., "The Champion", "The Blocker"). Type system should be extensible per domain. |
| O13 | Cross-experiment memory carryover | Strict isolation (no carryover) | High | Default is correct for scientific validity. Opt-in carryover flag is a later enhancement for longitudinal studies. |
| O14 | Sarvam scope: narratives only vs also interview dialogue | Narratives only (v1) | Medium | Interview mode involves real-time turn-by-turn dialogue. Enrichment at that granularity introduces more risk of scope creep. Start with narrative; evaluate before extending to interview. |
| O15 | Multilingual output via Sarvam | Not permitted (v1) | High | Language and culture are not the same. Generating in Hindi for a Tamil-speaking persona produces a different error than Western-default English. Multilingual output requires per-language, per-region validation before it can be approved. |
| O16 | Regional specificity depth | Geography-matched from persona location | Medium | How granular should regional enrichment be? State-level? Language-region? Tier classification? v1 defaults to urban-tier + region. More granular enrichment requires validation data. |
| O17 | Whether CR1-CR4 tests should be automated or human-evaluated | Human-evaluated (v1) | Medium | Automated stereotype detection is itself prone to bias. Human evaluation is slower but more reliable for v1. Automation can be added once patterns are established. |

### 14C. Component Phase Classification

Every major component is classified into exactly one phase. This prevents overbuilding and ensures implementation focus.

**Legend:**
- **v1 REQUIRED** — Must ship for the product to exist. No exceptions.
- **RECOMMENDED SOON AFTER v1** — Significantly improves quality/trust. Should ship within 2-3 sprints of v1.
- **LATER-PHASE** — Valuable but not blocking. Scheduled for Phase 3-4.
- **OUT OF SCOPE** — Explicitly not being built. May revisit in future product cycles.

#### Identity & Persona Construction

| Component | Phase | Rationale |
|-----------|-------|-----------|
| Base taxonomy (~150 attributes) | **v1 REQUIRED** | Without taxonomy, no structured persona construction. |
| Domain template library (CPG, SaaS, etc.) | **RECOMMENDED SOON AFTER v1** | Needed for non-grounded domains. v1 can use a single generic template. |
| Domain-data taxonomy extension (MiroFish-style) | **RECOMMENDED SOON AFTER v1** | Core value of Grounded Mode. v1 can operate in Proxy Mode. |
| Progressive conditional filling | **v1 REQUIRED** | Core generation mechanism. |
| Anchor-first ordering (8 core attributes) | **v1 REQUIRED** | Prevents incoherent profiles. |
| 5:3:2 stratification | **v1 REQUIRED** | Anti-homogeneity. Required for any cohort ≥ 5. |
| Life story generation | **v1 REQUIRED** | Identity-forming. Seeds core memory. |
| Narrative generation (first-person + third-person) | **v1 REQUIRED** | Required for identity statement and interview modality. |
| Population tables (census-calibrated demographics) | **RECOMMENDED SOON AFTER v1** | v1 can use LLM-estimated demographics with source:"estimated". Census tables improve accuracy. |
| Persona type system (8 types) | **v1 REQUIRED** | Guides cohort composition. |
| Sparsity prior for long-tail | **RECOMMENDED SOON AFTER v1** | Important for diversity but not blocking. |

#### Memory & Cognition

| Component | Phase | Rationale |
|-----------|-------|-----------|
| Core memory structure | **v1 REQUIRED** | Identity persistence. Injected into every LLM call. |
| Working memory (observations, reflections) | **v1 REQUIRED** | Temporal simulation depends on this. |
| Memory write (after perceive) | **v1 REQUIRED** | Core operation. |
| Memory retrieve (retrieval formula) | **v1 REQUIRED** | Core operation. |
| Reflection trigger + generation | **v1 REQUIRED** | Creates depth. Differentiator vs static prompting. |
| Memory eviction (cap at 1,000) | **v1 REQUIRED** | Prevents unbounded memory growth. |
| Memory promotion (working → core) | **RECOMMENDED SOON AFTER v1** | Rare operation. v1 can skip promotion; core stays fixed. |
| MemGPT-style hierarchical archival | **LATER-PHASE** | Only needed for 100+ turn simulations. |
| Perceive engine (Haiku) | **v1 REQUIRED** | First step of cognitive loop. |
| Reflect engine (Sonnet) | **v1 REQUIRED** | Creates higher-order insights. |
| Decide engine (5-step, Sonnet) | **v1 REQUIRED** | Decision mechanism. |
| Working memory reset (per experiment) | **v1 REQUIRED** | Experiment modularity depends on this. |

#### Grounding & Tendencies

| Component | Phase | Rationale |
|-----------|-------|-----------|
| Proxy tendency estimation (from attributes) | **v1 REQUIRED** | System must work without domain data. Proxy formulas are the fallback. |
| Tendency source labelling | **v1 REQUIRED** | Provenance tracking. P10 principle. |
| Reasoning prompt assembly (natural language tendencies) | **v1 REQUIRED** | How tendencies enter the cognitive loop. |
| Signal extraction pipeline (domain data → features) | **RECOMMENDED SOON AFTER v1** | Enables Grounded Mode. High value but not blocking. |
| Feature construction | **RECOMMENDED SOON AFTER v1** | Part of grounding pipeline. |
| Behavioural cluster derivation (GMM) | **RECOMMENDED SOON AFTER v1** | Part of grounding pipeline. |
| Cluster-to-tendency assignment | **RECOMMENDED SOON AFTER v1** | Part of grounding pipeline. |

#### Constraints & Validation

| Component | Phase | Rationale |
|-----------|-------|-----------|
| Hard constraint checker | **v1 REQUIRED** | Quality gate. Blocks impossible combinations. |
| Soft constraint flagger (tensions) | **v1 REQUIRED** | Produces required tensions. |
| Tendency-attribute consistency checker | **v1 REQUIRED** | Quality gate. |
| Narrative alignment check (automated scan) | **v1 REQUIRED** | Catches story-data contradictions. |
| Cohort distinctiveness metric (cosine distance) | **v1 REQUIRED** | Anti-homogeneity check. |
| Population distribution checks | **v1 REQUIRED** | Structural quality. |
| Behavioural validity tests (BV1-BV6) | **v1 REQUIRED** (BV1, BV2, BV4, BV5) / **RECOMMENDED** (BV3, BV6) | BV3 and BV6 require multi-turn simulation to test. |

#### Calibration

| Component | Phase | Rationale |
|-----------|-------|-----------|
| Benchmark calibration | **LATER-PHASE** | Trust layer. Requires grounding pipeline first. |
| Client cohort feedback loop | **LATER-PHASE** | Requires client outcome data. |
| Calibration state tracking in cohort envelope | **RECOMMENDED SOON AFTER v1** | Labelling is cheap. Even "uncalibrated" is useful metadata. |
| Calibration age checks | **LATER-PHASE** | Only relevant when populations are reused over months. |

#### Product Modalities

| Component | Phase | Rationale |
|-----------|-------|-----------|
| One-time survey | **v1 REQUIRED** | Simplest modality. First validation surface. |
| Temporal simulation | **v1 REQUIRED** | The differentiator. Proves the memory architecture works. |
| Post-event survey | **RECOMMENDED SOON AFTER v1** | Preserves working memory from simulation. Low incremental effort. |
| Deep interview | **RECOMMENDED SOON AFTER v1** | High-value modality. Leverages existing cognitive loop. |
| Persona persistence (cross-session reuse) | **RECOMMENDED SOON AFTER v1** | JSON serialization is straightforward. |
| Multi-user persona sharing | **LATER-PHASE** | Requires database, auth, permissions. Platform feature. |
| Social interaction between personas | **v1 COMPLETE (Sprints SA/SB/SC, 2026-04-03)** | Multi-agent social simulation shipped: `run_social_loop()`, 5 SocialSimulationLevels, SV1–SV5 validity gates, `--social-level` / `--social-topology` CLI flags. ISOLATED default preserves zero-overhead backward compatibility. |
| Real-time data feeds | **OUT OF SCOPE** | Massive infrastructure. Not needed for core value. |
| Fine-tuned models | **OUT OF SCOPE** | Locks to model version. Prompt-based approach preferred. |
| Predictive validity claims | **OUT OF SCOPE** | Requires calibration + validation cycles not yet built. |

### Build Order

The build order follows the corrected priority: identity and memory first, grounding and calibration after.

```
Phase 1: IDENTITY + MEMORY (the product)
  ├── Sprint 1: Taxonomy engine (base + domain extension)
  ├── Sprint 2: Identity constructor (progressive filling, life stories, narrative)
  ├── Sprint 3: Memory architecture (core/working split, write, retrieve, evict)
  ├── Sprint 4: Cognitive loop (perceive, reflect, decide)
  └── Sprint 5: Experiment modularity (working memory reset, modality switching)

Phase 2: GROUNDING + VALIDATION (trust layers)
  ├── Sprint 6: Signal extraction pipeline (domain data → features)
  ├── Sprint 7: Cluster derivation + tendency assignment (grounded mode)
  ├── Sprint 8: Constraint system (hard/soft/consistency checks)
  ├── Sprint 9: Validation framework (all 11 gates automated)
  └── Sprint 10: Cohort assembly (distinctiveness, type coverage, diversity)

Phase 3: CALIBRATION + SCALE (credibility)
  ├── Sprint 11: Benchmark calibration
  ├── Sprint 12: Client feedback loop
  ├── Sprint 13: Population-level validation reporting
  └── Sprint 14: Performance optimization (batching, caching, cost management)

Phase 4: PRODUCT MODES (full platform)
  ├── Sprint 15: One-time survey modality
  ├── Sprint 16: Temporal simulation modality
  ├── Sprint 17: Post-event survey modality
  ├── Sprint 18: Deep interview modality
  └── Sprint 19: Persona persistence and reuse (cross-session, cross-experiment)
```

**Phase 1 is the product. Phase 2 makes it trustworthy. Phase 3 makes it credible. Phase 4 makes it a platform.**

No phase should block the next from starting — but the phases represent dependency order. A persona without memory (skipping Phase 1, Sprint 3-4) cannot support temporal simulation (Phase 4, Sprint 16). A persona without grounding (skipping Phase 2) can still run surveys and interviews — it just won't be empirically anchored.

### Minimum Viable Product

The MVP that proves the thesis requires:
- Sprints 1-5 (identity + memory + cognitive loop + experiment modularity)
- Sprint 15 (one-time survey modality — simplest to validate)
- Sprint 16 (temporal simulation — the differentiator)

This produces: a population of taxonomy-deep, memory-persistent personas that can run through a stimulus sequence and show attitude/decision evolution over simulated time. No other commercial product does this with this level of identity depth.

---

## 15. Indian Cultural Realism Layer — Sarvam Integration

### 15A. Purpose

Indian personas generated by the standard Simulatte pipeline may default to Western-inflected expression: neutral-English phrasing, culturally decontextualized examples, institutional references drawn from the LLM's predominantly Western training corpus, and social context that reflects no particular geography.

The Indian Cultural Realism Layer exists to correct this. Its scope is precisely defined and narrow:

- Improve cultural specificity of Indian persona expression
- Reduce Westernized-default English bias in narratives, dialogue, and contextual framing
- Inject India-specific lived-context texture: social structures, institutions, consumption environments, family dynamics — as appropriate to the individual persona's attributes
- Make Indian personas feel like real people from real places in India, not like demographically-labelled Western personas

**This layer is an expression layer. It is not a reasoning layer, an identity layer, or a generation layer.**

It receives a fully completed persona record as input. It produces enriched expression as output. It does not modify the persona record.

### 15B. Activation Logic

The Indian Cultural Realism Layer is **off by default**.

It activates only when ALL of the following conditions are true:

1. **ICP geography / market = India** (or a defined Indian segment — e.g., "urban Indian women, 28-40")
2. **Client has explicitly opted in** via ICP Spec or runtime flag

If either condition is absent, the standard generation and expression flow runs unchanged.

```
ACTIVATION CHECK (evaluated before expression layer):

if persona.location.country == "India"
   AND client_config.sarvam_enrichment == true:
    → invoke Cultural Realism Layer (Section 15)
else:
    → proceed with standard expression
```

There is no automatic activation. There is no soft default. There is no "India persona? You probably want Sarvam." The opt-in must be explicit.

### 15C. Permitted Scope — What Sarvam May Do

Sarvam may operate on the following output surfaces only:

| Surface | What Is Permitted |
|---------|------------------|
| **Narrative (third-person)** | Rewrite for India-specific cultural texture, examples, institutional references, and lived-context detail — while preserving all factual content from the standard narrative |
| **Narrative (first-person)** | Adjust register, idiomatic style, and examples to match the persona's regional and demographic context |
| **Contextual examples** | Replace Western-default examples (e.g., "like Amazon reviews") with India-appropriate equivalents (e.g., "like Meesho seller ratings") where attribute-supported |
| **Social and family context cues** | Add specificity appropriate to the persona's household structure, location, and life stage — not assumed universals |
| **Decision environment texture** | Contextualise the decision setting: which channels, stores, apps, institutions, professionals, or social actors are realistic for this persona |
| **Interview dialogue tone** | When interview modality is used post-enrichment approval (see O14), match dialogue register to persona's regional and socioeconomic context |
| **Cultural reference grounding** | Replace generic or absent cultural references with India-specific ones that are traceable to the persona's attributes |

Every permitted operation must derive from the persona's existing attribute profile, life stories, and location. Sarvam does not invent new facts about the persona — it makes existing facts more culturally specific.

### 15D. Disallowed Scope — What Sarvam Must Not Do

Sarvam is **prohibited** from operating on or influencing the following:

| Prohibited Action | Reason |
|------------------|--------|
| Generating any part of the persona identity | Core generation is complete before Sarvam is invoked |
| Choosing or modifying attribute values | Attributes are finalized. Sarvam reads them; it does not write them |
| Changing key values | Values are part of core identity |
| Altering behavioural tendencies (price sensitivity, trust orientation, switching propensity) | Tendencies are computed from attributes. Sarvam cannot override them |
| Modifying core memory (identity statement, key values, life events, relationship map, constraints) | Core memory is immutable post-generation |
| Rewriting life-defining events | Life stories seed identity. Sarvam may not change what happened to the persona |
| Changing trust weights | Trust orientation is an attribute-derived tendency |
| Changing final decisions | Decision emerges from the cognitive loop. Sarvam operates after decisions, on expression only |
| Altering reflection outputs | Reflections are working memory. Sarvam does not touch working memory |
| Participating in perceive() / reflect() / decide() | These are cognitive loop operations. Sarvam is not part of the cognitive loop |
| Being invoked at any point during simulation | Sarvam operates on completed persona outputs, not on live simulation operations |

### 15E. Architectural Placement

Sarvam sits in exactly one position in the pipeline:

```
CORE PERSONA GENERATION
  ├── Taxonomy construction
  ├── Identity construction (demographics → attributes → life stories
  │    → derived insights → tendencies → core memory → narrative)
  ├── Cohort assembly
  └── Validation (Gates 1-11)
        │
        ▼
PERSONA RECORD FINALIZED
(immutable from this point forward)
        │
        ▼
OPTIONAL CULTURAL REALISM LAYER  ◄── Sarvam operates here only
  (only if India + opt-in)
  Input:  completed, validated persona record
  Output: enriched expression outputs (narratives, dialogue, contextual framing)
  Constraint: persona record is not modified; enriched outputs are additive
        │
        ▼
OUTPUT / EXPRESSION / INTERVIEW LAYER
  (summary cards, simulation prompts, interview dialogue)
        │
        ▼
EXPERIMENT EXECUTION
  (simulation, survey, interview — using standard cognitive loop)
```

Sarvam is never in the left branch of this pipeline. It is only in the post-core expression path.

### 15F. Output Constraints

Sarvam-enriched outputs produce an **enriched expression record** alongside the standard persona record. They do not replace the standard persona record.

The enriched expression record may contain:

```json
{
  "enrichment_applied": true,
  "enrichment_provider": "sarvam",
  "enrichment_scope": "narrative + contextual_examples",
  "enriched_narrative": {
    "third_person": "string — Sarvam-enriched version",
    "first_person": "string — Sarvam-enriched version"
  },
  "cultural_references_added": ["string — traceable to attribute"],
  "contextual_examples_replaced": [
    {
      "original": "string",
      "replacement": "string",
      "attribute_source": "string — which attribute justifies this"
    }
  ],
  "validation_status": {
    "cr1_isolation": "pass | fail | not_run",
    "cr2_stereotype_audit": "pass | fail | not_run",
    "cr3_cultural_realism": "pass | fail | not_run",
    "cr4_persona_fidelity": "pass | fail | not_run"
  }
}
```

The standard persona record (Section 5) is not overwritten. It is preserved intact. The enriched expression record is a separate, additive output.

### 15G. Anti-Stereotypicality in Indian Enrichment

All Indian cultural enrichment must comply with the Anti-Stereotypicality Constraints in Section 10. These apply to Sarvam outputs with the same force as to standard LLM outputs.

Specific rules for Sarvam enrichment:

**Rule S-1:** Every cultural detail added by Sarvam must be traceable to a specific field in the persona record (location, income bracket, household structure, education, employment, life stage, or a specific attribute value). If a detail cannot be traced to a persona field, it must not be added.

**Rule S-2:** Sarvam must not add cultural context that contradicts any existing attribute. Adding a joint family social context to a persona with `household.structure = "single-person"` is a constraint violation.

**Rule S-3:** Regional enrichment must match `location.region` and `location.urban_tier`. A Chennai persona must not receive North Indian cultural references. A Tier 3 persona must not receive metro consumption context.

**Rule S-4:** Indian diversity must be reflected, not flattened. A Tamil Nadu professional, a Rajasthan business owner, and a West Bengal homemaker are three different cultural contexts. Enrichment must differentiate, not collapse.

**Rule S-5:** Sarvam-enriched outputs are subject to the same Narrative Constraints as standard outputs (Section 10 — Narrative Constraints). Enrichment does not exempt outputs from those checks.

### 15H. Phase Classification

| Sarvam Component | Phase | Rationale |
|-----------------|-------|-----------|
| Core architecture (post-core placement, opt-in flag, permitted/disallowed scope) | **RECOMMENDED SOON AFTER v1** | High value for India deployments. Low architectural risk if scoped correctly. |
| Narrative enrichment (third-person + first-person) | **RECOMMENDED SOON AFTER v1** | Highest-impact, lowest-risk surface. |
| Contextual example replacement | **RECOMMENDED SOON AFTER v1** | Tractable and verifiable. |
| Interview dialogue enrichment | **LATER-PHASE** | Higher risk of scope creep into reasoning. Requires CR1-CR4 pass in interview context specifically. See O14. |
| Multilingual output | **OUT OF SCOPE** | Blocked pending regional validation. See O15. |
| Automatic activation for any Indian ICP | **OUT OF SCOPE** | Opt-in is non-negotiable. Automatic activation violates S21. |

---

## Appendix A: Reference Documents

| Document | Location | Purpose |
|----------|----------|---------|
| ICP Spec Template | `skill/MASTER_INVOCATION_SPEC.md` | User input collection |
| Skill Specification | `skill/SKILL_SPEC.md` | Skill invocation and output definition |
| Architecture Reference | `references/architecture.md` | Correlation rules, derived insights, memory schema, environment schema |
| Output Schema | `references/output_schema.md` | Full JSON schema with field definitions |
| Behavioural Grounding | `references/behavioural_grounding.md` | Parameter definitions and proxy formulas (NOTE: reframe per Section 3 — tendencies, not functions) |
| Data Grounding | `references/data_grounding.md` | Signal extraction pipeline |
| Calibration | `references/calibration.md` | Benchmark anchoring and client feedback loop |
| Competitive Landscape | `references/competitive_landscape_deep_research.md` | 12 competitors + 13 academic papers |
| Cognitive Architecture | `architecture/COGNITIVE_ARCHITECTURE.md` | Perceive/remember/reflect/decide engine |
| Quality Gates | `learnings/QUALITY_GATES.md` | Population, simulation, and test quality standards |
| Design Review | `DESIGN_REVIEW.md` | Gap analysis and sprint plan (NOTE: course-corrected by this spec) |

### Documents That Need Updating After This Spec

| Document | Required Update |
|----------|----------------|
| `references/behavioural_grounding.md` | Reframe from "decision functions" to "soft tendencies that shape reasoning" |
| `references/output_schema.md` | Update to match Section 5 of this spec (behavioural_tendencies replaces behavioural_params) |
| `references/architecture.md` | Section 6d (decision simulation integration) needs rewrite — remove formula-driven decision, preserve reasoning chain |
| `DESIGN_REVIEW.md` | Mark as superseded by this spec; preserve for historical context |
| `learnings/QUALITY_GATES.md` | Update gates B1-B4 to reference tendencies instead of params |

---

## Appendix B: Research Sources

### Foundational Papers
1. Wang et al. "DeepPersona: A Generative Engine for Scaling Deep Synthetic Personas" (NeurIPS LAW Workshop 2025)
2. Park et al. "Generative Agents: Interactive Simulacra of Human Behavior" (UIST 2023)
3. Park et al. "Generative Agent Simulations of 1,000 People" (2024)
4. MiroFish — seed-document-to-ontology, knowledge graph memory (2024)

### Competitive Intelligence
5. Simile — interview-grounded digital twins, 85% GSS accuracy
6. Fish.Dog/Ditto — census-calibrated, 300K personas, live data feeds
7. Aaru — $1B valuation, population-level prediction
8. Synthetic Users — 4-agent architecture, OCEAN calibration
9. Artificial Societies — social graph simulation, YC W25
10. SYMAR — Synthetic Memories from CRM data
11. Toluna HarmonAIze — 79M panel, 1M personas
12. Qualtrics Edge Audiences — 25yr survey data

### Academic Research
13. Argyle et al. "Out of One, Many" (2022) — silicon sampling
14. Horton "Homo Silicus" (2023) — LLMs as simulated economic agents
15. Bao et al. "Using LLMs to Create AI Personas for Replication of Media Effects" (2024) — 76% replication rate
16. Li et al. "LLM Generated Persona is a Promise with a Catch" (2025) — systematic biases
17. Population-Aligned Persona Generation (2025) — Importance Sampling + Optimal Transport
18. AlphaEvolve-based Persona Generators (2026) — support coverage optimization
19. AgentSociety (2025) — 10K agents, 5M interactions
20. CoALA framework — cognitive architecture for language agents
21. MemGPT/Letta — hierarchical memory management
22. BDI + LLMs integration research

---

*This document is the source of truth for the Simulatte Persona Generator. All implementation, sprint planning, and architecture decisions must be traceable to sections of this spec. If reality diverges from this spec, update the spec first — then update the implementation.*

*Version 1.2 (Canonical) — 2026-04-02*
