# Persona Generator — Skill Specification

This document defines what the Persona Generator Claude skill does, what it takes as input, and what it returns. This is the north star for where the system is heading.

---

## What the Skill Does

When invoked, the skill:

1. Takes a client brief (product, target market, category, geography)
2. Generates a psychologically grounded population of N personas
3. Optionally: runs a stimulus set through the population
4. Returns: a population file + (optionally) a scenario results report

---

## Invocation

```
/persona-generator
  --client "LittleJoys"
  --category "child nutrition"
  --market "urban India, Tier 1-2 cities"
  --n 200
  --run-scenario true
```

Or conversationally:
> "Generate 50 personas for a B2B SaaS targeting HR managers in mid-size Indian tech companies, then run the product demo sequence through them."

---

## Inputs

### Required
| Input | Description |
|---|---|
| Category | What product/service is this for? |
| Market | Who is the target consumer? (geography, demographics, context) |
| N | How many personas to generate? |

### Optional
| Input | Description |
|---|---|
| Stimulus set | Up to 5 stimuli to run through the population |
| Decision scenario | The purchase moment to simulate |
| Seed | For reproducibility |
| Constraints | Any hard rules the personas must satisfy |

---

## Outputs

### Always
- `personas.json` — the full population, validated, constraint-checked
- `population_summary.md` — distribution of key attributes across the population

### When scenario is run
- `scenario_results.json` — per-persona decisions, reasoning traces, WTP
- `insights_report.md` — decision distribution, top drivers, top objections, segment profiles

---

## Quality Standards

A population is not ready to use until:
- Hard violation rate < 5% (psychological anti-correlations enforced)
- All personas have narrative + first-person summary
- All personas have episodic memory bootstrapped (at least 3 seed memories)
- Constraint checker passes on all included personas

---

## The Three Modes

### Mode 1: Population Only
Generate N personas. Validate them. Return the population file.
Use case: Client wants the population to use in their own tools, or for qualitative reading.

### Mode 2: Population + Scenario
Generate the population, then run a provided stimulus set and decision scenario through all personas.
Use case: Client wants quantitative output — decision distributions, WTP, drivers.

### Mode 3: Insight Report
Mode 2 + automatic segmentation and insight extraction.
Use case: Client wants a deliverable they can act on immediately.

---

## What Makes a Good Persona Population

### Diversity requirements
- At least 3 age brackets represented
- Geographic spread (Tier 1 / Tier 2 / Tier 3 for India; equivalent for other markets)
- Income range representation
- Family structure variety
- Gender balance appropriate to category

### Psychological spread
- No single value dominating — the population should cover the full range of each psychological dimension
- Anti-correlations enforced (high risk tolerance cannot coexist with extreme loss aversion, etc.)
- Trust anchor variety — not all personas should trust the same source type

### Coherence requirements
- Each persona's psychology, values, and demographics must be internally consistent
- The narrative and first-person summary must match the attribute profile
- No field defaults left in (e.g. work_hours_per_week = 0 for a full-time employee)

---

## Generalisation Checklist (for new categories)

Before running the skill for a new category, confirm:

- [ ] The 5 most decision-relevant psychological attributes are identified
- [ ] Trust anchors are defined for this category (who does this consumer listen to?)
- [ ] At least 3 anti-correlation pairs are identified and added as constraints
- [ ] A realistic 5-stimulus sequence is defined (one per major channel)
- [ ] A realistic decision scenario is defined (the actual purchase moment)
- [ ] The Tier 1 generator schema includes category-specific attributes

---

## Known Limitations (current)

- Single-tick only: personas are run through stimuli sequentially, not over simulated time
- No WOM propagation: personas don't influence each other yet
- No competitive simulation: all stimuli are for one brand at a time
- India-first: demographic defaults and trust patterns are calibrated for Indian consumers
- 200 persona cap: larger populations not yet tested for performance

These are the Sprint 30+ roadmap items.

---

## Next-Phase Architecture (Sprint A/B/C)

The following capabilities are being added in the next phase. Reference documents exist for each.

### Grounded Mode (Sprint A + B)

When domain data is provided in the ICP Spec, the skill operates in Grounded Mode:
- Signal extraction runs before taxonomy construction (Step 1b)
- Behavioural parameters are estimated from data, not inferred from attributes
- The `behavioural_params` block is populated with `source: "cluster_estimated"`
- Personas have purchase probability surfaces, not point-estimate WTP

Reference: `references/behavioural_grounding.md`, `references/data_grounding.md`

### Calibration (Sprint C)

Before any population is delivered, benchmark calibration is applied:
- Simulated conversion rate is compared against domain benchmarks
- `purchase_prob.intercept` is adjusted until population output is within range
- Calibration state is recorded in the cohort envelope

When client outcome data is available, the client cohort feedback loop runs:
- KL divergence between simulated and real outcome distributions is computed
- Per-segment parameter adjustments are applied iteratively

Reference: `references/calibration.md`

### Mode Hierarchy (updated)

| Mode | When | What changes |
|------|------|-------------|
| Quick | Default, ≤ 5 personas | Proxy behavioural params, no calibration |
| Deep | ≥ 10 personas or domain data | Data-grounded behavioural params, benchmark calibration |
| Grounded | Domain data + calibration required | Cluster-estimated params, both calibration methods |
| Simulation-Ready | Any mode + simulation flag | Full memory schema, grounded params preferred |
