# Quality Gates — When Is Work Ready?

Standards that must be met before a population or simulation result is considered usable.

---

## Population Quality Gates

### Gate 1: Schema Validity
Every persona must parse against the Pydantic schema without error.
- Run: `Persona.model_validate(p_dict)` for every persona
- Failure rate target: 0%

### Gate 2: Constraint Compliance
Every persona must pass the hard constraint checker.
- Hard violation rate target: < 5%
- Soft violation rate: informational only, not a blocker
- Key rules: anti-correlation pairs, demographic consistency, work hours not defaulted

### Gate 3: Narrative Completeness
Every persona must have:
- `narrative` — 3rd person biographical summary (150-200 words)
- `first_person_summary` — 1st person voice (100 words)
- `display_name` — human-readable ID

### Gate 4: Population Distribution
The population should not be clustered:
- No city appearing in > 20% of personas
- No single age bracket > 40%
- At least 15% male personas (for categories with joint decision-making)
- Income distribution spanning at least 3 brackets

### Gate 5: Memory Bootstrap
Every persona should have at least 3 seed episodic memories before simulation starts.
A persona with zero memories will produce generic decisions — the memory system has nothing to retrieve.

---

## Simulation Quality Gates

### Gate 1: Zero Error Rate
Run `--max 5` first. All 5 must complete without error before running the full population.
Common failure modes:
- Model name not available (test with a direct API call first)
- max_tokens too low for decide() (use 2048)
- JSON truncation (see prompt patterns)

### Gate 2: Sanity Check on Decisions
After a full run, check:
- No single decision > 90% (would indicate a broken persona or model issue)
- At least 3 different decision types represented
- WTP median within ±20% of the ask price (extreme outliers suggest prompt issues)

### Gate 3: Driver Coherence
The top drivers should make category sense. For child nutrition: pediatrician, price, clean label, peer WOM. If the top driver is something like "color of packaging" — the stimulus prompts need review.

---

## Test Coverage Gates

Minimum test counts per component:
| Component | Minimum |
|---|---|
| MemoryManager | 15 tests |
| CognitiveAgent | 10 tests |
| ConstraintChecker | 20 tests |
| ReflectionEngine | 10 tests |
| Schema Coherence | 8 assertions |

All LLM calls must be mocked. Test suite must run in < 2 seconds.

### The Schema Coherence Test
This is the most important single test file. It asserts that every field path used in production code exists at the correct location on the schema.

When to update it:
- When the schema changes
- When a new field path is introduced in any production code
- After every sprint where schema fields are accessed

It is a regression guard. If it fails, it means either the schema changed without updating the code, or the code was written with a wrong path.

---

---

## Behavioural Grounding Gates (Sprint A — Next Phase)

These gates apply to personas generated in Grounded Mode or Simulation-Ready Mode.

### Gate B1: Behavioural Parameters Present
Every persona in Grounded Mode must have a `behavioural_params` block with all five parameters populated:
- `purchase_prob` (with `baseline_at_ask_price`)
- `price_elasticity` (with `value` and `band`)
- `switching_hazard` (with all five sub-fields)
- `trust_vector` (with all six channel weights)
- `objection_profile` (at least 2 entries)

### Gate B2: Parameter-Attribute Consistency
Run the 9 behavioural consistency checks from `references/architecture.md` Section 6b.
Violation rate target: < 5%

### Gate B3: Source Field Populated
Every behavioural parameter must have a `source` field set to one of:
`cluster_estimated`, `proxy_estimated`, or `benchmark_calibrated`
Parameters with `source: null` or missing source field: not permitted.

### Gate B4: Narrative Does Not Contradict Parameters
Check that the narrative does not:
- Cite a WTP figure more than 30% above or below the implied WTP from `purchase_prob`
- Describe the persona as "extremely loyal" when `switching_hazard.baseline_rate_per_period > 0.05`
- Describe high trust in a source type where `trust_vector.[type] < 0.25`

Automated check: regex scan for numeric WTP mentions, compare against parameter range.
Manual check: narrative review for trust description contradictions.

---

## G12 — Simulation Grounding Check (added April 2026)

### Background

During manual QA of 6 Lumio client simulation reports, three types of grounding contamination were found that had gone undetected. This led to the G12 gate.

### Three contamination types found in Lumio

**T1 — Injected Product Facts**
A product brief submitted for simulation contained `₹4,000–₹18,000` as an indicative price range. Lumio's actual prices are ₹29,999 and ₹54,999. This invented range contaminated persona WTP distributions across all 6 reports. No source document supported these figures.

**T2 — Impossible Persona Attributes**
Multiple personas were generated with prior exposure at Croma ("I saw the Lumio TV at the Croma demo last week"). Lumio is Amazon-only — it has no Croma presence. The personas were structurally impossible, which invalidated purchase-intent scoring.

**T3 — Quote Leakage**
Persona verbatim quotes included specific timings ("Netflix loads in 4 seconds on Lumio vs 22 seconds on Xiaomi") that were never in the product frame. The frame only said "2x faster." The model hallucinated specific numbers and leaked them into persona speech, giving false precision to a relative claim.

### Lessons learned

1. **Relative claims in product frames produce specific numbers in persona outputs.** If the frame says "faster," the model will invent how much faster. Lock down the frame or accept that quotes will contain invented numbers.
2. **Market facts must be versioned with the simulation date.** Lumio had no Croma presence *as of simulation date* — this needs to be explicit in the market facts JSON.
3. **T2 issues are almost always client-fatal.** A simulation that claims a brand has physical retail when it doesn't will undermine client trust immediately. CRITICAL severity is appropriate.
4. **Source documents are the T1 defence.** When source documents are passed to `run_grounding_check`, T1 issues reduce significantly because numeric claims can be verified against real brand material.

### Implementation

- Module: `src/validation/grounding_check.py`
- Market facts: `src/validation/market_facts/{client}.json`
- Tests: `tests/test_grounding_check.py`
- Protocol: `SIMULATTE_VALIDITY_PROTOCOL.md` — G12 row in Module 1 table + full T1/T2/T3 subsections

---

## Pre-Sprint Checklist

Before writing briefs for a new sprint:

- [ ] Read `src/taxonomy/schema.py` — note any field paths you'll reference
- [ ] Check `constraint_violations_report.json` — know the current population health
- [ ] Run `pytest tests/` — confirm the baseline is green before adding new code
- [ ] Read `README.md` in this Persona Generator folder — refresh context

---

## Pre-Demo Checklist

Before showing this to a client:

- [ ] Hard violation rate < 5%
- [ ] All 200 personas have narrative + first-person summary
- [ ] Full batch run completes with 0 errors
- [ ] Streamlit UI launches without ImportError
- [ ] Decision distribution is plausible (no single option > 85%)
- [ ] Top drivers are category-coherent
- [ ] WTP distribution is reasonable
- [ ] A/B test has been run and shows PASS

---

## Calibration Gates (Sprint C — Next Phase)

These gates apply before any population is delivered to a client or used for decision-making.

### Gate C1: Calibration Status Must Be Set
Every cohort envelope must have `calibration_state.status` set to a value other than `null`.
A cohort with `status: null` is incomplete and must not be delivered.

### Gate C2: Benchmark Calibration for New Domains
For any domain being run for the first time, benchmark anchoring (Method 1 from `references/calibration.md`) must be applied before delivery.
Required documentation: benchmark source, pre- and post-calibration conversion rates, adjustment applied.

### Gate C3: Conversion Rate Plausibility
Post-calibration simulated conversion rate must fall within:
- 2x the benchmark lower bound, OR
- 0.5x the benchmark upper bound
(i.e. for a benchmark of 2-8%, acceptable range is 1-16%)

If outside this range after 10 calibration iterations: flag as `CALIBRATION_FAILED` and document in delivery notes.

### Gate C4: Client Data Feedback Loop Trigger
If a client provides outcome data (even aggregate), the client cohort feedback loop (Method 2) must be applied before the next population delivery to that client.
The loop must run until KL divergence < 0.10 (soft) or < 0.05 (for insight-report deliveries).

### Gate C5: Calibration Age Check
Populations older than 6 months must be flagged as `stale_calibration` if reused.
Recommendation: recalibrate before reuse if market conditions have changed.
