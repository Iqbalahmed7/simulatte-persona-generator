# SIMULATTE VALIDITY PROTOCOL
### Extracted from Master Spec v1.2 — Section 12

**Status:** Canonical quality document. Extracted for standalone use in sprint acceptance criteria and QA review.
**Source:** `SIMULATTE_PERSONA_GENERATOR_MASTER_SPEC.md` Section 12
**Version:** Tracks master spec v1.2

This document is the complete test specification for population quality, behavioural validity, simulation quality, and calibration. Every sprint that produces persona or simulation output must run the applicable tests from this protocol before marking work complete.

---

## Module 1 — Structural Quality Gates

Run on every persona before output is produced. These are automated checks.

| Gate | What Is Checked | Target | Failure |
|------|----------------|--------|---------|
| **G1: Schema validity** | Every persona parses against the full schema without error | 100% pass rate | Any parse error blocks output |
| **G2: Hard constraint compliance** | Hard constraint violation rate (impossible attribute combinations) | < 5% | Reduce violating attributes; do not suppress the check |
| **G3: Tendency-attribute consistency** | Directional consistency between attribute values and tendency bands | < 5% violation rate | Flag as `TENDENCY_ATTRIBUTE_INCONSISTENCY`; resolve before output |
| **G4: Narrative completeness** | `first_person`, `third_person`, `display_name` all present and non-empty | 100% | Regenerate missing fields |
| **G5: Narrative alignment** | No contradictions between narrative and attribute/tendency profile | 0 contradictions | Automated scan + manual review; regenerate if failed |
| **G6: Population distribution** | No city > 20%, no age bracket > 40%, income spans ≥ 3 brackets | All pass | Resample until distribution is met |
| **G7: Cohort distinctiveness** | Mean pairwise cosine distance on 8 core attributes | > 0.35 | Resample most-similar pair from farther stratification band; max 3 attempts |
| **G8: Persona type coverage** | Unique types / required types per cohort size | N=3: ≥3 types; N=5: ≥4 types; N=10: all 8 | Regenerate under-covered types |
| **G9: Tension completeness** | Every persona has ≥ 1 explicit internal contradiction (value vs behaviour) | 100% | Regenerate personas with no documented tension |
| **G10: Memory bootstrap** *(Simulation-Ready mode only)* | Seed memories per persona | ≥ 3 per persona | Bootstrap additional seed memories before simulation |
| **G11: Tendency source coverage** | Every tendency has `source` field set (grounded / proxy / estimated) | 100% | Add source tracking; outputs without source labels are incomplete |

### Hard Constraint Reference

These specific combinations must never appear together in a valid persona:

| Combination | Correction |
|------------|-----------|
| Income below poverty line + premium preference > 0.85 | Reduce premium preference to ≤ 0.55 |
| Tier 3/rural + digital payment comfort > 0.85 | Reduce to ≤ 0.65 |
| Health anxiety < 0.2 + supplement belief > 0.80 | Raise health anxiety to ≥ 0.45 |
| Age < 25 + brand loyalty > 0.80 | Reduce brand loyalty to ≤ 0.60 |
| High income (top bracket) + extreme deal seeking > 0.85 | Reduce deal seeking to ≤ 0.60 |
| Risk tolerance > 0.80 + loss aversion > 0.80 | Reduce loss aversion to ≤ 0.50 |

### Tendency-Attribute Consistency Rules

| Attribute Condition | Required Tendency |
|-------------------|-----------------|
| `budget_consciousness > 0.70` | `price_sensitivity` band ≥ "high" |
| `budget_consciousness < 0.35` | `price_sensitivity` band ≤ "medium" |
| `brand_loyalty > 0.70` | `switching_propensity` = "low" |
| `social_proof_bias > 0.65` | `trust_orientation.peer` ≥ 0.65 |
| `authority_bias > 0.65` | `trust_orientation.expert` ≥ 0.65 |
| `ad_receptivity < 0.30` | `trust_orientation.ad` ≤ 0.25 |
| `information_need > 0.70` | `objection_profile` must include `need_more_information` |
| `risk_tolerance < 0.30` | `objection_profile` must include `risk_aversion` |

---

## Module 2 — Behavioural Validity Tests

Run on ≥ 3 sample personas per cohort before release. Some tests require simulation mode to be active (BV3, BV6). These tests verify that personas behave like coherent individuals, not just structurally valid records.

### BV1 — Repeated-Run Behavioural Stability

**What it means:** The same persona given the same stimulus sequence should produce substantially similar decisions across runs. Complete randomness = no identity. Perfect identity = unrealistic rigidity.

**How to test:** Run the same persona through the same 5-stimulus sequence 3 times.

**v1 threshold:**
- ≥ 2 of 3 runs produce the same final decision
- Reasoning traces share ≥ 60% of cited drivers
- Confidence scores within ±15 points across runs

**Failure:** Decisions flip randomly with no pattern. Or: outputs are byte-identical (no human variability).

---

### BV2 — Memory-Faithful Recall

**What it means:** Reasoning traces must cite memories that actually exist. The persona must not hallucinate experiences, and must not ignore pivotal ones.

**How to test:** After a 10-stimulus simulation, present a decision scenario. Check:
- (a) Every memory cited in the reasoning trace exists in working memory
- (b) Any observation with importance ≥ 8 that is topically relevant appears in retrieved memories

**v1 threshold:**
- (a) 100% citation validity — zero hallucinated memories
- (b) ≥ 80% recall of high-importance relevant observations

**Failure:** Persona cites experiences that were never presented as stimuli. Or: a high-importance negative experience (importance 9) is not mentioned in the decision.

---

### BV3 — Temporal Consistency Across Multi-Turn Simulation

*(Requires simulation mode)*

**What it means:** Attitudes must evolve coherently across a stimulus sequence, not reset between turns. Memory must influence decisions, not be ignored.

**How to test:** Run a 10-stimulus sequence with a clear arc (stimuli 1–5 positive, 6–10 mixed). Check:
- (a) Confidence/trust increases across stimuli 1–5
- (b) At least 1 reflection after stimulus 5 references the positive trend
- (c) Mixed stimuli 6–10 produce nuanced responses — not a full trust reset

**v1 threshold:**
- (a) Monotonic or near-monotonic confidence increase across the positive arc
- (b) ≥ 1 reflection references the accumulating trend
- (c) Final decision reasoning cites both positive and mixed experiences

**Failure:** No trust accumulation despite 5 positive stimuli. Or: a single negative stimulus completely overwrites all prior positive experience.

---

### BV4 — Interview Realism

**What it means:** In Deep Interview modality, the persona must answer in character, referencing its life stories, values, and experiences — not producing generic answers.

**How to test:** Present 5 open-ended interview questions (e.g., "Tell me about the last time you made a difficult purchase decision"). Evaluate:
- (a) Responses reference specific life story or core memory details
- (b) Responses are consistent with attribute profile
- (c) First-person voice maintained throughout
- (d) Persona volunteers unprompted elaboration

**v1 threshold:**
- (a) ≥ 3 of 5 responses cite specific life story or core memory detail
- (b) 0 contradictions with attribute profile
- (c) 100% first-person voice
- (d) ≥ 2 of 5 responses include unprompted elaboration

**Failure:** Generic answers that could apply to any persona. Broken character ("As an AI..."). Answers that contradict the profile.

---

### BV5 — Resistance to Persona Collapse Under Adjacent Scenarios

**What it means:** Two personas with similar profiles must produce detectably different responses. The system must not collapse adjacent personas into identical outputs.

**How to test:** Take two personas sharing the same persona type but differing in life stories, ≥ 2 key attributes, and ≥ 1 tension. Present the same scenario.

**v1 threshold:**
- (a) Different final decisions OR same decision with ≥ 3 different cited drivers
- (b) Reasoning traces share < 50% of verbatim language
- (c) ≥ 1 driver unique to each persona traceable to their specific life story or tension

**Failure:** Two "Pragmatist" personas produce nearly identical reasoning despite different life stories. The system is collapsing to the type label rather than differentiating on identity.

---

### BV6 — Believable Consistency vs Unrealistic Rigidity

*(Requires simulation mode)*

**What it means:** A persona should be consistent with its identity but not robotically so. Real humans occasionally act against their tendencies when context demands it.

**How to test:** Present 10 scenarios including 2 "override scenarios" designed to trigger departure from tendency (e.g., health emergency for price-sensitive persona; clear product failure for brand-loyal persona).

**v1 threshold:**
- (a) Tendency-consistent in 70–90% of scenarios (not 100%)
- (b) ≥ 1 of 2 override scenarios produces a departure with explicit cited reasoning
- (c) No persona shows 100% consistency across all 10 scenarios

**Failure:** Perfect consistency in all 10 scenarios including overrides (robot, not person). Or: random departures in 5+ scenarios without override context (no identity coherence).

---

## Module 3 — Simulation Quality Gates

Run on every simulation before results are used.

| Gate | Check | Threshold | Action on Failure |
|------|-------|-----------|------------------|
| **S1: Zero error rate** | Run --max 5 first; all 5 must complete without error | 100% completion | Debug before running full population |
| **S2: Decision diversity** | No single decision option > 90% of cohort | Warn if exceeded | Review stimulus design; may indicate broken persona or prompt issue |
| **S3: Driver coherence** | Top decision drivers are category-relevant | Manual review | Review stimulus prompts; check tendency-attribute assignment |
| **S4: WTP plausibility** | Median WTP within ±30% of ask price | Warn if outside | Check tendency-attribute proxy formulas; may need recalibration |

---

## Module 4 — Calibration Gates

*(Applies when calibration is performed — Phase 3)*

| Gate | Check | Threshold |
|------|-------|-----------|
| **C1: Status set** | `calibration_state.status` ≠ null | Required for delivery |
| **C2: Benchmark applied** | For new domains, benchmark anchoring applied first time | Required |
| **C3: Conversion plausibility** | Simulated conversion within 0.5x–2x of domain benchmark | Warn if outside |
| **C4: Client feedback trigger** | If client outcome data available, feedback loop applied | Required |
| **C5: Calibration age** | Populations > 6 months flagged as stale | Warning |

---

## Module 5 — Anti-Stereotypicality Check

Run on every Indian persona and every Sarvam-enriched output.

The following are **prohibited defaults**. Their presence without explicit derivation from the persona's attribute profile = check failure.

| Prohibited Default | Required Instead |
|-------------------|-----------------|
| Joint family assumed universally | Derive from `household.structure` |
| Low income assumed | Derive from `income_bracket` |
| Hindi-speaking assumed | Derive from `location.region` |
| Metro city defaulted | Respect ICP geography |
| Traditional/conservative assumed | Derive from `values` and `lifestyle` attributes |
| Weddings/festivals/arranged marriage as default texture | Use only when life stories specifically support it |
| Jugaad as universal Indian trait | Domain and segment specific; not a default |
| Single trust pattern for all Indian consumers | Derive from `trust_orientation` attributes |
| India treated as one culture | Regional, linguistic, socioeconomic specificity required |
| Class or caste-coded clichés | Derive from attributes and life stories only |

**Pass condition:** ≥ 90% of cultural details in the output are traceable to specific persona attributes. Zero prohibited defaults present without derivation.

---

## Gate Sequence Summary

```
For every persona generation run:
  → G1 through G11 (all applicable)

For every cohort:
  → G6 (distribution), G7 (distinctiveness), G8 (type coverage)
  → BV1, BV2, BV4, BV5 on ≥ 3 sample personas

For every simulation run:
  → S1 (5-persona trial first)
  → S2, S3, S4 after full run
  → BV3, BV6 on sample personas

For every Indian persona:
  → Module 5 (anti-stereotypicality)

For every Sarvam-enriched output:
  → Module 5
  → CR1–CR4 (see SIMULATTE_SARVAM_TEST_PROTOCOL.md)
```

---

*Extracted from master spec v1.2. If Section 12 of the master spec changes, update this document to match.*
