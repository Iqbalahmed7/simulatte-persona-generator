# SIMULATTE CONSTITUTION
### Extracted from Master Spec v1.2 — Section 13

**Status:** Canonical governance document. Extracted for standalone use in code review, sprint kickoff, and implementation verification.
**Source:** `SIMULATTE_PERSONA_GENERATOR_MASTER_SPEC.md` Section 13
**Version:** Tracks master spec v1.2

Every sprint, pull request, and architectural decision must be checkable against this document. If it cannot be checked, the work is not ready.

---

## Part I — Ten Non-Negotiable Principles

These are axioms. Violating any one is a spec violation that must be corrected before merge.

| # | Principle | Test: You Have Drifted If… |
|---|-----------|----------------------------|
| **P1** | A persona is a synthetic person, not a segment model. Personas have identity, memory, history, and cognition. | You can fully reconstruct a persona from a 10-field vector. |
| **P2** | The LLM is the cognitive engine. It perceives, reflects, and decides. It is not a narrator explaining pre-computed outputs. | The LLM's only role is generating text after decisions are made by other code. |
| **P3** | Memory is the product. Without memory there is no temporal simulation, no experiment modularity, no reuse. | Memory is "planned for a later sprint" while other features ship. |
| **P4** | Behavioural tendencies are soft priors, not decision functions. They shape reasoning. They do not replace it. The decision emerges from the LLM's reasoning trace, not from a formula. | You are computing P(purchase) from coefficients and using the LLM to narrate the result. |
| **P5** | Identity is life stories + values + events + relationships + constraints. Tendencies are properties of the persona, not the persona itself. Two personas with identical tendencies but different life stories are different people. | Personas with different life stories but same tendency bands produce identical decisions. |
| **P6** | Grounding supports the simulation — it does not replace it. Domain data anchors tendencies in evidence. It does not substitute for LLM reasoning, memory accumulation, or reflection. | Removing the grounding pipeline causes the cognitive loop to stop functioning. |
| **P7** | Calibration is a trust layer, not the product. It makes the simulation credible. It comes after identity, memory, and cognition work. | Calibration sprints are blocking cognition sprints. |
| **P8** | The core architecture is domain-agnostic. Domain-specific knowledge enters through taxonomy extensions and the grounding pipeline only. | You are adding domain-specific attributes (e.g., `pediatrician_trust`) to the base taxonomy. |
| **P9** | Every persona carries internal tension. A persona without contradiction is a stereotype. | Personas pass all constraint checks without a single flagged tension. |
| **P10** | Transparency over performance. Every tendency has a source label. Every reflection has citations. Every calibration has documentation. | Outputs omit source fields, or tendencies are unlabelled as to their provenance. |

---

## Part II — Ten Anti-Patterns to Avoid

| # | Anti-Pattern | What It Looks Like | Why It's Dangerous |
|---|-------------|--------------------|--------------------|
| **A1** | **Coefficient creep** | Adding more numerical parameters to the persona model — loyalty_score, churn_coefficient, WTP_intercept. | Transforms personas into statistical models. Every coefficient is a step toward replacing reasoning with formulas. |
| **A2** | **Narrative-last architecture** | Generating the narrative as the final step, after all decisions are made, as a human-readable summary. | Makes the narrative decorative. Narrative is generated before simulation (as part of identity) and read by the system (as part of core memory). |
| **A3** | **Memory deferral** | "We'll add memory in Phase 3, after calibration works." | Inverts the priority order. Without memory, you cannot validate temporal simulation. This already happened once in this project. |
| **A4** | **Domain leakage** | Adding category-specific attributes, constraints, or logic to the base system for one client's use case. | Makes the system work perfectly for one domain and break for all others. Domain knowledge belongs in extensions and grounding, not core. |
| **A5** | **Validation theater** | Reporting high aggregate correlation scores without testing individual-level behavioural validity (BV1–BV6). | Gives false confidence. A population can show 90% aggregate accuracy while every individual persona is stereotypical. |
| **A6** | **Type collapse** | Personas of the same type producing identical outputs. "All Pragmatists say the same thing." | Types are sampling guides, not personality scripts. Life stories, tensions, and attribute values must differentiate within types. |
| **A7** | **Grounding absolutism** | Refusing to generate personas without domain data. "We can't produce anything useful without 500 reviews." | The system must work in Proxy Mode. Grounding improves quality; its absence must not block generation. |
| **A8** | **Context window stuffing** | Putting the entire persona record — all 200 attributes, all memories, all tendencies — into every LLM call. | Wastes tokens, dilutes signal, increases cost. Only core memory + relevant working memories + tendency summary should be in context. |
| **A9** | **Platform-first thinking** | Building multi-user infrastructure, database schemas, API layers, and UI before the cognitive loop works. | The platform is meaningless without personas that think and remember. Engine first, chassis second. |
| **A10** | **Client-specific optimisation** | Tuning the system to produce output that one specific client likes, at the expense of generalizable quality. | Creates a consulting tool, not a product. The domain must be an input, not a hardcoded assumption. |

---

## Part III — Cultural Layer Anti-Patterns (CA1–CA7)

These specifically guard the Indian Cultural Realism Layer (Sarvam) from producing harm or drift.

| # | Anti-Pattern | What It Looks Like | Why It's Dangerous |
|---|-------------|--------------------|--------------------|
| **CA1** | **Sarvam as hidden reasoning engine** | Sarvam is invoked during perceive(), reflect(), or decide() — not just narrative enrichment. | Violates core architecture. Sarvam may only operate post-core, on expression. |
| **CA2** | **India mode becoming mandatory** | Cultural realism layer activates automatically for all Indian personas without client opt-in. | Removes client control. Mandatory activation makes it part of core, which it must not be. |
| **CA3** | **Cultural enrichment silently modifying decisions** | A persona chooses differently after Sarvam enrichment because cultural context shifted the framing. | Sarvam may change how a decision is narrated. It must not change what decision is made. |
| **CA4** | **Cultural realism as stereotype generation** | Sarvam defaults to generic Indian scripts — joint family, festivals, jugaad — rather than deriving from persona attributes. | Produces caricature, not realism. Violates Anti-Stereotypicality Constraints. |
| **CA5** | **Monolithic India treatment** | Same Indian context applied regardless of whether the persona is from Chennai, Chandigarh, or a Tier 3 town in Maharashtra. | India is not one culture. Regional, linguistic, and socioeconomic specificity is the point. |
| **CA6** | **Cultural layer scope creep** | Sarvam starts with narrative enrichment, then progressively used for interview tone, then reasoning priming, then decision framing — across releases. | Every scope expansion must be approved via spec revision. Sarvam's scope is defined in Master Spec Section 15C and does not expand by default. |
| **CA7** | **Conflating language with culture** | Using Sarvam for multilingual output (Hindi, Tamil, etc.) without controlling for cultural accuracy per region. | Generating in Hindi for a Tamil Nadu persona is not Indian cultural realism — it is a different error. Multilingual output is explicitly OUT OF SCOPE. |

---

## Part IV — Pre-Implementation Checklist

**Must be verified before starting any sprint or implementation task.**

```
PRE-IMPLEMENTATION CHECKLIST
=============================

□ 1. Does this work serve identity, memory, or cognition?
     If not, is Phase 1 complete? If incomplete, work on Phase 1 first.

□ 2. Does this change add numerical parameters to the persona model?
     If yes: are they soft tendencies (bands + descriptions) or hard coefficients?
     Coefficients = P4 violation.

□ 3. Does this change touch the base taxonomy or base schema?
     If yes: is the change domain-agnostic?
     Domain-specific changes to core = P8 violation.

□ 4. Does this change defer or deprioritise memory work?
     If yes: document why and flag for review. Memory deferral = P3 violation.

□ 5. Does this change introduce a decision that bypasses the cognitive loop?
     If yes: is there a documented reason? Bypassing the loop = P2 violation.

□ 6. Is the change traceable to a section of the master spec?
     If not: update the spec first, then implement.

□ 7. Do outputs carry source labels on tendencies and citations on reflections?
     If not: add provenance tracking. Unlabelled outputs = P10 violation.

□ 8. Have I checked the Settled Decisions table (Master Spec 14A)?
     Am I contradicting any settled decision?
     If yes: escalate — do not implement without formal spec revision.
```

---

## Part V — Pre-Release Checklist

**Must be verified before any population or simulation output is delivered or demonstrated.**

```
PRE-RELEASE CHECKLIST
======================

STRUCTURAL QUALITY
□  1. Schema validity: 100% parse rate
□  2. Hard constraint violations: < 5%
□  3. Tendency-attribute consistency: < 5% violation rate
□  4. Narrative completeness: 100%
□  5. Narrative alignment: 0 contradictions
□  6. Population distribution checks: all pass
□  7. Distinctiveness score: > 0.35
□  8. Persona type coverage: per cohort size rules
□  9. Tension completeness: 100%
□ 10. Tendency source coverage: 100%

BEHAVIOURAL QUALITY (run on ≥ 3 sample personas)
□ 11. BV1: Repeated-run stability — ≥ 2/3 same decision, ±15 confidence
□ 12. BV2: Memory-faithful recall — 100% citation validity, ≥ 80% high-importance recall
□ 13. BV4: Interview realism — ≥ 3/5 responses cite life stories, 0 character breaks
□ 14. BV5: Adjacent persona distinction — < 50% shared language in reasoning traces

SIMULATION QUALITY (if simulation mode)
□ 15. BV3: Temporal consistency — confidence trends match stimulus arc
□ 16. BV6: Override test — ≥ 1/2 overrides produce motivated departure
□ 17. Zero error rate on 5-persona trial run
□ 18. No single decision > 90%
□ 19. Memory bootstrap: ≥ 3 seed memories per persona

PROVENANCE
□ 20. Grounding mode labelled (grounded / proxy / estimated)
□ 21. Calibration state documented (or explicitly "uncalibrated")
□ 22. ICP Spec saved alongside output
```

---

*This document is extracted from the master spec and must remain in sync with it. If the master spec changes Section 13, update this document to match.*
*Master spec version this was extracted from: v1.2*
