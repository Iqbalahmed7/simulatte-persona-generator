"""Deterministic BehaviouralTendencies estimation from filled attribute profiles.

Sprint 2 — Identity Constructor.
Zero LLM calls. All tendency fields carry source="proxy".
"""

from __future__ import annotations

from statistics import mean
from typing import Optional

from src.schema.persona import (
    Attribute,
    BehaviouralTendencies,
    DerivedInsights,
    Objection,
    PriceSensitivityBand,
    TendencyBand,
    TrustOrientation,
    TrustWeights,
)


class TendencyEstimator:
    """Computes BehaviouralTendencies from attributes + derived_insights.

    All fields carry source="proxy". No LLM calls.
    """

    # -------------------------------------------------------------------
    # Public interface
    # -------------------------------------------------------------------

    def estimate(
        self,
        attributes: dict[str, dict[str, Attribute]],
        derived_insights: DerivedInsights,
    ) -> BehaviouralTendencies:
        """Compute BehaviouralTendencies from attributes and derived_insights.

        Args:
            attributes: Nested dict of category → name → Attribute.
            derived_insights: Already-computed DerivedInsights for this persona.

        Returns:
            Fully populated BehaviouralTendencies instance.
        """
        price_sensitivity = self._compute_price_sensitivity(attributes)
        trust_orientation = self._compute_trust_orientation(attributes)
        switching_propensity = self._compute_switching_propensity(attributes)
        objection_profile = self._compute_objection_profile(
            attributes, price_sensitivity, trust_orientation, derived_insights
        )
        reasoning_prompt = self._assemble_reasoning_prompt(
            price_sensitivity, trust_orientation, switching_propensity,
            objection_profile, derived_insights
        )

        return BehaviouralTendencies(
            price_sensitivity=price_sensitivity,
            trust_orientation=trust_orientation,
            switching_propensity=switching_propensity,
            objection_profile=objection_profile,
            reasoning_prompt=reasoning_prompt,
        )

    # -------------------------------------------------------------------
    # Safe attribute accessor
    # -------------------------------------------------------------------

    def _attr(
        self,
        attributes: dict[str, dict[str, Attribute]],
        category: str,
        name: str,
    ) -> float | str | None:
        """Return attribute value or None if missing."""
        try:
            return attributes[category][name].value
        except KeyError:
            return None

    # -------------------------------------------------------------------
    # Helper utilities
    # -------------------------------------------------------------------

    @staticmethod
    def _safe_float(
        value: float | str | None,
        default: float = 0.3,
    ) -> float:
        """Return float value or neutral default when None / non-numeric."""
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _avg(*values: Optional[float | str], default: float = 0.5) -> float:
        """Average of provided values; substitutes default for each missing one."""
        nums = []
        for v in values:
            if v is None:
                nums.append(default)
            else:
                try:
                    nums.append(float(v))
                except (TypeError, ValueError):
                    nums.append(default)
        return mean(nums) if nums else default

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, value))

    # -------------------------------------------------------------------
    # price_sensitivity
    # -------------------------------------------------------------------

    _PRICE_BAND_DESCRIPTIONS: dict[str, str] = {
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

    def _compute_price_sensitivity(
        self,
        attributes: dict[str, dict[str, Attribute]],
    ) -> PriceSensitivityBand:
        """Compute price sensitivity band from three budget-related attributes."""
        budget_consciousness = self._safe_float(
            self._attr(attributes, "values", "budget_consciousness"), 0.5
        )
        score = self._avg(
            self._attr(attributes, "values", "budget_consciousness"),
            self._attr(attributes, "values", "deal_seeking_intensity"),
            self._attr(attributes, "values", "economic_constraint_level"),
        )

        if score < 0.35:
            band = "low"
        elif score < 0.55:
            band = "medium"
        elif score < 0.75:
            band = "high"
        else:
            band = "extreme"

        # TR1 invariant: budget_consciousness > 0.70 → band must be "high" or "extreme"
        if budget_consciousness > 0.70 and band in ("low", "medium"):
            band = "high"

        # TR2 invariant: budget_consciousness < 0.35 → band must be "low" or "medium"
        if budget_consciousness < 0.35 and band in ("high", "extreme"):
            band = "medium"

        description = (
            f"You tend to be {band} price-sensitive — "
            f"{self._PRICE_BAND_DESCRIPTIONS[band]}"
        )

        return PriceSensitivityBand(band=band, description=description, source="proxy")

    # -------------------------------------------------------------------
    # trust_orientation
    # -------------------------------------------------------------------

    def _compute_trust_orientation(
        self,
        attributes: dict[str, dict[str, Attribute]],
    ) -> TrustOrientation:
        """Compute TrustOrientation weights and dominant channel."""
        neutral = 0.3  # neutral default for missing attributes

        authority_bias = self._safe_float(
            self._attr(attributes, "social", "authority_bias"), neutral
        )
        social_proof_bias = self._safe_float(
            self._attr(attributes, "social", "social_proof_bias"), neutral
        )
        peer_influence_strength = self._safe_float(
            self._attr(attributes, "social", "peer_influence_strength"), neutral
        )
        brand_loyalty = self._safe_float(
            self._attr(attributes, "values", "brand_loyalty"), neutral
        )
        # national_brand_attachment is not in base taxonomy — fall back to brand_loyalty alone
        national_brand_attachment = self._attr(attributes, "values", "national_brand_attachment")
        if national_brand_attachment is not None:
            brand_weight = self._clamp(
                brand_loyalty * 0.7 + self._safe_float(national_brand_attachment, neutral) * 0.3
            )
        else:
            brand_weight = self._clamp(brand_loyalty)

        ad_receptivity = self._safe_float(
            self._attr(attributes, "lifestyle", "ad_receptivity"), neutral
        )
        online_community_trust = self._safe_float(
            self._attr(attributes, "social", "online_community_trust"), neutral
        )
        influencer_susceptibility = self._safe_float(
            self._attr(attributes, "social", "influencer_susceptibility"), neutral
        )

        # TR6 invariant: ad_receptivity < 0.30 → trust_orientation.weights.ad <= 0.25
        ad_weight = self._clamp(ad_receptivity)
        if ad_receptivity < 0.30:
            ad_weight = min(ad_weight, 0.25)

        # TR4 invariant: social_proof_bias > 0.65 → weights.peer >= 0.65
        peer_weight = self._clamp(social_proof_bias * 0.9 + peer_influence_strength * 0.1)
        if social_proof_bias > 0.65:
            peer_weight = max(peer_weight, 0.65)

        # TR5 invariant: authority_bias > 0.65 → weights.expert >= 0.65
        expert_weight = self._clamp(authority_bias)
        if authority_bias > 0.65:
            expert_weight = max(expert_weight, 0.65)

        weights_dict = {
            "expert": expert_weight,
            "peer": peer_weight,
            "brand": brand_weight,
            "ad": ad_weight,
            "community": self._clamp(online_community_trust),
            "influencer": self._clamp(influencer_susceptibility),
        }

        # Find dominant channel
        dominant = max(weights_dict, key=lambda k: weights_dict[k])

        weights = TrustWeights(
            expert=weights_dict["expert"],
            peer=weights_dict["peer"],
            brand=weights_dict["brand"],
            ad=weights_dict["ad"],
            community=weights_dict["community"],
            influencer=weights_dict["influencer"],
        )

        _dominant_descriptions: dict[str, str] = {
            "expert": "you give heavy weight to credentialed experts and official sources when evaluating options.",
            "peer": "you lean on what peers and close social circles are doing before forming your own view.",
            "brand": "familiar brands provide the trust signal that moves you toward a decision.",
            "ad": "advertising messages reach you and meaningfully shape your awareness and preference.",
            "community": "online reviews and community consensus are central to your decision process.",
            "influencer": "creator endorsements and influencer signals carry significant weight in your choices.",
        }
        description = (
            f"You're most influenced by {dominant} — "
            f"{_dominant_descriptions.get(dominant, 'this channel shapes your trust and decisions.')}"
        )

        return TrustOrientation(
            weights=weights,
            dominant=dominant,
            description=description,
            source="proxy",
        )

    # -------------------------------------------------------------------
    # switching_propensity
    # -------------------------------------------------------------------

    def _compute_switching_propensity(
        self,
        attributes: dict[str, dict[str, Attribute]],
    ) -> TendencyBand:
        """Compute switching propensity.

        Low loyalty + high openness + low routine adherence → high switching.
        """
        brand_loyalty = self._safe_float(
            self._attr(attributes, "values", "brand_loyalty"), 0.5
        )
        indie_brand_openness = self._safe_float(
            self._attr(attributes, "values", "indie_brand_openness"), 0.5
        )
        routine_adherence = self._safe_float(
            self._attr(attributes, "lifestyle", "routine_adherence"), 0.5
        )

        score = self._avg(
            1.0 - brand_loyalty,
            indie_brand_openness,
            1.0 - routine_adherence,
        )

        # TR3 invariant: brand_loyalty > 0.70 must produce band="low"
        # Weight brand_loyalty heavily — if it's strongly high, force "low" band.
        if brand_loyalty > 0.70:
            band = "low"
            description = (
                "You tend to stay loyal to brands and routines you trust, rarely exploring alternatives."
            )
        elif score < 0.35:
            band = "low"
            description = (
                "You tend to stay loyal to brands and routines you trust, rarely exploring alternatives."
            )
        elif score < 0.65:
            band = "medium"
            description = (
                "You weigh options thoughtfully before switching, balancing familiarity with openness to change."
            )
        else:
            band = "high"
            description = (
                "You readily explore alternatives and are comfortable moving away from familiar brands or habits."
            )

        return TendencyBand(band=band, description=description, source="proxy")

    # -------------------------------------------------------------------
    # objection_profile
    # -------------------------------------------------------------------

    def _compute_objection_profile(
        self,
        attributes: dict[str, dict[str, Attribute]],
        price_sensitivity: PriceSensitivityBand,
        trust_orientation: TrustOrientation,
        derived_insights: DerivedInsights,
    ) -> list[Objection]:
        """Generate 2–4 objections using rule-based logic."""
        objections: list[Objection] = []

        risk_tolerance = self._safe_float(
            self._attr(attributes, "psychology", "risk_tolerance"), 0.5
        )
        information_need = self._safe_float(
            self._attr(attributes, "psychology", "information_need"), 0.5
        )
        social_proof_bias = self._safe_float(
            self._attr(attributes, "social", "social_proof_bias"), 0.5
        )

        # Rule 1: price sensitivity
        if price_sensitivity.band in ("high", "extreme"):
            objections.append(
                Objection(
                    objection_type="price_vs_value",
                    likelihood="high",
                    severity="blocking" if price_sensitivity.band == "extreme" else "friction",
                )
            )

        # Rule 2: risk aversion
        if risk_tolerance < 0.35:
            objections.append(
                Objection(
                    objection_type="risk_aversion",
                    likelihood="high",
                    severity="friction",
                )
            )

        # Rule 3: information need
        if information_need > 0.70:
            objections.append(
                Objection(
                    objection_type="need_more_information",
                    likelihood="medium",
                    severity="friction",
                )
            )

        # Rule 4: social proof gap
        if trust_orientation.dominant in ("peer", "authority") and social_proof_bias < 0.4:
            objections.append(
                Objection(
                    objection_type="social_proof_gap",
                    likelihood="medium",
                    severity="minor",
                )
            )

        # Fallback: guarantee at least 1 objection
        if not objections:
            objections.append(
                Objection(
                    objection_type="need_more_information",
                    likelihood="low",
                    severity="minor",
                )
            )

        return objections

    # -------------------------------------------------------------------
    # reasoning_prompt
    # -------------------------------------------------------------------

    _SWITCHING_PHRASES: dict[str, str] = {
        "low": "stay loyal to brands you trust",
        "medium": "weigh options before switching",
        "high": "explore alternatives readily",
    }

    def _assemble_reasoning_prompt(
        self,
        price_sensitivity: PriceSensitivityBand,
        trust_orientation: TrustOrientation,
        switching_propensity: TendencyBand,
        objection_profile: list[Objection],
        derived_insights: DerivedInsights,
    ) -> str:
        """Assemble the natural-language paragraph injected into LLM reasoning context."""
        switching_phrase = self._SWITCHING_PHRASES.get(
            switching_propensity.band, "weigh options before switching"
        )

        primary_objection = (
            objection_profile[0].objection_type.replace("_", " ")
            if objection_profile
            else "need for more information"
        )

        # description fields already contain the full sentence; use them directly
        lines = [
            price_sensitivity.description,
            trust_orientation.description,
            f"You tend to {switching_phrase}.",
            f"Your main concern when making decisions is typically {primary_objection}.",
        ]

        if derived_insights.key_tensions:
            lines.append(
                f"You often feel the tension between {derived_insights.key_tensions[0]}."
            )

        return " ".join(lines)
