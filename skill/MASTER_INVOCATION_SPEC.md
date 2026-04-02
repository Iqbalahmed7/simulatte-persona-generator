---
name: Master Invocation Spec
description: >
  Defines the ICP (Ideal Customer Profile) Spec format that must be collected
  from the user before any persona generation begins. This is the authoritative
  source of truth for what inputs are required, what they mean, and how they
  shape persona output. Load this file at Step 0 of every persona-generator run.
type: spec
version: 1.0
---

# Master Invocation Spec — Persona Generator

This document defines exactly what kind of personas the generator must build,
what information is required to build them, and how to prompt the user to
provide it. Every persona generation session begins here.

---

## Purpose

Personas built without a grounded ICP are generic, not useful. The ICP Spec
forces the user to define *who* they are building personas for and *why* —
so every generated persona is anchored to a real business decision, not
demographic trivia.

---

## Invocation Protocol

When the skill is triggered, the generator must:

1. **Present** the ICP Spec template below to the user (formatted, fillable)
2. **Wait** for the user to return a completed spec
3. **Validate** the spec — flag missing required fields, ask for clarification
4. **Confirm** the extracted business context (Step 1) before generating

Do NOT begin generating personas until a completed ICP Spec has been received
and confirmed by the user. If the user pushes back or says "just go ahead",
ask for the minimum required fields only (marked `[REQUIRED]`).

---

## ICP Spec Template

Present this block verbatim when the skill initiates. Tell the user to fill
it in and return it. Markdown format works. Plain text is fine too.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PERSONA GENERATOR — ICP SPEC
  Fill in the fields below and send back.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 1. Business Context [REQUIRED]

  Brand / Product / Service:
  _______________________________________________

  What decision or behaviour are you trying to understand?
  (e.g. "why customers churn after 30 days", "how they choose
  between us and a competitor at point of purchase")
  _______________________________________________
  _______________________________________________

  What will you DO with these personas?
  (e.g. "brief a product team", "feed a simulation", "test messaging")
  _______________________________________________

## 2. Target Population [REQUIRED]

  Who are these people? Describe in plain language:
  (e.g. "urban Indian women 28-40 who buy organic food occasionally")
  _______________________________________________
  _______________________________________________

  Geography / Market:
  _______________________________________________

  Life stage / Household context (if relevant):
  _______________________________________________

## 3. Persona Spec

  Number of personas needed:   [ ] 3   [ ] 5   [ ] 10   [ ] Other: ___

  Mode:   [ ] Quick (default)   [ ] Deep   [ ] Simulation-Ready

  Should personas span the full spectrum (early adopters to laggards)?
  [ ] Yes — full spectrum     [ ] No — focus on: _______________

  Any persona types you specifically WANT included?
  (e.g. "must have one price-sensitive persona", "include a churned user")
  _______________________________________________

  Any persona types you want EXCLUDED?
  _______________________________________________

## 4. Anchor Traits (optional but powerful)

  Are there specific psychographic or behavioural traits
  that MUST appear across all or some personas?
  (e.g. "high digital literacy", "strong family orientation", "distrust of brands")
  _______________________________________________

  Are there known segments or clusters you want represented?
  _______________________________________________

## 5. Domain Data (optional — but unlocks Grounded Mode)

  Paste any raw material below OR describe where to find it.
  Providing domain data switches the generator to Grounded Mode,
  which produces empirically-grounded behavioural parameters
  instead of LLM-inferred trait labels.

  WHAT TO PROVIDE (any of the following):
  - Customer reviews (copy-paste from App Store, Amazon, G2, Trustpilot)
  - Forum posts (Reddit threads, community discussions)
  - Interview transcripts or survey verbatims
  - Support tickets or NPS comments
  - Any text written BY your target users about this decision

  WHAT THE SYSTEM EXTRACTS FROM IT:
  - Purchase triggers (what made people buy)
  - Rejection signals (what made people not buy / churn)
  - Trust source citations (who/what influenced their decision)
  - Price sensitivity signals (how much price language appears)
  - Switching events (what drove people to competitors)

  IF NO DOMAIN DATA IS AVAILABLE:
  Describe where to find it and the system will suggest the
  minimum viable data set for this domain.
  Or leave blank — the system will use proxy estimation and
  mark behavioural parameters as estimated, not grounded.

  [Paste or describe data below this line]
  _______________________________________________

## 6. Output Preferences

  Format:   [ ] JSON + summary cards (default)   [ ] Cards only   [ ] JSON only

  Save location:   [ ] Current directory   [ ] Specify: _______________

  Language / cultural register for narratives:
  _______________________________________________

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Validation Rules

After receiving the completed spec, check the following before proceeding:

| Field | Rule |
|-------|------|
| Brand / Product | Must be specific enough to imply a domain |
| Decision/Behaviour | Must describe a human action or choice, not a metric |
| Target Population | Must name real demographic attributes, not just "our users" |
| Number of personas | Must be ≥ 3 for cohort diversity checks to be meaningful |
| Mode | Default to Quick if not specified |
| Domain data | If provided, switch to Deep mode automatically |

If the user provides fewer than the minimum required fields, respond with:

```
I need a bit more to get started. Can you confirm:
1. [Missing required field 1]
2. [Missing required field 2]

Everything else I can infer or default — just these two will unlock generation.
```

---

## Persona Type Definitions

The following types should be represented across any cohort of 5+ personas.
Use these to guide demographic and psychographic sampling, not as rigid boxes.

| Type | Description | Key signal |
|------|-------------|------------|
| **The Pragmatist** | Decides on utility and price. Minimises friction. | Low brand loyalty, high price sensitivity |
| **The Loyalist** | Has established habits; resistant to switching. | High consistency score, habitual decision style |
| **The Aspirant** | Purchases toward an identity they want, not who they are. | Gap between self-concept and current behaviour |
| **The Anxious Optimizer** | Over-researches. Delays decisions. Seeks certainty. | High analytical style, low risk appetite |
| **The Social Validator** | Won't act without peer signal. Word of mouth is the key. | Trust anchor: peer, social decision style |
| **The Value Rebel** | Rejects mainstream options on principle or identity grounds. | Counter-cultural values, high independence |
| **The Reluctant User** | Uses the product/service but wishes they didn't have to. | Low satisfaction, moderate-high churn risk |
| **The Power User** | Deeply engaged; evangelises; pushes product limits. | High feature orientation, high consistency score |

A well-formed cohort of 5 personas should contain at least 4 distinct types.
A cohort of 10 should span all 8. Flag gaps in the cohort review (Step 5).

---

## Persona Depth Standards

Every persona generated under this spec must meet the following minimums:

- **Life story specificity**: Named events, real ages, plausible places — no generics
- **Attribute coherence**: No contradictions between economic constraints and aspirational behaviour without an explicit tension noted
- **Cultural texture**: Language, references, and daily-life details drawn from the stated geography and demographic
- **Decision anchoring**: Every persona's decision bullets must map directly to the stated business decision in the ICP Spec
- **Tension requirement**: Every persona must carry at least one internal contradiction — a value they hold that conflicts with a behaviour they exhibit

---

## How This Spec Shapes Generation

| Spec field | How it is used |
|------------|----------------|
| Business Context → Decision | Becomes the lens for all decision bullets |
| Target Population | Seeds demographic anchor sampling (Step 3a) |
| Anchor traits | Forced attributes in taxonomy (Step 3c) |
| Domain data | Drives taxonomy construction in Deep Mode (Step 2) |
| Persona types specified | Overrides free sampling; forces inclusion |
| Mode | Controls taxonomy depth and memory output |
| Output preferences | Controls Step 6 file format and save location |

---

## Versioning

When the ICP Spec is received, save a copy alongside the output files as:
`icp_spec_[domain]_[timestamp].md`

This preserves the generation context and allows the run to be reproduced or
extended in future sessions.
