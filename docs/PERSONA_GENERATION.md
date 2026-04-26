# Persona Generation — How It Works

**System:** The Mind (a sub-brand of Simulatte) · **Production:** mind.simulatte.io

---

## What it is

A system that generates a behaviourally coherent synthetic person from a one-paragraph brief, in roughly 15 seconds, at a cost of about 7 cents.

Unlike a chatbot persona or a marketing personification, every generated persona is structured: 200+ attributes, a demographic anchor grounded in real census data, a decision psychology model, a memory store, and a behavioural coherence score. The same persona can be probed against a product (Litmus probe), chatted with one-to-one, scaled into a population of 5,000 like them, or exported to a research stack.

This document explains the pipeline that produces a single persona — the foundation everything else in Simulatte is built on.

---

## The problem we're solving

Traditional consumer research has two failure modes that compound. Surveys collect what people *say* they'd do, which correlates poorly with what they actually do. And they take six to twelve weeks at a cost of fifteen to fifty thousand dollars per study, by which point the question being asked has often moved on.

What teams actually need is a way to quickly, cheaply pressure-test "would Ravi, a 34-year-old software engineer in Bangalore, find this credible?" — and get an answer that's grounded in something more rigorous than a marketer's intuition.

That's what persona generation produces. Not a guess, not a chatbot in a costume — a structured profile that captures the texture of a real person well enough that you can ask it questions and get back answers that hold up to scrutiny.

---

## Inputs

The user provides up to three things:

1. **Brief** — a one-paragraph natural-language description. *"Ravi, 34, software engineer in Bangalore. Single, rents an apartment, earns ₹18L/year. Buys gadgets impulsively, healthy eating aspirations, active on Reddit and YouTube, uses 5 streaming subscriptions."*
2. **Domain** — the business context (CPG, SaaS, or Health & Wellness). This biases attribute generation toward what's relevant for that vertical.
3. **PDF (optional)** — a segmentation report, brand brief, or research document. The system extracts the persona requirements from the document and merges them with the natural-language brief.

The brief is the load-bearing input. Domain and PDF tighten the output but aren't strictly necessary.

---

## The pipeline

The system runs three stages, two of them in parallel where possible. Total wall time is 15–18 seconds.

### Stage 1 — Brief extraction

A single Haiku call reads the brief and produces a structured demographic anchor: name, age, gender, life stage, location (city + country + tier), education, employment (occupation + industry + seniority), and household composition.

This is the moment where free-text becomes structured. It's deliberately built with multiple fallbacks — if the model returns plain prose instead of JSON, we try a code-fence extraction, then a brace-scan, then a default schema. Empty or partial responses don't crash the pipeline.

The output is a clean dictionary of demographic facts that anchors everything that follows.

### Stage 2 — Persona generation (two parallel Haiku calls)

This is where the persona acquires depth. Two Haiku calls run concurrently:

**Prompt A** generates the inner life: narrative (first-person and third-person), derived insights (decision style, trust anchor, risk appetite, primary value orientation, key tensions, coping mechanism), behavioural tendencies (price sensitivity, trust orientation across categories, switching propensity, objection profile), decision bullets, and life stories.

**Prompt B** generates the outer life and structured detail: refined demographic detail (with fallbacks to fill in gaps from the anchor), employment specifics, household specifics, and the memory core (identity statement, key values, life-defining events, relationship map, immutable constraints, tendency summary).

The two prompts produce overlapping fields by design — when both populate `city` or `occupation`, the system picks the more specific one, and the redundancy gives us robustness. Empty fields from one prompt are backfilled from the other, eliminating the "missing city" failure mode that used to hit 1 in 5 generations.

Both calls share the structural context of the demographic anchor, so they converge on a consistent person rather than two halves that contradict each other.

### Stage 3 — Quality assessment

Once the persona is assembled, a deterministic local function computes a **Genuineness score** out of 10, based on four components:

| Component | Weight | What it measures |
|---|---|---|
| Demographic grounding | 40% | How many anchor fields actually got populated (age, location, occupation, education, household) |
| Behavioural consistency | 30% | Cross-attribute coherence — does the decision style match the values match the trust orientation |
| Narrative depth | 15% | Life stories, decision bullets, defining memory events present and substantive |
| Psychological completeness | 15% | Decision style, trust, risk, values, and behavioural tendencies all populated |

The score and its components are surfaced on the persona page. Users can click the chip to see the breakdown plus a list of the ground-truth sources used (demographic anchor, behavioural coherence model, LLM inference). The point of the score is not to pretend the persona is "real" — it's to be honest about where confidence is high (anchored facts) versus where it's extrapolated (LLM-generated narrative).

### Persistence

The final persona is written to disk as a JSON file at `pilots/the-mind/data/generated_personas/{persona_id}.json`. The `data/` directory is mounted to a Railway persistent volume, so personas survive deploys.

Each persona's `persona_id` is deterministic and shareable: `pg-web-{first-name}-{last-name}-{4-char-suffix}`. Visiting `/persona/{id}` loads the persona; visiting `/persona/{id}/probe` lets you test a product against them; visiting `/persona/{id}/chat` lets you talk to them.

---

## What you get out

A persona JSON file with these top-level blocks:

- `demographic_anchor` — name, age, gender, life stage, location, education, employment, household
- `narrative` — first-person and third-person prose descriptions (~150 words each), display name
- `derived_insights` — decision style, trust anchor, risk appetite, value orientation, consistency score (0–100), key tensions, coping mechanism
- `behavioural_tendencies` — price sensitivity (band + description), trust orientation (a dict of category → 0-1 trust score), switching propensity, objection profile, reasoning prompt
- `decision_bullets` — 5 short statements about how this person decides
- `life_stories` — 3–5 narrative episodes with title, narrative, age at event, emotional weight
- `attributes` — currently a slot for ~200 typed attributes (planned; populated for exemplar personas, empty for generated v1)
- `memory.core` — identity statement (first-person), key values, life-defining events, relationship map, immutable constraints, tendency summary
- `quality_assessment` — score out of 10, four component scores, source attribution
- `portrait_url` — populated on demand via a separate `/portrait` call to a fal.ai image model

The whole thing is roughly 8–12 KB of structured JSON.

---

## Why the persona feels real

The reason this output reads as a person rather than a survey response is the deliberate focus on structural coherence. Three design decisions matter most:

**Anchored, not invented.** The demographic anchor is constrained by what's real — Census-level distributions of occupation, education, household composition, regional income. The persona can't be a 34-year-old retired schoolteacher in a fishing village earning ₹18L; the anchor refuses to assemble that combination. This kills the "creative-writing-class" failure mode where personas drift into impossible territory.

**Tensions, not traits.** Most synthetic personas are built as bullet lists of attributes. Real people are built around contradictions: I want to eat healthy but I keep ordering Zomato at 11pm; I value financial discipline but I impulse-bought ₹40K worth of camera gear last month. Our generation prompt explicitly extracts the *tensions* — the gaps between aspiration and behaviour — and weaves them into the narrative and decision bullets. That's what makes the chat interactions feel human.

**Decision psychology, not opinions.** Asking "what would Ravi think of this energy bar" is a different question from "what would Ravi do?" The persona has an explicit decision style (analytical/intuitive/social/principled), trust anchor (peer/expert/data/heritage), and value orientation. When you probe a product, the system reasons through *that* lens, not a generic LLM-default voice. Two personas with different decision styles will respond differently to the same brief, in ways that are predictable from their structure.

---

## Where this fits in Simulatte

A single generated persona is the **demo unit**. It's what a visitor experiences in 90 seconds at mind.simulatte.io: type a brief, get a person, ask them questions, test a product against them.

A **population** of personas is the paid product. The same generation pipeline runs at 5,000-agent scale through Niobe + PopScale (Simulatte's population research engine), with the additional layer of demographic representativeness checks, probe parallelisation, and statistical aggregation. A simulation call produces a population, a research question, a probe design, and a synthesis report.

The Mind is the public face — the lead magnet, the demo, the proof point. Niobe is the workhorse that does the actual research work for paying clients.

---

## Cost and speed

Per generated persona:

| Stage | Model | Calls | Cost |
|---|---|---|---|
| Brief extraction | Haiku | 1 | $0.006 |
| Generation (parallel) | Haiku | 2 | $0.06 |
| Quality assessment | (local) | 0 | $0 |
| Portrait (optional) | gpt-image-1 | 1 | $0.05 |
| **Total (no portrait)** | | | **~$0.07** |
| **Total (with portrait)** | | | **~$0.13** |

Wall clock: 15–18 seconds, dominated by the parallel Haiku calls.

Storage: each persona is ~8–12 KB. 1 GB volume holds approximately 100,000 personas before we need to scale.

---

## Honest limitations

A generated persona is **a structured hypothesis**, not a real person. It's only as good as the brief that produced it.

- A vague brief produces a thin persona. The Genuineness score signals this honestly — a single-sentence brief lands around 5/10; a well-specified brief lands at 8.5/10.
- All the narrative, life stories, and behavioural tendencies are LLM-inferred from the demographic anchor and brief. They're plausible, internally consistent, and well-anchored — but they're extrapolations, not measurements.
- A single persona is a sample of one. To answer population-level questions ("what proportion of urban Indian software engineers would buy this?") you need Niobe — a population, not an individual.
- The persona is a snapshot. Long-running multi-session memory across many chats is not yet implemented. Each chat session starts fresh from the persona's static profile.
- Currently the `attributes` dictionary (intended for ~200 typed attributes) is empty for generated personas. Exemplar personas have it populated; generated personas will get it in a future sprint.

---

## What this enables that other tools don't

Most "AI persona" tools fall into one of two failure modes:
- **Chatbot personas** — a system prompt that says "you are Ravi" with no structural grounding. Quality varies wildly, no comparability across personas, no probe rigour.
- **Static persona libraries** — pre-built profiles of imagined customer types. Useful but not adaptive; can't be created on demand from a fresh brief.

The Mind sits in the gap. It's:

- **Generated on demand** from any brief, in ~15 seconds, ~$0.07
- **Structurally grounded** in real demographic distributions
- **Internally coherent** by construction, with a quality score
- **Probe-capable** — the same persona can be hit with the 8-question Litmus probe to produce structured purchase-intent data
- **Composable** — combine with Niobe to scale from one persona to 5,000 of them

It's the unit of cognition that the rest of the Simulatte system is built on.

---

## What's next for the system itself

- Populate the `attributes` dictionary during generation (200+ typed slots with provenance)
- Long-running memory across chat sessions (so Ravi remembers what you talked about last time)
- Multi-modal anchoring — let users upload a portrait and have the persona's traits constrained by what's visible
- Brief-quality scoring — predict the Genuineness score before generation runs, so users can be told "your brief is too thin, here's what to add"
- Persona families — generate sets of personas that vary along a controlled axis (e.g. five 34-year-old software engineers in Bangalore, varying only in income tier)

These are queued behind the launch sprint for the public sandbox.
