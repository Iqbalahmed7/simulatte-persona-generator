# SPRINT 1 BRIEF — CODEX
**Role:** Taxonomy Architect
**Sprint:** 1 — Foundation: Schema + Taxonomy
**Spec check:** Master Spec §6 (Taxonomy Strategy — Layer 1), §14A S4 (anchor-first settled), S6 (progressive filling settled)
**Previous rating:** n/a (Sprint 1)

---

## Your Job This Sprint

You own the base taxonomy. This is the attribute library that every persona will be built from. It must be domain-agnostic, decision-relevant, and structured for progressive conditional filling.

One file. It will be imported by the attribute filler (Goose's code).

---

## File: `src/taxonomy/base_taxonomy.py`

### What to Build

A structured Python module defining:
1. All ~150 base attributes across 6 categories
2. The 8 anchor attributes (filled first, in order)
3. Each attribute's metadata (type, range, description, population prior)

### Taxonomy Structure

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class AttributeDefinition:
    name: str
    category: str
    attr_type: Literal["continuous", "categorical"]

    # For continuous attributes:
    range_min: float | None = None      # typically 0.0
    range_max: float | None = None      # typically 1.0

    # For categorical attributes:
    options: list[str] | None = None    # valid option set

    description: str = ""               # what this attribute means for decision-making
    population_prior: float | None = None  # central tendency (0.0–1.0 for continuous)
    is_anchor: bool = False             # True for the 8 core attributes
    anchor_order: int | None = None     # 1-8, filled in this order before all others

    # Correlation hints (used by filler to maintain consistency)
    positive_correlates: list[str] = None   # attribute names that should move together
    negative_correlates: list[str] = None   # attribute names that should move inversely
```

### The 6 Categories — Target Attribute Counts

| Category | Target Count | What It Covers |
|----------|-------------|----------------|
| `psychology` | 30 | Decision biases, risk tolerance, emotional responsiveness, cognitive style, information processing |
| `values` | 25 | Priorities (price, quality, status, relationships, independence, security), moral foundations, identity orientation |
| `social` | 25 | Peer influence, authority trust, social proof sensitivity, conformity, WOM patterns, community engagement |
| `lifestyle` | 25 | Routines, time orientation, convenience preferences, health consciousness, tech comfort, media consumption |
| `identity` | 20 | Self-concept, aspiration gap, life satisfaction, agency, locus of control |
| `decision_making` | 25 | Analysis depth, decision speed, delegation patterns, regret sensitivity, satisficing vs maximizing |

**Total target: ~150. Acceptable range: 130–180.**

### The 8 Anchor Attributes (IS_ANCHOR = TRUE)

These are filled first, in this order, before all other attributes. Set `is_anchor=True` and `anchor_order=1` through `8`:

1. **personality_type** — Big Five mapped to decision orientation. Categorical: `["analytical_conscientious", "empathetic_agreeable", "independent_open", "cautious_neurotic", "social_extraverted"]`
2. **risk_tolerance** — Continuous 0.0–1.0. How willing to try new, untested options.
3. **trust_orientation_primary** — Categorical: `["self", "peer", "authority", "family"]`. Who they listen to most.
4. **economic_constraint_level** — Continuous 0.0–1.0. How much financial pressure shapes decisions (not income — this is the felt constraint).
5. **life_stage_priority** — Categorical: `["establishing", "building_family", "mid_career", "caregiver", "established", "transitioning"]`
6. **primary_value_driver** — Categorical: `["price", "quality", "brand", "convenience", "relationships", "status"]`
7. **social_orientation** — Continuous 0.0–1.0. How much social approval factors into decisions (0 = fully independent, 1 = fully socially-driven).
8. **tension_seed** — Categorical: `["aspiration_vs_constraint", "independence_vs_validation", "quality_vs_budget", "loyalty_vs_curiosity", "control_vs_delegation"]`. The primary internal contradiction.

### Example Attributes to Include Per Category

**Psychology (30):**
- `information_need` — how much research before deciding
- `analysis_paralysis` — tendency to delay despite sufficient info
- `loss_aversion` — sensitivity to potential losses vs gains
- `status_quo_bias` — preference for current state
- `health_anxiety` — tendency to over-index on health/safety claims
- `fear_appeal_responsiveness` — how much fear-based messaging moves them
- `emotional_persuasion_susceptibility` — emotional vs rational weighting
- `optimism_bias` — expectation that things will go well
- `sunk_cost_sensitivity` — weight given to past investments
- `scarcity_responsiveness` — response to limited availability framing
- ... (20 more in this space)

**Values (25):**
- `brand_loyalty` — strength of attachment to known brands
- `indie_brand_openness` — willingness to try unknown brands
- `deal_seeking_intensity` — active pursuit of discounts
- `environmental_consciousness` — weight given to sustainability
- `family_centricity` — extent to which family drives decisions
- `achievement_orientation` — career and status as motivators
- ... (19 more)

**Social (25):**
- `social_proof_bias` — how much peer behaviour influences own
- `wom_receiver_openness` — receptivity to word-of-mouth
- `authority_bias` — weight given to expert/official endorsement
- `peer_influence_strength` — strength of close social network pull
- `online_community_trust` — trust in online forums and reviews
- `influencer_susceptibility` — susceptibility to creator endorsements
- ... (19 more)

**Lifestyle (25):**
- `convenience_preference` — how much friction affects choices
- `routine_adherence` — strength of established habits
- `perceived_time_scarcity` — felt lack of time
- `digital_first_behavior` — tendency to research/buy online
- `health_consciousness` — general health-seeking behavior
- `impulsivity` — tendency toward unplanned decisions
- ... (19 more)

**Identity (20):**
- `aspiration_gap` — distance between current and desired self-image
- `self_efficacy` — belief in own ability to evaluate and decide
- `locus_of_control` — internal vs external attribution
- `identity_expression_through_purchase` — products as identity signals
- ... (16 more)

**Decision-making (25):**
- `research_before_purchase` — depth of pre-decision research
- `comparison_shopping` — tendency to compare across options
- `decision_delegation` — tendency to outsource choices to others
- `post_purchase_regret_sensitivity` — fear of making the wrong choice
- `satisficing_vs_maximizing` — "good enough" vs "best possible"
- ... (20 more)

### Correlation Hints (implement for these pairs)

```python
# These are used by the attribute filler to enforce consistency
KNOWN_CORRELATIONS = [
    ("budget_consciousness", "deal_seeking_intensity", "positive"),
    ("social_proof_bias", "wom_receiver_openness", "positive"),
    ("brand_loyalty", "indie_brand_openness", "negative"),
    ("risk_tolerance", "status_quo_bias", "negative"),
    ("information_need", "research_before_purchase", "positive"),
    ("perceived_time_scarcity", "convenience_preference", "positive"),
    ("authority_bias", "self_efficacy", "negative"),
    ("analysis_paralysis", "decision_delegation", "positive"),
]
```

### Module-Level Exports

```python
# All attributes as a list
BASE_TAXONOMY: list[AttributeDefinition] = [...]

# Anchor attributes in fill order
ANCHOR_ATTRIBUTES: list[AttributeDefinition] = [
    a for a in BASE_TAXONOMY if a.is_anchor
]
ANCHOR_ATTRIBUTES.sort(key=lambda a: a.anchor_order)

# By category
TAXONOMY_BY_CATEGORY: dict[str, list[AttributeDefinition]] = {
    "psychology": [...],
    "values": [...],
    "social": [...],
    "lifestyle": [...],
    "identity": [...],
    "decision_making": [...],
}

# Quick lookup
TAXONOMY_BY_NAME: dict[str, AttributeDefinition] = {
    a.name: a for a in BASE_TAXONOMY
}
```

---

## Constraints

- **No domain-specific attributes.** If an attribute only makes sense for one product category (e.g., `pediatrician_trust`, `saas_feature_complexity`), it belongs in a domain template, not here. See OpenCode's brief.
- **No numerical decision parameters.** Attributes are psychological/psychographic traits, not logistic function coefficients.
- **All continuous attributes** must have `range_min=0.0`, `range_max=1.0`, `population_prior` set to a realistic central tendency.
- **Attribute names** must be snake_case, descriptive, and consistent with the schema's `source` vocabulary.
- If you invent attribute names that are referenced in `references/architecture.md` (existing constraints), match the names exactly: `budget_consciousness`, `social_proof_bias`, `brand_loyalty`, `risk_tolerance`, `authority_bias`, `information_need`, `status_quo_bias`, `convenience_preference`, `deal_seeking_intensity`.

---

## Outcome File

When done, write `sprints/outcome_codex.md` with:
1. File created (with total attribute count per category)
2. Complete list of the 8 anchor attributes and their order
3. Any attributes where you were uncertain about the right category
4. Any attributes from `references/architecture.md` that you matched by name
5. Known gaps: categories where you felt the attributes were thin
