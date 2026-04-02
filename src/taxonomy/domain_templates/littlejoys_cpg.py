from __future__ import annotations

from src.taxonomy.base_taxonomy import AttributeDefinition
from src.taxonomy.domain_templates.cpg import CPG_DOMAIN_ATTRIBUTES, _domain_attr_definitions


# ---------------------------------------------------------------------------
# Littlejoys child-nutrition-specific domain attributes
# These extend the base CPG taxonomy with attributes relevant to Indian parent
# purchase decisions for child nutrition products.
#
# Note: elder_advice_weight and subscription_comfort are intentionally omitted
# here — they already exist in the base taxonomy.
# ---------------------------------------------------------------------------

_LITTLEJOYS_SPECIFIC: list[AttributeDefinition] = _domain_attr_definitions(
    [
        # -- child_nutrition group (belief/concern attributes) ---------------
        AttributeDefinition(
            name="supplement_necessity_belief",
            category="psychology",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.52,
            description=(
                "Degree to which the parent believes supplements are necessary "
                "for their child, as opposed to a food-first nutritional approach."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="immunity_concern",
            category="psychology",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.63,
            description=(
                "Level of parental concern about the child's immunity and "
                "susceptibility to illness; drives interest in immunity-boosting products."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="growth_concern",
            category="psychology",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.58,
            description=(
                "Level of parental concern about the child's physical growth, "
                "height, and weight relative to age-appropriate milestones."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="nutrition_gap_awareness",
            category="psychology",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.47,
            description=(
                "Parent's awareness that their child may be missing key nutrients "
                "from daily diet; higher values indicate active recognition of gaps."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="child_health_proactivity",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.55,
            description=(
                "Tendency to proactively address child health concerns rather than "
                "waiting until a problem arises; high values indicate prevention-first mindset."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="food_first_belief",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.49,
            description=(
                "Preference for meeting the child's nutritional needs through whole "
                "foods and diet rather than supplements or fortified products. "
                "Functionally the inverse of supplement_necessity_belief."
            ),
            is_anchor=False,
        ),

        # -- parent_influence group ------------------------------------------
        AttributeDefinition(
            name="pediatrician_influence",
            category="social",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.68,
            description=(
                "Degree to which a pediatrician's recommendation drives the parent's "
                "child-nutrition purchase decision; high values indicate near-prescriptive authority."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="child_taste_veto",
            category="social",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.54,
            description=(
                "How strongly the child's taste preference or rejection can block a "
                "parent's intended nutrition purchase; high values mean the child has "
                "effective veto power."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="guilt_driven_spending",
            category="psychology",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.43,
            description=(
                "Willingness to spend on child nutrition products driven by parental "
                "guilt (e.g., missing meals, busy schedule, perceived nutritional neglect)."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="best_for_my_child_intensity",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.71,
            description=(
                "Intensity of the 'only the best for my child' motivational frame; "
                "high values indicate willingness to choose premium products regardless "
                "of price when perceived child benefit is at stake."
            ),
            is_anchor=False,
        ),

        # -- child_context group --------------------------------------------
        AttributeDefinition(
            name="child_pester_power",
            category="social",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.48,
            description=(
                "Degree to which the child's persistent requests or advertising-driven "
                "demands influence the parent's purchase behaviour for food/nutrition products."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="partner_involvement",
            category="social",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.44,
            description=(
                "Level of partner/spouse involvement in child nutrition decisions; "
                "high values indicate joint decision-making, low values indicate "
                "primary caregiver decides unilaterally."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="mommy_group_influence",
            category="social",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.46,
            description=(
                "Influence of mommy groups, parenting WhatsApp communities, and online "
                "parenting forums on child nutrition purchase decisions."
            ),
            is_anchor=False,
        ),

        # -- purchase_context group -----------------------------------------
        AttributeDefinition(
            name="trial_pack_openness",
            category="decision_making",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.61,
            description=(
                "Willingness to try a small or trial-sized pack of a child nutrition "
                "product before committing to a full or bulk purchase."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="school_fee_pressure",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.41,
            description=(
                "Budget pressure created by school fees and associated education costs "
                "that competes with and reduces discretionary spend on child nutrition products."
            ),
            is_anchor=False,
        ),
    ]
)


# ---------------------------------------------------------------------------
# The full Littlejoys CPG template is the CPG base attributes plus all the
# child-nutrition-specific extensions defined above.
# ---------------------------------------------------------------------------

LITTLEJOYS_CPG_TEMPLATE: list[AttributeDefinition] = (
    CPG_DOMAIN_ATTRIBUTES + _LITTLEJOYS_SPECIFIC
)


__all__ = ["LITTLEJOYS_CPG_TEMPLATE"]
