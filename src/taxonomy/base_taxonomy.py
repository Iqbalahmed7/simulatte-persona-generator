"""Base, domain-agnostic persona taxonomy for Sprint 1.

This module provides ~150 attribute definitions across six categories,
including eight anchor attributes that should be filled first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Category = Literal[
    "psychology",
    "values",
    "social",
    "lifestyle",
    "identity",
    "decision_making",
]


@dataclass
class AttributeDefinition:
    name: str
    category: Category
    attr_type: Literal["continuous", "categorical"]

    # For continuous attributes.
    range_min: float | None = None
    range_max: float | None = None

    # For categorical attributes.
    options: list[str] | None = None

    description: str = ""
    population_prior: float | None = None
    is_anchor: bool = False
    anchor_order: int | None = None

    # Correlation hints used by the attribute filler.
    positive_correlates: list[str] = field(default_factory=list)
    negative_correlates: list[str] = field(default_factory=list)


def _continuous(
    name: str,
    category: Category,
    description: str,
    population_prior: float,
    *,
    is_anchor: bool = False,
    anchor_order: int | None = None,
) -> AttributeDefinition:
    return AttributeDefinition(
        name=name,
        category=category,
        attr_type="continuous",
        range_min=0.0,
        range_max=1.0,
        description=description,
        population_prior=population_prior,
        is_anchor=is_anchor,
        anchor_order=anchor_order,
    )


def _categorical(
    name: str,
    category: Category,
    description: str,
    options: list[str],
    *,
    is_anchor: bool = False,
    anchor_order: int | None = None,
) -> AttributeDefinition:
    return AttributeDefinition(
        name=name,
        category=category,
        attr_type="categorical",
        options=options,
        description=description,
        is_anchor=is_anchor,
        anchor_order=anchor_order,
    )


# Used by filler consistency logic.
KNOWN_CORRELATIONS: list[tuple[str, str, Literal["positive", "negative"]]] = [
    ("budget_consciousness", "deal_seeking_intensity", "positive"),
    ("social_proof_bias", "wom_receiver_openness", "positive"),
    ("brand_loyalty", "indie_brand_openness", "negative"),
    ("risk_tolerance", "status_quo_bias", "negative"),
    ("information_need", "research_before_purchase", "positive"),
    ("perceived_time_scarcity", "convenience_preference", "positive"),
    ("authority_bias", "self_efficacy", "negative"),
    ("analysis_paralysis", "decision_delegation", "positive"),
]


# KNOWN_CORRELATIONS_DICT: maps each attr name → list of (other_attr_name, direction) tuples
# Direction is "positive" or "negative"
KNOWN_CORRELATIONS_DICT: dict[str, list[tuple[str, str]]] = {}
for _a, _b, _dir in KNOWN_CORRELATIONS:
    KNOWN_CORRELATIONS_DICT.setdefault(_a, []).append((_b, _dir))
    KNOWN_CORRELATIONS_DICT.setdefault(_b, []).append((_a, _dir))


BASE_TAXONOMY: list[AttributeDefinition] = [
    # psychology (30)
    _categorical(
        "personality_type",
        "psychology",
        "Big Five mapped to a practical decision orientation.",
        [
            "analytical_conscientious",
            "empathetic_agreeable",
            "independent_open",
            "cautious_neurotic",
            "social_extraverted",
        ],
        is_anchor=True,
        anchor_order=1,
    ),
    _continuous(
        "risk_tolerance",
        "psychology",
        "Willingness to try new or uncertain options.",
        0.46,
        is_anchor=True,
        anchor_order=2,
    ),
    _continuous("information_need", "psychology", "Need for information before choosing.", 0.62),
    _continuous("analysis_paralysis", "psychology", "Tendency to delay despite enough information.", 0.43),
    _continuous("loss_aversion", "psychology", "Sensitivity to potential losses over equivalent gains.", 0.61),
    _continuous("status_quo_bias", "psychology", "Preference for current habits and known options.", 0.56),
    _continuous("health_anxiety", "psychology", "Tendency to worry about health or safety risks.", 0.42),
    _continuous(
        "health_supplement_belief",
        "psychology",
        "Belief in the efficacy of dietary supplements, vitamins, and nutraceuticals. "
        "High values indicate strong supplement advocacy; low values indicate skepticism.",
        0.45,
    ),
    _continuous("fear_appeal_responsiveness", "psychology", "Responsiveness to fear-framed messaging.", 0.38),
    _continuous(
        "emotional_persuasion_susceptibility",
        "psychology",
        "Likelihood of being moved by emotional framing.",
        0.52,
    ),
    _continuous("optimism_bias", "psychology", "Expectation that outcomes will generally be positive.", 0.57),
    _continuous("sunk_cost_sensitivity", "psychology", "Weight given to past investments when deciding.", 0.49),
    _continuous("scarcity_responsiveness", "psychology", "Reactivity to limited-time or low-stock framing.", 0.47),
    _continuous("novelty_seeking", "psychology", "Preference for trying unfamiliar options.", 0.45),
    _continuous("ambiguity_tolerance", "psychology", "Comfort with incomplete information.", 0.48),
    _continuous("cognitive_flexibility", "psychology", "Ability to update beliefs when evidence changes.", 0.53),
    _continuous("certainty_need", "psychology", "Need for predictability before acting.", 0.58),
    _continuous("delayed_gratification", "psychology", "Willingness to wait for better long-term outcomes.", 0.5),
    _continuous("impulsive_reactivity", "psychology", "Likelihood of quick emotionally-driven reactions.", 0.44),
    _continuous("planning_horizon", "psychology", "How far ahead trade-offs are considered.", 0.52),
    _continuous("uncertainty_avoidance", "psychology", "Discomfort with unknown outcomes.", 0.55),
    _continuous("cognitive_load_sensitivity", "psychology", "Performance drop under too many options or inputs.", 0.5),
    _continuous("stress_reactivity", "psychology", "How strongly stress shifts decision behavior.", 0.46),
    _continuous("emotional_regulation", "psychology", "Capacity to stay stable under emotional pressure.", 0.54),
    _continuous("perceived_self_control", "psychology", "Belief in ability to govern impulses and habits.", 0.51),
    _continuous("habit_strength", "psychology", "Strength of learned routines in daily choice.", 0.6),
    _continuous("change_fatigue", "psychology", "Tendency to tire from repeated change or new demands.", 0.41),
    _continuous("reward_sensitivity", "psychology", "Strength of response to immediate rewards.", 0.49),
    _continuous("guilt_sensitivity", "psychology", "How much guilt influences post-choice reflection.", 0.47),
    _continuous("shame_sensitivity", "psychology", "How much social shame risk shapes choice.", 0.4),
    _continuous("reflection_tendency", "psychology", "Tendency to review decisions and learn from outcomes.", 0.55),

    # values (25)
    _continuous(
        "economic_constraint_level",
        "values",
        "Perceived financial pressure shaping day-to-day decisions.",
        0.53,
        is_anchor=True,
        anchor_order=4,
    ),
    _categorical(
        "primary_value_driver",
        "values",
        "Dominant value lens used when prioritizing options.",
        ["price", "quality", "brand", "convenience", "relationships", "status"],
        is_anchor=True,
        anchor_order=6,
    ),
    _continuous("budget_consciousness", "values", "Attention to affordability and spend discipline.", 0.59),
    _continuous("brand_loyalty", "values", "Attachment to familiar and trusted brands.", 0.52),
    _continuous("indie_brand_openness", "values", "Openness to lesser-known or emerging brands.", 0.44),
    _continuous("deal_seeking_intensity", "values", "Active effort to find promotions and discounts.", 0.55),
    _continuous("environmental_consciousness", "values", "Importance of sustainability in decision criteria.", 0.47),
    _continuous("family_centricity", "values", "Degree to which family welfare drives choices.", 0.6),
    _continuous("achievement_orientation", "values", "Motivation from performance and advancement goals.", 0.51),
    _continuous("security_orientation", "values", "Preference for safety, stability, and low volatility.", 0.56),
    _continuous("autonomy_value", "values", "Importance of independent control over decisions.", 0.54),
    _continuous("tradition_orientation", "values", "Preference for conventional norms and familiar practices.", 0.45),
    _continuous("novelty_value", "values", "Importance of experimentation and fresh experiences.", 0.46),
    _continuous("relationship_priority", "values", "Weight placed on relational harmony and connection.", 0.58),
    _continuous("status_seeking", "values", "Desire to signal prestige or success.", 0.39),
    _continuous("fairness_concern", "values", "Sensitivity to fairness and equitable treatment.", 0.57),
    _continuous(
        "ethical_consumption_commitment",
        "values",
        "Willingness to align purchases with ethical principles.",
        0.43,
    ),
    _continuous("localism_preference", "values", "Preference for local producers and familiar origin.", 0.48),
    _continuous("premium_quality_preference", "values", "Readiness to pay more for perceived quality.", 0.45),
    _continuous("frugality_identity", "values", "Self-identification as prudent and non-wasteful.", 0.55),
    _continuous("experiential_spending_preference", "values", "Preference for experiences over possessions.", 0.41),
    _continuous("future_security_focus", "values", "Priority on long-term stability and preparedness.", 0.57),
    _continuous("generosity_norm", "values", "Tendency to include sharing and giving in choices.", 0.46),
    _continuous("self_improvement_drive", "values", "Motivation to choose options that improve capability.", 0.5),
    _continuous("comfort_priority", "values", "Preference for emotional and physical comfort outcomes.", 0.53),

    # social (25)
    _categorical(
        "trust_orientation_primary",
        "social",
        "Primary social source used for trust and guidance.",
        ["self", "peer", "authority", "family"],
        is_anchor=True,
        anchor_order=3,
    ),
    _continuous(
        "social_orientation",
        "social",
        "Extent to which social approval shapes decisions.",
        0.5,
        is_anchor=True,
        anchor_order=7,
    ),
    _continuous("social_proof_bias", "social", "Influence of visible peer behavior on own choices.", 0.55),
    _continuous("wom_receiver_openness", "social", "Receptivity to word-of-mouth recommendations.", 0.57),
    _continuous("authority_bias", "social", "Weight given to experts and formal authorities.", 0.48),
    _continuous("peer_influence_strength", "social", "Strength of close-peer influence in decisions.", 0.54),
    _continuous("online_community_trust", "social", "Trust in online communities and review ecosystems.", 0.49),
    _continuous("influencer_susceptibility", "social", "Susceptibility to creator and influencer endorsements.", 0.42),
    _continuous("elder_advice_weight", "social", "Weight given to elder or senior family recommendations.", 0.51),
    _continuous("authority_trust", "social", "Baseline trust level in institutional guidance.", 0.5),
    _continuous("conformity_tendency", "social", "Propensity to align with perceived group norms.", 0.47),
    _continuous("social_comparison_frequency", "social", "Frequency of comparing choices to peers.", 0.5),
    _continuous("reputational_concern", "social", "Concern about social image impact of decisions.", 0.45),
    _continuous("communal_obligation", "social", "Sense of duty to support community expectations.", 0.44),
    _continuous("network_diversity", "social", "Variety of social circles informing choices.", 0.46),
    _continuous("civic_participation", "social", "Engagement in civic or neighborhood participation.", 0.4),
    _continuous("group_identity_salience", "social", "Strength of in-group identity in decisions.", 0.5),
    _continuous("mentorship_seeking", "social", "Tendency to seek advice from experienced mentors.", 0.43),
    _continuous("reciprocity_expectation", "social", "Expectation of mutual support within relationships.", 0.56),
    _continuous("conflict_avoidance_social", "social", "Preference to avoid conflict in social decisions.", 0.52),
    _continuous("social_confidence", "social", "Confidence in navigating social interactions.", 0.51),
    _continuous("privacy_boundary_strength", "social", "Strength of boundaries around personal disclosure.", 0.5),
    _continuous("offline_community_engagement", "social", "Participation in local offline social communities.", 0.42),
    _continuous("collaborative_decision_preference", "social", "Preference for shared rather than solo decisions.", 0.53),
    _continuous("norm_enforcement_tendency", "social", "Tendency to reinforce norms in close networks.", 0.39),

    # lifestyle (25)
    _continuous("convenience_preference", "lifestyle", "How much friction reduction drives choices.", 0.61),
    _continuous("routine_adherence", "lifestyle", "Consistency with established daily routines.", 0.58),
    _continuous("perceived_time_scarcity", "lifestyle", "Subjective feeling of not having enough time.", 0.56),
    _continuous("digital_first_behavior", "lifestyle", "Tendency to search and act through digital channels first.", 0.6),
    _continuous("health_consciousness", "lifestyle", "General effort toward healthier habits and selections.", 0.52),
    _continuous("impulsivity", "lifestyle", "Likelihood of unplanned or spontaneous choices.", 0.45),
    _continuous("schedule_volatility", "lifestyle", "Unpredictability of daily or weekly schedule.", 0.48),
    _continuous("multitasking_preference", "lifestyle", "Preference for handling multiple tasks in parallel.", 0.5),
    _continuous("planning_rigidity", "lifestyle", "Preference for tightly planned routines.", 0.46),
    _continuous("sleep_discipline", "lifestyle", "Consistency in sleep timing and recovery routines.", 0.49),
    _continuous("physical_activity_orientation", "lifestyle", "Inclination toward regular physical movement.", 0.47),
    _continuous("food_experimentation", "lifestyle", "Willingness to try new foods and consumption patterns.", 0.44),
    _continuous("homebody_orientation", "lifestyle", "Preference for home-centric leisure and routines.", 0.51),
    _continuous("travel_frequency_preference", "lifestyle", "Preference for frequent travel and mobility.", 0.37),
    _continuous("media_discovery_openness", "lifestyle", "Openness to discovering new media and channels.", 0.54),
    _continuous("ad_receptivity", "lifestyle", "Baseline receptivity to advertising messages.", 0.41),
    _continuous("deal_alert_attention", "lifestyle", "Attention to app, email, or social discount alerts.", 0.52),
    _continuous("subscription_comfort", "lifestyle", "Comfort with recurring subscription commitments.", 0.46),
    _continuous("digital_payment_comfort", "lifestyle", "Comfort using digital payment methods.", 0.63),
    _continuous("simplicity_preference", "lifestyle", "Preference for simpler products and workflows.", 0.57),
    _continuous("clutter_tolerance", "lifestyle", "Tolerance for complexity and information clutter.", 0.43),
    _continuous("maintenance_patience", "lifestyle", "Patience for ongoing setup or maintenance tasks.", 0.45),
    _continuous("sustainability_habit_strength", "lifestyle", "Consistency of sustainability-oriented habits.", 0.4),
    _continuous("work_life_boundary_strength", "lifestyle", "Ability to maintain boundaries around work demands.", 0.47),
    _continuous("late_adoption_tendency", "lifestyle", "Tendency to adopt new trends later than peers.", 0.5),

    # identity (20)
    _categorical(
        "life_stage_priority",
        "identity",
        "Current life-stage frame that shapes major priorities.",
        [
            "establishing",
            "building_family",
            "mid_career",
            "caregiver",
            "established",
            "transitioning",
        ],
        is_anchor=True,
        anchor_order=5,
    ),
    _categorical(
        "tension_seed",
        "identity",
        "Primary recurring internal contradiction shaping behavior.",
        [
            "aspiration_vs_constraint",
            "independence_vs_validation",
            "quality_vs_budget",
            "loyalty_vs_curiosity",
            "control_vs_delegation",
        ],
        is_anchor=True,
        anchor_order=8,
    ),
    _continuous("aspiration_gap", "identity", "Distance between current and desired self-state.", 0.5),
    _continuous("self_efficacy", "identity", "Confidence in evaluating options and acting effectively.", 0.53),
    _continuous("locus_of_control", "identity", "Internal versus external attribution of outcomes.", 0.51),
    _continuous(
        "identity_expression_through_purchase",
        "identity",
        "Degree to which choices are used to express identity.",
        0.46,
    ),
    _continuous("life_satisfaction", "identity", "Overall satisfaction with life trajectory.", 0.52),
    _continuous("personal_agency", "identity", "Sense of being able to influence life direction.", 0.54),
    _continuous("resilience_identity", "identity", "Self-view as someone who can rebound from setbacks.", 0.5),
    _continuous("belonging_need", "identity", "Need to feel accepted and included by valued groups.", 0.57),
    _continuous("uniqueness_need", "identity", "Need to maintain a distinct personal identity.", 0.45),
    _continuous("role_stability", "identity", "Stability of key personal and social roles over time.", 0.49),
    _continuous("growth_mindset", "identity", "Belief that abilities can be developed over time.", 0.56),
    _continuous("failure_recovery_confidence", "identity", "Confidence in recovering after mistakes.", 0.5),
    _continuous("authenticity_priority", "identity", "Priority placed on being true to self in choices.", 0.58),
    _continuous("legacy_motivation", "identity", "Motivation to make choices with long-term meaning.", 0.43),
    _continuous("social_mobility_belief", "identity", "Belief that effort can improve social standing.", 0.47),
    _continuous("self_consistency_need", "identity", "Need for choices to align with prior self-image.", 0.55),
    _continuous("recognition_need", "identity", "Need for acknowledgment from others.", 0.44),
    _continuous("purpose_clarity", "identity", "Clarity of guiding purpose and direction.", 0.48),

    # decision_making (25)
    _continuous("research_before_purchase", "decision_making", "Depth of pre-choice research behavior.", 0.58),
    _continuous("comparison_shopping", "decision_making", "Tendency to compare alternatives before deciding.", 0.6),
    _continuous("decision_delegation", "decision_making", "Likelihood of outsourcing choices to others.", 0.41),
    _continuous(
        "post_purchase_regret_sensitivity",
        "decision_making",
        "Sensitivity to regret after making a decision.",
        0.5,
    ),
    _continuous(
        "satisficing_vs_maximizing",
        "decision_making",
        "Higher values indicate maximizing over good-enough satisficing.",
        0.47,
    ),
    _continuous("option_overload_sensitivity", "decision_making", "Decision quality drop with too many options.", 0.53),
    _continuous("default_acceptance", "decision_making", "Tendency to accept default recommendations.", 0.48),
    _continuous(
        "trial_before_commitment_preference",
        "decision_making",
        "Preference for trials or pilots before full commitment.",
        0.56,
    ),
    _continuous("switching_cost_sensitivity", "decision_making", "How strongly switching friction deters change.", 0.52),
    _continuous("purchase_timing_deliberation", "decision_making", "Deliberation on when to buy, not just what.", 0.54),
    _continuous(
        "deadline_pressure_susceptibility",
        "decision_making",
        "Likelihood of rushed decisions under time pressure.",
        0.45,
    ),
    _continuous("evidence_threshold", "decision_making", "Amount of evidence required before deciding.", 0.57),
    _continuous(
        "price_quality_tradeoff_tolerance",
        "decision_making",
        "Tolerance for trading quality against price constraints.",
        0.5,
    ),
    _continuous("brand_exploration_rate", "decision_making", "Frequency of exploring new brands or alternatives.", 0.44),
    _continuous("re_purchase_inertia", "decision_making", "Likelihood of repeating prior purchases.", 0.55),
    _continuous("return_aversion", "decision_making", "Reluctance to return or reverse a purchase.", 0.49),
    _continuous("negotiation_willingness", "decision_making", "Willingness to negotiate terms or pricing.", 0.4),
    _continuous("bundle_preference", "decision_making", "Preference for bundled solutions over standalone options.", 0.46),
    _continuous(
        "channel_consistency_preference",
        "decision_making",
        "Preference for sticking to familiar purchase channels.",
        0.51,
    ),
    _continuous("deal_waiting_patience", "decision_making", "Patience to wait for better offers before buying.", 0.5),
    _continuous("shortlisting_discipline", "decision_making", "Tendency to narrow options systematically.", 0.52),
    _continuous("cognitive_shortcut_reliance", "decision_making", "Reliance on heuristics versus full analysis.", 0.47),
    _continuous("last_mile_doubt", "decision_making", "Second thoughts near final commitment.", 0.46),
    _continuous("post_decision_rationalization", "decision_making", "Tendency to justify choices after committing.", 0.5),
    _continuous("feedback_loop_learning", "decision_making", "Use of outcomes to improve future decisions.", 0.54),
]


TAXONOMY_BY_NAME: dict[str, AttributeDefinition] = {a.name: a for a in BASE_TAXONOMY}


def _apply_correlation_hints() -> None:
    for left, right, direction in KNOWN_CORRELATIONS:
        left_attr = TAXONOMY_BY_NAME[left]
        right_attr = TAXONOMY_BY_NAME[right]

        if direction == "positive":
            if right not in left_attr.positive_correlates:
                left_attr.positive_correlates.append(right)
            if left not in right_attr.positive_correlates:
                right_attr.positive_correlates.append(left)
        else:
            if right not in left_attr.negative_correlates:
                left_attr.negative_correlates.append(right)
            if left not in right_attr.negative_correlates:
                right_attr.negative_correlates.append(left)


_apply_correlation_hints()


ANCHOR_ATTRIBUTES: list[AttributeDefinition] = [a for a in BASE_TAXONOMY if a.is_anchor]
ANCHOR_ATTRIBUTES.sort(key=lambda a: a.anchor_order if a.anchor_order is not None else 999)


TAXONOMY_BY_CATEGORY: dict[str, list[AttributeDefinition]] = {
    "psychology": [a for a in BASE_TAXONOMY if a.category == "psychology"],
    "values": [a for a in BASE_TAXONOMY if a.category == "values"],
    "social": [a for a in BASE_TAXONOMY if a.category == "social"],
    "lifestyle": [a for a in BASE_TAXONOMY if a.category == "lifestyle"],
    "identity": [a for a in BASE_TAXONOMY if a.category == "identity"],
    "decision_making": [a for a in BASE_TAXONOMY if a.category == "decision_making"],
}


def _validate_taxonomy() -> None:
    expected_anchor_order = [
        "personality_type",
        "risk_tolerance",
        "trust_orientation_primary",
        "economic_constraint_level",
        "life_stage_priority",
        "primary_value_driver",
        "social_orientation",
        "tension_seed",
    ]

    observed_anchor_order = [a.name for a in ANCHOR_ATTRIBUTES]
    if observed_anchor_order != expected_anchor_order:
        raise ValueError(
            "Anchor ordering mismatch. "
            f"Expected {expected_anchor_order}, observed {observed_anchor_order}."
        )

    if len(BASE_TAXONOMY) < 130 or len(BASE_TAXONOMY) > 180:
        raise ValueError(
            f"BASE_TAXONOMY size {len(BASE_TAXONOMY)} is outside accepted range 130-180."
        )

    category_counts = {name: len(attrs) for name, attrs in TAXONOMY_BY_CATEGORY.items()}
    expected_counts = {
        "psychology": 31,
        "values": 25,
        "social": 25,
        "lifestyle": 25,
        "identity": 20,
        "decision_making": 25,
    }

    if category_counts != expected_counts:
        raise ValueError(
            f"Category counts mismatch. Expected {expected_counts}, observed {category_counts}."
        )

    for attr in BASE_TAXONOMY:
        if attr.attr_type == "continuous":
            if attr.range_min != 0.0 or attr.range_max != 1.0:
                raise ValueError(f"Continuous attribute {attr.name} must be in [0.0, 1.0].")
            if attr.population_prior is None:
                raise ValueError(f"Continuous attribute {attr.name} must define population_prior.")
        else:
            if not attr.options:
                raise ValueError(f"Categorical attribute {attr.name} must define non-empty options.")


_validate_taxonomy()


__all__ = [
    "AttributeDefinition",
    "KNOWN_CORRELATIONS",
    "KNOWN_CORRELATIONS_DICT",
    "BASE_TAXONOMY",
    "ANCHOR_ATTRIBUTES",
    "TAXONOMY_BY_CATEGORY",
    "TAXONOMY_BY_NAME",
]
