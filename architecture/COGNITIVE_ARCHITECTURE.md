# Cognitive Architecture — How the Engine Works

This is the core engine. It is product-agnostic and can be applied to any consumer category.

---

## The Four Capabilities

Every persona in the simulation can do four things:

### 1. Perceive
A persona encounters a stimulus — an ad, a WhatsApp message, a price change, an expert recommendation, a social event.

The persona does not simply "receive" it. It processes it through its own psychological lens:
- A health-anxious persona amplifies medical claims
- A peer-influence-driven persona pays close attention to WOM
- A price-sensitive persona notices discounts others might ignore

**Output:** An importance score (how much they'll remember this), an emotional valence (how it made them feel), and an interpretation (what they think it means).

**Model:** claude-haiku-4-5 (fast, cheap — runs for every stimulus × every persona)

---

### 2. Remember
Every perceived stimulus is written to the persona's episodic memory.

Memory is not a flat list. It is weighted:
- **Recency:** Older memories decay over time (0.995/hour decay rate)
- **Salience:** High-importance memories stick longer
- **Cap:** Memory is bounded at 1,000 entries — low-salience memories are evicted when full

When a persona makes a decision, it retrieves the most *relevant* memories — not just the most recent. Relevance is scored by a combination of recency × importance × semantic similarity to the current scenario.

This is how a persona can "remember" a doctor's recommendation from two weeks ago and factor it into a purchase decision today.

---

### 3. Reflect
After accumulating enough experience (when cumulative salience > 5.0), a persona steps back and forms higher-order insights.

Rather than just holding a list of experiences, the persona synthesises patterns:
- "I keep being swayed by authority figures — doctors, experts"
- "I'm noticing I'm more open to new brands than I thought"
- "Price discounts are reducing my hesitation on this category"

These reflections are stored back as high-salience memory entries and influence future decisions.

**Trigger:** Cumulative salience of recent stimuli crosses 5.0
**Output:** 2–3 ReflectionInsight objects appended to episodic memory
**Model:** claude-sonnet-4-5 (reflection needs depth — don't use haiku here)

---

### 4. Decide
When placed in a purchase scenario, the persona reasons through the decision in five explicit steps:

1. **Gut reaction** — immediate emotional response
2. **Information processing** — what data do they focus on given their attributes?
3. **Constraint check** — budget limits, non-negotiables, trust requirements
4. **Social signal check** — what would their trust network say?
5. **Final decision** — what do they actually do?

**Output:** Decision (buy/trial/defer/research_more/reject), confidence score, reasoning trace, key drivers, objections, willingness-to-pay.

**Model:** claude-sonnet-4-5, max_tokens=2048 (the 5-step reasoning chain is long — do not use 512)

---

## The Full Flow

```
Stimulus arrives
      ↓
perceive() — scores importance and emotional valence through persona's psychology
      ↓
update_memory() — writes to episodic memory with salience weighting
      ↓
(if cumulative salience > 5.0)
reflect() — synthesises patterns into higher-order insights
      ↓
decide() — retrieves relevant memories, reasons through 5 steps, outputs decision
```

---

## What Makes This Different From Prompting a Persona Description

With a static persona description, every LLM call starts from zero. The model sees the profile, reads the stimulus, and responds. Two different stimuli given an hour apart are completely independent.

With this engine:
- Memory persists across stimuli
- Early experiences influence later ones
- Trust builds (or erodes) incrementally
- Reflections change how future stimuli are processed

The persona has a *history*, not just a *profile*.

---

## Psychological Dimensions That Drive Differentiation

These are the attributes that cause different personas to respond differently to the same stimulus:

| Dimension | What it does |
|---|---|
| Health anxiety | Amplifies medical/safety claims |
| Social proof bias | Makes peer WOM more influential |
| Authority bias | Makes expert/doctor endorsement more influential |
| Information need | Drives "research more" decisions instead of immediate action |
| Analysis paralysis | Slows decisions even when intent is positive |
| Loss aversion | Makes price promotions feel urgent |
| Best-for-child intensity | Overrides price sensitivity for perceived quality |
| Trust anchor | Determines *whose* opinion matters most |
| Decision style | Analytical vs intuitive vs social |

A persona with high health anxiety + high authority bias will respond to a pediatrician stimulus completely differently than a persona with low health anxiety + high peer influence. That's the differentiation the system produces.

---

## Schema Design Principles (for new categories)

When adapting this engine to a new product category:

1. **Identify the 3–5 psychological dimensions most relevant to purchase decisions in this category** — these become the high-weight attributes in the perceive() prompt

2. **Identify the trust sources** — who does the target consumer listen to? (doctors, friends, influencers, family elders, online reviews?) These become `trust_anchor` options

3. **Identify the anti-correlations** — pairs of attributes that cannot both be extreme simultaneously (e.g. high risk tolerance + high loss aversion is a contradiction). These become constraint rules.

4. **Define the decision scenario template** — what does a realistic purchase moment look like in this category? What information would be available?

5. **Define 5 standard stimuli** — one per major marketing channel relevant to the category. These become your benchmark stimulus set.
