# System Overview — The Shift From Profiles to Simulation

*Non-technical version. No field names, no code.*

---

## What The Old Approach Was

Most persona systems — including the earlier LittleJoys engine — are **profile generators**.

You put in parameters. You get back a richly described person — their name, their background, their values, their worries, their daily routine.

That person is **frozen**. They're a character sheet, not a character. They don't respond. They don't remember. They don't change.

To use a static persona, a human has to imagine what they'd do. That's creative work — valuable, but slow, subjective, and impossible to run at scale.

---

## What This System Is

This is a **behavioural simulation engine**.

The difference is not in how detailed the personas are. It's in what they can *do*.

A persona in this system can:
- **Encounter** a real stimulus — an ad, a friend's message, a doctor's comment, a price change
- **React** to it based on their specific psychology — not a generic reaction, their reaction
- **Remember** it — and have that memory influence how they process the next thing they see
- **Reflect** — after enough experiences, form opinions and patterns about what they're seeing
- **Decide** — when shown a purchase opportunity, reason through it and give you a decision with a specific "why"

The persona has a history, not just a profile.

---

## The Problem This Solves

The fundamental problem in consumer marketing is this:

**You can't talk to your whole market. So you guess.**

You run a focus group of 12 people. You commission a survey that gets answered by people who don't actually represent your buyer. You run an A/B test in market, which costs real money and gives you a result weeks later that you can't explain.

All of these approaches have the same flaw: they tell you *what happened*, not *why*. And they can't run forward — you can't ask "what would happen if we changed the price" without going back to market.

---

## What This System Offers Instead

A synthetic population of consumers you can run scenarios through — *before* spending anything in market.

- Show your campaign to 200 personas. Get individual decisions, with reasoning, in minutes.
- Change one variable (price, channel, message, sequence). Re-run. Compare.
- Segment the population by who bought, who deferred, who rejected — and read the exact reasons why.
- Ask: "What stimulus sequence would move the maximum number of deferral personas to buy?"

The key is that these aren't generic AI responses dressed up with different names. They are psychologically distinct agents with different values, different memories, and different trust systems — producing genuinely different behaviour.

---

## The Proof

We ran a direct comparison against generic AI prompting on the same stimuli.

**Generic approach:** "You are a 28-year-old Indian parent. Rate this stimulus."
**Our approach:** A full persona with psychological profile, accumulated memories, and reflections.

The question: do our personas actually behave differently from each other, or does the system just generate varied-sounding text that all means the same thing?

**Result: Our personas were 607% more distinct.**

The generic approach produced near-identical scores across all personas for 4 out of 5 stimuli — same stimulus, same answer, regardless of who the persona was. Our system produced meaningfully different scores because different personas genuinely prioritised different things.

---

## What This Looks Like In Practice

We ran 200 personas through a 5-stimulus sequence ending in a purchase scenario for a child nutrition product (LittleJoys, Pilot 1).

The decisions were not uniform:
- 62% bought immediately
- 16% wanted to research more first
- 12% wanted to try a small pack before committing
- 9% deferred
- 1% rejected outright

Each decision came with a specific reason. The #1 driver across the population was pediatrician recommendation — cited by 42% of personas. Not advertising. Not price. The doctor.

That is an actionable insight. It tells LittleJoys exactly where to focus acquisition: medical professional relationships, not Instagram spend.

---

## How It Generalises

The engine is not specific to child nutrition or India. The architecture works for any category where:
- The purchase is considered (not purely impulse)
- Multiple information sources influence the decision
- The buyer has a psychological profile that affects how they process information

This could be applied to: FMCG, financial products, healthcare, EdTech, real estate, B2B SaaS, luxury goods — any category where understanding *why* a consumer decides is as valuable as knowing *what* they decide.

The skill being built is: **give the system a client brief, it generates the population, runs the scenarios, and returns the insight.**
