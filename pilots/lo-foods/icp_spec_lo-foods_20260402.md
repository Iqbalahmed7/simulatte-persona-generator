---
preserved_at: 2026-04-02
generator_run: cohort-lo-foods-20260402
output_file: personas_lo_foods_20260402.json
---

# ICP Spec — Lo! Foods Persona Generation Run
## Preserved copy for reproducibility

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERSONA GENERATOR — ICP SPEC (PRE-FILLED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 1. Business Context

Brand / Product / Service:
Lo! Foods (India)

What decision or behaviour are you trying to understand?

- Why users are not repeating purchase (habit formation problem)
- Whether Lo! can move from keto niche to mainstream protein category
- Price sensitivity vs perceived value across segments
- Trust formation: doctor vs influencer vs brand
- Channel behavior: Amazon vs quick commerce vs D2C
- Product adoption barriers: taste, shelf-life, awareness
- Segment expansion beyond niche users

What will you DO with these personas?

- Feed into a behavioral simulation engine
- Run scenario-based experiments (pricing, messaging, GTM)
- Generate decision insights for product and growth strategy

---

## 2. Target Population

Who are these people?

Urban and semi-urban Indian consumers (age 22–50) interacting with health-oriented food products including:
- Keto / low-carb users
- Fitness / protein-conscious users
- Diabetic or caregiver households
- Health-conscious family grocery buyers
- Quick-commerce driven urban consumers

Geography / Market:
India (primary focus: Tier 1 + Tier 2 cities)

Life stage / Household context:
- Singles (young professionals)
- Married couples
- Families with children
- Caregiver households (diabetes context)

---

## 3. Persona Spec

Number of personas needed: 500

Mode: Simulation-Ready

Should personas span full spectrum:
Yes — include early adopters, mainstream users, and resistant users

Must include:
- Price-sensitive users
- Loyal keto users
- Diabetic trust-driven users
- Churn-risk users
- Quick-commerce impulse users

Exclude:
- Rural offline-only consumers with no digital exposure

---

## 4. Anchor Traits

Must appear across population:

- Mix of high and low health_goal_intensity
- Variation in trust_anchor (doctor, influencer, peer, label, brand)
- Mix of high and low budget sensitivity
- Mix of high and low habit stickiness

Known segments:

- Keto loyalists
- Protein explorers
- Diabetic / caregiver decision makers
- Health-conscious family shoppers
- Quick-commerce impulse buyers
- Gluten-free niche users

---

## 5. Domain Data

Use general knowledge of:
- Indian D2C food behavior
- Amazon and quick commerce buying behavior
- Health, fitness, diabetes, and diet-driven consumption patterns

No external data provided — infer realistically.

---

## 6. Output Preferences

Format: JSON only

Language: Indian English (neutral, not overly stylized)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Generation Parameters

Cohort sizes:
- keto_loyalist:      75
- protein_fitness:   120
- diabetic_caregiver: 80
- family_shopper:    100
- impulse_buyer:      75
- gluten_free:        30
- churn_risk:         20
- TOTAL:             500

Constraint rules enforced: 13
Hard violations in output: 0
Consistency score range: 74–97 (mean 88)
All personas above threshold (≥60): 100%

To reproduce: run generate_personas.py with random.seed(42)
