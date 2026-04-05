from __future__ import annotations

from src.taxonomy.base_taxonomy import AttributeDefinition
from src.taxonomy.domain_templates.cpg import CPG_DOMAIN_ATTRIBUTES, _domain_attr_definitions


# ---------------------------------------------------------------------------
# Lo! Foods FMCG domain-specific attributes
# These extend the base CPG taxonomy with attributes relevant to Indian
# functional food / health food purchase decisions across Lo! Foods'
# sub-brands: Lo! Keto, Protein Chef, DiabeSmart, Gluten Smart.
#
# Note: brand_loyalty, budget_consciousness, deal_seeking_intensity,
# subscription_comfort, and national_brand_attachment already exist in
# the base taxonomy or CPG extension and are intentionally omitted here.
# ---------------------------------------------------------------------------

_LOFOODS_SPECIFIC: list[AttributeDefinition] = _domain_attr_definitions(
    [
        # -- diet_identity group (values) ------------------------------------
        AttributeDefinition(
            name="keto_diet_adherence",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.08,
            description=(
                "Degree of adherence to a ketogenic diet; 0 = never heard of keto, "
                "1 = strict keto follower who tracks macros daily. Reflects the niche "
                "nature of keto in India (~2-3% strict adherents) with broader awareness."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="protein_consciousness",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.34,
            description=(
                "Degree to which the consumer actively seeks high-protein foods in "
                "daily diet; 0 = indifferent to protein content, 1 = protein-first "
                "mindset driving all food choices. Shaped by gym culture and mainstream "
                "fitness awareness in urban India."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="clean_label_importance",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.41,
            description=(
                "How strongly 'no maida, no palm oil, no preservatives, no added sugar' "
                "claims drive purchase decisions; 0 = indifferent to ingredient lists, "
                "1 = refuses to purchase without clean label verification."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="functional_food_trust",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.38,
            description=(
                "Trust in branded functional and health foods vs. skepticism about "
                "marketing claims; 0 = deep skeptic ('all just marketing, same as "
                "regular food'), 1 = true believer in functional food benefits. "
                "Lower priors reflect authentic Reddit/forum skepticism in Indian "
                "health food communities."
            ),
            is_anchor=False,
        ),

        # -- health_condition group (psychology) ----------------------------
        AttributeDefinition(
            name="diabetic_status",
            category="psychology",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.22,
            description=(
                "Health condition anchor for diabetes spectrum: 0 = no diabetes or "
                "family history, 0.5 = prediabetic or strong family history driving "
                "dietary caution, 1 = diagnosed Type 2 diabetic actively managing "
                "blood sugar through diet. Prior reflects India's ~11% diabetic + "
                "~15% prediabetic population skewed toward health-aware consumers."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="gluten_sensitivity_belief",
            category="psychology",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.06,
            description=(
                "Degree of gluten concern: 0 = no gluten awareness or concern, "
                "0.5 = self-diagnosed sensitivity or lifestyle choice to avoid gluten, "
                "1 = medically diagnosed celiac disease requiring strict avoidance. "
                "Low prior reflects low celiac awareness in India; lifestyle-driven "
                "gluten avoidance is rising in metro populations."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="weight_management_drive",
            category="psychology",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.51,
            description=(
                "How actively the consumer is pursuing weight management as a "
                "current goal; 0 = no active weight concern, 1 = weight loss or "
                "maintenance is a primary daily motivator for food choices. "
                "High prior in urban health-aware segments."
            ),
            is_anchor=False,
        ),

        # -- channel_behavior group (social) --------------------------------
        AttributeDefinition(
            name="quick_commerce_adoption",
            category="social",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.29,
            description=(
                "Frequency of using quick commerce platforms (Blinkit, Zepto, "
                "Swiggy Instamart) for grocery and food purchases; 0 = never uses "
                "quick commerce, 1 = primary grocery channel. Reflects metro India "
                "adoption patterns — high in Bangalore, Delhi, Mumbai."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="d2c_comfort",
            category="social",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.33,
            description=(
                "Comfort level buying directly from brand websites (D2C channels) "
                "for food products; 0 = prefers established marketplaces (Amazon, "
                "BigBasket), 1 = actively prefers D2C for freshness/authenticity/price."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="quick_commerce_trust",
            category="social",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.31,
            description=(
                "Trust in product quality, authenticity, and accurate weight/quantity "
                "delivery via quick commerce platforms; intentionally lower than "
                "quick_commerce_adoption to reflect documented Reddit/forum concerns "
                "about Blinkit/Zepto — expired products, weight discrepancies, "
                "FDA-flagged quality issues."
            ),
            is_anchor=False,
        ),

        # -- brand_perception group (psychology) ----------------------------
        AttributeDefinition(
            name="premium_price_tolerance",
            category="psychology",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.27,
            description=(
                "Willingness to pay 2x or more over mainstream equivalents for "
                "health claims; e.g., paying ₹99 for Protein Chef bread vs. ₹45 "
                "for Britannia. 0 = price-sensitive, buys mainstream, "
                "1 = actively pays premium for health credentials."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="indian_startup_brand_trust",
            category="psychology",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.35,
            description=(
                "Trust in Indian D2C / startup health brands vs. established FMCG "
                "companies (Britannia, ITC, Dabur, Patanjali); 0 = strongly prefers "
                "established brands for food trust, 1 = actively supports and trusts "
                "Indian health startups. Low prior reflects forum skepticism: "
                "'non-keto ingredients, poor or fake ratings.'"
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="doctor_endorsement_weight",
            category="psychology",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.61,
            description=(
                "How strongly a doctor's or dietitian's recommendation drives the "
                "consumer's food purchase decision; 0 = ignores medical authority "
                "for food choices, 1 = near-prescriptive — will not purchase without "
                "professional endorsement. High prior reflects Indian patient-doctor "
                "trust dynamic, especially for diabetic and high-stakes categories."
            ),
            is_anchor=False,
        ),

        # -- category_specific group (values) --------------------------------
        AttributeDefinition(
            name="subscription_tolerance",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.24,
            description=(
                "Willingness to commit to a recurring food delivery subscription "
                "(weekly, monthly); 0 = strongly prefers one-time purchases, "
                "1 = actively seeks subscription convenience and savings. "
                "Low prior reflects high churn rates in Indian food subscription market."
            ),
            is_anchor=False,
        ),
        AttributeDefinition(
            name="tier2_health_aspiration",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.44,
            description=(
                "In Tier 2/3 city consumers: aspiration toward metro health food "
                "lifestyle — interest in products seen as 'what urban India eats.' "
                "0 = content with local/traditional food choices, "
                "1 = actively seeks metro-branded health products as status/aspiration. "
                "Primarily relevant for C9 archetype; low-signal for metro personas."
            ),
            is_anchor=False,
        ),
    ]
)

# Merged template: CPG base + Lo! Foods specific
LOFOODS_FMCG_TEMPLATE: list[AttributeDefinition] = (
    CPG_DOMAIN_ATTRIBUTES + _LOFOODS_SPECIFIC
)
