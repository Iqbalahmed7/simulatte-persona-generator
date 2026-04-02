"""Deterministic DerivedInsights computation from filled attribute profiles.

Sprint 2 — Identity Constructor.
Zero LLM calls. All derivations are rule-based formulas.
"""

from __future__ import annotations

from statistics import mean
from typing import Optional

from src.schema.persona import (
    Attribute,
    CopingMechanism,
    DemographicAnchor,
    DerivedInsights,
)
from src.taxonomy.base_taxonomy import KNOWN_CORRELATIONS


class DerivedInsightsComputer:
    """Computes DerivedInsights deterministically from a filled attribute profile."""

    # -------------------------------------------------------------------
    # Public interface
    # -------------------------------------------------------------------

    def compute(
        self,
        attributes: dict[str, dict[str, Attribute]],
        demographic_anchor: DemographicAnchor,
    ) -> DerivedInsights:
        """Compute all DerivedInsights fields from attributes.

        No LLM calls. All rule-based.

        Args:
            attributes: Nested dict of category → name → Attribute.
            demographic_anchor: Demographic context (used for descriptions).

        Returns:
            Fully populated DerivedInsights instance.
        """
        decision_style, decision_style_score = self._compute_decision_style(attributes)
        trust_anchor = self._compute_trust_anchor(attributes)
        risk_appetite = self._compute_risk_appetite(attributes)
        primary_value_orientation = self._compute_primary_value_orientation(attributes)
        coping_mechanism = self._compute_coping_mechanism(attributes)
        consistency_score = self._compute_consistency_score(attributes)
        consistency_band = self._compute_consistency_band(consistency_score)
        key_tensions = self._compute_key_tensions(attributes)

        return DerivedInsights(
            decision_style=decision_style,
            decision_style_score=decision_style_score,
            trust_anchor=trust_anchor,
            risk_appetite=risk_appetite,
            primary_value_orientation=primary_value_orientation,
            coping_mechanism=coping_mechanism,
            consistency_score=consistency_score,
            consistency_band=consistency_band,
            key_tensions=key_tensions,
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
    def _safe_float(value: float | str | None, default: float = 0.5) -> float:
        """Return float value or default when None / non-numeric."""
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _avg(*values: Optional[float | str], default: float = 0.5) -> float:
        """Average of numeric values; falls back to default for each missing one."""
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

    # -------------------------------------------------------------------
    # decision_style
    # -------------------------------------------------------------------

    def _compute_decision_style(
        self,
        attributes: dict[str, dict[str, Attribute]],
    ) -> tuple[str, float]:
        """Return (decision_style, decision_style_score).

        Tie-breaking priority: analytical > social > emotional > habitual.
        """
        emotional_score = self._avg(
            self._attr(attributes, "psychology", "emotional_persuasion_susceptibility"),
            self._attr(attributes, "psychology", "fear_appeal_responsiveness"),
        )
        analytical_score = self._avg(
            self._attr(attributes, "psychology", "information_need"),
            self._attr(attributes, "decision_making", "research_before_purchase"),
        )
        habitual_score = self._avg(
            self._attr(attributes, "lifestyle", "routine_adherence"),
            self._attr(attributes, "psychology", "status_quo_bias"),
        )
        social_score = self._avg(
            self._attr(attributes, "social", "social_proof_bias"),
            self._attr(attributes, "social", "peer_influence_strength"),
        )

        scores = {
            "emotional": emotional_score,
            "analytical": analytical_score,
            "habitual": habitual_score,
            "social": social_score,
        }

        # Tie-break order (highest priority first)
        tie_break_order = ["analytical", "social", "emotional", "habitual"]

        winning_score = max(scores.values())
        # Among all styles that achieved the winning score, pick by tie-break priority
        winners = [style for style in tie_break_order if scores[style] == winning_score]
        decision_style = winners[0]  # first match in priority order

        total = sum(scores.values()) or 1.0
        decision_style_score = winning_score / total

        return decision_style, round(decision_style_score, 6)

    # -------------------------------------------------------------------
    # trust_anchor
    # -------------------------------------------------------------------

    def _compute_trust_anchor(
        self,
        attributes: dict[str, dict[str, Attribute]],
    ) -> str:
        """Read trust_orientation_primary categorical attribute directly."""
        value = self._attr(attributes, "social", "trust_orientation_primary")
        valid = {"self", "peer", "authority", "family"}
        if isinstance(value, str) and value in valid:
            return value
        # Default: "self" if missing
        return "self"

    # -------------------------------------------------------------------
    # risk_appetite
    # -------------------------------------------------------------------

    def _compute_risk_appetite(
        self,
        attributes: dict[str, dict[str, Attribute]],
    ) -> str:
        """Map risk_tolerance float → low / medium / high."""
        rt = self._safe_float(
            self._attr(attributes, "psychology", "risk_tolerance"), default=0.5
        )
        if rt < 0.35:
            return "low"
        elif rt < 0.65:
            return "medium"
        else:
            return "high"

    # -------------------------------------------------------------------
    # primary_value_orientation
    # -------------------------------------------------------------------

    _VALUE_DRIVER_MAP: dict[str, str] = {
        "price": "price",
        "quality": "quality",
        "brand": "brand",
        "convenience": "convenience",
        "relationships": "quality",  # closest proxy
        "status": "brand",           # closest proxy
    }

    def _compute_primary_value_orientation(
        self,
        attributes: dict[str, dict[str, Attribute]],
    ) -> str:
        """Map primary_value_driver → PrimaryValueOrientation literal."""
        driver = self._attr(attributes, "values", "primary_value_driver")
        if isinstance(driver, str):
            mapped = self._VALUE_DRIVER_MAP.get(driver)
            if mapped:
                return mapped
        # Default fallback
        return "quality"

    # -------------------------------------------------------------------
    # coping_mechanism
    # -------------------------------------------------------------------

    _TENSION_COPING_MAP: dict[str, tuple[str, str]] = {
        "aspiration_vs_constraint": (
            "routine_control",
            "You rely on structured routines to manage the gap between your aspirations and current constraints.",
        ),
        "independence_vs_validation": (
            "social_validation",
            "You seek external validation to resolve the tension between wanting independence and needing approval.",
        ),
        "quality_vs_budget": (
            "research_deep_dive",
            "You cope with quality-vs-budget tensions by researching thoroughly to find the best value possible.",
        ),
        "loyalty_vs_curiosity": (
            "optimism_bias",
            "You lean toward optimism that a new choice will match or beat your trusted option, easing the loyalty-vs-curiosity pull.",
        ),
        "control_vs_delegation": (
            "denial",
            "You manage the discomfort of delegation by downplaying uncertainty and trusting that things will work out.",
        ),
    }

    def _compute_coping_mechanism(
        self,
        attributes: dict[str, dict[str, Attribute]],
    ) -> CopingMechanism:
        """Derive CopingMechanism from tension_seed anchor."""
        tension_seed = self._attr(attributes, "identity", "tension_seed")
        if isinstance(tension_seed, str) and tension_seed in self._TENSION_COPING_MAP:
            coping_type, description = self._TENSION_COPING_MAP[tension_seed]
        else:
            # Default fallback
            coping_type = "routine_control"
            description = (
                "You rely on structured routines to bring predictability to an uncertain situation."
            )
        return CopingMechanism(type=coping_type, description=description)

    # -------------------------------------------------------------------
    # consistency_score
    # -------------------------------------------------------------------

    def _compute_consistency_score(
        self,
        attributes: dict[str, dict[str, Attribute]],
    ) -> int:
        """Measure attribute profile consistency via correlation-pair satisfaction.

        For each pair in KNOWN_CORRELATIONS:
          - positive pair: pair_score = 1 - abs(val_a - val_b)
          - negative pair: pair_score = abs(val_a - val_b)
        consistency_score = int(mean(all pair_scores) * 100)
        Default: 75 if no pairs can be evaluated.
        """
        pair_scores: list[float] = []

        # Build a flat lookup: attr_name → float value regardless of category
        flat: dict[str, float] = {}
        for cat_attrs in attributes.values():
            for name, attr in cat_attrs.items():
                if attr.type == "continuous":
                    try:
                        flat[name] = float(attr.value)
                    except (TypeError, ValueError):
                        pass

        for attr_a, attr_b, direction in KNOWN_CORRELATIONS:
            val_a = flat.get(attr_a)
            val_b = flat.get(attr_b)
            if val_a is None or val_b is None:
                # Cannot evaluate this pair — skip
                continue
            if direction == "positive":
                pair_scores.append(1.0 - abs(val_a - val_b))
            else:  # "negative"
                pair_scores.append(abs(val_a - val_b))

        if not pair_scores:
            return 75  # default when no pairs evaluable

        raw = mean(pair_scores)
        return int(raw * 100)

    # -------------------------------------------------------------------
    # consistency_band
    # -------------------------------------------------------------------

    @staticmethod
    def _compute_consistency_band(score: int) -> str:
        """Map 0–100 consistency score → low / medium / high."""
        if score < 50:
            return "low"
        elif score < 75:
            return "medium"
        else:
            return "high"

    # -------------------------------------------------------------------
    # key_tensions
    # -------------------------------------------------------------------

    _TENSION_SEED_READABLE: dict[str, str] = {
        "aspiration_vs_constraint": "Aspires to more than current constraints allow",
        "independence_vs_validation": "Wants independence but craves external validation",
        "quality_vs_budget": "Desires quality but is constrained by budget",
        "loyalty_vs_curiosity": "Torn between brand loyalty and curiosity for new options",
        "control_vs_delegation": "Wants control but is drawn to delegating decisions to others",
    }

    # Soft-constraint checks from §10 — (category_a, attr_a, category_b, attr_b, readable_tension)
    # Applies when pair diverges >0.35 in the "wrong" direction (i.e. soft constraint violated).
    _SOFT_CONSTRAINTS: list[tuple[str, str, str, str, str]] = [
        (
            "social", "authority_bias",
            "identity", "self_efficacy",
            "High authority deference conflicts with strong self-reliance",
        ),
        (
            "psychology", "analysis_paralysis",
            "decision_making", "decision_delegation",
            "Paralysis and delegation tendency reinforce each other, risking decision avoidance",
        ),
        (
            "psychology", "risk_tolerance",
            "psychology", "status_quo_bias",
            "High risk tolerance coexisting with strong status-quo bias creates inconsistent decision patterns",
        ),
        (
            "values", "budget_consciousness",
            "values", "deal_seeking_intensity",
            "Budget focus and deal-seeking are unusually misaligned",
        ),
        (
            "social", "social_proof_bias",
            "social", "wom_receiver_openness",
            "High social proof reliance but low word-of-mouth openness is atypical",
        ),
    ]

    def _compute_key_tensions(
        self,
        attributes: dict[str, dict[str, Attribute]],
    ) -> list[str]:
        """Derive key_tensions list (≥ 1 guaranteed).

        Sources:
        1. Human-readable tension_seed (always included).
        2. Soft-constraint violations.
        3. Extreme divergence on positive-correlation pairs (|diff| > 0.6).
        """
        tensions: list[str] = []

        # 1. tension_seed — always first
        tension_seed = self._attr(attributes, "identity", "tension_seed")
        if isinstance(tension_seed, str) and tension_seed in self._TENSION_SEED_READABLE:
            tensions.append(self._TENSION_SEED_READABLE[tension_seed])
        else:
            tensions.append("Recurring internal tension shaping decision-making")

        # Build flat float lookup
        flat: dict[str, float] = {}
        for cat_attrs in attributes.values():
            for name, attr in cat_attrs.items():
                if attr.type == "continuous":
                    try:
                        flat[name] = float(attr.value)
                    except (TypeError, ValueError):
                        pass

        # 2. Soft-constraint checks
        for cat_a, name_a, cat_b, name_b, readable in self._SOFT_CONSTRAINTS:
            val_a = flat.get(name_a)
            val_b = flat.get(name_b)
            if val_a is None or val_b is None:
                continue
            # These are positive-correlation pairs; flagged when values diverge >0.4
            diff = abs(val_a - val_b)
            if diff > 0.4:
                tensions.append(readable)

        # 3. Extreme divergence on positive-correlation pairs from KNOWN_CORRELATIONS
        for attr_a, attr_b, direction in KNOWN_CORRELATIONS:
            if direction != "positive":
                continue
            val_a = flat.get(attr_a)
            val_b = flat.get(attr_b)
            if val_a is None or val_b is None:
                continue
            if abs(val_a - val_b) > 0.6:
                tensions.append(
                    f"{attr_a.replace('_', ' ').title()} and "
                    f"{attr_b.replace('_', ' ').title()} are unusually misaligned"
                )

        return tensions
