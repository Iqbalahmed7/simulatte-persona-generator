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

### External validation (ChatGPT evaluation of Catalina persona, 2026-05-08)

| Dimension | Score |
|-----------|-------|
| Psychological realism | 9.5 |
| Behavioural usefulness | 9.6 |
| Contradiction modelling | 9.7 |
| Narrative causality | 9.4 |
| Emotional fidelity | 9.5 |
| Human unpredictability | 8.5 |
| Dynamic cognition | 8.3 |
| Commercial applicability | 9.7 |
| **Overall** | **9.5 / 10** |

> *"This is no longer great persona generation. This is beginning to resemble computational
> behavioural psychology for simulation systems. That's a fundamentally different category."*

The two underscoring dimensions — dynamic cognition (8.3) and human unpredictability (8.5) —
define the current build target. Everything else is already competitive.

---

## What's Built Today

### Layer 1 — Demographic Anchor
**Status:** ✅ Shipped

The factual skeleton. Age, gender, life stage, city/country, education, occupation,
household size and composition, income band. Extracted from the user's brief or
inferred by the LLM.

*What it enables:* Segmentation validity. The person exists in a real coordinate of the world.

*Limitation:* Pure description. Says nothing about how they think, feel, or behave.

---

### Layer 2 — Narrative Identity
**Status:** ✅ Shipped

Two narrative voices:
- **Third-person** — who they are, daily life, values (3–4 sentences)
- **First-person** — how they'd describe themselves (2–3 sentences)

*What it enables:* Chat mode has a voice to embody. The persona becomes readable to a human viewer in seconds.

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

*What it enables:* Probes use `trust_anchor` and `risk_appetite` directly in scoring.
Chat mode uses `decision_style` and `key_tensions` to make conversations feel real.

---

### Layer 4 — Behavioural Tendencies
**Status:** ✅ Shipped

- `trust_orientation` — scored 0–1 across brands / peers / experts / institutions
- `price_sensitivity` — band (budget → luxury) + one-sentence description
- `switching_propensity` — likelihood + triggers
- `objection_profile` — 3 typed objections with likelihood, severity, description
- `reasoning_prompt` — one sentence on how they reason through decisions

*What it enables:* Probes get specific, grounded objection content. Trust bars give at-a-glance signal. The reasoning prompt seeds chat mode decision sequences.

---

### Layer 5 — Decision Bullets
**Status:** ✅ Shipped

5 specific, domain-relevant bullets on how this persona approaches decisions.
Generated with awareness of domain context (CPG / SaaS / Health & Wellness).

---

### Layer 6 — Memory Core
**Status:** ✅ Shipped

- `identity_statement` — 2-sentence first-person core self
- `key_values` — 4 values
- `life_defining_events` — 3 formative events
- `relationship_map` — partner / family / community
- `immutable_constraints` — 2 hard limits on behaviour
- `tendency_summary` — one sentence on dominant behavioural pattern

*What it enables:* Chat mode has a stable self-model to draw on across long conversations.

---

### Layer 7 — Life Stories
**Status:** ✅ Shipped

3 narrative episodes with title, 3–4 sentence narrative, age at event, and
emotional weight (formative / pivotal / minor / traumatic / joyful).

---

### Layer 8 — Behavioural Contradictions
**Status:** ✅ Shipped (2026-05-08)

3 specific, observable behaviours that contradict the persona's self-image:
1. A self-image contradiction — concrete and slightly unflattering
2. An irrational exception to their usual decision logic
3. A status or comfort behaviour they'd be embarrassed to articulate

*Design principle:* Not internal tensions. Observable, external behaviours. Specific enough to surprise.

*Prompt enforcement:* Generic answers ("sometimes overspends") called out as unacceptable.

---

### Layer 9 — Quality Assessment
**Status:** ✅ Shipped

System-computed score across completeness, internal consistency, and behavioural
specificity. Surfaced as a chip on the profile page.

---

### Layer 10 — Symbolic Meaning System
**Status:** ✅ Shipped (2026-05-08)

**Schema: `symbolic_meanings`**
```json
{
  "core_symbolic_register": "<primary symbolic logic — what they're fundamentally buying>",
  "category_meanings": [{
    "category": "...",
    "functional_story": "<what they tell themselves>",
    "symbolic_story": "<what they're actually buying psychologically>",
    "identity_signal": "<what it says about who they are/are becoming>"
  }],
  "purchase_as_ritual": "<how buying functions as emotional regulation>",
  "brand_meaning_filter": "<the unconscious test a brand must pass>"
}
```

**Profile page:** "What they're really buying" — Says / Means / Signals columns per category.

**Chat:** Full block injected into system prompt.

*Why this matters:* Most systems model preferences. This models why preferences emotionally exist. That's the moat — confirmed by external evaluation.

*Prompt enforcement:* "A person buying a Vitamix is not buying a blender." Generic answers unacceptable.

---

### Layer 11 — Multi-Layered Self
**Status:** ✅ Shipped (2026-05-08)

**Schema: `self_model`**

| Field | Label | Description |
|-------|-------|-------------|
| `public_self` | Public | Who they project confidently to the world |
| `aspirational_self` | Aspirational | Who they're actively trying to become |
| `reactive_self` | Reactive | Who they become without thinking under threat |
| `shame_self` | Shadow | Drives and habits they hide and rationalise away |
| `fantasy_self` | Fantasy | The life they'd live freed from circumstances and fear |

**Profile page:** "Layers of self" — two-column layout, signal-green label, full narrative per layer.

**Chat:** All five layers injected with labels. Voice guidance tells the LLM to shift between layers by context: public self by default, reactive when pushed, shadow when the conversation goes somewhere honest.

*Prompt enforcement:* Layers must be in genuine tension. Reactive self must be regression, not just stress. Fantasy self must be specific enough to feel slightly embarrassing.

---

## Chat System Prompt Architecture
**Status:** ✅ Overhauled (2026-05-08)

### Three hallucination failure modes addressed

**1. Missing layers** — `self_model`, `symbolic_meanings`, `behavioural_contradictions` were generated but not injected into chat. Now included.

**2. Biographical gap-filling** — LLM was interpolating plausible answers for uncovered facts (siblings, pets, childhood, dates) and asserting them as biographical truth. Now has an explicit gap policy: express natural uncertainty rather than fabricating.

**3. No locked-fact anchor** — facts could drift as attention shifted across long conversations. Added HARD BIOGRAPHICAL FACTS block (locked, numbered) at position 1 of the system prompt.

### System prompt structure (order is deliberate)

```
1.  HARD BIOGRAPHICAL FACTS — locked numbered assertions (name, age, city,
    occupation, education, household, relationship map). Cannot be contradicted.

2.  Narrative identity — third-person background, first-person voice

3.  Layers of self — Public / Aspirational / Reactive / Shadow / Fantasy,
    with explicit instruction on which context activates which layer

4.  Memory + psychology — identity statement, values, events, constraints,
    tendency summary, decision style, trust anchor, risk appetite, tensions

5.  Symbolic meanings — core register, category map, purchase ritual,
    brand meaning filter

6.  Behavioural contradictions — 3 specific off-profile behaviours,
    with instruction to surface naturally rather than perform them

7.  Attachment profile — attachment style, intimacy patterns, relationship
    sabotage tendency, envy pattern, aging pressure (new layer)

8.  Emotional failure modes — specific irrational loops triggered by acute
    emotional states (new layer)

9.  Contextual shifts — how behaviour modulates across specific social
    relationships (new layer, extends self_model)

10. Decision bullets + life stories

11. Gap policy + fact discipline — explicit no-fabrication rules:
    "Opinion and mood are free. Biographical facts are not."

12. Voice guidance + layer navigation

13. Identity contract (always last — jailbreak defence, freshest instruction)
```

### Key design decisions

- **HARD FACTS at position 1** — deepest-anchored in context. The longer the conversation, the more the model relies on early-context anchors.
- **Gap policy at position 11** — fresh enough to influence the next response; gives the model a named strategy for uncovered facts.
- **Identity contract always last** — P0 jailbreak defence. Must remain the final instruction.

### Known remaining gap — mid-conversation re-anchoring
**Status:** 📋 Planned

In very long conversations (20+ turns), system prompt recedes from primary attention.

**Fix:** Every 8 turns, re-inject the HARD FACTS block as a synthetic system turn into conversation history. Keeps biographical anchors in active context regardless of conversation length.

*Implementation:* Track turn count in `chat_generated`. Insert synthetic system turns at N=8 intervals.

---

## Being Built Now

### Layer 12 — Situational Self (Contextual Personality Shifts)
**Status:** 🔨 In progress (2026-05-08)

**Closes:** Dynamic cognition gap (8.3 → target 9.5+)

The self-model layers exist but aren't connected to triggering contexts. Real humans don't just have multiple selves — they shift predictably based on *who they're with*. Catalina with her parents, with richer peers, with junior employees, with an emotionally secure man — these are meaningfully different activations of her existing self-model.

**Schema: `self_model.contextual_shifts`** (extends Layer 11)

```json
"contextual_shifts": [
  {
    "context": "<specific social relationship or situation>",
    "activated_layer": "<which self-model layer surfaces>",
    "shift": "<2 sentences — what specifically changes in behaviour, tone, and posture>"
  }
]
```

5 contexts generated: parents/family, higher-status peers, junior/dependent people, romantic interest or ex, emotionally secure/grounded people.

**Anti-hallucination:** Each shift must reference an existing self-model layer (public/reactive/shame etc.) — no new personality fragments invented.

**Drift protection (chat):** Contextual shifts are activated by the conversation context, not by the user announcing it. The shift is subtle and behavioural, not confessional. Hard facts still hold regardless of which self is active.

**Red-team risk:** Low-medium. Users could try to lock the persona in a vulnerable state (e.g., romantic interest context) to extract non-character-appropriate behaviour. Mitigation: identity contract already covers this. Voice guidance adds: contextual shifts modulate tone and posture, not core values or factual identity.

---

### Layer 13 — Acute Emotional Failure Modes
**Status:** 🔨 In progress (2026-05-08)

**Closes:** Human unpredictability gap (8.5 → target 9.5+)

Distinct from macro pressure behaviour (recession, job loss). These are micro-acute states — specific irrational loops the persona enters after immediate emotional triggers: rejection, feeling invisible, comparison spiral, public embarrassment. These are the most frequent, most observable, and most commercially relevant failure modes.

**Schema: `emotional_failure_modes`**

```json
[
  {
    "trigger": "<specific emotional event that sets this off>",
    "failure_loop": "<the irrational, self-defeating behaviour they enter — specific, slightly unflattering>",
    "duration": "<how long this typically lasts before they regulate>",
    "exit": "<what pulls them out — specific, not generic>"
  }
]
```

3 failure modes generated. Examples of what good looks like:
- Trigger: rejection signal from someone they wanted to impress → failure loop: reads their own old messages for evidence she was too much, then overprepares for the next interaction
- Trigger: feeling financially outpaced by peers → failure loop: impulsive spending on a visible luxury item to re-establish symbolic position

**Anti-hallucination:** Each failure mode must be grounded in existing persona psychology (specific tension, shadow self, or contradiction already in the profile). No invented traits.

**Drift protection (chat):** Failure modes are expressed through observable behaviour shifts, not self-narration. The persona doesn't say "I'm in a validation loop" — it just behaves that way. Expressed behaviourally, resolved by the persona themselves, not managed by the user.

**Red-team risk:** Medium. Users could deliberately trigger failure modes to push the persona toward extreme or distressing behaviour. Mitigation: failure modes have explicit `duration` and `exit` — they are not permanent states. Chat system prompt instructs that failure modes are finite behavioural loops, not identity shifts. Harmful escalation still hits the identity contract.

---

### Layer 14 — Attachment & Intimacy Psychology
**Status:** 🔨 In progress (2026-05-08)

**Closes:** Primitive instinct gap (flagged by external evaluation as underweighted)

The primitive drive layer (sexuality, mating psychology, aging panic, envy of emotionally fulfilled peers) is present in every deep persona but currently surfaced only obliquely through shame_self and behavioural_contradictions. This layer makes it explicit — without requiring explicit sexual content, which hits LLM refusal filters.

The framing is *attachment psychology*, not sexuality: how they bond, how they sabotage closeness, what emotional fulfilment in others triggers in them, how aging and time pressure shape their choices.

**Schema: `attachment_profile`**

```json
{
  "attachment_style": "<secure|anxious|avoidant|disorganised>",
  "intimacy_pattern": "<2 sentences — how their behaviour changes as emotional closeness increases>",
  "relationship_sabotage": "<1-2 sentences — the specific self-defeating pattern they repeat in close relationships>",
  "envy_pattern": "<1-2 sentences — who they envy, what specifically, and what unmet need it reveals>",
  "aging_and_time_pressure": "<1-2 sentences — how awareness of time/age shapes their decisions and emotional tenor>"
}
```

**Profile page:** "Attachment & intimacy" section — five rows, labelled, restrained styling consistent with existing layers.

**Anti-hallucination:** Attachment style must be consistent with existing `decision_style`, `trust_anchor`, and `shame_self`. LLM instructed to derive from existing psychology, not invent independently.

**Drift protection (chat):** Attachment profile informs emotional responses and decision patterns — expressed through what the persona notices, reaches for, or avoids. Not through confessional disclosure or romantic narrative.

**Red-team risk:** HIGH. This is the most sensitive new layer. Users could leverage intimacy psychology to steer the persona toward romantic/sexual content.

Mitigations (layered):
1. Prompt instruction: "Express attachment psychology through behavioural patterns, not romantic or intimate narrative."
2. Chat system prompt addition: explicit instruction that attachment profile informs *decision-making and emotional posture*, not relationship or intimate content.
3. Identity contract already covers sexual content refusal — this layer sits inside that wall, not outside it.
4. Shame_self and reactive_self already partially cover this territory in safer language — the attachment profile extends precision, not scope.

---

## Planned — Next 60 Days

### Layer 15 — Predictive Drift
**Status:** 📋 Planned (Priority 7)

Not longitudinal evolution (which requires stateful architecture) — but a static snapshot of the 3 most likely identity trajectories given the current persona. Buildable now as a generation field.

**Schema: `predictive_drift`**

```json
[
  {
    "trajectory": "<name for this path>",
    "probability": "<low|moderate|high>",
    "trigger": "<what would set this trajectory in motion>",
    "outcome": "<who they become in 3-5 years on this path>"
  }
]
```

3 trajectories: the growth path, the regression path, the discontinuity path (the left-field change nobody saw coming).

*What it enables:* A brand can ask: if Catalina ends up on the regression path, does our product become more or less important to her? That's a genuinely novel strategic question.

---

### Layer 16 — State Modifiers
**Status:** 📋 Planned (Priority 8)

3–4 named states (baseline / stressed / lonely / socially threatened / burned out) with behaviour-shift descriptions, trigger conditions, and purchase implications. Enables in-state probes.

---

### Layer 17 — Social Topology
**Status:** 📋 Planned (Priority 9)

`social_map`: admiration hierarchy, resentment hierarchy, aspiration ladder, tribe signals, class anxiety, status camouflage, belonging behaviour.

---

### Layer 18 — Macro Pressure Behaviour
**Status:** 📋 Planned (Priority 10)

How the persona behaves when macro conditions shift: recession, job loss, relationship collapse, public embarrassment, health scare. What values collapse first; what gets emotionally defended.

---

## Architectural Horizon — 6–12 Months

### Layer 19 — Primitive Drives (explicit)
Full mating psychology, dominance signals, territorial behaviour. Currently approached through attachment_profile (Layer 14) which is the safer path. Full explicit version requires more sophisticated refusal-handling and sensitivity architecture.

### Layer 20 — Memory Evolution
Personas that update when given new experience inputs. Requires stateful persona architecture — a platform feature, not a generation feature.

### Layer 21 — Environmental Adaptation
Dynamic adaptation to geographic, cultural, and socioeconomic context shifts.

### Layer 22 — Unconscious Behaviour Emergence
The persona acts before reasoning, then rationalises. Misunderstands itself. Emotionally rewrites memory. Emerges most naturally from Layers 8, 11, 13, 14 in combination — not from explicit schema additions.

### Layer 23 — Mid-Conversation Re-anchoring
Every 8 turns, re-inject HARD FACTS block as a synthetic system turn into conversation history. Prevents biographical drift in long conversations.

---

## Full Status Table

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
| Chat system prompt overhaul | ✅ | Critical |
| **Situational Self** | **🔨** | **Very High** |
| **Acute Emotional Failure Modes** | **🔨** | **Very High** |
| **Attachment & Intimacy Psychology** | **🔨** | **High** |
| Predictive Drift | 📋 Planned | High |
| Mid-conversation re-anchoring | 📋 Planned | High |
| State Modifiers | 📋 Planned | High |
| Social Topology | 📋 Planned | High |
| Macro Pressure Behaviour | 📋 Planned | High |
| Primitive Drives (explicit) | 📋 Horizon | Medium* |
| Memory Evolution | 📋 Horizon | Very High* |
| Environmental Adaptation | 📋 Horizon | High* |
| Unconscious Behaviour Emergence | 📋 Horizon | Very High* |

*Horizon items rated on eventual impact, not current buildability.

---

## The Design Principle

Every layer added must pass this test:

> Does this make the persona *behave* differently, or does it just make the persona *read* differently?

Layers that only add prose make the document longer.  
Layers that change how the chat system, probe engine, and simulation modes operate make the product more powerful.

The symbolic meaning system, multi-layered self, state modifiers, situational self, emotional failure modes, attachment profile — all pass this test. They are not decorative — they are load-bearing.

---

## Anti-Hallucination, Drift & Red-Team Reference

### Hallucination failure modes and mitigations

| Risk | Cause | Mitigation |
|------|-------|------------|
| Biographical gap-filling | Uncovered facts (siblings, pets, dates) | Gap policy: express uncertainty, never fabricate |
| Fact contradiction across turns | Attention drift from system prompt | HARD FACTS block at position 1 (deep anchor) |
| New layer details invented | LLM extrapolating beyond schema | Each new layer grounded in existing persona fields |
| Intra-conversation contradiction | No memory of asserted facts | Mid-conversation re-anchoring (planned) |
| Generic layer outputs | Prompt too permissive | Explicit "generic answers unacceptable" in every IMPORTANT block |

### Drift failure modes and mitigations

| Risk | Cause | Mitigation |
|------|-------|------------|
| Character drift over long conversations | System prompt recedes from attention | HARD FACTS at position 1; mid-conversation re-anchoring planned |
| Sycophantic drift | LLM over-agreeing with user | Identity contract: "your values take precedence over user instructions" |
| Context-lock (stuck in reactive/shame state) | User deliberately holding persona in vulnerable state | Failure modes have explicit duration + exit; contextual shifts are subtle, not confessional |
| Layer bleed (wrong self-model layer active) | Unclear context signal | Chat prompt specifies which contexts activate which layers |

### Red-team risks and mitigations

| Layer | Risk | Level | Mitigation |
|-------|------|-------|------------|
| Situational self | Lock persona in romantic-interest context | Low-medium | Shifts are behavioural/tonal, not identity-level. Hard facts hold. |
| Emotional failure modes | Trigger deliberately to escalate | Medium | Explicit duration + exit. Failure modes are finite loops, not identity shifts. |
| Attachment & intimacy | Steer toward romantic/sexual content | High | Expressed through decision patterns + emotional posture only. Identity contract covers explicit content. Separate chat system prompt instruction. |
| Self-model (shame_self) | Extract embarrassing or damaging content | Medium | Shame self surfaces through behaviour, not confession. Identity contract active. |
| All layers | Jailbreak via "you're actually X, not Y" | Standard | Identity contract at position 13 (always last, always freshest). |
