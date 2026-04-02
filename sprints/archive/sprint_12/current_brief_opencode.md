# SPRINT 12 BRIEF — OPENCODE
**Role:** Health & Wellness Domain Template
**Sprint:** 12 — Persistence + Reporting
**Spec ref:** Master Spec §6 (Domain Template Strategy), §14C (v1 domain coverage)
**Previous rating:** 20/20

---

## Context

The template library has CPG and SaaS. Sprint 12 adds a Health & Wellness (H&W) template — the third vertical and a natural fit given the `health_supplement_belief` attribute just added in Sprint 11. Domain templates add 30–60 domain-specific attributes on top of the base taxonomy.

---

## File: `src/taxonomy/domain_templates/health_wellness.py`

```python
"""Health & Wellness domain template.

Sprint 12. Domain-specific attributes for health, fitness, nutrition,
and wellness product categories.

Adds 35–45 attributes across 4 supplement categories:
- health_attitudes      — beliefs and orientations toward health
- health_behaviours     — observable health-related activities
- health_consumption    — product/channel consumption patterns
- health_information    — how they seek and evaluate health information

Base taxonomy attributes (health_anxiety, health_consciousness,
health_supplement_belief) are the bridge to this template —
they are already in base_taxonomy.py and are referenced but not duplicated.
"""
from __future__ import annotations

from src.taxonomy.domain_templates.template_loader import DomainAttribute, DomainTemplate


HEALTH_WELLNESS_TEMPLATE = DomainTemplate(
    domain="health_wellness",
    description="Health, fitness, nutrition, and wellness products and services.",
    attributes=[
        # ── health_attitudes ──────────────────────────────────────────────
        DomainAttribute(
            name="preventive_health_orientation",
            category="health_attitudes",
            description="Degree to which persona prioritises prevention over treatment.",
            attr_type="continuous",
            default_value=0.55,
        ),
        DomainAttribute(
            name="holistic_health_belief",
            category="health_attitudes",
            description="Belief that physical, mental, and spiritual health are interconnected.",
            attr_type="continuous",
            default_value=0.50,
        ),
        DomainAttribute(
            name="scepticism_of_pharma",
            category="health_attitudes",
            description="Distrust of pharmaceutical companies and conventional medicine.",
            attr_type="continuous",
            default_value=0.30,
        ),
        DomainAttribute(
            name="fitness_identity",
            category="health_attitudes",
            description="Extent to which being fit/active is central to self-image.",
            attr_type="continuous",
            default_value=0.45,
        ),
        DomainAttribute(
            name="body_image_concern",
            category="health_attitudes",
            description="Level of concern about physical appearance and body composition.",
            attr_type="continuous",
            default_value=0.48,
        ),
        DomainAttribute(
            name="natural_product_preference",
            category="health_attitudes",
            description="Preference for natural, organic, or clean-label products.",
            attr_type="continuous",
            default_value=0.60,
        ),
        DomainAttribute(
            name="health_fatalism",
            category="health_attitudes",
            description="Belief that health outcomes are largely predetermined by genetics/fate.",
            attr_type="continuous",
            default_value=0.28,
        ),

        # ── health_behaviours ─────────────────────────────────────────────
        DomainAttribute(
            name="exercise_frequency",
            category="health_behaviours",
            description="Frequency of intentional physical exercise (0=never, 1=daily).",
            attr_type="continuous",
            default_value=0.45,
        ),
        DomainAttribute(
            name="dietary_restriction_adherence",
            category="health_behaviours",
            description="Strictness of adherence to dietary rules (vegan, keto, etc.).",
            attr_type="continuous",
            default_value=0.30,
        ),
        DomainAttribute(
            name="sleep_hygiene",
            category="health_behaviours",
            description="Consistency and quality of sleep practices.",
            attr_type="continuous",
            default_value=0.55,
        ),
        DomainAttribute(
            name="stress_management_activity",
            category="health_behaviours",
            description="Active use of stress-reduction practices (meditation, yoga, etc.).",
            attr_type="continuous",
            default_value=0.40,
        ),
        DomainAttribute(
            name="healthcare_provider_visit_frequency",
            category="health_behaviours",
            description="How often persona proactively visits doctors/practitioners.",
            attr_type="continuous",
            default_value=0.40,
        ),
        DomainAttribute(
            name="self_monitoring_behaviour",
            category="health_behaviours",
            description="Use of wearables/apps to track health metrics.",
            attr_type="continuous",
            default_value=0.38,
        ),

        # ── health_consumption ────────────────────────────────────────────
        DomainAttribute(
            name="supplement_spend_willingness",
            category="health_consumption",
            description="Willingness to spend on dietary supplements and vitamins.",
            attr_type="continuous",
            default_value=0.45,
        ),
        DomainAttribute(
            name="functional_food_adoption",
            category="health_consumption",
            description="Adoption of functional foods (fortified, probiotic, protein-enriched).",
            attr_type="continuous",
            default_value=0.48,
        ),
        DomainAttribute(
            name="pharmacy_vs_online_channel_preference",
            category="health_consumption",
            description="Preference for pharmacy (1.0) vs online health retailers (0.0).",
            attr_type="continuous",
            default_value=0.55,
        ),
        DomainAttribute(
            name="brand_loyalty_health_products",
            category="health_consumption",
            description="Tendency to repurchase the same health product brands.",
            attr_type="continuous",
            default_value=0.52,
        ),
        DomainAttribute(
            name="subscription_model_affinity",
            category="health_consumption",
            description="Comfort with subscribing to regular health product deliveries.",
            attr_type="continuous",
            default_value=0.38,
        ),
        DomainAttribute(
            name="premium_health_product_tolerance",
            category="health_consumption",
            description="Willingness to pay premium prices for perceived health benefits.",
            attr_type="continuous",
            default_value=0.48,
        ),

        # ── health_information ────────────────────────────────────────────
        DomainAttribute(
            name="doctor_recommendation_weight",
            category="health_information",
            description="Importance placed on doctor/clinician recommendations.",
            attr_type="continuous",
            default_value=0.72,
        ),
        DomainAttribute(
            name="peer_health_influence",
            category="health_information",
            description="Susceptibility to health advice from friends and family.",
            attr_type="continuous",
            default_value=0.55,
        ),
        DomainAttribute(
            name="social_media_health_content_consumption",
            category="health_information",
            description="Time spent consuming health content on social media.",
            attr_type="continuous",
            default_value=0.42,
        ),
        DomainAttribute(
            name="clinical_evidence_requirement",
            category="health_information",
            description="Demand for clinical trial / scientific evidence before adopting.",
            attr_type="continuous",
            default_value=0.55,
        ),
        DomainAttribute(
            name="health_influencer_trust",
            category="health_information",
            description="Trust placed in health influencers and fitness content creators.",
            attr_type="continuous",
            default_value=0.35,
        ),
        DomainAttribute(
            name="label_reading_diligence",
            category="health_information",
            description="Tendency to carefully read ingredient lists and nutrition labels.",
            attr_type="continuous",
            default_value=0.58,
        ),
        DomainAttribute(
            name="alternative_medicine_openness",
            category="health_information",
            description="Openness to Ayurveda, homeopathy, traditional medicine, etc.",
            attr_type="continuous",
            default_value=0.40,
        ),
    ],
)
```

---

## Add health_wellness to `src/taxonomy/domain_templates/template_loader.py`

Read `template_loader.py` first to understand the existing pattern, then register the new template. Look for where `CPG_TEMPLATE` and `SAAS_TEMPLATE` are registered (likely a `DOMAIN_TEMPLATES` dict or `get_template()` function).

Add:
```python
from src.taxonomy.domain_templates.health_wellness import HEALTH_WELLNESS_TEMPLATE
# Then register it in whatever pattern the file uses (dict, list, etc.)
```

---

## File: `tests/test_domain_health.py`

### Test 1: health_wellness template loads without error

```python
def test_hw_template_loads():
    from src.taxonomy.domain_templates.health_wellness import HEALTH_WELLNESS_TEMPLATE
    assert HEALTH_WELLNESS_TEMPLATE is not None
    assert HEALTH_WELLNESS_TEMPLATE.domain == "health_wellness"
```

### Test 2: template has 25+ attributes

```python
def test_hw_template_attribute_count():
    from src.taxonomy.domain_templates.health_wellness import HEALTH_WELLNESS_TEMPLATE
    count = len(HEALTH_WELLNESS_TEMPLATE.attributes)
    assert count >= 25, f"Expected ≥25 attributes, got {count}"
```

### Test 3: all attributes have valid continuous default values

```python
def test_hw_template_valid_defaults():
    from src.taxonomy.domain_templates.health_wellness import HEALTH_WELLNESS_TEMPLATE
    for attr in HEALTH_WELLNESS_TEMPLATE.attributes:
        assert attr.attr_type == "continuous"
        assert 0.0 <= attr.default_value <= 1.0, (
            f"{attr.name}: default_value {attr.default_value} out of [0,1]"
        )
```

### Test 4: expected categories are present

```python
def test_hw_template_categories():
    from src.taxonomy.domain_templates.health_wellness import HEALTH_WELLNESS_TEMPLATE
    categories = {attr.category for attr in HEALTH_WELLNESS_TEMPLATE.attributes}
    assert "health_attitudes" in categories
    assert "health_behaviours" in categories
    assert "health_consumption" in categories
    assert "health_information" in categories
```

### Test 5: template loader can retrieve health_wellness template

```python
def test_template_loader_finds_hw():
    """health_wellness must be discoverable via template_loader."""
    from src.taxonomy.domain_templates.template_loader import get_template
    # get_template may accept "health_wellness" or a case variant — try both
    try:
        template = get_template("health_wellness")
    except Exception:
        # If get_template raises for unknown domain, check the registry dict directly
        from src.taxonomy.domain_templates import template_loader
        registry = getattr(template_loader, "DOMAIN_TEMPLATES", None)
        if registry:
            assert "health_wellness" in registry or "health" in str(registry)
            return
        raise
    assert template is not None
```

### Test 6: No attribute names clash with base taxonomy

```python
def test_hw_no_name_clashes_with_base_taxonomy():
    from src.taxonomy.domain_templates.health_wellness import HEALTH_WELLNESS_TEMPLATE
    from src.taxonomy.base_taxonomy import BASE_TAXONOMY

    base_names = {a.name for a in BASE_TAXONOMY}
    hw_names = {a.name for a in HEALTH_WELLNESS_TEMPLATE.attributes}
    clashes = base_names & hw_names
    assert clashes == set(), f"Name clashes with base taxonomy: {clashes}"
```

---

## Constraints

- No LLM calls.
- Read `template_loader.py` first to understand `DomainAttribute`, `DomainTemplate` signatures and how templates are registered.
- All `DomainAttribute` fields must match exactly what `template_loader.py` defines — check field names (`name`, `category`, `description`, `attr_type`, `default_value` — but verify first).
- 6 tests, all pass without `--integration`.
- Full suite must remain 186+ passed.

---

## Outcome File

Write `sprints/outcome_opencode.md` with:
1. Files created (line counts)
2. Attribute categories overview
3. Template loader registration approach
4. Test results (6/6)
5. Full suite result
6. Known gaps
