# Prompt Patterns — Reusable Templates for Each Engine Stage

These are the battle-tested prompt structures from the LittleJoys pilot. Adapt the category-specific sections for new clients; keep the structure.

---

## 1. Stimulus Importance Scoring (perceive)

Used when a persona encounters a stimulus. Returns importance score + emotional valence + interpretation.

**Key design principles:**
- Provide the persona's psychological profile in condensed form — only the attributes most relevant to this category
- Use 1-10 raw scale then normalise to 0.0–1.0 ((raw-1)/9) for consistency
- Ask for dominant attributes activated — this becomes the "reason" the score is what it is
- Always request valid JSON only — no preamble

**Structure:**
```
PERSONA PROFILE (condensed):
- [5–7 most category-relevant psychological attributes with scores]
- Decision style, trust anchor

STIMULUS:
[type, source, content]

TASK:
Score on:
1. IMPORTANCE (1-10)
2. EMOTIONAL_VALENCE (-1.0 to 1.0)
3. DOMINANT_ATTRIBUTES (2-3 activated attributes)
4. INTERPRETATION (one sentence)

Return valid JSON only.
```

**Model:** claude-haiku-4-5
**Max tokens:** 512

---

## 2. Purchase Decision (decide)

Used at the purchase moment. Returns a full 5-step reasoning chain.

**Key design principles:**
- Include core memory summary (narrative + first-person voice) — this anchors the persona's identity
- Include retrieved memories — top 10 most relevant episodic memories to this specific decision
- Force 5 explicit steps — gut → information → constraints → social → final
- Ask for structured JSON with reasoning_trace as an array — easy to parse and display
- Use sonnet, not haiku — depth matters here
- Set max_tokens=2048 — the 5-step trace is long; truncation at 512 causes JSON parse failures

**Structure:**
```
=== PERSONA: [name] ===
Decision style, trust anchor, risk appetite, values, coping mechanism
Budget: Rs[X]/month, [price_sensitivity] sensitivity

=== CORE MEMORY ===
[first_person_summary + narrative excerpt]

=== RECENT RELEVANT MEMORIES ===
[top 10 retrieved memories, formatted as: event_type | valence | content]

=== SCENARIO ===
[purchase situation description]

=== TASK ===
STEP 1 - INITIAL REACTION
STEP 2 - INFORMATION PROCESSING
STEP 3 - CONSTRAINT CHECK
STEP 4 - SOCIAL SIGNAL CHECK
STEP 5 - FINAL DECISION

Return JSON: decision, confidence, reasoning_trace[], key_drivers[], objections[], willingness_to_pay, follow_up_action
```

**Model:** claude-sonnet-4-5
**Max tokens:** 2048

---

## 3. Reflection (reflect)

Used after cumulative salience > 5.0. Generates higher-order insights from recent memories.

**Key design principles:**
- "Based ONLY on the memories above" — keeps insights grounded, not hallucinated
- Ask specifically for patterns and emerging beliefs — not event summaries
- Format memories with index numbers — the model returns source_indices so you can trace which memories generated each insight
- Cap at max_insights=3 — more than 3 insights from 20 memories is diluted

**Structure:**
```
PERSONA CONTEXT:
- ID, age, decision style, trust anchor

RECENT MEMORIES (most recent first):
[{index}] [{event_type}|val:{valence}|sal:{salience}] {content[:120]}

TASK:
Generate {n} higher-order insights about this persona's relationship with [category].

Focus on:
- Emerging beliefs or attitudes (not event summaries)
- Patterns across multiple memories
- Decision-making triggers

Return JSON: insights[{insight, confidence, source_indices[], emotional_valence}]
```

**Model:** claude-sonnet-4-5
**Max tokens:** 1024

---

## 4. Naive Baseline (for A/B testing)

Used only for benchmarking. Intentionally strips out all psychological depth.

**Structure:**
```
You are a {age}-year-old [market description] evaluating a [category] stimulus.

STIMULUS:
Type: {type}
Source: {source}
Content: {content}

Rate on:
1. IMPORTANCE (1-10)
2. EMOTIONAL_VALENCE (-1.0 to 1.0)
3. INTERPRETATION (one sentence)

Return valid JSON only.
```

**Model:** claude-haiku-4-5
**Max tokens:** 256
**Normalise:** (importance - 1) / 9.0 to match the memory-backed scale

---

## 5. Persona Generation Prompt (for new populations)

Used when generating personas from a client brief. Returns structured persona dicts.

**Key design principles:**
- Generate in batches of 10-20 — full populations in one call tend to lose coherence
- Always specify the anti-correlation constraints explicitly — models will violate them without reminders
- Request narrative AND first-person summary — both are required for the memory system to work
- Specify the field schema explicitly — don't let the model invent field names

**Structure:**
```
Generate {n} persona(s) for the following brief:

PRODUCT: [product name and description]
MARKET: [geographic, demographic, psychographic target]
CATEGORY: [product category]

Each persona must include:
- Demographics (age, city, family structure, income bracket)
- Psychology (health_anxiety, social_proof_bias, authority_bias, risk_tolerance, loss_aversion, analysis_paralysis, decision_speed, information_need)
- Values (relevant category-specific values)
- Decision profile (decision_style, trust_anchor, price_sensitivity)
- Narrative (3rd person, 150-200 words)
- First person summary (1st person, 100 words)

Constraints:
- risk_tolerance and loss_aversion cannot both exceed 0.75
- analysis_paralysis and decision_speed cannot both exceed 0.8
- [category-specific constraints]

Return as JSON array.
```

---

## Common Mistakes to Avoid

**1. max_tokens too low on decide()**
The 5-step reasoning trace with JSON wrapper needs ~1500 tokens minimum. Setting 512 causes truncated JSON → parse failure. Always use 2048 for decide().

**2. Using model names that don't exist**
Confirmed working (as of Sprint 29): `claude-haiku-4-5`, `claude-sonnet-4-5`
Not working: `claude-haiku-3-5`, `claude-3-5-haiku-20241022`, `claude-3-5-sonnet-20241022`
Always test model availability before running a full batch.

**3. f-string HTML entities from Goose**
If Goose (Grok) writes a file with `&#39;` or `&lt;` inside Python f-strings — the syntax is broken. The import check passes but runtime fails. Always test with a function call, not just import.

**4. Hardcoded field names in prompts**
If you change the schema, update the prompts. The prompt in perceive() lists specific attribute names — if the schema renames a field, the prompt breaks silently (model gets 0 instead of the actual value).
