"""
diversity_checker.py — G6 Population Distribution checks for a cohort.

Rules:
  Failures (hard):
    1. No city > 20% of cohort
    2. No age bracket > 40% of cohort
    3. Income spans >= 3 distinct brackets

  Warnings (soft, from §11 Diversity Metrics table):
    4. No decision_style > 50% of cohort
    5. Trust anchor: >= 3 distinct anchors represented
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.schema.persona import PersonaRecord


@dataclass
class DiversityResult:
    passed: bool
    failures: list[str]
    warnings: list[str]
    city_distribution: dict[str, float]      # city → fraction
    age_distribution: dict[str, float]       # bracket → fraction
    income_distribution: dict[str, float]    # bracket → fraction


def _age_bracket(age: int) -> str:
    if age < 25:
        return "18-24"
    if age < 35:
        return "25-34"
    if age < 45:
        return "35-44"
    if age < 55:
        return "45-54"
    if age < 65:
        return "55-64"
    return "65+"


def _distribution(values: list[str]) -> dict[str, float]:
    """Compute fraction each unique value takes of total."""
    n = len(values)
    counts: dict[str, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return {k: c / n for k, c in counts.items()}


def check_diversity(personas: list[PersonaRecord]) -> DiversityResult:
    """
    G6 — Population Distribution checks:
    1. No city > 20% of cohort
    2. No age bracket > 40% of cohort
    3. Income spans >= 3 distinct brackets

    Also check from §11 Diversity Metrics table:
    4. No decision_style > 50% of cohort (warning, not failure)
    5. Trust anchor: >= 3 distinct anchors represented (warning, not failure)

    Rules 1-3 are failures. Rules 4-5 are warnings.
    """
    failures: list[str] = []
    warnings: list[str] = []

    # --- Gather raw values from each persona ---
    cities: list[str] = []
    ages: list[str] = []
    income_brackets: list[str] = []
    decision_styles: list[str] = []
    trust_anchors: list[str] = []

    for p in personas:
        cities.append(p.demographic_anchor.location.city)
        ages.append(_age_bracket(p.demographic_anchor.age))
        income_brackets.append(p.demographic_anchor.household.income_bracket)
        decision_styles.append(p.derived_insights.decision_style)
        trust_anchors.append(p.derived_insights.trust_anchor)

    # --- Compute distributions ---
    city_distribution = _distribution(cities)
    age_distribution = _distribution(ages)
    income_distribution = _distribution(income_brackets)

    # --- Rule 1: No city > 20% ---
    for city, fraction in city_distribution.items():
        if fraction > 0.20:
            failures.append(
                f"City '{city}' represents {fraction:.1%} of cohort (max allowed: 20%)"
            )

    # --- Rule 2: No age bracket > 40% ---
    for bracket, fraction in age_distribution.items():
        if fraction > 0.40:
            failures.append(
                f"Age bracket '{bracket}' represents {fraction:.1%} of cohort (max allowed: 40%)"
            )

    # --- Rule 3: Income spans >= 3 distinct brackets ---
    distinct_income_brackets = len(income_distribution)
    if distinct_income_brackets < 3:
        failures.append(
            f"Only {distinct_income_brackets} distinct income bracket(s) represented "
            f"(minimum required: 3)"
        )

    # --- Rule 4 (warning): No decision_style > 50% ---
    decision_style_dist = _distribution(decision_styles)
    for style, fraction in decision_style_dist.items():
        if fraction > 0.50:
            warnings.append(
                f"Decision style '{style}' represents {fraction:.1%} of cohort (recommended max: 50%)"
            )

    # --- Rule 5 (warning): >= 3 distinct trust anchors ---
    distinct_trust_anchors = len(set(trust_anchors))
    if distinct_trust_anchors < 3:
        warnings.append(
            f"Only {distinct_trust_anchors} distinct trust anchor(s) represented "
            f"(recommended minimum: 3)"
        )

    passed = len(failures) == 0

    return DiversityResult(
        passed=passed,
        failures=failures,
        warnings=warnings,
        city_distribution=city_distribution,
        age_distribution=age_distribution,
        income_distribution=income_distribution,
    )
