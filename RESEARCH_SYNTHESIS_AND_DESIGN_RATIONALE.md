# Research Synthesis & Design Rationale — Simulatte Persona Generator

**Version:** 1.0
**Date:** 2026-04-02
**Purpose:** This document captures the full research base, competitive analysis, academic foundations, and design reasoning that produced the Master Specification. It exists so that future contributors, advisors, or investors can understand *why* the system is designed the way it is — not just *what* it does.

---

## Table of Contents

1. [Research Scope & Method](#1-research-scope--method)
2. [Foundational Papers — Deep Analysis](#2-foundational-papers--deep-analysis)
3. [Competitive Landscape — Full Mapping](#3-competitive-landscape--full-mapping)
4. [Academic Research — Broader Field](#4-academic-research--broader-field)
5. [Known Failures & Risks in LLM Persona Systems](#5-known-failures--risks-in-llm-persona-systems)
6. [Design Decisions & Rationale](#6-design-decisions--rationale)
7. [What We Chose Not to Do (and Why)](#7-what-we-chose-not-to-do-and-why)
8. [The Course Correction](#8-the-course-correction)
9. [Positioning & Market Gap](#9-positioning--market-gap)
10. [Open Research Questions](#10-open-research-questions)

---

## 1. Research Scope & Method

### What Was Researched

Five research streams were pursued in parallel:

| Stream | Scope | Sources |
|--------|-------|---------|
| **Foundational papers** | Three papers that define the hybrid approach | DeepPersona (NeurIPS LAW 2025), Generative Agents (UIST 2023 + 1,000 People 2024), MiroFish (2024) |
| **Competitive landscape** | Every commercial synthetic persona/population platform identifiable as of April 2026 | 12 companies profiled: Simile, Fish.Dog/Ditto, Aaru, Synthetic Users, Artificial Societies, SYMAR, Toluna, Qualtrics, Yabble/YouGov, Lakmoos, Evidenza, Expected Parrot |
| **Academic research** | LLM-based social simulation, synthetic population generation, cognitive architectures for agents, persona validation, known failure modes | 20+ papers from 2022-2026, spanning NeurIPS, UIST, ACM, AAMAS, ArXiv |
| **Cognitive architecture theory** | How to give an LLM agent memory, reasoning, and persistent identity | CoALA, MemGPT/Letta, BDI+LLM integration, RAISE framework |
| **Validation science** | How to know if a synthetic persona is any good | Four-level validity framework, distributional tests, behavioral replication studies, NNGroup three-study evaluation |

### What Was Not Researched (and why)

- **Specific client domains** (e.g., child nutrition, SaaS): Deliberately excluded. The master spec must be domain-agnostic. Domain-specific knowledge enters through the grounding pipeline, not through the architecture.
- **Implementation frameworks/libraries**: Not yet. The spec must be stable before technology choices are made.
- **Pricing strategy**: Out of scope for a technical specification.

---

## 2. Foundational Papers — Deep Analysis

### 2.1 DeepPersona (Wang et al., NeurIPS LAW Workshop 2025)

**Paper:** "DeepPersona: A Generative Engine for Scaling Deep Synthetic Personas"
**ArXiv:** 2511.07338

#### The Problem It Solves

Prior persona generation methods produce shallow profiles — a name, age, occupation, and a few personality traits. These are sufficient for simple prompt conditioning but fail when personas need to sustain complex, domain-specific conversations or make nuanced decisions. The depth gap: prior methods produce ~10-20 attributes; real humans carry hundreds of attributes that influence their decisions.

#### The Mechanism

**Taxonomy construction:**
- Mined 62,000 real human-ChatGPT conversations from the LMSYS-Chat-1M dataset
- Extracted every human attribute mentioned in those conversations
- Organized into a hierarchical taxonomy of 8,496 attribute nodes
- This is not a theoretical taxonomy — it reflects what real humans actually talk about when describing themselves and their decisions

**Progressive attribute filling:**
- Anchor-first: 8 core attributes are filled first (age, gender, education, occupation, personality type, values orientation, decision style, primary life concern)
- Each subsequent attribute is sampled *conditioned on all previously assigned attributes*
- This prevents the "independent sampling" problem where a persona ends up with contradictory traits (e.g., a rural farmer with a $200K tech salary)
- The conditioning is done by the LLM, which has implicit knowledge of attribute co-occurrence from training data

**5:3:2 stratification:**
- For any cohort, personas are stratified by cosine distance from the cohort centroid
- 50% within 0.15 distance (near — the mainstream)
- 30% at 0.15-0.35 distance (mid — the variations)
- 20% beyond 0.35 distance (far — the outliers and edge cases)
- This directly counters the homogeneity bias in LLM outputs

**Population tables:**
- Demographic attributes are sampled from empirical population distributions (census data, survey marginals)
- Not from LLM priors, which overrepresent how demographics have been *written about* rather than how they actually distribute

#### Key Results

| Metric | DeepPersona | Best Prior Method | Improvement |
|--------|-------------|-------------------|-------------|
| WVS alignment (KS statistic) | Best | Baseline | 43% improvement |
| Response deviation from human survey data | Lowest | Baseline | 31.7% reduction |
| Attribute coverage per persona | ~200 | ~10-20 | ~10x deeper |
| Narrative text per persona | ~1MB | ~100 words | ~10,000x richer |
| GPT-4.1-mini personalized QA accuracy | +11.6% | Baseline | Direct downstream impact |

#### What Simulatte Takes From DeepPersona

1. **Anchor-first taxonomy ordering** — the 8 core attributes concept. We adapt the specific 8 to be more decision-relevant.
2. **Progressive conditional filling** — each attribute conditioned on all prior. Prevents contradictions.
3. **5:3:2 stratification** — the specific ratio for forcing diversity. Critical for countering homogeneity.
4. **Population tables for demographics** — empirical marginals, not LLM priors.
5. **Sparsity prior** — rare attributes are not zero-probability. Long-tail coverage matters.

#### What Simulatte Does NOT Take

- The specific 8,496-node taxonomy. We build our own (smaller, ~150 base + domain extension) because our taxonomy needs to be actionable for decision simulation, not comprehensive for conversation.
- The LMSYS-Chat mining pipeline. Our taxonomy is built from domain data when available, not from chat logs.
- The evaluation method (WVS survey alignment). We need behavioral validity, not just survey response validity.

---

### 2.2 Generative Agents (Park et al., UIST 2023 + 1,000 People Extension 2024)

**Paper 1:** "Generative Agents: Interactive Simulacra of Human Behavior" (UIST 2023)
**Paper 2:** "Generative Agent Simulations of 1,000 People" (ArXiv 2411.10109, Nov 2024)

#### The Problem It Solves

LLM personas without memory are stateless. Every interaction starts from zero. Two stimuli presented an hour apart are processed independently. There is no accumulation, no learning, no attitude evolution. This makes temporal simulation impossible — and temporal simulation is the core of Simulatte's value proposition.

#### The Mechanism (Paper 1 — Smallville)

**Memory stream:**
- Every event the agent perceives is written to a timestamped memory stream
- Three types of entries: observations (what happened), reflections (what the agent thinks about what happened), and plans (what the agent intends to do)
- The stream is the agent's experiential history

**Retrieval formula:**
```
retrieval_score = α · recency + β · importance + γ · relevance
```
- Recency: exponential decay from the timestamp (recent memories score higher)
- Importance: LLM-assigned score 1-10 at the time of observation (pivotal events score higher)
- Relevance: cosine similarity between the memory content and the current query (topically related memories score higher)
- Default: α = β = γ = 1.0 (equal weighting)

**Reflection trigger:**
- When the sum of importance scores of recent observations exceeds a threshold (~150 in the paper), the agent pauses and reflects
- Reflections synthesize 2-3 higher-order insights from recent observations
- Reflections are stored back in the memory stream with pointers to the source observations
- This creates a hierarchy: observations → reflections → meta-reflections
- Reflections occur roughly 2-3 times per simulated game day

**Planning:**
- Agents decompose their day into hour-level blocks, then 5-15 minute actions
- Plans are stored in memory and influence subsequent perception and decision-making
- Plans can be revised when unexpected events occur

**Key result:** Cohen's d = 8.16 improvement in believability vs no-memory baseline. This is an extraordinary effect size — 8 standard deviations. The TrueSkill evaluation with 100 human evaluators confirmed that memory-equipped agents were overwhelmingly preferred.

#### The Mechanism (Paper 2 — 1,000 People)

**Interview-based memory scaffolding:**
- 1,052 real people were interviewed about their lives, values, and decision-making
- Interview transcripts were used to seed the memory of LLM agents
- Each agent's memory was scaffolded with the real person's experiences, not generated from demographics alone

**Key results:**

| Metric | Interview-Based | Persona-Based | Demographic-Only |
|--------|----------------|---------------|-----------------|
| GSS accuracy | 0.85 | 0.70-0.75 | 0.55-0.71 |
| Big Five accuracy | 0.80 | — | — |
| Economic games | 0.66 | — | — |
| Population-level correlation | r = 0.98 | — | — |

- Interview-based agents dramatically outperformed demographic-only and persona-based conditioning
- Political bias reduced 36-62% vs demographic models
- Racial bias reduced 7-38%
- Trimmed transcripts (80% content reduction) retained 0.79-0.83 accuracy — meaning the scaffold doesn't need to be enormous
- **This paper is the foundation of Simile's $100M commercial product**

#### What Simulatte Takes From Generative Agents

1. **Memory stream architecture** — the observation/reflection/plan structure
2. **Retrieval formula** — recency × importance × relevance with tunable weights
3. **Reflection triggers** — importance accumulation threshold
4. **The fundamental insight**: memory is what makes an agent believable. Without memory, all the taxonomy depth in the world doesn't help.
5. **Core/working memory separation** — we extend this: core is identity (immutable), working is experience (resettable per experiment)

#### What Simulatte Does NOT Take

- **Interview requirement.** Park's 1,000-person study requires interviewing real people. Simulatte must work without interviews — our life stories are LLM-generated from taxonomy-grounded profiles, not transcribed from real humans. This is a fidelity tradeoff we accept for scalability and domain flexibility.
- **The Smallville environment model.** The spatial simulation (rooms, objects, pathways) is specific to the game-world context. Simulatte's "environment" is a business context (stimuli, channels, decision points), not a physical space.
- **The specific threshold of 150.** We use a lower threshold (50 default) because our simulations run fewer observations per persona than Smallville's continuous environment.

---

### 2.3 MiroFish (2024)

#### The Problem It Solves

Both DeepPersona and Generative Agents require significant upfront configuration — a pre-defined taxonomy (DeepPersona) or interview transcripts (Generative Agents). MiroFish demonstrates that an LLM can *infer* the ontology from a seed document, eliminating manual schema design.

#### The Mechanism

**Seed-document-to-ontology:**
- Given a document describing the domain (a brief, a product spec, a market report), the LLM extracts the relevant entity types, relationships, and attributes
- No pre-defined schema required — the ontology emerges from the content

**Unified knowledge graph (Zep Cloud):**
- All agent memory (observations, facts, relationships, temporal state) is stored in a single queryable knowledge graph
- Agents read from and write to this graph during simulation
- Temporal edge metadata tracks *when* something was learned and *how* it relates to other knowledge

**OASIS social simulation engine:**
- Multi-agent environment where agents interact on simulated social platforms (Twitter, Reddit)
- Agents can influence each other's opinions through social interaction

**ReACT report agent:**
- After simulation, a report agent with an `InterviewAgents` tool can interrogate individual agents about their experiences and decisions
- This enables the post-event survey and deep interview modalities

#### What Simulatte Takes From MiroFish

1. **Domain-adaptive taxonomy extension** — the principle that the system can infer domain-specific attributes from provided data, rather than requiring pre-defined schemas
2. **Memory as a queryable structure** — not just a flat list but a structure that supports retrieval by recency, importance, relevance, and relationship
3. **Temporal metadata on memory** — when something was learned matters for how it's weighted
4. **The interview-agent concept** — agents that can be interrogated about their experiences post-simulation

#### What Simulatte Does NOT Take

- **Zep Cloud as the specific technology.** Our memory architecture is designed to be implementable in multiple backends (JSON files, SQLite, a knowledge graph, etc.)
- **OASIS social simulation.** Multi-agent social interaction is deferred to v2. The complexity of opinion propagation through networks is a separate research problem.
- **Zero-configuration aspiration.** MiroFish aims for zero manual configuration. Simulatte accepts that the ICP Spec requires human input — the user must define who they're building personas for and why. What we automate is the taxonomy extension, not the problem definition.

---

## 3. Competitive Landscape — Full Mapping

### 3.1 Market Structure

The synthetic persona/population market (as of April 2026) has split into distinct tiers:

**Tier 1: Deep Identity Systems**
| Company | Approach | Fidelity | Persistence | Cognition | Scale |
|---------|----------|----------|-------------|-----------|-------|
| Simile | Interview-grounded twins | Highest (85% GSS) | Yes (memory) | Yes (perceive/reflect/decide) | Low (requires interviews) |
| **Simulatte** (target) | Taxonomy-grounded + memory | High (target) | Yes (core/working split) | Yes (full cognitive loop) | Medium (no interview requirement) |

**Tier 2: Statistically Calibrated Populations**
| Company | Approach | Fidelity | Persistence | Cognition | Scale |
|---------|----------|----------|-------------|-----------|-------|
| Fish.Dog/Ditto | Census + live data, 300K personas | Medium-High (92% focus group) | Partial (consistent profiles) | No | Very High |
| Aaru | Population prediction, multi-agent | Unknown (black box) | Unknown | Unknown | Very High |
| Toluna | 79M-panel-grounded, 1M personas | Medium | Partial (consistent responses) | No | Very High |
| Qualtrics Edge | 25yr survey data fine-tuned | Medium | No (stateless) | No | High |

**Tier 3: Response Generators**
| Company | Approach | Fidelity | Persistence | Cognition | Scale |
|---------|----------|----------|-------------|-----------|-------|
| Synthetic Users | 4-agent QA architecture | Medium | Minimal (session) | Partial (multi-agent QA) | High |
| Evidenza | Persona panel + Synthetic CMOs | Medium | Unknown | No | High |
| Yabble/YouGov | Augmented data model | Low-Medium | Session only | No | High |
| SYMAR | CRM-injected "Synthetic Memories" | Medium | Yes (from CRM) | No | Medium |

**Tier 4: Niche/Specialized**
| Company | Niche |
|---------|-------|
| Artificial Societies | Social graph/network effects simulation |
| Lakmoos | Neuro-symbolic AI (explainability focus) |
| Expected Parrot (EDSL) | Open-source survey DSL (academic) |

### 3.2 Detailed Competitor Analysis

#### Simile — The Benchmark

**Founded by:** Stanford generative agents team (Joon Sung Park, Michael Bernstein, Percy Liang)
**Funding:** $100M Series A, Index Ventures (Feb 2026). Angels: Fei-Fei Li, Andrej Karpathy.
**Customers:** CVS Health, Telstra, Suntory, Wealthfront, Banco Itau

**What they do right:**
- Deepest fidelity to individual humans (interview-grounded)
- Direct lineage from the most cited paper in the field
- Simulation engine runs entire cohorts across scenarios simultaneously
- Agents reflect, plan, and interact — genuine cognitive architecture

**Their limitation (Simulatte's opportunity):**
- Requires interviewing real people. This means:
  - Expensive ($100K-$250K+/year enterprise pricing)
  - Slow (interview collection + processing before any simulation)
  - Domain-locked (new domain = new interviews)
  - Not self-serve (no PM can spin up personas for a quick test)
- Simulatte generates comparable-depth personas from taxonomy + domain data, without interviews. Lower fidelity ceiling, but dramatically more accessible and domain-flexible.

#### Fish.Dog/Ditto — The Scale Play

**Key stats:** 300K+ personas across 50+ countries. Live data feeds (weather, news, cultural context updated daily). EY: 95% correlation. 92% focus group overlap across 50+ parallel studies.

**What they do right:**
- Census-calibrated demographic foundations
- Live data grounding (personas "live in the present")
- Social interaction simulation (group discussions, opinion shifting)
- Academic partnerships (Harvard, Cambridge, Stanford, Oxford)
- MCP integration (Claude Code compatible)

**Their limitation:**
- No deep individual identity. These are statistically representative respondents, not synthetic people with life histories.
- No memory persistence across experiments. Each study is independent.
- No cognitive loop — responses are generated, not reasoned through.
- At $50-75K/year, still enterprise-positioned.

#### Aaru — The Black Box

**Key stats:** $1B headline valuation, $50M+ Series A. Customers: EY, Accenture, Interpublic Group, political campaigns.

**What they claim:**
- "Every population and audience on the globe" including hard-to-reach groups
- EY replicated their Global Wealth Research Report in one day (90% median correlation with a 6-month, multi-country original study)
- Accurately predicted NY Democratic primary

**Their limitation:**
- No publicly disclosed technical architecture
- No published validation methodology
- Complete black box — no transparency into how agents are constructed
- Enterprise-only, no published pricing
- Impossible to assess the validity of their claims without knowing the method

#### Synthetic Users — The Multi-Agent QA System

**Architecture:** 4 agents (Planner, Interviewer, Critic, Router) coordinated by a lightweight router that selects and sequences multiple LLMs.

**What they do right:**
- OCEAN/Big Five calibration against real-world population distributions
- "Synthetic Organic Parity" methodology — regular comparison against real interviews
- RAG-based grounding (retrieves facts at answer-time from CRM, interviews, docs)
- Pay-per-respondent pricing ($2-$27) makes it accessible
- Published their foundational research references (Out of One Many, Homo Silicus)

**Their limitation:**
- No persistent identity across studies
- No temporal simulation capability
- Primarily a survey/interview tool, not a simulation platform
- The Critic agent validates realism but doesn't enable memory or cognition

#### Artificial Societies — The Network Effects Player

**Founded by:** Cambridge computational social scientist + applied behavioral scientist. YC W25. EUR 4.5M seed. 15K users, 100K+ simulations.

**What they do right:**
- Social graph simulation — personas influence each other through network connections
- 2.5M+ real-world persona profiles as foundational data
- Published in British Journal of Psychology
- 95% opinion distribution accuracy (deliberately capped — "exceeding 95% would suggest overfitting")
- Most affordable: $40/month unlimited

**Their limitation:**
- No deep individual identity — these are nodes in a network, not synthetic people
- Network simulation is the product, not persona depth
- Doesn't support the "reuse the same persona across experiments" paradigm

#### SYMAR — The Memory Injection Pioneer

**Key concept:** "Synthetic Memories" — injects real data (past surveys, CRM records) into personas as memory, grounding responses in actual customer behavior.

**What they do right:**
- Closest conceptual match to Simulatte's memory architecture
- The insight that memory injection (not just demographic conditioning) improves persona quality
- Belkin case study: "indistinguishable from historical human data"
- EUR 99/month — most accessible pricing in the market

**Their limitation:**
- Memory is static (injected from CRM), not accumulated through simulation
- No cognitive loop — memory informs responses but there's no perceive→reflect→decide process
- No working memory separation — can't reset experiment state while preserving identity

### 3.3 Validation Claims Summary

| Company | Claimed Accuracy | Method | Independent? |
|---------|-----------------|--------|-------------|
| Simile | 85% GSS, 80% Big Five, 66% economic games | Park et al. 2024 paper | Yes (peer-reviewed) |
| Fish.Dog/Ditto | 92% focus group overlap, 95% EY correlation | 50+ parallel studies | Partially (EY is customer) |
| Aaru | 90% EY wealth report correlation | Single case study | No |
| Synthetic Users | 85-92% parity | Regular organic comparison | Self-reported |
| Artificial Societies | 95% opinion distribution | British Journal of Psychology | Yes (peer-reviewed) |
| Evidenza | 88-97% correlation | 100+ head-to-head tests | Self-reported |
| Toluna | "Rigorously tested" | Not detailed | No |
| Qualtrics | "Does not reproduce training responses" | Internal 4-step framework | Self-reported |
| Lakmoos | 98%+ similarity | 20 client benchmarks | Self-reported |

**Assessment:** Only Simile and Artificial Societies have peer-reviewed validation. Most claims are self-reported aggregate correlation metrics, which can mask individual-level failures and tail underrepresentation.

---

## 4. Academic Research — Broader Field

### 4.1 LLM-Based Social Simulation

**"Out of One, Many" (Argyle et al., 2022)**
The seminal paper that started the field. Demonstrated that GPT-3 conditioned on demographic descriptions could produce responses resembling those of specific human subpopulations. Coined the term "silicon sampling." Limitation: demographic conditioning alone is shallow — produces stereotypes, not individuals.

**"Homo Silicus" (Horton, 2023)**
Demonstrated LLMs as simulated economic agents. LLM "participants" exhibited standard behavioral economics patterns (loss aversion, anchoring, framing effects). Key finding: LLMs can replicate *directional* economic behavior but not *calibrated* magnitudes. Willingness-to-pay estimates were plausible but not accurate without grounding data.

**AgentSociety (Feb 2025)**
10,000+ agents, ~5 million interactions. Tested political polarization, inflammatory messages, UBI policies, hurricane impacts. Alignment between simulated and real-world experimental results validates that LLM agent populations can reproduce macro-level social phenomena. Key limitation: individual-level decisions were not validated, only population-level distributions.

**"AI Agents Are Not (Yet) a Panacea for Social Simulation" (2026)**
Critical position paper arguing that current LLM agent simulations:
- Conflate pattern matching with genuine reasoning
- Lack grounding in the specific populations they claim to represent
- Are not validated against individual-level behavioral data
- Risk "validation theater" where impressive aggregate metrics mask fundamental limitations

**Implications for Simulatte:** Population-level validation is necessary but not sufficient. Individual personas must also demonstrate behavioral coherence (decisions consistent with identity and memory, not just demographically plausible).

### 4.2 Synthetic Population Generation (Non-LLM)

**Iterative Proportional Fitting (IPF):**
The standard method for generating synthetic populations that match known marginal distributions (e.g., census data). Used in transportation modeling, epidemiology, and urban planning for decades. Limitation: produces demographics only, no psychological or behavioral depth.

**Bayesian Networks:**
Used to model conditional dependencies between attributes. Given that a person is female, 35, and lives in a metro area, what is the probability distribution over income, education, and employment? More expressive than IPF but requires a defined network structure.

**Deep Generative Models (VAEs, GANs):**
Can learn complex joint distributions from data and sample new synthetic records. SDV (Synthetic Data Vault) toolkit is the open-source reference implementation. Limitation: requires training data with all relevant attributes — which doesn't exist for psychological and behavioral attributes.

**Implications for Simulatte:** Use IPF or Bayesian networks for demographic marginal alignment (the demographic_anchor). Use LLM-based progressive filling for psychological and behavioral attributes where no training data exists. This hybrid approach combines the rigor of statistical population generation with the depth of LLM-based persona construction.

### 4.3 Cognitive Architectures for Language Agents

**CoALA (Cognitive Architectures for Language Agents):**
A theoretical framework proposing that language agents should have:
- Working memory (current context, active goals)
- Episodic memory (past experiences, timestamped)
- Semantic memory (general knowledge, facts)
- Procedural memory (how to do things, habits)
- A perceive→retrieve→reason→act→update cycle

Simulatte's architecture maps directly to CoALA:
- Core memory ≈ semantic + procedural (identity, values, tendencies)
- Working memory ≈ episodic + working (observations, reflections, simulation state)
- The cognitive loop ≈ perceive→retrieve→reason→act→update

**MemGPT/Letta:**
Hierarchical memory management for LLM agents. Three tiers:
- Main context (what's in the current prompt window)
- Recall storage (recent context that has overflowed the window)
- Archival storage (long-term storage for retrieval)
Explicit memory management operators: core_memory_append, core_memory_replace, archival_memory_insert, archival_memory_search.

**Implication for Simulatte:** For v1, our 1,000-entry cap with eviction is sufficient. For long simulations (100+ turns), MemGPT-style hierarchical archival should be an extension. The architecture should support this without redesign — the evicted observations should be archivable, not deleted.

**BDI (Belief-Desire-Intention) + LLMs:**
BDI is a classical agent architecture:
- Beliefs: what the agent thinks is true about the world
- Desires: what the agent wants (goals, values)
- Intentions: what the agent has committed to doing

BDI maps naturally to Simulatte's persona model:
- Beliefs ≈ core memory (worldview, life-defining events, relationship map)
- Desires ≈ key values + primary value orientation
- Intentions ≈ plans in working memory

Recent research integrates BDI with LLMs: the BDI structure constrains the LLM's reasoning, preventing persona drift by anchoring decisions to explicit beliefs, desires, and intentions.

### 4.4 Persona Validation Science

**Four Levels of Validity:**

| Level | Question | Method | Simulatte Target |
|-------|----------|--------|-----------------|
| **Face validity** | Does it look like a real person? | Human evaluation, expert review | v1 |
| **Distributional validity** | Do population statistics match real-world distributions? | KS tests, chi-squared, marginal comparison | v1 |
| **Behavioral validity** | Do decisions match observed patterns? | Comparison against behavioral data, A/B replication | v1 (partial) |
| **Predictive validity** | Can it forecast real-world outcomes? | Prediction vs actual outcomes | v2+ (requires calibration) |

**Bao et al. (2024) — Marketing Experiment Replication:**
- 19,447 AI personas deployed across 133 experimental findings from Journal of Marketing
- 76% of main effects replicated (84/111)
- 68% overall including interactions (90/133)
- Failure cases: complex multi-way interactions, scenarios requiring embodied experience, culturally specific responses
- **Implication:** LLM personas can replicate known experimental effects with moderate-to-high success. The failures cluster in complexity and cultural specificity — exactly the areas where deep identity and grounding help most.

**Population-Aligned Persona Generation (Sep 2025):**
- Mined 681K blog posts to create 160K+ narrative personas
- Importance Sampling + Optimal Transport for distributional alignment against IPIP Big Five (1M individuals, 223 countries)
- 49.8% error reduction vs GPT-4o baseline
- Key finding: LLM persona generation systematically underrepresents low-Extraversion and low-Emotional Stability regions
- **Implication:** Without explicit correction (like 5:3:2 stratification), LLM-generated populations will be biased toward agreeable, emotionally stable, extraverted personas. This is a structural bias, not a prompt engineering problem.

**AlphaEvolve-based Persona Generators (Feb 2026):**
- Uses iterative optimization with LLMs as mutation operators
- Prioritizes *support coverage* (spanning what is possible) over *density matching* (matching how common each type is)
- Outperforms baselines across six diversity metrics
- Produces populations spanning rare trait combinations
- **Implication:** For populations intended for experimentation (not demographic representation), coverage of the possibility space matters more than matching the exact distribution. Simulatte should prioritize this in its diversity enforcement.

### 4.5 Digital Twins of Consumers

**"Using GPT for Market Research" (Brand, Israeli, Ngwe, 2023):**
- Demonstrated that GPT can produce realistic willingness-to-pay estimates
- Key caveat: estimates are directionally correct but not calibrated — actual WTP magnitudes require grounding data
- **Implication:** The cognitive loop can produce plausible decisions, but tendencies from grounding data are needed to anchor magnitudes.

**NNGroup Three-Study Evaluation (2025):**
Three systematic studies were evaluated:

Study 1 (Kim & Lee, 2024): Survey-based finetuned twins
- 78% accuracy for filling in missing survey data, but only 67% for new questions
- Population-level: r=0.98 for known questions, r=0.68 for novel ones
- Less accurate for marginalized groups

Study 2 (Park et al., 2024): Interview-based twins
- 0.85 GSS, 0.80 Big Five, 0.66 economic games
- Interview-based dramatically outperformed demographic-only

Study 3 (Arora et al., 2025): Synthetic users for product research
- Captured directional trends but NOT effect magnitudes
- "Synthetic users tended to cluster more closely around the average response, showing less diversity"
- Consistently lower standard deviations than human data

**NNGroup conclusion:** Useful for directional insights and supplementing human research. Not reliable as sole source for high-stakes decisions or edge case identification.

**Implication for Simulatte:** We must be honest about what the system can and cannot do. It produces directionally valid, depth-rich personas for experimentation and insight generation. It does not produce ground truth. The grounding pipeline and calibration layers improve magnitude accuracy, but the system should always be positioned as a complement to, not a replacement for, real research.

---

## 5. Known Failures & Risks in LLM Persona Systems

### 5.1 Systematic Failures Documented in Literature

| Failure | Description | Evidence | Simulatte Mitigation |
|---------|-------------|----------|---------------------|
| **Homogeneity bias** | LLM outputs cluster around modal/average personalities. Tails and extremes are underrepresented. | NNGroup Study 3, Population-Aligned Persona paper | 5:3:2 stratification, distinctiveness metric, far-from-center forced sampling |
| **Sycophancy** | Personas agree with the framing of questions rather than responding from their identity. | Multiple studies, particularly in survey contexts | Strong identity anchoring through core memory, adversarial tension design |
| **Persona drift** | Character fades over long contexts. The LLM reverts to its default personality. | Observed in Generative Agents extended runs | Core memory always in context window, periodic re-anchoring, reflection mechanism reinforces identity |
| **Cultural bias** | WEIRD (Western, Educated, Industrialized, Rich, Democratic) psychology dominates. Non-Western behavioral patterns are underrepresented. | Argyle et al., Population-Aligned Persona paper | Domain-specific taxonomy extension, population tables from local census data, explicit cultural attribute categories |
| **Tail underrepresentation** | Extreme positions, rare trait combinations, and minority viewpoints are systematically absent. | Population-Aligned Persona paper (low-Extraversion, low-Emotional Stability underrepresented) | Sparsity prior, AlphaEvolve-style coverage optimization, 20% far-band sampling |
| **"Too consistent"** | LLM personas make more internally consistent decisions than real humans. Real humans show noise, contradictions, and mood effects. | Multiple behavioral studies | Tension requirement (every persona has ≥1 internal contradiction), noise injection in tendency assignment |
| **Prompt sensitivity** | Small wording changes produce large response shifts, independent of persona identity. | Samoylov (Conjointly) demonstrated income varying $111K-$273K across prompt variants | Standardized prompt templates for cognitive operations, tendency-based reasoning rather than open-ended generation |
| **Information asymmetry failure** | Agents struggle with scenarios requiring incomplete or private knowledge. | Park et al. economic games (66% — lowest accuracy) | Explicit constraint system (immutable_constraints, absolute_avoidances), information state tracked in simulation_state |

### 5.2 Risk Assessment for Simulatte

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Homogeneity despite stratification | Medium | High — undermines diversity claims | Multiple diversity metrics, rejection sampling, human review |
| Drift in long simulations (50+ turns) | High | Medium — decisions become generic | Core memory re-injection, reflection re-anchoring, maximum simulation length guidelines |
| Domain grounding data insufficient | Medium | Medium — tendencies are proxy-quality | Minimum viable data requirements (200+ items), clear labeling of proxy vs grounded |
| Calibration without outcome data | High | Low-Medium — magnitudes uncalibrated | Benchmark anchoring as minimum, honest positioning about limitations |
| Compute cost at scale | Medium | High — 200 personas × 50 stimuli = 40K LLM calls | Model routing (Haiku for perceive, Sonnet for decide), batching, caching |
| User misinterpretation as ground truth | High | Very High — bad decisions from synthetic data | Explicit "source" labels on all tendencies, calibration status visible, documentation |

---

## 6. Design Decisions & Rationale

### 6.1 Why Taxonomy-Based Construction (Not Interview-Based or Demographic-Only)

**Decision:** Build personas from a structured taxonomy (~150 base + domain extension), not from interview transcripts (Simile) or demographic profiles alone (Fish.Dog, Aaru).

**Rationale:**
- Interview-based achieves highest fidelity (85% GSS) but requires real human interviews per domain. This is a $100K+ enterprise play that cannot scale to self-serve.
- Demographic-only produces statistically representative but shallow personas. No internal life, no psychological depth, no memory substrate.
- Taxonomy-based occupies the middle: deeper than demographics, more scalable than interviews. The progressive conditional filling produces coherent, internally consistent identities without requiring external data (though grounding data improves them).

**Tradeoff accepted:** Lower fidelity ceiling than interview-based twins. The maximum accuracy we can expect without interviews is likely 70-80% on GSS-type benchmarks (between demographic-only at 55-71% and interview-based at 85%). We accept this for dramatically better scalability and domain flexibility.

### 6.2 Why Core/Working Memory Split (Not Unified Stream or Stateless)

**Decision:** Separate persona memory into immutable core (identity) and resettable working (experiment state).

**Rationale:**
- Simulatte's value proposition is experiment modularity — the same persona runs through multiple experiments. This requires memory isolation between experiments while preserving identity across them.
- A unified stream (Park et al.) doesn't support this — experiment A's observations would contaminate experiment B.
- Stateless (most competitors) can't support temporal simulation at all.
- The core/working split enables all four product modalities: survey (working empty), simulation (working accumulates), post-event survey (working preserved), interview (working optionally carried).

**Tradeoff accepted:** More complex memory management than a flat stream. The promotion mechanism (working → core) adds implementation complexity.

### 6.3 Why Soft Tendencies (Not Parametric Decision Functions)

**Decision:** Behavioural tendencies are natural-language soft priors injected into LLM reasoning context, not logistic functions or coefficient vectors that compute decisions.

**Rationale:** This was the critical course correction in the design process. The initial architecture (Sprint A-C) treated behavioural parameters as decision functions:
```
P(purchase) = sigmoid(β₀ + β₁·price_gap + β₂·need + β₃·trust)
```
This produced calibrated outputs but collapsed the persona into a segment model. The LLM became a narrator explaining a pre-computed decision, not a cognitive agent reasoning through one.

The corrected approach:
```
"You tend to be quite price-sensitive — cost is usually one of the first things
you notice and evaluate."
```
The LLM reasons with this tendency. The decision emerges from the reasoning. This preserves:
- Situational override (a price-sensitive parent might splurge for a sick child)
- Internal conflict (values and tendencies can be in tension)
- Narrative coherence (the reasoning trace is genuine, not post-hoc)
- The difference between a persona and a formula

**Tradeoff accepted:** Less precisely calibrated outputs. A parametric function gives you P(purchase) = 0.62. A soft tendency gives you a decision with a reasoning trace. The reasoning trace is more useful for insight generation; the probability is more useful for quantitative prediction. We prioritize the former and use calibration as a population-level correction, not an individual-level override.

### 6.4 Why 5:3:2 Stratification (Not Random or Uniform)

**Decision:** Enforce a 50/30/20 split between near-center, mid-range, and far personas.

**Rationale:**
- Random sampling from LLM priors produces homogeneous cohorts (documented in Population-Aligned Persona paper)
- Uniform sampling produces too many extreme/unusual personas that don't represent the realistic center of the population
- 5:3:2 matches DeepPersona's empirically validated ratio: enough center to be representative, enough periphery to capture the tails, enough far-out to include edge cases
- This directly addresses the "clustering around means" failure documented by NNGroup and others

### 6.5 Why Domain-Agnostic Core (With Domain Extensions)

**Decision:** The base taxonomy, memory architecture, cognitive loop, and constraint system are domain-agnostic. Domain-specific knowledge enters only through taxonomy extensions and the grounding pipeline.

**Rationale:**
- The initial system was built with Indian child nutrition as the pilot domain. This led to domain-specific attributes leaking into the core schema (e.g., `pediatrician_trust`, `ayurvedic_inclination`, `best_for_child_intensity`)
- A domain-agnostic core means the same system can serve SaaS, healthcare, financial services, consumer goods, etc. without architectural changes
- Domain templates provide a library of pre-built extensions for common domains
- When domain data is provided, the system generates domain-specific extensions automatically (MiroFish-style)

### 6.6 Why LLM-as-Cognitive-Engine (Not LLM-as-Storyteller)

**Decision:** The LLM runs perceive(), reflect(), and decide() — it is the cognitive mechanism of the persona, not just the narrative generator.

**Rationale:**
- Park et al.'s 8-standard-deviation improvement comes from LLM agents that perceive, remember, reflect, and plan — not from better stories
- If decisions are made by formulas and the LLM only narrates, then:
  - Situational reasoning is lost (formulas can't handle novel scenarios)
  - Memory is irrelevant (the formula doesn't read memory)
  - Reflections are decorative (they don't influence decisions)
  - The "persona" is just a profile with a storytelling layer
- The LLM as cognitive engine means memory actually matters — past experiences are retrieved and reasoned about during decisions

### 6.7 Why Build Order: Identity → Memory → Cognition → Grounding → Calibration

**Decision:** Phase 1 (identity + memory + cognitive loop) before Phase 2 (grounding + validation) before Phase 3 (calibration).

**Rationale:**
- The initial architecture inverted this: it prioritized calibration (Sprint C) before memory was implemented
- The user course correction was explicit: "Do not defer memory, persistence, or simulation just because they are hard"
- Identity and memory are the product. A well-constructed persona with proxy tendencies is more valuable than a parametrically calibrated segment model without memory.
- Grounding improves quality but is not required for functionality
- Calibration improves trust but is not required for value delivery
- The MVP (identity + memory + cognitive loop + survey + simulation) proves the thesis without grounding or calibration

---

## 7. What We Chose Not to Do (and Why)

### 7.1 Interview Requirement

**Not doing:** Requiring interviews with real humans to seed persona memory (Simile's approach).

**Why not:** Dramatically limits scalability and domain flexibility. Adds weeks and $10K+ per domain. Makes self-serve impossible. The fidelity tradeoff (85% → ~75% on GSS-type benchmarks) is acceptable for the accessibility gain.

**What we do instead:** Life stories and core memory are generated from taxonomy-grounded profiles. Domain data (reviews, forums, transcripts) provides empirical grounding without requiring controlled interviews.

### 7.2 Social Interaction Between Personas

**Not doing (v1):** Personas influencing each other through social graphs (Artificial Societies' approach).

**Why not:** Opinion propagation through networks is a complex research problem in its own right. Adding it before individual persona behavior is validated would compound uncertainty. And the core value proposition (deep, persistent, individually-addressable personas) doesn't require it.

**When we'll add it:** v2 roadmap item. After individual personas are validated and the temporal simulation modality works.

### 7.3 Fine-Tuned Models

**Not doing:** Training custom models on persona data (Qualtrics Edge approach).

**Why not:** Fine-tuning locks you to a model version and requires retraining when the base model improves. Prompt-based + memory-based approaches benefit from every model upgrade automatically. Also, fine-tuning requires large training datasets of persona-response pairs, which we don't have.

### 7.4 Real-Time Data Feeds

**Not doing (v1):** Continuously updating personas with live market/news/cultural data (Fish.Dog approach).

**Why not:** Adds massive infrastructure complexity. The value of live data depends on the use case — for most persona experiments (test this messaging, simulate this product launch), a static population is sufficient. Live data matters for ongoing brand tracking, which is a v2+ use case.

### 7.5 Predictive Validity Claims

**Not doing (v1):** Claiming the system can predict real-world outcomes.

**Why not:** Predictive validity requires calibrated behavioral parameters, a feedback loop with real outcomes, and multiple validation cycles. Claiming predictive power without this infrastructure is irresponsible and would undermine credibility.

**What we claim instead:** Face validity, distributional validity, and behavioral validity (directional). The system produces rich, internally coherent personas whose aggregate behavior is directionally plausible. Quantitative prediction requires calibration (Phase 3).

### 7.6 Replacing LLM Reasoning With Formulas

**Not doing:** Computing P(purchase) from a logistic function and using the LLM only to explain it.

**Why not:** This was tried in Sprints A-C and produced the "segment model with narrative attached" failure mode. The user explicitly corrected this approach. Parametric decisions strip out everything that makes a persona more than a profile: situational reasoning, memory integration, internal conflict, the capacity to surprise.

### 7.7 Domain-Specific Base Schema

**Not doing:** Baking domain-specific attributes (pediatrician_trust, SaaS_feature_gap) into the core schema.

**Why not:** Makes the system domain-locked. Every new domain requires schema changes. Domain-specific knowledge belongs in the taxonomy extension layer and the grounding pipeline.

---

## 8. The Course Correction

This section documents the critical design course correction that occurred during the research process. It is preserved here so that future contributors understand why certain early decisions were reversed and what principles prevent regression.

### What Happened

The initial architecture design (Sprints A-C) drifted toward a coefficient-first, calibration-first model:

**Sprint A (Schema + Behavioural Parameters):** Added a `behavioural_params` block with logistic purchase probability functions, price elasticity coefficients, switching hazard rates, and trust vectors. Each was a numerical parameter with a specific functional form.

**Sprint B (Data Grounding):** Built a pipeline to estimate these parameters from domain data (reviews, forums, transcripts). The output was a set of regression coefficients per behavioral cluster.

**Sprint C (Calibration):** Built benchmark anchoring and client feedback loops to calibrate the parametric outputs against real-world conversion rates.

The resulting system was architecturally sound for *quantitative prediction*. But it had drifted from the original vision in several critical ways:

### The Drift

1. **Personas became containers for coefficients.** The identity (life stories, values, defining events) was generated *after* the parameters and was constrained to be *consistent with* them. The parameters drove the persona, not the other way around.

2. **The LLM became a storyteller.** In the `decide()` function, the behavioral parameters computed the probability, and the LLM generated a reasoning trace *explaining* the pre-computed decision. The LLM was decorative.

3. **Memory was deferred.** The Sprint plan put memory and temporal simulation in "Phase 3" (after calibration). The rationale was that calibration needed to work before simulation was meaningful. This inverted the priority order.

4. **Calibration blocked cognition.** Sprint planning treated calibration as a prerequisite for useful output. This meant the cognitive loop (perceive, reflect, decide) was never built.

### The Correction

The user pushed back explicitly:

> "Do not collapse the system into a segment model with narratives attached."
>
> "Do not defer memory, persistence, or simulation just because they are hard."
>
> "Personas are synthetic people with identity, memory, tendencies, and history."
>
> "The LLM is the cognitive engine, not just a storyteller."
>
> "Grounding should strengthen the simulation, not replace it."

### What Changed

| Aspect | Before Correction | After Correction |
|--------|------------------|------------------|
| Behavioural parameters | Logistic functions with β coefficients | Soft tendency bands with natural-language descriptions |
| How decisions are made | Formula computes probability → LLM narrates | LLM reasons through decision with tendencies as soft context |
| Role of the LLM | Storyteller (generates narrative) | Cognitive engine (perceives, reflects, decides) |
| Priority order | Calibration → Grounding → then eventually Memory | Identity/Memory → Cognitive Loop → Grounding → Calibration |
| Build order | Sprint A (params) → B (grounding) → C (calibration) → "later" (memory) | Sprint 1-5 (identity, memory, cognition) → 6-10 (grounding) → 11-14 (calibration) |
| What a persona IS | A set of parameters with a narrative attached | A synthetic person with identity, memory, and tendencies |

### The Guardrails

Section 13 of the Master Spec contains 7 absolute prohibitions that prevent regression to the coefficient-first model. These exist because the drift happened once and could happen again:

1. Do not collapse to segment model
2. Do not replace reasoning with formulas
3. Do not defer memory
4. Do not reduce LLM to storytelling
5. Do not prioritize calibration over cognition
6. Do not treat tendencies as identity
7. Do not bake domain-specific features into core

---

## 9. Positioning & Market Gap

### The Landscape Matrix

```
                    Deep Identity
                         │
                  Simile ●
                         │
                         │   ● Simulatte (target position)
                         │
           SYMAR ●       │
                         │
   ──────────────────────┼──────────────────────── Temporal Simulation
                         │
    Synthetic Users ●    │     ● Artificial Societies
                         │
              Yabble ●   │  ● Fish.Dog/Ditto
                         │
        Qualtrics ●      │     ● Aaru
                         │
                  Toluna ●│ ● Evidenza
                         │
                    Shallow/Stateless
```

### The Gap Simulatte Fills

No existing product combines all four:
1. **Taxonomy-deep identity** (200+ attributes, life stories, defining events, internal tensions)
2. **Persistent memory** (core/working split, resettable per experiment, accumulates during simulation)
3. **Cognitive agency** (perceive → remember → reflect → decide, LLM as reasoning engine)
4. **Domain-adaptive grounding** (works without data, improves with data, domain-agnostic core)

**Simile** has (1) + (2) + (3) but requires interviews and is enterprise-locked.
**Fish.Dog** has scale and live data but no (1), (2), or (3).
**SYMAR** has a form of (2) (injected memories) but no (1) or (3).
**Artificial Societies** has network simulation but no individual-level (1), (2), or (3).

### Who Is the Customer

Simulatte serves users who need:
- **Depth** — not just survey responses but understanding *why* a persona decides what it decides
- **Reuse** — the same personas across multiple experiments, retaining identity
- **Temporal dimension** — how attitudes and decisions evolve over a sequence of experiences
- **Domain flexibility** — ability to create personas for new domains without interviews or custom data collection

This is: product managers testing messaging, UX researchers exploring user journeys, founders validating product concepts, agencies running strategic insight projects, simulation researchers building behavioral models.

This is NOT: quantitative market research teams needing statistically representative samples (Fish.Dog/Toluna), enterprise strategy teams needing population-level prediction (Aaru), or academic psychologists studying specific real individuals (Simile).

---

## 10. Open Research Questions

These are questions the current research base does not definitively answer. They are documented here as future research priorities.

### 10.1 Optimal Reflection Threshold

Park et al. use importance sum > 150 (with importance scores 1-10, roughly 15-25 observations between reflections). The current Simulatte spec uses > 50 (roughly 7-10 observations). The right threshold depends on:
- Simulation length (short surveys vs long temporal simulations)
- Stimulus intensity (high-importance stimuli need fewer to trigger reflection)
- Persona type (analytical personas might reflect more frequently)

**Research needed:** Empirical testing across different simulation lengths and persona types to identify optimal thresholds.

### 10.2 Memory Decay Rate

The current spec uses a 0.995/hour decay rate for recency scoring. This is borrowed from Park et al.'s Smallville implementation where simulated time progresses continuously. In Simulatte's stimulus-based simulations, the time between stimuli may be irregular.

**Research needed:** Should decay be time-based (hours since observation) or event-based (number of stimuli since observation)? Different experiments may need different decay models.

### 10.3 Fidelity Ceiling Without Interviews

Park et al. demonstrated that interview-based agents achieve 85% GSS accuracy while demographic-only models achieve 55-71%. Simulatte sits between these: taxonomy-grounded identities with progressive filling, but no interview data.

**Research needed:** What is the achievable fidelity ceiling with taxonomy-based construction + domain grounding, without interviews? This is Simulatte's most important empirical question.

### 10.4 Grounding Data Quality Threshold

The spec requires 200+ reviews/posts for Grounded Mode. This is a rough estimate based on GMM clustering stability requirements.

**Research needed:** Systematic testing of cluster stability across different data volumes and quality levels. How many reviews produce stable clusters? How much does data quality (platform, detail level, temporal recency) affect cluster quality?

### 10.5 Cross-Domain Taxonomy Transfer

The base taxonomy is designed to be domain-agnostic, but some attributes may be irrelevant in certain domains (e.g., `health_consciousness` in a B2B SaaS context).

**Research needed:** How much does irrelevant attribute noise affect persona quality? Should the system prune irrelevant base attributes per domain, or does the progressive filling handle this naturally?

### 10.6 Noise Injection for Realism

Real humans show decision noise — the same person presented with the same scenario twice may decide differently. LLM personas are more consistent than real humans.

**Research needed:** How much decision noise should be injected to match real human variability? Can temperature tuning alone achieve this, or does the system need explicit noise mechanisms?

### 10.7 Multi-Persona Calibration

Current calibration methods (benchmark anchoring, client feedback) adjust population-level outputs. But populations are composed of individuals. Adjusting one persona's tendencies to improve population accuracy might make that individual less coherent.

**Research needed:** How to distribute population-level calibration adjustments across individual personas without breaking individual coherence.

---

*This document captures the complete research foundation for the Simulatte Persona Generator Master Specification. It should be updated as new research findings emerge, competitors evolve, or design decisions are revised.*

*Version 1.0 — 2026-04-02*
