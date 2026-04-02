"""Assign grounded BehaviouralTendencies to a PersonaRecord.

Sprint 8 — Grounding Pipeline Stage 4.
No LLM calls.
"""
from __future__ import annotations

import math

from src.grounding.types import BehaviouralArchetype
from src.schema.persona import (
    BehaviouralTendencies,
    Objection,
    PersonaRecord,
    PriceSensitivityBand,
    TendencyBand,
    TrustOrientation,
    TrustWeights,
)

# Must match exactly what's in src/generation/tendency_estimator.py
PRICE_BAND_DESCRIPTIONS: dict[str, str] = {
    "low": (
        "you rarely let price dictate your choices, prioritising value and quality "
        "over finding the cheapest option."
    ),
    "medium": (
        "you balance affordability with value, willing to pay more for quality "
        "but keeping an eye on the total spend."
    ),
    "high": (
        "you consistently seek deals and carefully weigh every purchase against "
        "your available budget before committing."
    ),
    "extreme": (
        "price is a decisive barrier — you will delay, switch, or forgo a purchase "
        "if it does not meet a strict budget threshold."
    ),
}

DOMINANT_DESCRIPTIONS: dict[str, str] = {
    "expert": "you give heavy weight to credentialed experts and official sources when evaluating options.",
    "peer": "you lean on what peers and close social circles are doing before forming your own view.",
    "brand": "familiar brands provide the trust signal that moves you toward a decision.",
    "ad": "advertising messages reach you and meaningfully shape your awareness and preference.",
    "community": "online reviews and community consensus are central to your decision process.",
    "influencer": "creator endorsements and influencer signals carry significant weight in your choices.",
}

_SWITCHING_BAND_DESCRIPTIONS: dict[str, str] = {
    "low": "You tend to stay loyal to brands and routines you trust, rarely exploring alternatives.",
    "medium": "You weigh options thoughtfully before switching, balancing familiarity with openness to change.",
    "high": "You readily explore alternatives and are comfortable moving away from familiar brands or habits.",
}

_OBJECTION_MAP: dict[str, Objection] = {
    "price_vs_value": Objection(
        objection_type="price_vs_value",
        likelihood="high",
        severity="friction",
    ),
    "switching_cost_concern": Objection(
        objection_type="switching_cost_concern",
        likelihood="medium",
        severity="minor",
    ),
    "need_more_information": Objection(
        objection_type="need_more_information",
        likelihood="medium",
        severity="friction",
    ),
}

_OBJECTION_DEFAULT = Objection(
    objection_type="need_more_information",
    likelihood="low",
    severity="minor",
)


def _persona_to_vector(persona: PersonaRecord) -> list[float]:
    """Convert persona attributes to a 9-dim feature vector for archetype matching.

    Dimension map:
      0: price_salience_index  → proxy from price_sensitivity.band:
            "extreme" → 0.9, "high" → 0.7, "medium" → 0.4, "low" → 0.15
      1: trust_expert          → trust_orientation.weights.expert
      2: trust_peer            → trust_orientation.weights.peer
      3: trust_brand           → trust_orientation.weights.brand
      4: trust_community       → trust_orientation.weights.community
      5: switching_price       → 0.8 if switching_propensity.band == "high" else 0.2
      6: switching_service     → 0.3 if switching_propensity.band != "low" else 0.1
      7: trigger_need          → 0.6 (neutral default — no direct attribute)
      8: trigger_rec           → trust_orientation.weights.peer * 0.8
    """
    bt = persona.behavioural_tendencies

    price_band_map = {"extreme": 0.9, "high": 0.7, "medium": 0.4, "low": 0.15}
    price_val = price_band_map.get(bt.price_sensitivity.band, 0.4)

    weights = bt.trust_orientation.weights

    switch_band = bt.switching_propensity.band
    switching_price = 0.8 if switch_band == "high" else 0.2
    switching_service = 0.3 if switch_band != "low" else 0.1

    trigger_rec = weights.peer * 0.8

    return [
        float(price_val),
        float(weights.expert),
        float(weights.peer),
        float(weights.brand),
        float(weights.community),
        float(switching_price),
        float(switching_service),
        0.6,
        float(trigger_rec),
    ]


def _euclidean_distance(a: list[float], b: list[float]) -> float:
    """Compute Euclidean distance between two equal-length vectors."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _build_grounded_tendencies(
    archetype: BehaviouralArchetype,
    persona: PersonaRecord,
) -> BehaviouralTendencies:
    """Build new BehaviouralTendencies from archetype, source='grounded'."""
    # --- price_sensitivity ---
    band = archetype.price_sensitivity_band
    price_description = f"You tend to be {band} price-sensitive — {PRICE_BAND_DESCRIPTIONS[band]}"
    price_sensitivity = PriceSensitivityBand(
        band=band,
        description=price_description,
        source="grounded",
    )

    # --- trust_orientation ---
    raw_weights = archetype.trust_orientation_weights
    # Clamp all weights to [0.0, 1.0]
    clamped = {k: max(0.0, min(1.0, float(v))) for k, v in raw_weights.items()}

    trust_weights = TrustWeights(
        expert=clamped.get("expert", 0.0),
        peer=clamped.get("peer", 0.0),
        brand=clamped.get("brand", 0.0),
        ad=clamped.get("ad", 0.0),
        community=clamped.get("community", 0.0),
        influencer=clamped.get("influencer", 0.0),
    )

    dominant = max(clamped, key=lambda k: clamped[k])
    dominant_desc = DOMINANT_DESCRIPTIONS.get(
        dominant, "this channel shapes your trust and decisions."
    )
    trust_description = f"You're most influenced by {dominant} — {dominant_desc}"
    trust_orientation = TrustOrientation(
        weights=trust_weights,
        dominant=dominant,
        description=trust_description,
        source="grounded",
    )

    # --- switching_propensity ---
    switch_band = archetype.switching_propensity_band
    switch_description = _SWITCHING_BAND_DESCRIPTIONS.get(
        switch_band,
        "You weigh options thoughtfully before switching, balancing familiarity with openness to change.",
    )
    switching_propensity = TendencyBand(
        band=switch_band,
        description=switch_description,
        source="grounded",
    )

    # --- objection_profile ---
    objection_profile: list[Objection] = []
    for obj_str in archetype.primary_objections:
        objection_profile.append(_OBJECTION_MAP.get(obj_str, _OBJECTION_DEFAULT))
    if not objection_profile:
        objection_profile.append(_OBJECTION_DEFAULT)

    # --- reasoning_prompt (reuse from existing persona) ---
    reasoning_prompt = persona.behavioural_tendencies.reasoning_prompt

    return BehaviouralTendencies(
        price_sensitivity=price_sensitivity,
        trust_orientation=trust_orientation,
        switching_propensity=switching_propensity,
        objection_profile=objection_profile,
        reasoning_prompt=reasoning_prompt,
    )


def assign_grounded_tendencies(
    persona: PersonaRecord,
    archetypes: list[BehaviouralArchetype],
) -> PersonaRecord:
    """Find nearest archetype and upgrade persona's BehaviouralTendencies.

    Steps:
    1. Convert persona attributes to a 9-dim feature vector
       using _persona_to_vector().
    2. Find nearest BehaviouralArchetype by Euclidean distance to centroid.
    3. Build new BehaviouralTendencies from nearest archetype,
       all fields with source="grounded".
    4. Return updated PersonaRecord via model_copy(update={"behavioural_tendencies": ...}).

    If archetypes is empty, return persona unchanged.
    """
    if not archetypes:
        return persona

    persona_vec = _persona_to_vector(persona)

    nearest = min(
        archetypes,
        key=lambda arch: _euclidean_distance(persona_vec, arch.centroid),
    )

    new_bt = _build_grounded_tendencies(nearest, persona)

    return persona.model_copy(update={"behavioural_tendencies": new_bt})
