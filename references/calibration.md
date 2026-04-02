# Calibration Layer — Reference

## Purpose

Calibration is the mechanism that connects simulated persona behaviour to real-world outcome data. Without calibration, a persona population can produce plausible-sounding outputs that are systematically wrong — e.g. 80% simulated conversion in a category where real conversion is 5%.

**What calibration does:**
- Compares simulated aggregate outcomes against real-world benchmarks or client data
- Identifies which persona segments are over- or under-performing relative to reality
- Adjusts behavioural parameters to bring simulated outputs within empirically-grounded ranges

**What calibration does NOT do:**
- Does not modify individual persona narratives or psychographic attributes
- Does not make every persona "accurate" — only the population aggregate
- Does not replace the need for domain data in the grounding pipeline

---

## Calibration Methods

### Method 1: Benchmark Anchoring

**Use when:** No client outcome data is available.
**Reliability:** Weak — catches gross errors but cannot fine-tune
**When to apply:** Before every population delivery in a new domain

#### Step 1: Set Benchmark Targets

Select the appropriate benchmarks for the domain being simulated:

| Domain | Metric | Benchmark Range | Source |
|--------|--------|----------------|--------|
| B2B SaaS | Free-to-paid conversion | 2–8% | Mixpanel PLG Report |
| B2B SaaS | Monthly logo churn | 2–8% | Recurly Subscription Economy Index |
| B2B SaaS | Annual net revenue retention | 100–130% | OpenView SaaS Benchmarks |
| Consumer subscription | Monthly churn | 3–10% | Recurly |
| E-commerce (general) | Cart-to-purchase conversion | 2–4% | Shopify Benchmarks |
| E-commerce | Repeat purchase rate (90-day) | 25–40% | Klaviyo E-commerce Benchmarks |
| Mobile app (freemium) | Day-7 retention | 15–25% | Amplitude Mobile Benchmarks |
| Mobile app (freemium) | Free-to-paid conversion | 1–5% | Various |
| FMCG first purchase | Trial conversion | 5–15% | Nielsen / Kantar (category-dependent) |
| Child nutrition India | Trial after 5 stimuli | 60–80% | Validated in LittleJoys Pilot 1 |

If the domain does not appear in this table, search for a relevant industry report before proceeding. Do not use a benchmark from an adjacent category without flagging the approximation.

#### Step 2: Run Population Simulation

Run the persona population through a standard scenario (or the client's scenario if available). Record:
- Simulated conversion rate (buy + trial / total)
- Simulated churn rate (for scenarios with a time dimension)
- Simulated WTP distribution (mean, median, P10, P90)

#### Step 3: Compute Divergence

```
conversion_gap = simulated_rate - benchmark_midpoint
churn_gap      = simulated_rate - benchmark_midpoint

If |conversion_gap| > 0.10 (10 percentage points): CALIBRATION REQUIRED
If |churn_gap| > 0.05:                              CALIBRATION REQUIRED
Otherwise:                                           WITHIN TOLERANCE
```

#### Step 4: Apply Intercept Adjustment

When conversion is out of range, adjust the `purchase_prob.intercept` (β₀) across the population:

```
Adjustment direction:
  simulated > benchmark upper bound → reduce β₀ by δ
  simulated < benchmark lower bound → raise β₀ by δ

Adjustment size: δ = 0.05 per iteration
Maximum iterations: 10
Stop when: simulated rate falls within benchmark range
           OR iterations exhausted (flag as CALIBRATION_FAILED)

Apply adjustment uniformly across all personas in the population.
Store as: cohort.calibration_state.intercept_adjustment = δ_total
```

#### Step 5: Document the Calibration

```json
{
  "calibration_method": "benchmark_anchoring",
  "benchmark_source": "Mixpanel PLG Report 2025",
  "benchmark_target": { "low": 0.02, "high": 0.08 },
  "pre_calibration_rate": 0.23,
  "post_calibration_rate": 0.06,
  "iterations": 7,
  "intercept_adjustment_applied": -0.35,
  "status": "CALIBRATED | WITHIN_TOLERANCE | CALIBRATION_FAILED"
}
```

---

### Method 2: Client Cohort Feedback Loop

**Use when:** Client provides aggregate outcome data (even just headline numbers)
**Reliability:** Medium-to-strong depending on data richness
**When to apply:** For any returning client or any engagement with real outcome data

#### Input Required (minimum)

The client must provide at least one of:
- Aggregate conversion rate (e.g. "our free-to-paid is 4.8%")
- Aggregate monthly churn (e.g. "we lose about 5% of subscribers per month")
- Decision distribution (e.g. "about 30% buy immediately, 40% defer, 30% never convert")

Individual-level data (if available) improves accuracy but is not required.

#### Step 1: Map Client Segments to Persona Segments

Create a segment correspondence table:
```
Client segment → Persona segment
"churned in month 1" → personas with switching_hazard.baseline_rate > 0.08
"converted from free trial" → personas with purchase_prob.baseline_at_ask_price > 0.50
"never converted" → personas with purchase_prob.baseline_at_ask_price < 0.25
```

#### Step 2: Run Simulation and Extract Segment Rates

Run the full population through the client's scenario. Compute per-segment rates:
```
for each persona_segment:
  simulated_rate = count(target_decision) / count(segment_total)
  client_rate    = [from client data or interpolated]
  divergence     = |simulated_rate - client_rate|
```

#### Step 3: Compute KL Divergence

```
KL_divergence = sum over all segments of:
  client_rate * log(client_rate / simulated_rate)

If KL_divergence < 0.05:  ACCEPTABLE — no adjustment needed
If KL_divergence 0.05–0.20: MINOR CALIBRATION — adjust over-performing segments
If KL_divergence > 0.20:  MAJOR CALIBRATION — systematic parameter adjustment needed
```

#### Step 4: Attribution and Adjustment

Identify which segment is driving divergence:
- Over-converting segments: reduce `purchase_prob.intercept` by δ = 0.05
- Under-churning segments: reduce `switching_hazard.baseline_rate_per_period` by δ = 0.005
- Under-converting segments: raise `purchase_prob.intercept` by δ = 0.05

Apply per segment, not globally. This preserves inter-segment differentiation.

Iterate until KL divergence < 0.05 or plateau (< 0.01 improvement over 3 iterations).

#### Step 5: Document and Store

```json
{
  "calibration_method": "client_cohort_feedback",
  "client_data_provided": ["aggregate_conversion_rate", "aggregate_churn"],
  "pre_calibration_kl_divergence": 0.18,
  "post_calibration_kl_divergence": 0.04,
  "iterations": 4,
  "segments_adjusted": ["high_intent", "price_sensitive"],
  "status": "CALIBRATED"
}
```

---

## When to Recalibrate

Calibration is not permanent. Recalibrate when:
- A new domain is added (always start with benchmark anchoring)
- Client provides new outcome data
- More than 6 months have passed since last calibration
- Simulated outputs diverge from client expectations by > 15 percentage points
- A major schema change is made to `behavioural_params`

---

## Calibration State in Schema

The cohort envelope (see `references/output_schema.md`) carries a `calibration_state` block:

```json
{
  "calibration_state": {
    "status": "uncalibrated | benchmark_calibrated | client_calibrated | calibration_failed",
    "method_applied": "benchmark_anchoring | client_cohort_feedback | none",
    "last_calibrated": "ISO datetime | null",
    "benchmark_source": "string | null",
    "pre_calibration_metrics": {
      "conversion_rate": null,
      "churn_rate": null,
      "kl_divergence": null
    },
    "post_calibration_metrics": {
      "conversion_rate": null,
      "churn_rate": null,
      "kl_divergence": null
    },
    "intercept_adjustment_applied": null,
    "segments_adjusted": [],
    "notes": "string | null"
  }
}
```

The `status` field must be set at generation time:
- New population: `uncalibrated`
- After benchmark anchoring: `benchmark_calibrated`
- After client feedback loop: `client_calibrated`
- If calibration failed to converge: `calibration_failed`

---

## What Calibration Cannot Fix

Be explicit with clients about calibration limits:

1. **It calibrates population aggregates, not individual persona accuracy.** A calibrated population will have the right conversion rate, but any individual persona may still be "wrong" about their decision.

2. **It cannot fix a broken taxonomy.** If the attribute taxonomy doesn't capture the real differentiators in a market, calibrating the behavioural parameters won't help — the wrong things are being measured.

3. **It cannot compensate for missing segments.** If the persona population doesn't include a segment that represents 30% of the real market, calibration will try to over-weight the segments that are present.

4. **Benchmark calibration is weak by design.** Industry benchmarks are averages across many companies and contexts. A specific client's situation may legitimately differ. Use benchmark calibration as a sanity check, not as a ground truth.

5. **Calibration drift.** Markets change. A calibration from 12 months ago may be meaningfully wrong today. Track calibration age.
