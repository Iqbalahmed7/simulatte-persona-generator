# Persona Output Schema

Full JSON schema with field definitions. Every persona output must conform to this structure.

## Top-Level Schema

```json
{
  "persona_id": "pg-[domain_prefix]-[001]",
  "generated_at": "2026-04-01T10:00:00Z",
  "generator_version": "1.0",
  "domain": "string — e.g. 'indian-parent-nutrition', 'saas-mid-market-buyer'",
  "mode": "quick | deep | simulation-ready",

  "demographic_anchor": { ... },
  "life_stories": [ ... ],
  "attributes": { ... },
  "derived_insights": { ... },
  "narrative": "string — 2000 chars, first-person",
  "decision_bullets": ["string", ...],
  "memory": { ... }
}
```

---

## demographic_anchor

```json
{
  "name": "string — realistic name for the population (not generic)",
  "age": 34,
  "gender": "female | male | non-binary",
  "location": {
    "country": "string",
    "region": "string",
    "city": "string",
    "urban_tier": "metro | tier2 | tier3 | rural"
  },
  "household": {
    "structure": "nuclear | joint | single-parent | couple-no-kids | other",
    "size": 4,
    "income_bracket": "string — e.g. '8-12 LPA' or '$50-80k'",
    "dual_income": true
  },
  "life_stage": "string — e.g. 'new parent', 'mid-career professional', 'empty nester'",
  "education": "high-school | undergraduate | postgraduate | doctoral",
  "employment": "full-time | part-time | self-employed | homemaker | student | retired"
}
```

---

## life_stories

Array of 2-3 vignettes. Each:

```json
{
  "title": "string — short descriptive title",
  "when": "string — age or life period, e.g. 'age 12' or 'after first child'",
  "event": "string — concrete, specific description, 100-150 words",
  "lasting_impact": "string — how this shaped their values/behaviour today, 2-3 sentences"
}
```

---

## attributes

Organized by category. All continuous values are 0.0–1.0 (UnitInterval).
Categorical values use the specified option set.

```json
{
  "[category_name]": {
    "[attribute_name]": {
      "value": 0.72,
      "type": "continuous | categorical",
      "label": "string — human-readable label for this value, e.g. 'high'",
      "source": "sampled | inferred | anchored | domain_data"
    }
  }
}
```

**source field meanings:**
- `sampled` — drawn from the demographic distribution
- `inferred` — derived from life stories or other attributes
- `anchored` — set by user-provided anchor trait
- `domain_data` — extracted from provided forum/review text

**Mandatory categories (always present):**
- `psychology` — decision-making biases, risk tolerance, emotional responsiveness
- `values` — what they prioritise (price, quality, brand, relationships)
- `social` — peer influence, WOM sensitivity, authority bias
- `lifestyle` — daily routines, convenience vs. effort trade-offs
- `domain_specific` — attributes specific to the business problem

---

## derived_insights

Always computed deterministically from attributes (never LLM-generated).

```json
{
  "decision_style": "emotional | analytical | habitual | social",
  "decision_style_score": 0.72,
  "trust_anchor": "self | peer | authority | family",
  "risk_appetite": "low | medium | high",
  "primary_value_orientation": "price | quality | brand | convenience | features",
  "coping_mechanism": {
    "type": "routine_control | social_validation | research_deep_dive | denial | optimism_bias",
    "description": "string — 1-2 sentence behavioural description"
  },
  "consistency_score": 78,
  "consistency_band": "low | medium | high",
  "key_tensions": [
    "string — e.g. 'Wants best-for-child but faces hard budget ceiling'",
    "string"
  ]
}
```

---

## behavioural_params

Added in next-phase architecture (Sprint A). Present in Grounded Mode and Simulation-Ready Mode. Optional in Quick Mode (populated with proxy estimates if omitted).

See `references/behavioural_grounding.md` for full parameter definitions, proxy formulas, and calibration rules.

```json
{
  "behavioural_params": {
    "mode": "grounded | proxy | benchmark_calibrated",
    "purchase_prob": {
      "intercept": 0.42,
      "price_gap_coeff": -0.31,
      "need_intensity_coeff": 0.55,
      "trust_level_coeff": 0.48,
      "baseline_at_ask_price": 0.62,
      "source": "cluster_estimated | proxy_estimated | benchmark_calibrated",
      "calibration_applied": false,
      "calibration_factor": null,
      "calibrated_baseline": null
    },
    "price_elasticity": {
      "value": -0.38,
      "band": "low | medium | high | extreme",
      "source": "cluster_estimated | proxy_estimated",
      "proxy_signal": "string — formula used if proxy_estimated"
    },
    "switching_hazard": {
      "baseline_rate_per_period": 0.04,
      "satisfaction_multiplier": 0.6,
      "competitive_stimulus_multiplier": 1.8,
      "switching_cost_index": 0.45,
      "estimated_tenure_periods": 18,
      "source": "cluster_estimated | proxy_estimated"
    },
    "trust_vector": {
      "expert": 0.72,
      "peer": 0.85,
      "brand": 0.28,
      "ad": 0.12,
      "community": 0.61,
      "influencer": 0.44,
      "dominant_anchor": "peer",
      "source": "cluster_estimated | proxy_estimated"
    },
    "objection_profile": [
      {
        "objection_type": "string — from standard vocabulary",
        "probability": 0.58,
        "severity": "blocking | friction | minor",
        "addressability": "high | medium | low"
      }
    ]
  }
}
```

---

## memory

Always present, even if not in simulation-ready mode (fields will be empty).

```json
{
  "core_memory": {
    "identity_statement": "string — 25-word first-person summary",
    "key_values": ["string", "string", "string"],
    "life_defining_events": [
      {
        "age_when": 9,
        "event": "string — brief description",
        "lasting_impact": "string"
      }
    ],
    "relationship_map": {
      "primary_decision_partner": "string",
      "key_influencers": ["string"],
      "trust_network": ["string"]
    },
    "immutable_constraints": {
      "budget_ceiling": "string | null",
      "non_negotiables": ["string"],
      "absolute_avoidances": ["string"]
    }
  },
  "operational_stream": [],
  "brand_memories": {},
  "purchase_history": [],
  "simulation_state": {
    "current_turn": 0,
    "importance_accumulator": 0.0,
    "reflection_count": 0,
    "awareness": {},
    "consideration_set": [],
    "last_decision": null
  }
}
```

---

## Cohort Array

When generating multiple personas, wrap in a cohort envelope:

```json
{
  "cohort_id": "cohort-[domain]-[timestamp]",
  "generated_at": "ISO datetime",
  "domain": "string",
  "business_problem": "string — the original business problem statement",
  "mode": "quick | deep | simulation-ready",
  "taxonomy_used": {
    "categories": ["string"],
    "total_attributes": 42,
    "domain_data_used": true
  },
  "personas": [ { ... }, { ... } ],
  "cohort_summary": {
    "decision_style_distribution": {
      "emotional": 0.4, "analytical": 0.2, "habitual": 0.2, "social": 0.2
    },
    "trust_anchor_distribution": {
      "self": 0.3, "peer": 0.4, "authority": 0.2, "family": 0.1
    },
    "risk_appetite_distribution": {
      "low": 0.3, "medium": 0.5, "high": 0.2
    },
    "consistency_scores": {
      "mean": 74, "min": 61, "max": 91
    },
    "behavioural_params_summary": {
      "price_elasticity_distribution": {
        "low": 0.3, "medium": 0.5, "high": 0.2
      },
      "mean_baseline_purchase_prob": 0.48,
      "mean_baseline_switch_rate": 0.04,
      "dominant_trust_anchor": "peer",
      "top_objection_types": ["need_more_information", "price_vs_value", "trust_deficit"],
      "params_source_distribution": {
        "cluster_estimated": 0.0,
        "proxy_estimated": 1.0,
        "benchmark_calibrated": 0.0
      }
    },
    "calibration_state": {
      "status": "uncalibrated | benchmark_calibrated | client_calibrated | calibration_failed",
      "method_applied": "benchmark_anchoring | client_cohort_feedback | none",
      "last_calibrated": "ISO datetime | null",
      "benchmark_source": "string | null",
      "pre_calibration_metrics": {
        "conversion_rate": null,
        "churn_rate": null,
        "kl_divergence": null
      },
      "post_calibration_metrics": {
        "conversion_rate": null,
        "churn_rate": null,
        "kl_divergence": null
      },
      "intercept_adjustment_applied": null,
      "segments_adjusted": [],
      "notes": "string | null"
    },
    "coverage_assessment": "string — 2-3 sentences on diversity and gaps",
    "dominant_tensions": ["string", "string"]
  }
}
```

---

## Persona ID Convention

Format: `pg-[domain_prefix]-[3-digit-number]`

Domain prefix examples:
- `inp` — Indian parent / nutrition
- `smb` — SaaS mid-market buyer
- `ftb` — first-time buyer (real estate)
- `hlc` — healthcare consumer
- `gen` — generic / no specific domain

Example: `pg-inp-007`, `pg-smb-023`

---

## Summary Card (Markdown)

The human-readable output. One per persona.

```markdown
## [Name], [age], [city] — `[persona_id]`

> [identity_statement from core_memory — 25 words]

**Decision profile:** [decision_style] · [trust_anchor] · [risk_appetite] risk · [primary_value_orientation]-focused

**Life in brief:**
[2-3 sentences weaving together life story highlights]

**Key tensions:**
- [tension_1]
- [tension_2]

**What drives their decision:**
[coping_mechanism description]

**Decision bullets:**
- [bullet_1]
- [bullet_2]
- [bullet_3]
- [bullet_4]
- [bullet_5]
- [bullet_6]

**Consistency score:** [score]/100 ([band])

---
*Generated by persona-generator skill v1.0 | [domain] | [timestamp]*
```
