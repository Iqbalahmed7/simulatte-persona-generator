"""src/cohort/type_coverage.py — Persona type classification and cohort coverage gate (G8).

Implements the 8-type persona classification system from Master Spec §11 and
the cohort composition coverage rules (G8).

All classification is rule-based — no LLM calls.
"""

from __future__ import annotations

from enum import Enum

from src.schema.persona import PersonaRecord


# ---------------------------------------------------------------------------
# Persona type enum
# ---------------------------------------------------------------------------

class PersonaType(str, Enum):
    PRAGMATIST = "The Pragmatist"
    LOYALIST = "The Loyalist"
    ASPIRANT = "The Aspirant"
    ANXIOUS_OPTIMIZER = "The Anxious Optimizer"
    SOCIAL_VALIDATOR = "The Social Validator"
    VALUE_REBEL = "The Value Rebel"
    RELUCTANT_USER = "The Reluctant User"
    POWER_USER = "The Power User"


# ---------------------------------------------------------------------------
# Cohort coverage rules
# ---------------------------------------------------------------------------

_COVERAGE_RULES: dict[int, int] = {
    3: 2,   # >= 2 distinct types (was 3)
    5: 3,   # >= 3 distinct types (was 4)
    10: 8,  # all 8 types (unchanged)
}


def _required_types(n: int) -> int:
    """Return the minimum number of distinct persona types required for a cohort of size n."""
    if n < 3:
        return 1
    if n < 5:
        return 2
    if n < 10:
        return 3
    return 8


# ---------------------------------------------------------------------------
# Attribute access helper
# ---------------------------------------------------------------------------

def _get_attr_value(persona: PersonaRecord, attr_name: str, default=None):
    """Safe attribute access across all categories.

    Iterates every category dict in persona.attributes and returns the
    .value of the first matching attribute found.  Returns `default` if
    the attribute is absent.
    """
    for category in persona.attributes.values():
        if attr_name in category:
            return category[attr_name].value
    return default


# ---------------------------------------------------------------------------
# Per-type scoring functions
# ---------------------------------------------------------------------------

def _score_pragmatist(persona: PersonaRecord) -> float:
    """
    Pragmatist — Low brand loyalty, high price sensitivity.

    Signals:
        price_sensitivity.band in ("high", "extreme")  → +0.4
        switching_propensity.band in ("high", "extreme") → +0.3
        brand_loyalty < 0.35                           → +0.3
    """
    score = 0.0

    if persona.behavioural_tendencies.price_sensitivity.band in ("high", "extreme"):
        score += 0.4

    if persona.behavioural_tendencies.switching_propensity.band in ("high", "extreme"):
        score += 0.3

    brand_loyalty = _get_attr_value(persona, "brand_loyalty")
    if brand_loyalty is not None and isinstance(brand_loyalty, (int, float)) and brand_loyalty < 0.35:
        score += 0.3

    return score


def _score_loyalist(persona: PersonaRecord) -> float:
    """
    Loyalist — High consistency, habitual decision style.

    Signals:
        switching_propensity.band in ("low", "very_low") → +0.4
        decision_style == "habitual"                     → +0.4
        brand_loyalty > 0.75                             → +0.2
    """
    score = 0.0

    if persona.behavioural_tendencies.switching_propensity.band in ("low", "very_low"):
        score += 0.4

    if persona.derived_insights.decision_style == "habitual":
        score += 0.4

    brand_loyalty = _get_attr_value(persona, "brand_loyalty")
    if brand_loyalty is not None and isinstance(brand_loyalty, (int, float)) and brand_loyalty > 0.75:
        score += 0.2

    return score


def _score_aspirant(persona: PersonaRecord) -> float:
    """
    Aspirant — Gap between self-concept and behaviour (aspiration_vs_constraint tension).

    Signals:
        tension_seed == "aspiration_vs_constraint"           → +0.5
        primary_value_driver in ("status", "brand")          → +0.3
        economic_constraint_level > 0.6                      → +0.2
    """
    score = 0.0

    tension_seed = _get_attr_value(persona, "tension_seed")
    if tension_seed == "aspiration_vs_constraint":
        score += 0.5

    primary_value_driver = _get_attr_value(persona, "primary_value_driver")
    if primary_value_driver in ("status", "brand"):
        score += 0.3

    economic_constraint_level = _get_attr_value(persona, "economic_constraint_level")
    if (
        economic_constraint_level is not None
        and isinstance(economic_constraint_level, (int, float))
        and economic_constraint_level > 0.6
    ):
        score += 0.2

    return score


def _score_anxious_optimizer(persona: PersonaRecord) -> float:
    """
    Anxious Optimizer — High analytical style, low risk appetite.

    Signals:
        decision_style == "analytical"          → +0.4
        risk_tolerance < 0.3                    → +0.3
        analysis_paralysis > 0.6 (if present)   → +0.3
    """
    score = 0.0

    if persona.derived_insights.decision_style == "analytical":
        score += 0.4

    risk_tolerance = _get_attr_value(persona, "risk_tolerance")
    if (
        risk_tolerance is not None
        and isinstance(risk_tolerance, (int, float))
        and risk_tolerance < 0.3
    ):
        score += 0.3

    analysis_paralysis = _get_attr_value(persona, "analysis_paralysis")
    if (
        analysis_paralysis is not None
        and isinstance(analysis_paralysis, (int, float))
        and analysis_paralysis > 0.6
    ):
        score += 0.3

    return score


def _score_social_validator(persona: PersonaRecord) -> float:
    """
    Social Validator — Trust anchor: peer, social decision style.

    Signals:
        trust_anchor == "peer"            → +0.5
        decision_style == "social"        → +0.3
        social_proof_bias > 0.65          → +0.2
    """
    score = 0.0

    if persona.derived_insights.trust_anchor == "peer":
        score += 0.5

    if persona.derived_insights.decision_style == "social":
        score += 0.3

    social_proof_bias = _get_attr_value(persona, "social_proof_bias")
    if (
        social_proof_bias is not None
        and isinstance(social_proof_bias, (int, float))
        and social_proof_bias > 0.65
    ):
        score += 0.2

    return score


def _score_value_rebel(persona: PersonaRecord) -> float:
    """
    Value Rebel — Counter-cultural values, high independence.

    Signals:
        tension_seed == "independence_vs_validation"           → +0.3
        social_orientation < 0.3                               → +0.3
        brand_loyalty < 0.25                                   → +0.2
        primary_value_driver not in ("brand", "status")        → +0.2
    """
    score = 0.0

    tension_seed = _get_attr_value(persona, "tension_seed")
    if tension_seed == "independence_vs_validation":
        score += 0.3

    social_orientation = _get_attr_value(persona, "social_orientation")
    if (
        social_orientation is not None
        and isinstance(social_orientation, (int, float))
        and social_orientation < 0.3
    ):
        score += 0.3

    brand_loyalty = _get_attr_value(persona, "brand_loyalty")
    if (
        brand_loyalty is not None
        and isinstance(brand_loyalty, (int, float))
        and brand_loyalty < 0.25
    ):
        score += 0.2

    primary_value_driver = _get_attr_value(persona, "primary_value_driver")
    if primary_value_driver not in ("brand", "status"):
        score += 0.2

    return score


def _score_reluctant_user(persona: PersonaRecord) -> float:
    """
    Reluctant User — Low satisfaction, moderate-high churn risk.

    Signals:
        switching_propensity.band in ("high", "extreme") → +0.3
        brand_loyalty < 0.4                              → +0.2
        tension_seed == "loyalty_vs_curiosity"           → +0.3
        risk_tolerance < 0.4                             → +0.2
    """
    score = 0.0

    if persona.behavioural_tendencies.switching_propensity.band in ("high", "extreme"):
        score += 0.3

    brand_loyalty = _get_attr_value(persona, "brand_loyalty")
    if (
        brand_loyalty is not None
        and isinstance(brand_loyalty, (int, float))
        and brand_loyalty < 0.4
    ):
        score += 0.2

    tension_seed = _get_attr_value(persona, "tension_seed")
    if tension_seed == "loyalty_vs_curiosity":
        score += 0.3

    risk_tolerance = _get_attr_value(persona, "risk_tolerance")
    if (
        risk_tolerance is not None
        and isinstance(risk_tolerance, (int, float))
        and risk_tolerance < 0.4
    ):
        score += 0.2

    return score


def _score_power_user(persona: PersonaRecord) -> float:
    """
    Power User — High feature orientation, high consistency.

    Signals:
        decision_style == "analytical"                   → +0.2
        brand_loyalty > 0.80                             → +0.4
        switching_propensity.band in ("very_low", "low") → +0.4
    """
    score = 0.0

    if persona.derived_insights.decision_style == "analytical":
        score += 0.2

    brand_loyalty = _get_attr_value(persona, "brand_loyalty")
    if (
        brand_loyalty is not None
        and isinstance(brand_loyalty, (int, float))
        and brand_loyalty > 0.80
    ):
        score += 0.4

    if persona.behavioural_tendencies.switching_propensity.band in ("very_low", "low"):
        score += 0.4

    return score


# ---------------------------------------------------------------------------
# Ordered list of (PersonaType, scorer) pairs — order determines tie-breaking
# ---------------------------------------------------------------------------

_SCORERS: list[tuple[PersonaType, object]] = [
    (PersonaType.PRAGMATIST,       _score_pragmatist),
    (PersonaType.LOYALIST,         _score_loyalist),
    (PersonaType.ASPIRANT,         _score_aspirant),
    (PersonaType.ANXIOUS_OPTIMIZER, _score_anxious_optimizer),
    (PersonaType.SOCIAL_VALIDATOR, _score_social_validator),
    (PersonaType.VALUE_REBEL,      _score_value_rebel),
    (PersonaType.RELUCTANT_USER,   _score_reluctant_user),
    (PersonaType.POWER_USER,       _score_power_user),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_persona_type(persona: PersonaRecord) -> PersonaType:
    """Classify a persona into one of the 8 types using attribute signals.

    Rule-based. No LLM calls. Returns the single best-match type.

    Tie-breaking: if two types share the highest score, the one that appears
    first in enum order (PRAGMATIST → POWER_USER) wins.

    If no scorer returns a score > 0 (very sparse persona), defaults to
    PersonaType.PRAGMATIST.
    """
    best_type: PersonaType = PersonaType.PRAGMATIST
    best_score: float = 0.0

    for persona_type, scorer in _SCORERS:
        score = scorer(persona)  # type: ignore[operator]
        if score > best_score:
            best_score = score
            best_type = persona_type

    return best_type


def check_type_coverage(
    personas: list[PersonaRecord],
) -> tuple[bool, list[PersonaType], list[PersonaType]]:
    """Check cohort composition rules (G8).

    Coverage requirements by cohort size:
        N == 3  : >= 3 distinct types
        N == 5  : >= 4 distinct types
        N >= 10 : all 8 types
        other N : >= min(N, 8) distinct types

    Args:
        personas: List of PersonaRecord objects in the cohort.

    Returns:
        A 3-tuple of:
            passed        (bool)             — True if the coverage rule is met.
            present_types (list[PersonaType]) — Distinct types found in the cohort.
            missing_types (list[PersonaType]) — Types absent from the cohort.
    """
    all_types: list[PersonaType] = list(PersonaType)

    present_set: set[PersonaType] = {
        classify_persona_type(p) for p in personas
    }

    present_types: list[PersonaType] = [t for t in all_types if t in present_set]
    missing_types: list[PersonaType] = [t for t in all_types if t not in present_set]

    required = _required_types(len(personas))
    passed = len(present_types) >= required

    return passed, present_types, missing_types
