# Persona Quality Roadmap
## From Archetype to Adaptive Cognition

**Last updated:** 2026-05-08  
**Status:** Living document — updated as layers ship

---

## The Benchmark

> "I don't just understand this person. I can predict how they'll evolve."

That's the line between a persona and a computational model of human behaviour.
Simulatte's current output is already beyond static demographics and agency psychographics.
This document maps every layer — built, building, and planned — against that benchmark.

---

## What's Built Today

### Layer 1 — Demographic Anchor
**Status:** ✅ Shipped

The factual skeleton. Age, gender, life stage, city/country, education, occupation,
household size and composition, income band. Extracted from the user's brief or
inferred by the LLM.

*What it enables:* Segmentation validity. The person exists in a real coordinate of
the world.

*Limitation:* Pure description. Says nothing about how they think, feel, or behave.

---

### Layer 2 — Narrative Identity
**Status:** ✅ Shipped

Two narrative voices:
- **Third-person** — who they are, daily life, values (3–4 sentences)
- **First-person** — how they'd describe themselves (2–3 sentences)

*What it enables:* Chat mode has a voice to embody. The persona becomes readable to
a human viewer in seconds.

*Limitation:* Still a fixed description. The person is explained, not simulated.

---

### Layer 3 — Derived Insights
**Status:** ✅ Shipped

Structured psychological signals:
- `decision_style` — analytical / emotional / habitual / social
- `primary_value_orientation` — price / quality / brand / convenience / features
- `trust_anchor` — self / peer / authority / family
- `risk_appetite` — low / moderate / high
- `consistency_score` — integer 60–95 (how predictable their behaviour is)
- `key_tensions` — 3 internal conflicts
- `coping_mechanism` — type + one-sentence description

*What it enables:* The probe and chat modes use these to calibrate responses.
Probes use `trust_anchor` and `risk_appetite` directly in scoring. Chat mode uses
`decision_style` and `key_tensions` to make conversations feel real.

*Limitation:* These are labels, not behaviour generators. They describe the system
without modelling its dynamics.

---

### Layer 4 — Behavioural Tendencies
**Status:** ✅ Shipped

Four structured sub-fields:
- `trust_orientation` — scored 0–1 across brands / peers / experts / institutions
- `price_sensitivity` — band (budget → luxury) + one-sentence description
- `switching_propensity` — likelihood + triggers
- `objection_profile` — 3 typed objections with likelihood, severity, and description
- `reasoning_prompt` — one sentence on how they reason through decisions

*What it enables:* Probes get specific, grounded objection content. Trust bars on
the profile page give at-a-glance signal. The reasoning prompt seeds chat mode
decision sequences.

*Limitation:* Still static. Does not adapt to context, pressure, or the social
environment the person is in.

---

### Layer 5 — Decision Bullets
**Status:** ✅ Shipped

5 specific, domain-relevant bullets on how this persona approaches decisions.
Generated with awareness of the domain context (CPG / SaaS / Health & Wellness).

*What it enables:* Rapid orientation for anyone reading the persona. Useful for
pitching the persona to a client team.

---

### Layer 6 — Memory Core
**Status:** ✅ Shipped

Deep identity substrate:
- `identity_statement` — 2-sentence first-person core self
- `key_values` — 4 values
- `life_defining_events` — 3 formative events
- `relationship_map` — partner / family / community
- `immutable_constraints` — 2 hard limits on their behaviour
- `tendency_summary` — one sentence on dominant behavioural pattern

*What it enables:* Chat mode has a stable self-model to draw on across long
conversations. The persona doesn't drift or forget who they are.

---

### Layer 7 — Life Stories
**Status:** ✅ Shipped

3 narrative episodes with title, 3–4 sentence narrative, age at event, and
emotional weight (formative / pivotal / minor / traumatic / joyful).

*What it enables:* The chat mode can reference specific episodes when they're
relevant. Probes can draw on formative experiences to explain brand relationships.
The profile page gives viewers a sense of lived experience.

---

### Layer 8 — Behavioural Contradictions
**Status:** ✅ Shipped (2026-05-08 — Priority 1)

3 specific, observable behaviours that contradict the persona's self-image:
1. A self-image contradiction — something concrete and slightly unflattering
2. An irrational exception to their usual decision logic
3. A status or comfort behaviour they'd be embarrassed to articulate

*What it enables:* The persona stops feeling like a therapy report and starts feeling
like a real person. Chat conversations can surface these without prompting.
Contradictions are where human authenticity lives.

*Design principle:* These are not internal tensions (Layer 3 already covers that).
They are observable, external behaviours. Specific enough to be surprising.

---

### Layer 9 — Quality Assessment
**Status:** ✅ Shipped

System-computed score across completeness, internal consistency, and behavioural
specificity. Surfaced as a chip on the profile page.

---

## Being Built Now

### Layer 10 — Symbolic Meaning System
**Status:** 🔨 In progress (2026-05-08 — Priority 2)

The single largest gap in current persona quality.

Humans don't buy products. They buy symbols, emotional futures, identity repair,
status camouflage, and belonging. A persona that only models functional reasoning
(price / quality / trust) misses the deepest layer of consumer motivation.

**Schema: `symbolic_meanings`**

A structured map of what product categories *mean* to this person — not what they
think about them, but what they represent symbolically.

```json
"symbolic_meanings": {
  "core_symbolic_register": "<one sentence — the primary symbolic logic this person operates from when consuming>",
  "category_meanings": [
    {
      "category": "<product/service category>",
      "functional_story": "<what they tell themselves they're buying>",
      "symbolic_story": "<what they're actually buying at a psychological level>",
      "identity_signal": "<what owning/using this says about who they are or are becoming>"
    }
  ],
  "purchase_as_ritual": "<one sentence — how buying functions as emotional regulation or identity maintenance for this person>",
  "brand_meaning_filter": "<one sentence — the test a brand must pass to feel right to them, beyond product fit>"
}
```

*What it enables:*
- Probes surface *symbolic* purchase intent, not just functional intent
- Branding recommendations become identity-level, not feature-level
- Chat mode can explain *why* she's drawn to something she can't rationally justify
- Luxury, wellness, CPG use cases unlock their deepest value

*Why this is the highest-ROI next layer:*  
Every other layer improves the persona. This one directly improves the probe output
that buyers are paying for. No survey can produce symbolic meaning data at this
resolution. This is Simulatte's moat.

---

## Planned — Next 60 Days

### Layer 11 — Multi-Layered Self
**Status:** 📋 Planned (Priority 3)

Humans are not one coherent personality. They operate across multiple self-models
simultaneously, often in tension with each other.

**Schema: `self_model`**

| Layer | Description |
|-------|-------------|
| `public_self` | Who they present to the world |
| `aspirational_self` | Who they're trying to become |
| `reactive_self` | Who they become under stress or threat |
| `shame_self` | The behaviours and drives they hide or deny |
| `fantasy_self` | The life they'd live if freed from constraints |

*What it enables:*  
Chat mode becomes uncanny. The gap between public self and shame self is where the
most truthful conversations happen. Probes can distinguish aspirational purchase
intent from reactive purchase intent — two very different things.

---

### Layer 12 — State Modifiers
**Status:** 📋 Planned (Priority 4)

Behaviour is not fixed — it shifts with internal state. A calm, intentional
Vanessa and a sleep-deprived, lonely Vanessa make different decisions.

**Schema: `state_modifiers`**

3–4 named states with behaviour-shift descriptions:
- `baseline` — default operating mode
- `stressed` — under work, financial, or social pressure
- `lonely_or_disconnected` — socially depleted state
- `socially_threatened` — triggered by comparison or status challenge
- `burned_out` — emotional and cognitive depletion

Each state includes: trigger conditions, behaviour shifts, purchase implications,
what they become in this state.

*What it enables:*  
Probes can be run "in state" — e.g. "how does Vanessa respond to this product when
she's socially threatened?" That's a fundamentally different research capability.
Chat mode can detect state drift in conversation and adapt.

---

### Layer 13 — Social Topology
**Status:** 📋 Planned (Priority 5)

Identity is relational, not isolated. Vanessa behaves differently around different
people, and those differences reveal more about her than her stated self does.

**Schema: `social_map`**

- `admiration_hierarchy` — who she looks up to and why
- `resentment_hierarchy` — who she envies or resents and what that reveals
- `aspiration_ladder` — the social position she's oriented toward
- `tribe_signals` — how she identifies her in-group
- `class_anxiety` — where she sits vs. where she thinks she sits
- `status_camouflage` — how she signals status without appearing to signal status
- `belonging_behaviour` — what she does to feel included

*What it enables:*  
Marketing targeting becomes relational, not demographic. Brand positioning can map
to aspirational social positions, not just stated preferences. Qualitative research
simulations become far richer.

---

### Layer 14 — Pressure Behaviour
**Status:** 📋 Planned (Priority 6)

Real humans are most revealing at the edge of stability. How does this persona
behave when the world shifts under them?

**Schema: `pressure_profile`**

Scenarios: recession, relationship collapse, public embarrassment, health scare,
job loss, social rejection, cultural trend shift.

For each: what values collapse first, what behaviours become irrational, what
coping systems emerge, what identity fragments, what gets emotionally defended.

*What it enables:*  
Resilience planning, crisis communication, brand loyalty stress-testing.
A brand can ask: if Vanessa loses her income, does she abandon us or do we become
more important to her? That's a genuinely novel research question.

---

## Architectural Horizon — 6–12 Months

### Layer 15 — Primitive Drives
Beneath articulated identity: mating psychology, dominance, envy, shame,
attraction, scarcity fear, aging anxiety. These often conflict directly with
conscious identity. The contradiction is humanity.

*Implementation note:* Requires careful framing to avoid sensitivity issues in
LLM generation. The contradiction layer (Layer 8) approaches this obliquely,
which is the safer path for now.

---

### Layer 16 — Memory Evolution
Personas that update when given new experience inputs. A persona who has been in
a secure relationship for 2 years looks different from the same persona at baseline.

*Implementation note:* Requires stateful persona architecture — a platform feature,
not a generation feature. Not buildable in the current SSE pipeline.

---

### Layer 17 — Environmental Adaptation
The same persona in Austin vs NYC vs rural Italy becomes meaningfully different.
Dynamic adaptation to geographic, cultural, and socioeconomic context shifts.

---

### Layer 18 — Unconscious Behaviour
The persona sometimes acts before reasoning, then rationalises. Misunderstands
itself. Emotionally rewrites memory. This layer emerges most naturally from
sophisticated chat interactions drawing on Layers 8, 11, and 12 — not from
explicit schema additions.

---

## Current Persona Score

| Layer | Status | Impact |
|-------|--------|--------|
| Demographic Anchor | ✅ | Baseline |
| Narrative Identity | ✅ | High |
| Derived Insights | ✅ | High |
| Behavioural Tendencies | ✅ | High |
| Decision Bullets | ✅ | Medium |
| Memory Core | ✅ | High |
| Life Stories | ✅ | High |
| Behavioural Contradictions | ✅ | Very High |
| Quality Assessment | ✅ | Medium |
| Symbolic Meaning System | ✅ | Very High |
| **Multi-Layered Self** | **✅** | **Very High** |
| State Modifiers | 📋 Planned | High |
| Social Topology | 📋 Planned | High |
| Pressure Behaviour | 📋 Planned | High |
| Primitive Drives | 📋 Horizon | Medium* |
| Memory Evolution | 📋 Horizon | Very High* |
| Environmental Adaptation | 📋 Horizon | High* |
| Unconscious Behaviour | 📋 Horizon | Very High* |

*Horizon items rated on eventual impact, not current buildability.

---

## The Design Principle

Every layer added must pass this test:

> Does this make the persona *behave* differently, or does it just make the persona
> *read* differently?

Layers that only add prose make the document longer.  
Layers that change how the chat system, probe engine, and simulation modes operate
make the product more powerful.

The symbolic meaning system, multi-layered self, and state modifiers all pass this
test. They are not decorative — they are load-bearing.
