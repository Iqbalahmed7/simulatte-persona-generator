# SIMULATTE — SARVAM INTEGRATION TEST PROTOCOL
### Extracted from Master Spec v1.2 — Sections 12 (CR1–CR4) and 15

**Status:** Canonical QA document for the Indian Cultural Realism Layer.
**Source:** `SIMULATTE_PERSONA_GENERATOR_MASTER_SPEC.md` Sections 12 and 15
**Version:** Tracks master spec v1.2
**Applies to:** Any sprint that touches the Sarvam integration, and every domain approved for Sarvam enrichment.

---

## Governing Rule (Must Be Read First)

**Sarvam must never influence who the persona is.**
**Sarvam may only influence how the persona is expressed and culturally contextualised.**

This means:
- Same underlying persona
- Same core identity
- Same behavioural tendencies
- Same memory structure
- Same reasoning outcome
- Richer Indian realism only in the narrative and contextual layer

All four tests below verify this rule from different angles. All four must pass before Sarvam enrichment is approved for any domain.

---

## Activation Pre-Check

Before running CR1–CR4, verify the activation conditions are met:

```
ACTIVATION PRE-CHECK
=====================
□ 1. persona.location.country == "India"?
□ 2. client_config.sarvam_enrichment == true (explicit opt-in)?
□ 3. persona record is fully finalized and validated (Gates G1–G11 passed)?
□ 4. Sarvam is being invoked AFTER persona record finalization, not during generation?

If any condition fails → do not invoke Sarvam → document why in the enrichment record.
```

---

## CR1 — Isolation Test (Core Persona Fidelity)

### What It Means
Sarvam enrichment must change texture, not substance. The standard output and Sarvam-enriched output must be recognisably the same person making the same decisions.

### How to Test

1. Take a finalized, validated persona (G1–G11 passed)
2. Run it through a decision scenario using the standard cognitive loop → record output A
3. Run the same persona through the same scenario with Sarvam enrichment active → record output B
4. Compare A and B field by field:

| Field | Status | Allowed Difference |
|-------|--------|-------------------|
| `attributes` (all values) | **Must not differ** | Zero tolerance |
| `behavioural_tendencies` (all fields) | **Must not differ** | Zero tolerance |
| `memory.core` (all fields) | **Must not differ** | Zero tolerance |
| `memory.working` (observations, reflections) | **Must not differ** | Zero tolerance |
| Final decision (buy / defer / reject / etc.) | **Must not differ materially** | Zero tolerance |
| Top 2–3 cited drivers | **Same drivers** | May be expressed differently |
| Reasoning trace structure | **Same 5-step structure** | Wording may differ |
| Confidence score | **Within ±5 points** | Small variation acceptable |
| Narrative phrasing | **May differ** | Cultural texture expected |
| Cultural examples cited | **May differ** | This is the point |
| Idiomatic style | **May differ** | Regional register expected |
| Contextual references | **May differ** | India-specific references expected |

### Pass Condition
- Zero attribute/tendency/memory changes
- Final decision identical
- Confidence within ±5 points
- At least 1 cultural reference present in output B that is absent from output A (confirms the layer is doing something)

### Fail Conditions
- Sarvam-enriched persona makes a different decision
- Enrichment removes or softens a tension
- Enrichment silently adds an attribute (e.g., raises `health_anxiety`)
- Reasoning trace changes structure (e.g., drops from 5 steps to 3)
- Confidence score diverges by > 5 points

### Failure Response
CR1 failure = **Sarvam integration is broken**. The layer has leaked into cognition. Do not ship. Debug the architectural boundary — Sarvam must receive a completed persona as a read-only input.

---

## CR2 — Stereotype Audit

### What It Means
Sarvam-enriched outputs must derive Indian context from the persona's attribute profile, not from generic Indian cultural scripts. Indian diversity must be reflected; India must not be flattened into one culture.

### Prohibited Defaults (Reference: Master Spec Section 10)

The following are prohibited unless explicitly derivable from the persona's attributes:

| Prohibited Default | What to Check |
|-------------------|--------------|
| Joint family assumed | Check `household.structure` — single/couple/nuclear are valid |
| Low income assumed | Check `income_bracket` |
| Hindi-speaking assumed | Check `location.region` — South/East India are not Hindi belts |
| Metro city defaulted | Check `location.urban_tier` — Tier 2 and Tier 3 are valid |
| Traditional/conservative assumed | Check `values` and `lifestyle` attributes |
| Weddings/festivals/arranged marriage as default texture | Must trace to a specific life story element |
| Jugaad framing | Must trace to specific `lifestyle` or `values` attribute |
| Single trust pattern for all Indian users | Must derive from `trust_orientation` weights |
| India treated as one culture | Regional specificity must match `location.region` |
| Class/caste-coded clichés | Must derive from attributes, not assumed group scripts |

### How to Test

For each Sarvam-enriched output:

1. List every cultural reference, contextual detail, and India-specific example in the output
2. For each item, identify the persona field it derives from (attribute name, life story element, or location)
3. Check whether any prohibited default appears without derivation

### Pass Condition
- ≥ 90% of cultural details are traceable to a specific field in the persona record
- 0 prohibited defaults present without explicit derivation

### Fail Conditions
- A Chennai persona described with North Indian cultural references
- A single-person household described consulting their joint family
- A high-income urban professional described using jugaad without any lifestyle attribute supporting it
- Tier 2 city persona described with metro consumption patterns

### Failure Response
CR2 failure = **stereotype generation**. Regenerate the enrichment with explicit attribute-derivation constraints. If the LLM consistently defaults to stereotypes, the Sarvam enrichment prompt needs explicit anti-stereotypicality instructions.

---

## CR3 — Cultural Realism Audit

### What It Means
Indian personas enriched by Sarvam should feel grounded in actual Indian lived experience — not as Western-default personas with Indian names, and not as caricatures. This test requires human evaluation.

### How to Test

Present the Sarvam-enriched output to a human evaluator with domain knowledge of the target segment. The evaluator must not be shown the standard (non-enriched) output.

Ask the evaluator to rate the following on a 1–5 scale:

| Dimension | Question | 1 | 5 |
|-----------|---------|---|---|
| Cultural specificity | Does this persona feel specific to the segment and geography described? | Generic / could be anyone | Specific and grounded in this segment |
| Avoidance of caricature | Does the output avoid stereotypical Indian tropes? | Heavy use of clichés | No clichés; feels real |
| Institutional accuracy | Are the Indian institutions, channels, and references correct for this segment? | Wrong/generic | Accurate and specific |
| Lived context richness | Does the persona's daily context feel real and grounded? | Thin / vague | Rich and specific |

### Pass Condition
- Mean evaluator rating ≥ 4.0 / 5.0 across all four dimensions
- Minimum 2 independent evaluators per domain before Sarvam enrichment is approved for that domain
- Neither evaluator scores any dimension below 3.0

### Fail Conditions
- Evaluator says "this could be any urban Indian" (too generic)
- Evaluator says "this reads like an outsider's idea of India" (caricature)
- Evaluator says "this sounds like an American with an Indian name" (Western default bias)
- Any dimension scores < 3.0

### Failure Response
CR3 failure = **insufficient cultural grounding**. Review the Sarvam enrichment prompt. May require domain-specific grounding data (reviews, forum posts from that specific segment). Do not approve Sarvam for this domain until CR3 passes.

---

## CR4 — Persona Fidelity Audit

### What It Means
After Sarvam enrichment, the persona must still sound like the same individual. Enrichment changes texture; it must not produce a different person.

### How to Test

1. Generate 5 persona pairs: [standard narrative, Sarvam-enriched narrative] for 5 different personas
2. Remove all identifying labels and shuffle — evaluator does not know which is which
3. Present pairs in randomised order and ask: "Are these two descriptions of the same person? Yes / No / Unsure."
4. If evaluator says No: ask them to identify what changed (decision-relevant trait, values, identity)

### Pass Condition
- Evaluator confirms same person in ≥ 4 of 5 pairs
- Any "No" answers are attributable to phrasing, not to identity-level differences

### Fail Conditions
- Standard narrative describes an independent, research-driven buyer; enriched describes a consensus-seeking family-oriented buyer (different identity, not texture)
- Standard narrative describes low price sensitivity; enriched describes frugality and budget anxiety (tendency leak)
- Evaluator consistently cannot match pairs (enrichment is producing a different persona)

### Failure Response
CR4 failure = **identity corruption**. The enrichment is overwriting persona identity, not adding cultural texture. Architectural investigation required: check whether Sarvam is reading from attribute fields or only from narrative fields. Sarvam must only rewrite expression, not regenerate identity.

---

## CR Tests — Quick Reference

| Test | What It Checks | Pass Condition | Who Runs It |
|------|---------------|----------------|-------------|
| CR1: Isolation | Decisions/attributes unchanged by enrichment | 0 changes to structure; decision identical; confidence ±5 | Automated (diff the records) |
| CR2: Stereotype audit | Cultural details derive from attributes, not generic scripts | ≥ 90% traceable; 0 prohibited defaults | Manual/automated |
| CR3: Cultural realism | Output feels grounded in real Indian segment context | ≥ 4.0/5.0 human rating across 4 dimensions | Human evaluators (≥ 2 per domain) |
| CR4: Persona fidelity | Enriched output is the same person, not a different one | ≥ 4/5 pairs confirmed same person | Human evaluators |

---

## Domain Approval Gate

Before Sarvam enrichment is used in production for any domain:

```
DOMAIN APPROVAL GATE
=====================
□ CR1 passed (automated — run 10 personas, all pass)
□ CR2 passed (manual — 3 spot checks, ≥ 90% traceable)
□ CR3 passed (2 independent human evaluators, ≥ 4.0/5.0)
□ CR4 passed (2 independent human evaluators, ≥ 4/5 pairs)
□ Anti-stereotypicality check passed (Module 5 from Validity Protocol)
□ Result documented in domain approval record:
    - Domain: [name]
    - Date approved: [date]
    - Evaluators: [names/IDs]
    - CR scores: [scores]
    - Known limitations: [any caveats]
```

---

## What Is Never Tested Here

These are out of scope for this protocol because they are structural invariants, not test targets:

- Whether Sarvam should be optional (it is — S21 is settled)
- Whether Sarvam should work for non-India personas (it does not — S22 is settled)
- Whether multilingual output is supported (it is not — O15 is open, currently blocked)
- Whether Sarvam operates during simulation (it does not — CA1 anti-pattern)

---

*Extracted from master spec v1.2. If Sections 12 or 15 change, update this document to match.*
