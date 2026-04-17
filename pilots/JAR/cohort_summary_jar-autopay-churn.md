# Cohort Summary — JAR AutoPay Churn
## 8 Personas | Problem 1: Savings Habit Decay
**Generated: 2026-04-07**

---

```
COHORT SUMMARY — 8 personas, jar-autopay-churn
────────────────────────────────────────────────────────────────
Decision style distribution:
  Emotional  25% (pg-jar-001 Sunita, pg-jar-002 Ravi)
  Analytical 25% (pg-jar-006 Pradeep, pg-jar-008 Vikram)
  Habitual   37% (pg-jar-003 Kavitha, pg-jar-005 Arjun, pg-jar-007 Meena)
  Social     12% (pg-jar-004 Dinesh)

Trust anchor distribution:
  Family     38% (Sunita, Ravi, Meena)
  Peer       25% (Dinesh, Arjun)
  Authority  12% (Kavitha)
  Self       25% (Pradeep, Vikram)

Risk appetite:
  Low        38% (Sunita, Dinesh, Vikram)
  Medium     25% (Ravi, Pradeep)
  High       37% (Kavitha, Arjun, Meena — resilience type, not risk-seeking)

Primary value orientation:
  Price       50% (Sunita, Ravi, Dinesh, Meena)
  Quality     25% (Kavitha, Pradeep)
  Features    12% (Arjun)
  Convenience 12% (Vikram)

Consistency scores:
  Mean: 89 | Min: 78 (Vikram) | Max: 94 (Sunita, Ravi)

Notable clusters:
  (1) HABIT-ANCHORED RETAINERS: Kavitha, Meena, Arjun — retain via different mechanisms
      (routine, cultural obligation, streak identity) but share low habit_fragility.
      Collectively prove that retention is a mindset variable, not an income variable.
  (2) GOAL-DRIVEN RETAINERS: Ravi — single most retention-stable persona;
      goal specificity insulates against all shock types tested.
  (3) SOCIAL FRAGILE: Dinesh — retention is entirely outsourced to Raju;
      a high-probability churn cluster that looks stable but isn't.
  (4) IDENTITY SAVERS: Vikram — performative saving without roots;
      high income, first to exit when the identity narrative is disrupted.

Coverage gaps:
  - Northeast India / tribal community gold saving behavior not represented
  - Muslim-majority Tier 3 context (different gold cultural norms) absent
  - Female breadwinner in nuclear household (distinct from Kavitha's dual-income context) absent
  - Age 45–55 segment not covered (pre-retirement savers may have distinct shock responses)
────────────────────────────────────────────────────────────────
```

---

## Key Finding: The Churn Trigger Ranking

Across all 8 personas, churn probability per shock event:

| Shock Event | Mean Churn Probability | Highest-Risk Persona | Why It Ranks |
|---|---|---|---|
| **UPI Mandate Expiry** | 4.9/10 | Sunita (8/10), Dinesh (7/10) | Affects 6/8 personas meaningfully. Not a financial event — a pure UX/friction event. Jar has full control over this. |
| **Scam Narrative** | 4.0/10 | Sunita (9/10), Dinesh (8/10) | Socially transmitted, spreads through family and WhatsApp. Hardest for Jar to counter after it lands. |
| **Medical Expense** | 2.4/10 | Sunita (7/10) | Matters primarily when it coincides with mandate expiry or when AutoPay is already fragile |
| **Gold Price Drop 8%** | 2.1/10 | Vikram (7/10), Pradeep (3/10 rising) | Lower than expected; cultural gold trust buffers most personas. Key risk: sustained corrections |

**Critical insight:** The #1 churn trigger is a **product design problem** (UPI mandate friction), not a behavioral or financial problem. Jar controls it completely.

---

## Best Single Universal Intervention

**Flexible Pause ("Pause for 7 days — we'll restart automatically")**

Effective for 7/8 personas. Only Pradeep and Kavitha don't actively need it (and it doesn't harm them).

Why it works universally:
- Sunita: eliminates re-setup terror
- Ravi: prevents procrastination spiral during mandate expiry
- Dinesh: removes dependency on Raju for re-setup
- Arjun: works only if paired with "your streak will be preserved"
- Pradeep: useful during slow business season
- Meena: gold safety framing variant ("your gold is safe, take a break")
- Vikram: would have prevented his actual churn entirely

---

## The Income-Churn Paradox (Critical Business Finding)

| Persona | Income | Churn Risk |
|---|---|---|
| Meena | ₹9,500/month | Near-zero |
| Sunita | ₹12,000/month | Very high |
| Vikram | ₹48,000/month | Churned at day 67 |
| Kavitha | ₹42,000/month | Near-zero |

**Income is not a predictor of churn.** The real predictors, in order:

1. **habit_fragility** — how easily a disruption breaks the behavior
2. **savings_goal_specificity** — whether there's a named goal anchoring the behavior
3. **intrinsic_motivation** — whether saving is self-driven or externally triggered
4. **tech_setup_friction_sensitivity** — whether mandate re-setup is a barrier

These four variables should replace income-band as the segmentation axis for intervention targeting.

---

## Cohort Dominant Tensions

1. **Cultural gold trust (universal, high) vs. first-loss panic (universal, untested)** — every persona in this cohort carries cultural trust in gold that has never been tested by a real price correction. The volatility scenario (Problem 5) will reveal which of these eight personas holds and which breaks when that trust is first challenged.

2. **Income volatility reality vs. savings aspiration** — 6/8 personas face ±20–40% monthly income variance, yet all aspire to daily savings consistency. The gap between aspiration and cash flow reality is the structural driver of churn; no intervention addresses it directly except the flexible pause.

---

## Cohort Calibration State

```
calibration_state:
  status: uncalibrated
  method_applied: none
  params_source: proxy_estimated (CMIE, PRICE ICE 360°, RBI HFC Report, Play Store signals)
  benchmark_available: yes — Jar internal analytics (30/60/90 day retention rates)
  recommended_next_step: provide Jar's actual cohort churn curves by day-30/60/90 to
    calibrate switching_hazard.baseline_rate_per_period per segment. Even a single
    aggregate churn rate would allow intercept adjustment across all 8 personas.
```
