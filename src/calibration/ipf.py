"""Iterative Proportional Fitting (IPF) for census-calibrated demographics.

Master Spec §2 (Research Synthesis): "IPF is the standard method for
census-calibrated synthetic populations."

IPF adjusts a synthetic population's demographic marginals to match
empirical census targets. Given a cohort of personas and target
distributions for age, gender, location, income, etc., IPF iteratively
re-weights the population until marginals converge.

Usage:
    from src.calibration.ipf import ipf_reweight, MarginalTarget

    targets = [
        MarginalTarget("age_bracket", {"18-29": 0.22, "30-44": 0.27, "45-64": 0.30, "65+": 0.21}),
        MarginalTarget("gender", {"female": 0.51, "male": 0.49}),
    ]
    weights = ipf_reweight(personas, targets, max_iter=100)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Convergence threshold: stop when max marginal error < this.
_CONVERGENCE_THRESHOLD = 0.005
_MAX_ITER = 200


@dataclass
class MarginalTarget:
    """Target marginal distribution for one demographic dimension."""
    dimension: str                    # e.g. "age_bracket", "gender", "region"
    distribution: dict[str, float]    # category → target proportion (must sum to ~1.0)


@dataclass
class IPFResult:
    """Result of IPF reweighting."""
    weights: list[float]              # per-persona weight (sums to N)
    converged: bool
    iterations: int
    max_residual: float               # largest marginal error at termination
    marginal_errors: dict[str, dict[str, float]]  # dimension → category → error


def _extract_dimension(persona, dimension: str) -> str | None:
    """Extract a demographic dimension value from a persona.

    Supports dot-notation (e.g. "location.region") and bracket lookup
    on the demographic_anchor.
    """
    anchor = persona.demographic_anchor

    # Direct attribute
    if hasattr(anchor, dimension):
        return str(getattr(anchor, dimension))

    # Nested (e.g. "location.region", "household.income_bracket")
    parts = dimension.split(".")
    obj = anchor
    for part in parts:
        if hasattr(obj, part):
            obj = getattr(obj, part)
        else:
            return None
    return str(obj)


def _age_to_bracket(age: int) -> str:
    """Map numeric age to standard bracket."""
    if age < 18:
        return "under_18"
    if age < 30:
        return "18-29"
    if age < 45:
        return "30-44"
    if age < 65:
        return "45-64"
    return "65+"


def _classify_persona(persona, dimension: str) -> str | None:
    """Classify a persona into a category for a given dimension."""
    if dimension == "age_bracket":
        age = getattr(persona.demographic_anchor, "age", None)
        if age is not None:
            return _age_to_bracket(age)
        return None

    return _extract_dimension(persona, dimension)


def ipf_reweight(
    personas: list,
    targets: list[MarginalTarget],
    max_iter: int = _MAX_ITER,
    convergence: float = _CONVERGENCE_THRESHOLD,
) -> IPFResult:
    """Run IPF to compute per-persona weights matching target marginals.

    Algorithm:
      1. Initialize all weights to 1.0
      2. For each target dimension:
         a. Compute current weighted marginal distribution
         b. For each category: compute ratio = target_proportion / current_proportion
         c. Multiply each persona's weight by its category's ratio
      3. Repeat until convergence or max_iter

    Args:
        personas: List of PersonaRecord objects
        targets:  List of MarginalTarget (one per dimension)
        max_iter: Maximum iterations (default 200)
        convergence: Stop when max marginal error < this (default 0.005)

    Returns:
        IPFResult with per-persona weights and convergence diagnostics.
    """
    n = len(personas)
    if n == 0:
        return IPFResult(weights=[], converged=True, iterations=0,
                         max_residual=0.0, marginal_errors={})

    # Pre-classify each persona for each dimension.
    classifications: dict[str, list[str | None]] = {}
    for target in targets:
        classifications[target.dimension] = [
            _classify_persona(p, target.dimension) for p in personas
        ]

    # Initialize weights.
    weights = [1.0] * n

    converged = False
    iteration = 0

    for iteration in range(1, max_iter + 1):
        max_residual = 0.0

        for target in targets:
            cats = classifications[target.dimension]

            # Compute current weighted distribution.
            category_weight: dict[str, float] = {}
            for i, cat in enumerate(cats):
                if cat is not None:
                    category_weight[cat] = category_weight.get(cat, 0.0) + weights[i]

            total_weight = sum(category_weight.values())
            if total_weight == 0.0:
                continue

            # Compute adjustment ratios.
            ratios: dict[str, float] = {}
            for cat, target_prop in target.distribution.items():
                current_prop = category_weight.get(cat, 0.0) / total_weight
                if current_prop > 0.0:
                    ratios[cat] = target_prop / current_prop
                else:
                    ratios[cat] = 1.0  # category not present — can't adjust

                residual = abs(target_prop - current_prop)
                max_residual = max(max_residual, residual)

            # Apply ratios to weights.
            for i, cat in enumerate(cats):
                if cat is not None and cat in ratios:
                    weights[i] *= ratios[cat]

        if max_residual < convergence:
            converged = True
            break

    # Normalize weights so they sum to N.
    w_sum = sum(weights)
    if w_sum > 0:
        weights = [w * n / w_sum for w in weights]

    # Compute final marginal errors.
    marginal_errors: dict[str, dict[str, float]] = {}
    for target in targets:
        cats = classifications[target.dimension]
        category_weight: dict[str, float] = {}
        for i, cat in enumerate(cats):
            if cat is not None:
                category_weight[cat] = category_weight.get(cat, 0.0) + weights[i]

        total_weight = sum(category_weight.values())
        dim_errors: dict[str, float] = {}
        for cat, target_prop in target.distribution.items():
            current_prop = category_weight.get(cat, 0.0) / total_weight if total_weight > 0 else 0.0
            dim_errors[cat] = round(target_prop - current_prop, 4)
        marginal_errors[target.dimension] = dim_errors

    if not converged:
        logger.warning(
            "IPF did not converge after %d iterations (max_residual=%.4f)",
            iteration, max_residual,
        )

    return IPFResult(
        weights=weights,
        converged=converged,
        iterations=iteration,
        max_residual=round(max_residual, 4),
        marginal_errors=marginal_errors,
    )


# ---------------------------------------------------------------------------
# Pre-built census targets
# ---------------------------------------------------------------------------

US_CENSUS_TARGETS = [
    MarginalTarget("age_bracket", {
        "18-29": 0.21, "30-44": 0.26, "45-64": 0.31, "65+": 0.22,
    }),
    MarginalTarget("gender", {
        "female": 0.51, "male": 0.49,
    }),
]

INDIA_CENSUS_TARGETS = [
    MarginalTarget("age_bracket", {
        "18-29": 0.34, "30-44": 0.28, "45-64": 0.25, "65+": 0.13,
    }),
    MarginalTarget("gender", {
        "female": 0.48, "male": 0.52,
    }),
    MarginalTarget("location.urban_tier", {
        "metro": 0.25, "tier2": 0.30, "tier3": 0.25, "rural": 0.20,
    }),
]
