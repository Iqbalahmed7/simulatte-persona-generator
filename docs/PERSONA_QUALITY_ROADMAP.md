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
**Status:** ✅ Shipped (2026-05-08)

3 specific, observable behaviours that contradict the persona's self-image:
1. A self-image contradiction — something concrete and slightly unflattering
2. An irrational exception to their usual decision logic
3. A status or comfort behaviour they'd be embarrassed to articulate

*What it enables:* The persona stops feeling like a therapy report and starts feeling
like a real person. Chat conversations can surface these without prompting.
Contradictions are where human authenticity lives.

*Design principle:* These are not internal tensions (Layer 3 already covers that).
They are observable, external behaviours. Specific enough to be surprising.

*Prompt instruction enforced:* Generic answers like "sometimes overspends" are called
out as unacceptable in the generation prompt itself.

---

### Layer 9 — Quality Assessment
**Status:** ✅ Shipped

System-computed score across completeness, internal consistency, and behavioural
specificity. Surfaced as a chip on the profile page.

---

### Layer 10 — Symbolic Meaning System
**Status:** ✅ Shipped (2026-05-08)

Humans don't buy products. They buy symbols, emotional futures, identity repair,
status camouflage, and belonging. A persona that only models functional reasoning
(price / quality / trust) misses the deepest layer of consumer motivation.

**Schema: `symbolic_meanings`**

```json
"symbolic_meanings": {
  "core_symbolic_register": "<primary symbolic logic — what they're fundamentally buying when they buy anything>",
  "category_meanings": [
    {
      "category": "<product/service category>",
      "functional_story": "<what they tell themselves they're buying>",
      "symbolic_story": "<what they're actually buying at a psychological level>",
      "identity_signal": "<what owning/using this says about who they are or are becoming>"
    }
  ],
  "purchase_as_ritual": "<how buying functions as emotional regulation or identity maintenance>",
  "brand_meaning_filter": "<the unconscious test a brand must pass beyond product fit>"
}
```

**Profile page:** "What they're really buying" section — 3-column card per category
(Says / Means / Signals) + two footer cards (Purchase as ritual, Brand meaning filter).

**Chat:** Full symbolic meanings block injected into system prompt so the LLM can
explain *why* the persona is drawn to something they can't rationally justify.

*Prompt instruction enforced:* "A person buying a Vitamix is not buying a blender.
They are buying evidence that they are someone who cooks real food." Generic answers
are called out as unacceptable.

---

### Layer 11 — Multi-Layered Self
**Status:** ✅ Shipped (2026-05-08)

Humans are not one coherent personality. They operate across multiple self-models
simultaneously, often in tension with each other.

**Schema: `self_model`**

| Field | Label | Description |
|-------|-------|-------------|
| `public_self` | Public | Who they project confidently to the world |
| `aspirational_self` | Aspirational | Who they're actively trying to become |
| `reactive_self` | Reactive | Who they become without thinking under threat or overwhelm |
| `shame_self` | Shadow | Drives and habits they hide and rationalise away |
| `fantasy_self` | Fantasy | The life they'd live if circumstances and fear were removed |

**Profile page:** "Layers of self" section — two-column layout with signal-green
layer name, static descriptor, and full narrative per layer.

**Chat:** All five layers injected into the system prompt with labels. Voice guidance
explicitly instructs the LLM to let layers surface appropriately: public self by
default, reactive self when pushed, shadow when the conversation goes somewhere honest.

*Prompt instruction enforced:* Layers must be in genuine tension with each other.
Reactive self must feel like regression, not just a stressed version of public self.
Fantasy self must be specific enough to feel slightly embarrassing — not generic.

---

## Chat System Prompt Architecture
**Status:** ✅ Overhauled (2026-05-08)

The chat system prompt is the mechanism by which all persona layers reach the
conversation. Its structure directly determines hallucination rate, character
consistency, and conversation quality.

### Three hallucination failure modes addressed

**1. Missing layers** — `self_model`, `symbolic_meanings`, and `behavioural_contradictions`
were generated but not injected into the chat system prompt. Chat mode had no
access to any of them. All three now included.

**2. Biographical gap-filling** — when asked about something not in the persona JSON
(siblings, childhood city, pets, specific dates), the LLM would interpolate a
plausible-sounding answer and assert it as fact. A different answer could emerge
later in the same or a future conversation.

**3. No locked-fact anchor** — nothing explicitly prevented the LLM from contradicting
its own biographical statements as conversations lengthened and attention drifted.

### System prompt structure (order is deliberate)

```
1. HARD BIOGRAPHICAL FACTS — locked numbered assertions (never contradict these)
   Name, age, city/country, occupation, education, household, relationship map

2. Narrative identity
   Third-person background, first-person self-description

3. Layers of self (self_model)
   Public / Aspirational / Reactive / Shadow / Fantasy — labelled and usable

4. Memory + psychology
   Identity statement, values, defining events, constraints, tendency summary
   Decision style, trust anchor, risk appetite, value orientation, key tensions
   Price sensitivity, reasoning prompt

5. Symbolic meanings
   Core symbolic register, category map (Says / Means / Signals), purchase ritual,
   brand meaning filter

6. Behavioural contradictions
   3 specific behaviours that break the neat profile — surfaced naturally in chat

7. Decision bullets + life stories
   Grounding detail for decision sequences and narrative recall

8. Gap policy + fact discipline (anti-hallucination rules)
   Explicit instruction: express natural uncertainty for facts not in the document.
   "I don't really talk about that" / "it's complicated" are valid responses.
   Opinion and mood are free to express. Biographical facts are not to be fabricated.

9. Voice guidance
   First person, 2–5 sentences, let self-model layers show, no AI disclosure

10. Identity contract (always last — freshest instruction, jailbreak defence)
    Non-negotiable character lock, public figure policy, harm refusal
```

### Key design decisions

- **HARD FACTS at position 1** — deepest-anchored in the model's context. The longer
  the conversation, the more the model relies on early-context anchors.
- **Gap policy at position 8** — late enough to be fresh, gives the model a named
  strategy for uncovered facts rather than defaulting to interpolation.
- **Identity contract always last** — this is the P0 jailbreak defence and must remain
  the final instruction the model reads before the conversation begins.

### Known remaining gap — mid-conversation re-anchoring

**Status:** 📋 Planned

In very long conversations (20+ turns), the system prompt recedes from the model's
primary attention window. The hard facts and gap policy, while anchored at the top,
can lose influence.

**Planned fix:** Every 8 turns, re-inject the HARD FACTS block as a system message
into the conversation history. This keeps biographical anchors in the active context
regardless of conversation length.

*Implementation:* Requires changes to the conversation history management in
`chat_generated` — track turn count and insert synthetic system turns at intervals.
Lightweight; can be done as a standalone session.

---

## Planned — Next 60 Days

### Layer 12 — State Modifiers
**Status:** 📋 Planned (Priority 4)

Behaviour is not fixed — it shifts with internal state. A calm, intentional persona
and a sleep-deprived, socially-threatened version of the same persona make different
decisions.

**Schema: `state_modifiers`**

3–4 named states with behaviour-shift descriptions:
- `baseline` — default operating mode
- `stressed` — under work, financial, or social pressure
- `lonely_or_disconnected` — socially depleted state
- `socially_threatened` — triggered by comparison or status challenge
- `burned_out` — emotional and cognitive depletion

Each state: trigger conditions, behaviour shifts, purchase implications, what they
become in this state.

*What it enables:* Probes can be run "in state" — how does this persona respond to
a product when socially threatened vs calm? That's a fundamentally different research
capability. Chat mode can detect state drift in conversation and adapt.

---

### Layer 13 — Social Topology
**Status:** 📋 Planned (Priority 5)

Identity is relational, not isolated. The persona behaves differently around
different people, and those differences reveal more than any stated preference.

**Schema: `social_map`**

- `admiration_hierarchy` — who they look up to and why
- `resentment_hierarchy` — who they envy or resent and what that reveals
- `aspiration_ladder` — the social position they're oriented toward
- `tribe_signals` — how they identify their in-group
- `class_anxiety` — where they sit vs. where they think they sit
- `status_camouflage` — how they signal status without appearing to signal status
- `belonging_behaviour` — what they do to feel included

*What it enables:* Marketing targeting becomes relational, not demographic. Brand
positioning maps to aspirational social positions, not just stated preferences.
Qualitative research simulations become far richer.

---

### Layer 14 — Pressure Behaviour
**Status:** 📋 Planned (Priority 6)

Real humans are most revealing at the edge of stability.

**Schema: `pressure_profile`**

Scenarios: recession, relationship collapse, public embarrassment, health scare,
job loss, social rejection, cultural trend shift.

For each: what values collapse first, what behaviours become irrational, what
coping systems emerge, what identity fragments, what gets emotionally defended.

*What it enables:* Resilience planning, crisis communication, brand loyalty
stress-testing. If this persona loses their income, do they abandon the brand or
does it become more important to them?

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

## Current Status

| Component | Status | Impact |
|-----------|--------|--------|
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
| Multi-Layered Self | ✅ | Very High |
| **Chat system prompt overhaul** | **✅** | **Critical** |
| Mid-conversation re-anchoring | 📋 Planned | High |
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

The symbolic meaning system, multi-layered self, state modifiers, and the chat
system prompt overhaul all pass this test. They are not decorative — they are
load-bearing.
