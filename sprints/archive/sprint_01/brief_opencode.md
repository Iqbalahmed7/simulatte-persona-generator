# SPRINT 1 BRIEF — OPENCODE
**Role:** Domain Template Architect
**Sprint:** 1 — Foundation: Schema + Taxonomy
**Spec check:** Master Spec §6 (Taxonomy Strategy — Layer 2), §14A S9 (domain-agnostic core settled)
**Previous rating:** n/a (Sprint 1)

---

## Your Job This Sprint

You build the domain extension layer — the 30–60 domain-specific attributes that sit on top of the base taxonomy for a given domain. You also build the template loader that merges a domain template into the base taxonomy for use by the attribute filler.

Three files. They extend the base taxonomy (Codex's code) — they do not replace it.

---

## Files

```
src/taxonomy/domain_templates/
  cpg.py            ← Consumer packaged goods domain extension
  saas.py           ← SaaS / B2B domain extension
  template_loader.py ← Template selection + base + domain merge
```

---

## File 1: `src/taxonomy/domain_templates/cpg.py`

### What It Does

Defines 30–60 domain-specific attributes for the CPG (consumer packaged goods) domain. These cover purchase behaviour specific to physical products bought regularly: grocery, FMCG, personal care, household goods.

### Structure

```python
from src.taxonomy.base_taxonomy import AttributeDefinition
from typing import Literal

CPG_DOMAIN_ATTRIBUTES: list[AttributeDefinition] = [
    AttributeDefinition(
        name="private_label_acceptance",
        category="values",
        attr_type="continuous",
        range_min=0.0,
        range_max=1.0,
        population_prior=0.5,
        description="Willingness to buy store-brand alternatives over national brands.",
        is_anchor=False,
    ),
    # ... (30-60 total)
]
```

### Attribute Coverage Required (CPG)

You must cover these decision-relevant areas for CPG personas:

| Area | Example Attributes |
|------|--------------------|
| **Brand relationship** | private_label_acceptance, national_brand_attachment, pack_size_preference |
| **Shopping channel** | online_grocery_adoption, modern_trade_preference, kirana_preference (India-relevant) |
| **Promotion response** | coupon_redemption_rate, bundle_offer_responsiveness, cashback_sensitivity |
| **Category involvement** | personal_care_involvement, food_health_involvement, household_product_involvement |
| **Replenishment pattern** | stockpiling_tendency, pantry_loading_frequency, subscription_box_openness |
| **Label reading** | ingredient_scrutiny, nutritional_label_check, country_of_origin_sensitivity |
| **Social/occasion** | gifting_frequency, occasion_driven_purchase, impulse_at_checkout |
| **Trial** | new_product_trial_rate, category_exploration_width |

**Total: 35–50 attributes.** Do not pad to hit a number — include what is decision-relevant.

### Constraints

- Every attribute must map to a valid `category` from the base taxonomy: `psychology`, `values`, `social`, `lifestyle`, `identity`, `decision_making`.
- No attribute that already exists in the base taxonomy (e.g., `deal_seeking_intensity`, `brand_loyalty`, `convenience_preference` are in the base — do not duplicate).
- Use `is_anchor=False` for all domain extension attributes.
- `population_prior` must be set to a realistic CPG population central tendency.
- All continuous attributes use `range_min=0.0`, `range_max=1.0`.

---

## File 2: `src/taxonomy/domain_templates/saas.py`

### What It Does

Defines 30–60 domain-specific attributes for the SaaS / B2B domain. These cover software evaluation and adoption behaviour for business decision-makers (SMB owner, procurement lead, team manager).

### Structure

Same pattern as `cpg.py`:

```python
from src.taxonomy.base_taxonomy import AttributeDefinition

SAAS_DOMAIN_ATTRIBUTES: list[AttributeDefinition] = [
    AttributeDefinition(
        name="feature_complexity_tolerance",
        category="psychology",
        attr_type="continuous",
        range_min=0.0,
        range_max=1.0,
        population_prior=0.4,
        description="Willingness to learn complex feature sets in exchange for power and control.",
        is_anchor=False,
    ),
    # ... (30-60 total)
]
```

### Attribute Coverage Required (SaaS)

| Area | Example Attributes |
|------|--------------------|
| **Evaluation style** | free_trial_dependency, proof_of_concept_requirement, demo_request_tendency |
| **Buying authority** | solo_decision_authority, procurement_process_tolerance, committee_buy_in_need |
| **Feature vs UX** | feature_complexity_tolerance, ux_over_features_preference, onboarding_patience |
| **Vendor relationship** | vendor_trust_sensitivity, sales_rep_influence, csm_engagement_preference |
| **Switching cost perception** | data_migration_anxiety, integration_lock_in_sensitivity, switching_cost_aversion |
| **Pricing model** | per_seat_preference, usage_based_comfort, annual_commitment_willingness |
| **Growth orientation** | scalability_concern, enterprise_upgrade_aspiration, startup_tool_openness |
| **Security/compliance** | security_compliance_prioritisation, data_sovereignty_concern, audit_trail_need |

**Total: 35–50 attributes.**

### Constraints

Same as CPG — no duplication of base taxonomy attributes.

---

## File 3: `src/taxonomy/domain_templates/template_loader.py`

### What It Does

Selects the right domain template and merges it with the base taxonomy into a single ordered list that the attribute filler can consume.

### Interface

```python
from src.taxonomy.base_taxonomy import AttributeDefinition, BASE_TAXONOMY
from src.taxonomy.domain_templates.cpg import CPG_DOMAIN_ATTRIBUTES
from src.taxonomy.domain_templates.saas import SAAS_DOMAIN_ATTRIBUTES

DOMAIN_REGISTRY: dict[str, list[AttributeDefinition]] = {
    "cpg": CPG_DOMAIN_ATTRIBUTES,
    "saas": SAAS_DOMAIN_ATTRIBUTES,
}

def load_taxonomy(domain: str) -> list[AttributeDefinition]:
    """
    Returns the full merged taxonomy for the given domain:
    BASE_TAXONOMY + domain extension attributes.

    Domain attributes are appended after base taxonomy attributes.
    Anchors are not modified — they always come from the base taxonomy.

    Raises ValueError if domain is not registered.
    """
    ...

def get_domain_attributes(domain: str) -> list[AttributeDefinition]:
    """
    Returns only the domain extension attributes (not the base taxonomy).
    Used by the attribute filler to know which attributes are domain-specific
    (to be filled last, conditioned on the full base profile).
    """
    ...

def list_domains() -> list[str]:
    """Returns all registered domain names."""
    return list(DOMAIN_REGISTRY.keys())
```

### Merge Rules

1. Base taxonomy attributes always come first.
2. Domain extension attributes are appended after base taxonomy attributes.
3. The filling order contract: anchors → base non-anchors → domain-specific.
4. If a domain attribute shares a name with a base attribute, raise `ValueError` on load (duplication is a programming error, not a runtime condition).
5. `load_taxonomy("unknown_domain")` raises `ValueError` with a helpful message listing valid domains.

### The `domain` Field

The `domain` value passed to `load_taxonomy()` comes from `PersonaRecord.domain` (set at generation time). Match it case-insensitively and strip whitespace to be robust, but do not infer — if the domain is not registered, fail loudly.

---

## Integration Contract

- **Imports from Codex:** `from src.taxonomy.base_taxonomy import AttributeDefinition, BASE_TAXONOMY`
- **Consumed by Goose:** `from src.taxonomy.domain_templates.template_loader import load_taxonomy, get_domain_attributes`
- **Domain attributes** passed to `get_domain_attributes()` are filled last in the attribute filler (they are conditioned on the full base profile).

---

## Constraints

- **No domain-specific attributes in base_taxonomy.py.** Any attribute that only makes sense for one domain belongs here, not there. If you find yourself wanting to add something to the base taxonomy, stop — put it in the domain template.
- **No anchor attributes in domain templates.** Domain templates only extend — they do not define new anchors.
- **No numerical coefficients.** Domain attributes are the same kind (psychographic/behavioural traits) as base taxonomy attributes.
- **Names must be snake_case, descriptive, and not already present in the base taxonomy.** Check Codex's attribute names before writing yours.

---

## Outcome File

When done, write `sprints/outcome_opencode.md` with:
1. Files created (with attribute counts per file)
2. CPG attribute list (all names + category)
3. SaaS attribute list (all names + category)
4. Any attribute you were unsure whether to put in base vs domain (list and explain)
5. Any attribute names that overlap with base taxonomy names (ideally: zero)
6. Known gaps in CPG or SaaS coverage
