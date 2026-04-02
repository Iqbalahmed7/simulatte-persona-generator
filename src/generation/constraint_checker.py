from __future__ import annotations

from typing import Any

from src.schema.persona import Attribute, PersonaRecord
from src.taxonomy.base_taxonomy import KNOWN_CORRELATIONS


class ConstraintViolation:
    def __init__(
        self,
        constraint_id: str,
        constraint_type: str,
        description: str,
        severity: str,
        attr_a: str | None = None,
        attr_b: str | None = None,
        suggested_fix: str | None = None,
    ):
        self.constraint_id = constraint_id
        self.constraint_type = constraint_type
        self.description = description
        self.severity = severity
        self.attr_a = attr_a
        self.attr_b = attr_b
        self.suggested_fix = suggested_fix

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "constraint_type": self.constraint_type,
            "description": self.description,
            "severity": self.severity,
            "attr_a": self.attr_a,
            "attr_b": self.attr_b,
            "suggested_fix": self.suggested_fix,
        }


class ConstraintChecker:
    """
    Provides the runtime enforcement layer for hard and soft constraints.
    Called by attribute filler mid-fill and by validators post-fill.
    """

    def check_hard_constraints(
        self,
        persona: PersonaRecord,
    ) -> list[ConstraintViolation]:
        """
        Runs all 6 hard constraint checks (HC1–HC6).
        Returns list of violations — empty list means clean.
        Hard violations are blocking: the persona should not be accepted.
        """
        violations: list[ConstraintViolation] = []

        # HC1: household.income_bracket in ["below_poverty", "poverty_line"]
        #       AND premium_quality_preference > 0.85
        income_bracket = persona.demographic_anchor.household.income_bracket
        pqp = self._get_attr_value(persona, "values", "premium_quality_preference")
        if (
            ("poverty" in income_bracket.lower())
            and isinstance(pqp, (int, float))
            and pqp > 0.85
        ):
            violations.append(
                ConstraintViolation(
                    constraint_id="HC1",
                    constraint_type="hard",
                    description=(
                        "Poverty-level income bracket is incompatible with very high "
                        "premium_quality_preference (> 0.85)"
                    ),
                    severity="blocking",
                    attr_a="income_bracket",
                    attr_b="premium_quality_preference",
                    suggested_fix="Reduce premium_quality_preference to ≤ 0.55",
                )
            )

        # HC2: location.urban_tier in ["tier3", "rural"]
        #       AND digital_payment_comfort > 0.85
        urban_tier = persona.demographic_anchor.location.urban_tier
        dpc = self._get_attr_value(persona, "lifestyle", "digital_payment_comfort")
        if (
            urban_tier in ("tier3", "rural")
            and isinstance(dpc, (int, float))
            and dpc > 0.85
        ):
            violations.append(
                ConstraintViolation(
                    constraint_id="HC2",
                    constraint_type="hard",
                    description=(
                        "Tier-3 or rural location is incompatible with very high "
                        "digital_payment_comfort (> 0.85)"
                    ),
                    severity="blocking",
                    attr_a="urban_tier",
                    attr_b="digital_payment_comfort",
                    suggested_fix="Reduce digital_payment_comfort to ≤ 0.55",
                )
            )

        # HC3: health_anxiety < 0.2 AND health_supplement_belief > 0.80
        # health_supplement_belief is not yet in the taxonomy — skip silently if None.
        health_anxiety = self._get_attr_value(persona, "psychology", "health_anxiety")
        health_supp = self._get_attr_value(persona, "psychology", "health_supplement_belief")
        if (
            health_supp is not None
            and isinstance(health_anxiety, (int, float))
            and isinstance(health_supp, (int, float))
            and health_anxiety < 0.2
            and health_supp > 0.80
        ):
            violations.append(
                ConstraintViolation(
                    constraint_id="HC3",
                    constraint_type="hard",
                    description=(
                        "Very low health_anxiety (< 0.2) contradicts very high "
                        "health_supplement_belief (> 0.80)"
                    ),
                    severity="blocking",
                    attr_a="health_anxiety",
                    attr_b="health_supplement_belief",
                    suggested_fix="Reduce health_supplement_belief to ≤ 0.50",
                )
            )

        # HC4: demographic_anchor.age < 25 AND brand_loyalty > 0.80
        brand_loyalty = self._get_attr_value(persona, "values", "brand_loyalty")
        if (
            persona.demographic_anchor.age < 25
            and isinstance(brand_loyalty, (int, float))
            and brand_loyalty > 0.80
        ):
            violations.append(
                ConstraintViolation(
                    constraint_id="HC4",
                    constraint_type="hard",
                    description=(
                        "Age < 25 is incompatible with very high brand_loyalty (> 0.80)"
                    ),
                    severity="blocking",
                    attr_a="age",
                    attr_b="brand_loyalty",
                    suggested_fix="Reduce brand_loyalty to ≤ 0.55",
                )
            )

        # HC5: household.income_bracket in ["high", "top_bracket", "top-bracket"]
        #       AND deal_seeking_intensity > 0.85
        deal_seeking = self._get_attr_value(persona, "values", "deal_seeking_intensity")
        if (
            ("high" in income_bracket.lower() or "top" in income_bracket.lower())
            and isinstance(deal_seeking, (int, float))
            and deal_seeking > 0.85
        ):
            violations.append(
                ConstraintViolation(
                    constraint_id="HC5",
                    constraint_type="hard",
                    description=(
                        "High or top income bracket is incompatible with very high "
                        "deal_seeking_intensity (> 0.85)"
                    ),
                    severity="blocking",
                    attr_a="income_bracket",
                    attr_b="deal_seeking_intensity",
                    suggested_fix="Reduce deal_seeking_intensity to ≤ 0.55",
                )
            )

        # HC6: risk_tolerance > 0.80 AND loss_aversion > 0.80
        risk_tolerance = self._get_attr_value(persona, "psychology", "risk_tolerance")
        loss_aversion = self._get_attr_value(persona, "psychology", "loss_aversion")
        if (
            isinstance(risk_tolerance, (int, float))
            and isinstance(loss_aversion, (int, float))
            and risk_tolerance > 0.80
            and loss_aversion > 0.80
        ):
            violations.append(
                ConstraintViolation(
                    constraint_id="HC6",
                    constraint_type="hard",
                    description=(
                        "Very high risk_tolerance (> 0.80) contradicts very high "
                        "loss_aversion (> 0.80)"
                    ),
                    severity="blocking",
                    attr_a="risk_tolerance",
                    attr_b="loss_aversion",
                    suggested_fix="Reduce loss_aversion to ≤ 0.50",
                )
            )

        return violations

    def check_correlation_consistency(
        self,
        attributes: dict[str, dict[str, Attribute]],
    ) -> list[ConstraintViolation]:
        """
        Checks KNOWN_CORRELATIONS from base taxonomy.
        Threshold: positive pair violated if |a - b| > 0.5.
        Negative pair violated if (a + b > 1.5).
        Returns list of soft violations.
        """
        violations: list[ConstraintViolation] = []

        # Create a flat map for easier lookup
        flat_attrs: dict[str, float] = {}
        for category in attributes.values():
            for name, attr in category.items():
                if isinstance(attr.value, (int, float)):
                    flat_attrs[name] = float(attr.value)

        for attr_a_name, attr_b_name, direction in KNOWN_CORRELATIONS:
            if attr_a_name in flat_attrs and attr_b_name in flat_attrs:
                val_a = flat_attrs[attr_a_name]
                val_b = flat_attrs[attr_b_name]

                if direction == "positive":
                    if abs(val_a - val_b) > 0.5:
                        violations.append(
                            ConstraintViolation(
                                constraint_id=f"CORR_{attr_a_name}_{attr_b_name}",
                                constraint_type="soft",
                                description=f"Correlation violation (positive): {attr_a_name} and {attr_b_name} should track together",
                                severity="tension",
                                attr_a=attr_a_name,
                                attr_b=attr_b_name,
                            )
                        )
                elif direction == "negative":
                    if (val_a + val_b) > 1.5:
                        violations.append(
                            ConstraintViolation(
                                constraint_id=f"CORR_{attr_a_name}_{attr_b_name}",
                                constraint_type="soft",
                                description=f"Correlation violation (negative): {attr_a_name} and {attr_b_name} should oppose each other",
                                severity="tension",
                                attr_a=attr_a_name,
                                attr_b=attr_b_name,
                            )
                        )

        return violations

    def check_all(
        self,
        persona: PersonaRecord,
    ) -> tuple[list[ConstraintViolation], list[ConstraintViolation]]:
        """
        Returns (hard_violations, soft_violations).
        """
        hard = self.check_hard_constraints(persona)
        soft = self.check_correlation_consistency(persona.attributes)
        return hard, soft

    def _get_attr_value(
        self,
        persona: PersonaRecord,
        category: str,
        name: str,
    ) -> float | str | None:
        """
        Safe accessor for persona.attributes[category][name].value.
        """
        try:
            return persona.attributes[category][name].value
        except KeyError:
            return None
