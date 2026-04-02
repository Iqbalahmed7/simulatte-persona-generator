# Design Review — Persona Creation Layer
**Date:** 2026-04-02
**Status:** Accepted — Sprint Plan Activated
**Review Type:** Architecture Gap Analysis → Next-Phase Design

---

## Context

This document captures the outcome of a design review conducted on 2026-04-02. It identifies critical gaps in the current persona creation system and defines the next-phase architecture to move from "LLM-generated believable personas" to "data-grounded, behaviourally realistic, and eventually predictive synthetic populations."

This document is the source of truth for Sprint planning from this point forward. Every sprint that touches persona generation must reference it.

---

## A. Critical Gaps in Current Persona Creation

### Gap 1: LLM Priors Dominate Every Layer

**Demographics are sampled from LLM training distributions, not real populations.**
When the system generates a "mid-market SaaS buyer" or "urban Indian parent," the output is the modal version of that archetype from LLM training data — articles, case studies, marketing content. The persona represents how that segment has been *written about*, not how it actually distributes in the real world. Heavy users, edge-case segments, and underrepresented cohorts are systematically absent.

**Psychological traits are assigned for narrative coherence, not empirical fit.**
The anti-correlation constraints in `references/architecture.md` are grounded in academic psychology literature as it exists in LLM training data. There is no evidence those correlations hold in any specific target population. "High openness correlates with low neuroticism" may be true in a WEIRD psychology sample. It may not hold for a 45-year-old enterprise IT buyer.

**WTP and price sensitivity are reasoning outputs, not estimated parameters.**
The current system produces: *"Sarah is budget-conscious because CFO approval is required."* That's a causal story, not a parameter. It tells you direction, not magnitude. There is no way to know if a persona's WTP of "~$500/month" is calibrated against anything real.

**Decision simulations are internally consistent but unverifiable.**
The gut → info → constraints → social → final reasoning chain produces coherent output. But coherence is not accuracy. A persona can generate a well-reasoned "no" decision when the real population buys at 40% conversion. There is no mechanism to catch this.

---

### Gap 2: Schema Assumes the Wrong Causal Direction

The current schema assumes demographics → psychology → decision profile. In reality:
- Behavioural signals (churn, switching, purchase) are not derived from demographics
- Many behavioural patterns are driven by situational factors, social proof, and habitual patterns that do not map cleanly to schema fields
- The schema treats attributes as stable; but churn, switching, and purchase events are highly contextual and state-dependent

---

### Gap 3: Population-Level Validation Is Aesthetic, Not Statistical

The cohort summary checks diversity of outputs — e.g., "a mix of high and low price sensitivity." But it does not check accuracy of distributions. Checking diversity is not the same as checking that 23% of a simulated segment is price-sensitive, which matches observed churn patterns in that market.

---

### Gap 4: Monetization Behaviour Is Modelled as Traits, Not Functions

Purchase likelihood, churn probability, LTV — these are event rates over time, not personality labels. The current system treats "price sensitivity" as a trait. In reality it is a function: P(purchase) drops by X% per $Y price increase in this segment. That function can be estimated from data. The current system cannot represent it.

---

### Gap 5: No Calibration Loop

There is no mechanism to compare simulated outputs against industry benchmarks or client outcome data. The system can produce personas that all reject a reasonable offer, with no mechanism to detect or correct this.

---

### Gaps Ranked by Criticality

1. **Behavioural calibration** — most urgent; without this, all outputs are unverifiable
2. **Data grounding** — calibration requires something to calibrate against
3. **Feedback loops** — calibration done once decays; needs a re-anchoring mechanism
4. **Empirical constraint modelling** — the copula approach is structurally sound but running on theoretical correlations

---

## B. Next-Phase Architecture

### Principle

Separate the grounding problem from the persona problem. You do not need every persona to be "real." You need the *population* to behave realistically.

- Behavioural parameters are estimated at segment level from data, then assigned to individual personas with controlled variance
- Calibration operates at the population level, comparing aggregate simulated outcomes to real benchmarks
- Individual persona narrative remains LLM-generated but is constrained by empirically-grounded parameters
- **The LLM is a storyteller, not a decision-maker**

---

### Layer 1: Data Grounding

Full specification: `references/data_grounding.md`

#### Signal Types and Sources

| Signal | Source | Label |
|--------|---------|-------|
| Purchase triggers | Reddit, App Store 4-5★, Amazon Verified Purchase | "bought because", "finally decided" |
| Rejection / objections | 1-3★ reviews, Trustpilot/G2/Capterra | "cancelled because", "too expensive" |
| Switching events | Reddit competitor transition posts | "moved from X to Y", "switched after" |
| Price sensitivity proxy | Price mention frequency in reviews, sale/coupon mentions | Correlation: price drop events → review spike |
| Trust channel weighting | Source citations in reviews ("saw on YouTube", "friend recommended") | Source type frequency × purchase correlation |
| Population demographics | US Census ACS, BLS, Pew Research | Static marginal distribution anchors |
| Behavioural base rates | Mixpanel, Recurly, Amplitude public benchmarks | Soft calibration targets |
| Client data (optional) | CRM exports, purchase history, churn labels, NPS | Strongest signal; use when available |

#### Pipeline

```
Stage 1 — Signal Extraction
  Input:  raw review/forum text
  Output: labelled signal corpus
  Method: extract sentences with decision-language markers
          (trigger verbs: bought, cancelled, switched, refused, waited)
          tag by type: purchase / rejection / switching / trust
          retain metadata: platform, rating, date, category

Stage 2 — Feature Construction
  Input:  labelled signal corpus
  Output: feature vectors per review cluster
  Compute:
    - price_salience_index       = price_mentions / total_mentions
    - trust_source_distribution  = proportion by type [peer/expert/brand/ad]
    - switching_trigger_taxonomy = [price/feature/service/competitive]
    - objection_cluster_frequency = relative frequency by semantic group

Stage 3 — Behavioural Cluster Derivation
  Input:  feature vectors
  Output: K behavioural archetypes with parameter distributions
  Method: GMM clustering on behavioural features (NOT demographics)
          characterise each cluster:
            price_elasticity_proxy, loyalty_propensity,
            trust_channel_weights, primary_switching_trigger,
            dominant_objection_type
          cross-tabulate with demographics to build conditional distributions
```

This pipeline is built once per domain/market, then reused. Start with 3-5 target markets.

---

### Layer 2: Behavioural Parameters

Full specification: `references/behavioural_grounding.md`

These replace LLM-generated trait labels. They are estimated from data and stored as functional parameters.

#### Purchase Likelihood Function
```
P(purchase | price, need_intensity, trust_level, n_alternatives)
  = sigmoid(β₀ + β₁·price_gap + β₂·need_intensity + β₃·trust_level)

β coefficients: estimated from behavioural cluster data
  via logistic regression on proxy labels
  (verified purchase + high rating = bought; switching language = rejected)
```

#### Price Elasticity
```
price_elasticity_proxy = Δ(purchase_probability) / Δ(relative_price)

Estimated from: price mention frequency × rejection signal correlation
Represented as: slope parameter β₁ in the purchase function
  High elasticity = β₁ steep (e.g. -0.5)
  Low elasticity  = β₁ shallow (e.g. -0.1)
```

#### Switching Hazard Rate
```
P(switch | satisfaction_level, alternative_proximity, switching_cost)
  modelled as a hazard function over time

Parameters:
  baseline_switch_rate_per_period  — from churned-user review frequency
  satisfaction_modifier            — satisfaction reduces rate
  competitive_stimulus_modifier    — competitor stimulus raises rate
```

#### Trust Vector
```
trust_vector = {
  expert:      0.0–1.0,  // doctors, analysts, certified reviewers
  peer:        0.0–1.0,  // friends, community members
  brand:       0.0–1.0,  // official brand content
  ad:          0.0–1.0,  // paid advertising
  community:   0.0–1.0,  // user groups, forums
  influencer:  0.0–1.0   // content creators
}

Weights: estimated from trust source citation frequency in reviews
         weighted by whether citing that source correlated with purchase
```

**Key distinction from current system:**
- Current: persona *reasons about* why it would buy → narrative drives the decision
- Next: persona *has parameters* → parameters drive the decision → narrative explains it post-hoc

---

### Layer 3: Empirical Constraint System

The copula approach is preserved but seeded with empirical correlation matrices.

```
Current:  Gaussian copula with correlation matrix from
          psychology literature + LLM priors

Next:     Gaussian copula with correlation matrix estimated
          from behavioural cluster feature co-occurrence

Where: correlation(price_sensitivity, switching_propensity)
     = Pearson correlation computed from Stage 3 feature vectors
```

Hard constraints remain for logical impossibilities. Soft constraints replace psychological validity rules — an attribute combination can be rare but not impossible; sample from the low-probability region rather than rejecting outright.

---

### Layer 4: Calibration

Full specification: `references/calibration.md`

#### Method 1: Benchmark Anchoring (no client data required)

```
Step 1: Define target outcome metrics per domain
  SaaS:        free-to-paid 2–8%, monthly churn 2–8%
  E-commerce:  cart conversion 2–4%, repeat purchase 25–40%
  Source: Mixpanel, Recurly, Shopify public benchmarks

Step 2: Run population simulation — record conversion rate, churn rate

Step 3: Compute divergence vs. benchmark range
  If outside range: adjust purchase_prob_function intercept (β₀)
  until aggregate output falls within bounds

Step 4: Document the adjustment as a calibration factor
  Store: segment → calibration_factor lookup
```

#### Method 2: Client Cohort Feedback Loop (requires outcome data)

```
Input:  client provides aggregate outcome data
        (even just: "our free-to-paid is 5%, churn is 6% monthly")

Step 1: Run simulation against client scenario
Step 2: Compute KL divergence:
        simulated outcomes vs. client-reported outcomes
Step 3: Attribute divergence by persona segment
Step 4: Adjust parameters by δ = 0.05–0.10 per iteration
Step 5: Re-run → check divergence → iterate
        Stop when KL divergence < threshold or plateaus
```

**Critical principle:** calibration adjusts population-level behaviour, not individual personas. Personas remain synthetic. What becomes empirically anchored is the aggregate.

---

### End-to-End Construction Pipeline

```
DATA SOURCES → Signal Extraction → Feature Construction → Behavioural Clustering
                                                                    ↓
ICP Definition → Segment Selection → Constraint Graph (empirical) → Copula Sampling
                                                                    ↓
                        Demographic + Psychographic Attribute Vector
                                                                    ↓
                    Behavioural Parameter Assignment (from cluster data)
                                                                    ↓
                          Narrative Layer (LLM — storyteller only)
                                                                    ↓
                              Simulation-Ready Persona
```

| Component | Method |
|-----------|--------|
| Narrative text, identity | LLM-generated |
| Demographics, psychographics | Sampled from empirical copula |
| Behavioural parameters | Learned/estimated from data pipeline |
| Edge cases, sparse data | Inferred via constraint graph + Bayesian imputation |

---

## C. What Changes in Outputs

After this redesign, personas will have:

1. **WTP as a probability surface, not a point estimate**
   — "P(purchase) at $100: 0.72, at $150: 0.48, at $200: 0.22" instead of "WTP ~$150"

2. **Stable population-level behaviour across runs**
   — Behavioural parameters are deterministic at persona level; variance is controlled

3. **Objection profiles with frequency weights**
   — "integration complexity (0.6), price vs ROI (0.45), vendor trust (0.3)"
   instead of "may object to integration complexity"

4. **Fewer impossible combinations**
   — Empirical constraint graph rejects statistically implausible attribute combinations

5. **Calibrated conversion rates**
   — Simulated population-level conversion falls within real-world benchmark ranges

6. **Trust vectors instead of trust labels**
   — Channel-specific weights that modulate decision probability when that source is encountered

What does NOT change: persona distinctiveness, narrative richness, decision reasoning trace structure, memory architecture. These are strengths. Do not touch them.

---

## D. What to Defer

**1. Memory loop and temporal simulation**
The perceive → remember → reflect → decide loop requires calibrated base personas to be meaningful. Temporal simulation on uncalibrated personas produces drift in an unknown direction. Build this *after* the calibration layer is working.

**2. Predictive capability**
Prediction requires calibrated behavioural parameters, a feedback loop with real outcomes, and enough iterations to validate the model. This is Phase 3.

**3. Social influence and network effects**
Multi-agent simulation where personas influence each other adds no value until individual persona behaviour is calibrated.

**4. Real-time data ingestion**
Build the one-time pipeline first. Make it work. Automate later.

**5. Full 5-stage LLM reasoning trace (simplify, don't remove)**
The 5-stage trace is over-engineered as a decision *generator*. Keep it as a decision *explainer*. Strip to 3 stages. The decision is made by parameters; the trace explains it post-hoc.

**6. Dual constraint system**
Once empirical correlation data is available, the hardcoded psychological anti-correlations in `references/architecture.md` become redundant. Replace them when empirical data is available. Do not run both in parallel.

---

## Sprint Plan

| Sprint | Focus | Key Deliverables |
|--------|-------|-----------------|
| **Sprint A** | Schema + Behavioural Parameters | `behavioural_params` in output schema, `BEHAVIOURAL_GROUNDING.md`, updated architecture rules |
| **Sprint B** | Data Grounding Layer | `data_grounding.md`, updated ICP spec with signal extraction, updated skill flow |
| **Sprint C** | Calibration Layer | `calibration.md`, calibration state in cohort envelope, updated quality gates |

Sprints A, B, and C are sequential — A must complete before B, B before C.
Sprint A is the unblocking dependency.

---

*Design review conducted: 2026-04-02*
*Next review checkpoint: after Sprint C completion*
