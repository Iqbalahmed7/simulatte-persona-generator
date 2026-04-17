---
name: JAR AutoPay Churn — ICP Spec
description: Invocation spec for Problem 1 persona generation — Savings Habit Decay & AutoPay Churn
type: icp_spec
domain: jar-autopay-churn
generated_at: 2026-04-07T00:00:00Z
---

# ICP Spec — JAR Savings Habit Decay & AutoPay Churn

## 1. Business Context

**Brand / Product:** Jar — Indian fintech app, digital gold savings via UPI AutoPay

**Decision / Behaviour:** Why do first-time savers lapse after 30–60 days, and which intervention prevents permanent churn? Focus on the 12-month savings journey from first AutoPay setup to either sustained habit or permanent exit.

**Use of personas:** Feed a simulation engine testing 5 retention interventions against 4 shock events. Also brief Jar's product and growth teams on intervention design.

## 2. Target Population

**Who:** Indian adults 18–45, monthly income ₹10K–50K, Tier 2/3 cities. 95% first-time formal savers with no prior investment experience. UPI-enabled smartphone users.

**Geography:** Tier 2 cities (pop. 1–10 lakh) and Tier 3 cities (pop. <1 lakh). 60% of Jar's actual user base is from this segment.

**Life stage:** Young singles 18–25 / Early family 26–35 / Established 36–45. Family financial interdependence is high — income is shared or claimed by household obligations.

## 3. Persona Spec

**Number:** 8

**Mode:** Deep + Simulation-Ready

**Spectrum:** Not full spectrum — focused on the churn-vulnerable population (first-time savers, 0–180 day range). Edge cases included to test income-doesn't-predict-churn hypothesis.

**Required types:**
1. Fragile Starters — ₹10–20K, Tier 3, first-time saver
2. Aspirational Disciplined — ₹20–35K, Tier 2, goal-oriented
3. Habit-Formed Savers — ₹35–50K, Tier 2, 90+ day streak
4. Socially-Anchored — any income, peer-driven adoption
5. Gamification-Responsive — 18–25, streak identity
6. Price-Sensitive Rationalist — ₹20–40K, investment mindset
7. Edge Case A — Persistent non-churner at ₹10K income
8. Edge Case B — High-income churner at ₹45–50K

## 4. Anchor Traits

**All personas must:**
- Reflect Tier 2/3 India income volatility (±20–35% monthly variance per CMIE)
- Hold at least one behavioral contradiction (cultural gold trust + first-loss anxiety)
- Encode decision logic under 4 specific shock events
- Map responses to 5 specific retention interventions

**Forced behavioral parameter:** habit_fragility must vary dramatically across personas — this is the primary segmentation variable.

## 5. Domain Data

No raw domain data provided. Behavioral parameters calibrated as proxy_estimated using:
- CMIE Consumer Pyramids (income volatility, expense shock frequency)
- PRICE ICE 360° Survey (savings aspiration vs. behavior gap)
- RBI Household Finance Committee Report (gold % of household wealth, risk tolerance)
- Google Play Store reviews — Jar app, 1–3 star (churn language, real friction signals)
- NPCI Annual Report (UPI AutoPay mandate failure rates)

All behavioural_params marked as source: "proxy_estimated" until client data is provided for calibration.

## 6. Output Preferences

**Format:** JSON cohort array + markdown summary cards + cohort summary
**Save location:** /Users/admin/Documents/Simulatte Projects/Persona Generator/pilots/JAR/
**Language register:** Hindi-inflected English for narratives; Tier 2/3 India cultural register
