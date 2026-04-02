# Persona Generator — Architecture Reference

## 1. Attribute Correlation Rules

When filling attributes progressively (Step 3c), enforce these correlation
constraints. If two assigned values violate a rule, adjust the second value
to be consistent with the first — never break coherence for variety's sake.

### Universal Cross-Domain Rules

| Attribute A | Direction | Attribute B | ρ / Rule |
|---|---|---|---|
| health_anxiety | → high | supplement/preventive product interest | ρ ≥ 0.50 |
| budget_consciousness | → high | discount/deal seeking | ρ ≥ 0.65 |
| social_proof_bias | → high | wom_receiver_openness | ρ ≥ 0.60 |
| brand_loyalty | → high | indie_brand_openness | inverse (ρ ≤ −0.50) |
| authority_bias | → high | medical/expert trust | ρ ≥ 0.55 |
| risk_tolerance | → low | status_quo_bias | ρ ≥ 0.60 |
| information_need | → high | research_before_purchase | ρ ≥ 0.55 |
| perceived_time_scarcity | → high | convenience_preference | ρ ≥ 0.60 |
| elder_advice_weight | → high | western_brand_trust | inverse (ρ ≤ −0.40) |
| income | → low + best_for_child_intensity > 0.7 | FLAG as tension — resolve by narrative |

### Hard Constraints (never violate)

These combinations are economically or psychologically impossible.
If both emerge from sampling, lower the second value:

- `income < 3 LPA AND organic_preference > 0.85` → reduce organic_preference to ≤ 0.55
- `Tier 3 geography AND digital_payment_comfort > 0.85` → reduce to ≤ 0.65
- `health_anxiety < 0.2 AND supplement_necessity_belief > 0.80` → raise health_anxiety to ≥ 0.45
- `homemaker status AND perceived_time_scarcity > 0.80` → reduce to ≤ 0.65
- `age < 25 AND brand_loyalty > 0.80` → reduce to ≤ 0.60 (loyalty develops over time)
- `high income (> 25 LPA) AND extreme deal_seeking > 0.85` → reduce to ≤ 0.60

---

## 2. Derived Insights — Computation Rules

These are deterministic. Apply them after attribute filling.
Do not use LLM to assign these — compute them from the filled values.

### Decision Style
Compute four scores and take the maximum:

```
emotional_score  = (emotional_persuasion_susceptibility + fear_appeal_responsiveness) / 2
analytical_score = (information_need + (1 - analysis_paralysis)) / 2
habitual_score   = (status_quo_bias + brand_loyalty) / 2
social_score     = (social_proof_bias + peer_influence_strength) / 2

decision_style = argmax(emotional, analytical, habitual, social)
```

### Risk Appetite
```
if risk_tolerance < 0.38 → "low"
if risk_tolerance > 0.62 → "high"
else → "medium"
```

### Primary Value Orientation (priority-ordered)
```
if budget_consciousness > 0.65 → "price"
elif domain_necessity_belief > 0.60 AND domain_gap_awareness > 0.60 → "quality/nutrition"
elif brand_loyalty > 0.65 → "brand"
elif convenience_preference > 0.65 → "convenience"
else → "features"
```

### Trust Anchor (priority-ordered)
```
if social_proof_bias > 0.60 AND wom_receiver_openness > 0.60 → "peer"
elif authority_bias > 0.65 AND domain_expert_trust > 0.60 → "authority"
elif elder_advice_weight > 0.65 → "family"
else → "self"
```

### Coping Mechanism (priority-ordered)
```
if simplicity_preference > 0.62 AND routine_adherence > 0.58 → "routine_control"
elif social_proof_bias > 0.65 → "social_validation"
elif information_need > 0.70 AND research_before_purchase > 0.65 → "research_deep_dive"
elif status_quo_bias > 0.65 → "denial/avoidance"
else → "optimism_bias"
```

### Consistency Score
Average five coherence signals, scale to [40, 100]:
```
s1 = 1 - |risk_tolerance - (1 - budget_consciousness)|
s2 = 1 - |brand_loyalty - (1 - indie_brand_openness)|
s3 = 1 - |authority_trust - authority_bias|
s4 = 1 - |deal_seeking - budget_consciousness|
s5 = 1 - |social_proof_bias - peer_influence|
score = int(40 + mean(s1..s5) * 60)
```
Flag any persona with score < 60 and review for contradictions before delivery.

---

## 3. Memory Architecture

### Core Memory (seed at generation time)

The Core Memory is the persona's immutable identity. It is seeded from
the generated profile and does not change during short simulations.
It contains the information that should always be present in the LLM
context window when the persona acts.

```json
{
  "core_memory": {
    "identity_statement": "[25-word first-person summary of who this person is]",
    "key_values": ["value_1", "value_2", "value_3"],
    "life_defining_events": [
      {
        "age_when": 9,
        "event": "...",
        "lasting_impact": "..."
      }
    ],
    "relationship_map": {
      "primary_decision_partner": "[who they consult most]",
      "key_influencers": ["..."],
      "trust_network": ["..."]
    },
    "immutable_constraints": {
      "hard_budget_ceiling": "[INR/currency value if applicable]",
      "non_negotiables": ["..."],
      "absolute_avoidances": ["..."]
    }
  }
}
```

### Operational Memory Stream (empty at generation, populated at runtime)

Each entry in the stream represents one perceived event.
The retrieval score formula: `score = α·recency + β·importance + γ·relevance`
where α=β=γ=1 by default (adjust per application).

```json
{
  "operational_stream": [
    {
      "id": "mem-001",
      "timestamp": "[ISO datetime]",
      "type": "observation | reflection | plan",
      "content": "[natural language description of the event]",
      "importance": 7,
      "emotional_valence": 0.3,
      "last_accessed": "[ISO datetime]",
      "source_ids": []
    }
  ]
}
```

**Importance scoring guide (1-10):**
- 1-3: Mundane (saw an ad, checked a price)
- 4-6: Moderately significant (friend mentioned a product, tried a sample)
- 7-8: Significant (paediatrician recommended, bad experience with product)
- 9-10: Pivotal (child had an adverse reaction, peer strongly endorsed)

### Reflection Trigger
Reflections are generated when `sum(importance of last 50 observations) > 80`.
They synthesise 3 high-level insights from recent observations and are stored
back to the stream with `type: "reflection"` and `source_ids` pointing to
the observations that informed them.

**Critical: reflections must include `source_ids`.**
A reflection without citation pointers is untrustworthy and should be discarded.

### Memory Promotion to Core Memory
Only promote a reflection to `core_memory` when:
- Its importance score is ≥ 9
- It has ≥ 3 valid source citations
- It does not contradict an existing core_memory entry

Promoted fields: values, non-negotiables, relationship_map entries only.
**Never update demographic_anchor or life_defining_events via reflection.**

---

## 4. Environment Schema

When building an environment for simulation (Simulation-Ready Mode),
generate the following structure from the business problem:

```json
{
  "environment": {
    "domain": "...",
    "spaces": [
      {
        "id": "space-001",
        "name": "...",
        "description": "...",
        "objects": [
          {
            "id": "obj-001",
            "name": "...",
            "current_state": "...",
            "possible_states": ["..."]
          }
        ]
      }
    ],
    "social_actors": [
      {
        "role": "paediatrician | peer | family | influencer | brand",
        "credibility_weight": 0.85,
        "interaction_frequency": "weekly | monthly | occasionally"
      }
    ],
    "friction_events": [
      {
        "event_type": "out_of_stock | price_increase | negative_review | competitor_launch",
        "probability_per_turn": 0.05,
        "impact_attributes": ["brand_loyalty", "consideration_set"]
      }
    ]
  }
}
```

---

## 5. Source Papers

This architecture synthesises three research papers:

1. **DeepPersona (NeurIPS 2025)** — taxonomy construction from human discourse,
   progressive attribute filling, bias-free sampling, narrative generation.
   Key result: 32% higher attribute coverage, 44% better uniqueness vs baselines.

2. **Generative Agents: Interactive Simulacra of Human Behavior (UIST 2023)**
   Park et al. — memory stream, retrieval scoring (recency × importance × relevance),
   reflection trees, planning. Key result: 8 standard deviations better believability
   vs no-memory baseline.

3. **MiroFish (2024)** — ontology generation from seed documents, knowledge graph
   as unified memory backend, behavioral parameter generation.

Full architecture documentation: `docs/PERSONA_GENERATOR_MASTER.md`
(in the LittleJoys project, or regenerate for new projects from this skill).

---

## 6. Behavioural Grounding Rules (Sprint A — Next Phase Architecture)

These rules define how behavioural parameters are assigned and validated. They supplement the correlation rules in Section 1.

### 6a. Parameter Assignment Order

Behavioural parameters must be assigned after attributes are filled (Step 3c), not before. The order is:

1. Fill all `attributes` values (existing Step 3c)
2. Compute `derived_insights` deterministically (existing Step 3d)
3. Assign `behavioural_params` using cluster data (preferred) or proxy formulas
4. Run consistency checks between `attributes` and `behavioural_params`
5. Generate `narrative` (existing Step 3e) — must not contradict behavioural_params

### 6b. Behavioural Parameter Consistency Rules

These checks must pass before a persona is considered valid in Grounded Mode:

| Attribute | Constraint | Behavioural Param | Direction |
|-----------|-----------|-------------------|-----------|
| `budget_consciousness > 0.70` | → | `price_elasticity ≤ -0.35` | must be elastic |
| `budget_consciousness < 0.35` | → | `price_elasticity ≥ -0.20` | must be inelastic |
| `brand_loyalty > 0.70` | → | `switching_hazard.baseline_rate_per_period ≤ 0.03` | low churn |
| `status_quo_bias > 0.65` | → | `switching_hazard.switching_cost_index ≥ 0.50` | high friction |
| `social_proof_bias > 0.65` | → | `trust_vector.peer ≥ 0.65` | peer-trusting |
| `authority_bias > 0.65` | → | `trust_vector.expert ≥ 0.65` | expert-trusting |
| `ad_receptivity < 0.30` | → | `trust_vector.ad ≤ 0.25` | ad-resistant |
| `information_need > 0.70` | → | `objection_profile` must include `need_more_information` | research-driven |
| `risk_tolerance < 0.30` | → | `objection_profile` must include `risk_aversion` | risk-averse |

Violations of these rules are flagged as `BEHAVIOURAL_CONSISTENCY_VIOLATION` and must be resolved before output is produced.

### 6c. Narrative Constraint

The first-person narrative (Step 3e) must not:
- State a specific WTP figure that contradicts `purchase_prob.baseline_at_ask_price`
- Describe switching behaviour that contradicts `switching_hazard.baseline_rate_per_period`
- Describe trust in a source type where `trust_vector.[type] < 0.25`

The narrative may include:
- Qualitative language derived from the parameters ("I rarely switch products I like" when baseline_rate < 0.03)
- Specific price ranges derived from the price_elasticity curve
- Trust descriptions derived from the dominant_anchor in trust_vector

### 6d. Decision Simulation Integration

When the behavioural_params block is present, the decide() function must:
1. Use `purchase_prob.baseline_at_ask_price` as the starting probability
2. Adjust by `price_elasticity` if the scenario price differs from ask price
3. Adjust by `trust_vector.[stimulus_source_type]` for each stimulus in memory
4. Check `objection_profile` for blocking objections that override the probability
5. Output the final probability alongside the qualitative decision label

The 5-stage reasoning trace is preserved as an explanation layer but the final decision is anchored to the computed probability.
