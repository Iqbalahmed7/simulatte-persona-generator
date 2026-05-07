from src.schema.persona import PersonaRecord
from src.schema.receipt import (
    LOW_CONSISTENCY_THRESHOLD,
    NOISE_FLAG_THRESHOLD,
    OOD_CONFIDENCE_THRESHOLD,
    ArchetypeAnchor,
    ResponseReceipt,
    SignalTrace,
)


def build_receipt(
    persona: PersonaRecord,
    confidence: int,
    noise_applied: int,
    foundation_version: str | None = None,
) -> ResponseReceipt:
    """Build a ResponseReceipt from persona attributes after noise injection.

    Signal extraction priority:
      1. behavioural_tendencies (most direct purchase-relevant signals)
      2. derived_insights (psychographic profile)
      3. demographic_anchor (baseline demographic signals)
      4. immutable_constraints from core_memory (hard limits)

    influence_direction is set only for inherently directional signals
    (price/risk/switching, budget ceilings, non-negotiables). Signals whose
    effect depends on the question being asked carry direction=None.

    No LLM calls. All signals extracted deterministically from the persona record.

    TODO: foundation_version is a passthrough today. When Spec 01 (Longitudinal
    Panel) lands, decide() must thread the active PopScale foundation version
    into this call so the receipt and Calibration Card reference the same
    foundation snapshot.
    """
    signals: list[SignalTrace] = []

    bt = persona.behavioural_tendencies
    di = persona.derived_insights
    da = persona.demographic_anchor

    # --- Priority 1: behavioural_tendencies ---
    signals.append(SignalTrace(
        signal_name="price_sensitivity",
        signal_category="behavioral",
        signal_value=bt.price_sensitivity.band,
        influence_direction=_price_sensitivity_direction(bt.price_sensitivity.band),
    ))
    signals.append(SignalTrace(
        signal_name="trust_orientation",
        signal_category="behavioral",
        signal_value=bt.trust_orientation.dominant,
    ))
    signals.append(SignalTrace(
        signal_name="switching_propensity",
        signal_category="behavioral",
        signal_value=bt.switching_propensity.band,
        influence_direction=_switching_direction(bt.switching_propensity.band),
    ))

    # --- Priority 2: derived_insights ---
    signals.append(SignalTrace(
        signal_name="decision_style",
        signal_category="psychographic",
        signal_value=di.decision_style,
    ))
    signals.append(SignalTrace(
        signal_name="risk_appetite",
        signal_category="psychographic",
        signal_value=di.risk_appetite,
        influence_direction=_risk_direction(di.risk_appetite),
    ))
    signals.append(SignalTrace(
        signal_name="primary_value_orientation",
        signal_category="psychographic",
        signal_value=di.primary_value_orientation,
    ))

    # --- Priority 3: demographic_anchor ---
    signals.append(SignalTrace(
        signal_name="life_stage",
        signal_category="demographic",
        signal_value=da.life_stage,
    ))
    signals.append(SignalTrace(
        signal_name="income_bracket",
        signal_category="demographic",
        signal_value=da.household.income_bracket,
    ))

    # --- Priority 4: immutable_constraints from core_memory ---
    if persona.memory and persona.memory.core:
        cm = persona.memory.core
        if cm.immutable_constraints.budget_ceiling:
            signals.append(SignalTrace(
                signal_name="budget_ceiling",
                signal_category="memory",
                signal_value=cm.immutable_constraints.budget_ceiling,
                influence_direction="against",
            ))
        for non_neg in cm.immutable_constraints.non_negotiables:
            signals.append(SignalTrace(
                signal_name="non_negotiable",
                signal_category="memory",
                signal_value=non_neg,
                influence_direction="toward",
            ))

    # --- Archetype anchor ---
    active_tendencies: list[str] = []
    if bt.price_sensitivity.band in ("high", "extreme"):
        active_tendencies.append(f"price_sensitive_{bt.price_sensitivity.band}")
    if bt.switching_propensity.band == "low":
        active_tendencies.append("brand_loyal")
    elif bt.switching_propensity.band == "high":
        active_tendencies.append("switcher")
    if di.risk_appetite == "low":
        active_tendencies.append("risk_averse")
    elif di.risk_appetite == "high":
        active_tendencies.append("risk_tolerant")

    archetype = ArchetypeAnchor(
        decision_style=di.decision_style,
        value_orientation=di.primary_value_orientation,
        active_tendencies=active_tendencies,
    )

    # --- OOD detection ---
    ood = confidence < OOD_CONFIDENCE_THRESHOLD
    ood_reason: str | None = None
    if ood:
        ood_reason = (
            f"Confidence {confidence} below threshold {OOD_CONFIDENCE_THRESHOLD}. "
            f"Persona consistency_score={di.consistency_score}, noise={noise_applied}."
        )

    # --- Confidence flags ---
    confidence_flags: list[str] = []
    if di.consistency_score < LOW_CONSISTENCY_THRESHOLD:
        confidence_flags.append("low_consistency_persona")
    if abs(noise_applied) >= NOISE_FLAG_THRESHOLD:
        confidence_flags.append("high_noise_applied")
    if di.decision_style == "habitual":
        confidence_flags.append("habitual_responder")

    return ResponseReceipt(
        source_signals=signals,
        archetype_anchor=archetype,
        confidence_score=confidence,
        confidence_flags=confidence_flags,
        out_of_distribution=ood,
        ood_reason=ood_reason,
        noise_applied=noise_applied,
        foundation_version=foundation_version,
    )


def _price_sensitivity_direction(band: str) -> str:
    if band in ("high", "extreme"):
        return "against"
    if band == "low":
        return "toward"
    return "neutral"


def _switching_direction(band: str) -> str:
    if band == "high":
        return "toward"
    if band == "low":
        return "against"
    return "neutral"


def _risk_direction(appetite: str) -> str:
    if appetite == "low":
        return "against"
    if appetite == "high":
        return "toward"
    return "neutral"
