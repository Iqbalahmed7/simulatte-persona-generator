"""Health & Wellness domain template.

Sprint 12. Domain-specific attributes for health, fitness, nutrition,
and wellness product categories.

Adds 27 attributes across 4 domain categories:
- health_attitudes      — beliefs and orientations toward health
- health_behaviours     — observable health-related activities
- health_consumption    — product/channel consumption patterns
- health_information    — how they seek and evaluate health information

Base taxonomy attributes (health_anxiety, health_consciousness,
health_supplement_belief) are the bridge to this template —
they are already in base_taxonomy.py and are referenced but not duplicated.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.taxonomy.base_taxonomy import AttributeDefinition


@dataclass
class DomainTemplate:
    """Lightweight wrapper that groups domain attributes with metadata."""

    domain: str
    description: str
    attributes: list[AttributeDefinition]


def _domain_attr_definitions(
    attrs: list[AttributeDefinition],
) -> list[AttributeDefinition]:
    for a in attrs:
        setattr(a, "is_domain_specific", True)

        pp = getattr(a, "population_prior", None)
        if isinstance(pp, (int, float)):
            v = float(pp)
            if v > 0.66:
                label = "high"
            elif v > 0.33:
                label = "medium"
            else:
                label = "low"
            setattr(a, "population_prior", {"value": v, "label": label})
    return attrs


HEALTH_WELLNESS_DOMAIN_ATTRIBUTES: list[AttributeDefinition] = _domain_attr_definitions(
    [
        # ── health_attitudes ──────────────────────────────────────────────
        AttributeDefinition(
            name="preventive_health_orientation",
            category="health_attitudes",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.55,
            description="Degree to which persona prioritises prevention over treatment.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="holistic_health_belief",
            category="health_attitudes",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.50,
            description="Belief that physical, mental, and spiritual health are interconnected.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="scepticism_of_pharma",
            category="health_attitudes",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.30,
            description="Distrust of pharmaceutical companies and conventional medicine.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="fitness_identity",
            category="health_attitudes",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.45,
            description="Extent to which being fit/active is central to self-image.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="body_image_concern",
            category="health_attitudes",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.48,
            description="Level of concern about physical appearance and body composition.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="natural_product_preference",
            category="health_attitudes",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.60,
            description="Preference for natural, organic, or clean-label products.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="health_fatalism",
            category="health_attitudes",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.28,
            description="Belief that health outcomes are largely predetermined by genetics/fate.",
            is_anchor=False,
        ),

        # ── health_behaviours ─────────────────────────────────────────────
        AttributeDefinition(
            name="exercise_frequency",
            category="health_behaviours",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.45,
            description="Frequency of intentional physical exercise (0=never, 1=daily).",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="dietary_restriction_adherence",
            category="health_behaviours",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.30,
            description="Strictness of adherence to dietary rules (vegan, keto, etc.).",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="sleep_hygiene",
            category="health_behaviours",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.55,
            description="Consistency and quality of sleep practices.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="stress_management_activity",
            category="health_behaviours",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.40,
            description="Active use of stress-reduction practices (meditation, yoga, etc.).",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="healthcare_provider_visit_frequency",
            category="health_behaviours",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.40,
            description="How often persona proactively visits doctors/practitioners.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="self_monitoring_behaviour",
            category="health_behaviours",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.38,
            description="Use of wearables/apps to track health metrics.",
            is_anchor=False,
        ),

        # ── health_consumption ────────────────────────────────────────────
        AttributeDefinition(
            name="supplement_spend_willingness",
            category="health_consumption",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.45,
            description="Willingness to spend on dietary supplements and vitamins.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="functional_food_adoption",
            category="health_consumption",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.48,
            description="Adoption of functional foods (fortified, probiotic, protein-enriched).",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="pharmacy_vs_online_channel_preference",
            category="health_consumption",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.55,
            description="Preference for pharmacy (1.0) vs online health retailers (0.0).",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="brand_loyalty_health_products",
            category="health_consumption",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.52,
            description="Tendency to repurchase the same health product brands.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="subscription_model_affinity",
            category="health_consumption",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.38,
            description="Comfort with subscribing to regular health product deliveries.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="premium_health_product_tolerance",
            category="health_consumption",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.48,
            description="Willingness to pay premium prices for perceived health benefits.",
            is_anchor=False,
        ),

        # ── health_information ────────────────────────────────────────────
        AttributeDefinition(
            name="doctor_recommendation_weight",
            category="health_information",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.72,
            description="Importance placed on doctor/clinician recommendations.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="peer_health_influence",
            category="health_information",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.55,
            description="Susceptibility to health advice from friends and family.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="social_media_health_content_consumption",
            category="health_information",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.42,
            description="Time spent consuming health content on social media.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="clinical_evidence_requirement",
            category="health_information",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.55,
            description="Demand for clinical trial / scientific evidence before adopting.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="health_influencer_trust",
            category="health_information",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.35,
            description="Trust placed in health influencers and fitness content creators.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="label_reading_diligence",
            category="health_information",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.58,
            description="Tendency to carefully read ingredient lists and nutrition labels.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="alternative_medicine_openness",
            category="health_information",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.40,
            description="Openness to Ayurveda, homeopathy, traditional medicine, etc.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="wellness_app_engagement",
            category="health_information",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.36,
            description="Frequency of engaging with wellness and health-tracking apps.",
            is_anchor=False,
        ),
    ]
)


HEALTH_WELLNESS_TEMPLATE = DomainTemplate(
    domain="health_wellness",
    description="Health, fitness, nutrition, and wellness products and services.",
    attributes=HEALTH_WELLNESS_DOMAIN_ATTRIBUTES,
)


__all__ = ["HEALTH_WELLNESS_DOMAIN_ATTRIBUTES", "HEALTH_WELLNESS_TEMPLATE"]
