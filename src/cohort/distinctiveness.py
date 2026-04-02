"""
distinctiveness.py — G7 Cohort Distinctiveness enforcement.

Computes mean pairwise cosine distance on the 8 anchor attributes across all
persona pairs. Enforces threshold > 0.35. Identifies the most similar pair for
resampling if below threshold.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from src.schema.persona import PersonaRecord


# The 8 anchor attributes (from §6 ANCHOR_ATTRS)
_ANCHOR_ATTRS = [
    "personality_type",           # categorical — encode as index
    "risk_tolerance",             # continuous 0-1
    "trust_orientation_primary",  # categorical
    "economic_constraint_level",  # continuous 0-1
    "life_stage_priority",        # categorical
    "primary_value_driver",       # categorical
    "social_orientation",         # continuous 0-1
    "tension_seed",               # categorical
]

_CATEGORICAL_VOCABS: dict[str, list[str]] = {
    "personality_type": ["analytical", "social", "habitual", "spontaneous"],
    "trust_orientation_primary": ["self", "peer", "expert", "brand", "authority", "community"],
    "life_stage_priority": ["career", "family", "personal_growth", "legacy", "survival"],
    "primary_value_driver": ["price", "quality", "brand", "convenience", "relationships", "status"],
    "tension_seed": [
        "aspiration_vs_constraint", "independence_vs_validation",
        "quality_vs_budget", "loyalty_vs_curiosity", "control_vs_delegation",
    ],
}

# Continuous attributes — read directly from attributes dict, no vocab needed
_CONTINUOUS_ATTRS = {"risk_tolerance", "economic_constraint_level", "social_orientation"}


@dataclass
class DistinctivenessResult:
    passed: bool
    mean_pairwise_distance: float
    threshold: float
    most_similar_pair: tuple[str, str] | None   # (persona_id_a, persona_id_b)
    failures: list[str]
    resample_attempts: int = 0


def _get_attr_value(persona: PersonaRecord, attr_name: str) -> float | str | None:
    """
    Look up an anchor attribute from a PersonaRecord.

    Attributes are stored in persona.attributes as a two-level dict:
        {category: {attr_name: Attribute}}
    We search all categories for the requested attr_name.
    Returns the raw value (float or str), or None if not found.
    """
    for category_attrs in persona.attributes.values():
        if attr_name in category_attrs:
            return category_attrs[attr_name].value
    return None


def _encode_anchor_vector(persona: PersonaRecord) -> list[float]:
    """
    Return an 8-element float vector for cosine distance computation.
    - Continuous attrs: use raw value (already 0-1)
    - Categorical attrs: encode as index/len(vocab) → normalised 0-1
    - Missing attr: default to 0.5
    """
    vector: list[float] = []

    for attr_name in _ANCHOR_ATTRS:
        raw = _get_attr_value(persona, attr_name)

        if raw is None:
            # Missing attribute — default to mid-point
            vector.append(0.5)
            continue

        if attr_name in _CONTINUOUS_ATTRS:
            # Should be a float already (validated by schema)
            try:
                vector.append(float(raw))
            except (TypeError, ValueError):
                vector.append(0.5)
        else:
            # Categorical — encode as index / (len(vocab) - 1) to spread 0-1
            vocab = _CATEGORICAL_VOCABS.get(attr_name, [])
            if not vocab:
                vector.append(0.5)
                continue
            try:
                idx = vocab.index(str(raw))
                # Normalise: 0 → 0.0, last → 1.0
                # Guard single-item vocabs to avoid division by zero
                denom = len(vocab) - 1 if len(vocab) > 1 else 1
                vector.append(idx / denom)
            except ValueError:
                # Value not in vocab — default to mid-point
                vector.append(0.5)

    return vector


def _cosine_distance(a: list[float], b: list[float]) -> float:
    """
    Returns 1 - cosine_similarity.
    Range: [0, 1]. Higher = more different.
    Guard against zero vectors (return 0.0 distance — identical).
    """
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return 1.0 - (dot / (mag_a * mag_b))


def _mean_pairwise_distance(vectors: list[list[float]]) -> float:
    """All pairs (i, j) where i < j. Return mean cosine distance."""
    n = len(vectors)
    if n < 2:
        return 0.0
    distances = []
    for i in range(n):
        for j in range(i + 1, n):
            distances.append(_cosine_distance(vectors[i], vectors[j]))
    return sum(distances) / len(distances)


def _auto_threshold(n: int) -> float:
    """Return the auto-scaled distinctiveness threshold for cohort size n."""
    if n <= 3:
        return 0.10
    if n <= 5:
        return 0.15
    if n <= 9:
        return 0.25
    return 0.35


def check_distinctiveness(
    personas: list[PersonaRecord],
    threshold: float | None = None,   # None = auto-scale by N
) -> DistinctivenessResult:
    """
    G7 — Cohort Distinctiveness:
    Compute mean pairwise cosine distance on 8 anchor attributes.
    Threshold scales by cohort size (0.10–0.35) when threshold is None.

    Auto-scale table:
        N <= 3 : threshold = 0.10
        N <= 5 : threshold = 0.15
        N <= 9 : threshold = 0.25
        N >= 10: threshold = 0.35

    If below threshold:
    - Identify the most similar pair (lowest cosine distance)
    - Include their persona_ids in most_similar_pair for the assembler to resample

    Does NOT perform resampling — returns the result for the assembler to act on.
    """
    failures: list[str] = []

    if threshold is None:
        threshold = _auto_threshold(len(personas))

    if len(personas) < 2:
        # Cannot compute pairwise distance with fewer than 2 personas
        return DistinctivenessResult(
            passed=True,
            mean_pairwise_distance=0.0,
            threshold=threshold,
            most_similar_pair=None,
            failures=[],
        )

    # Encode every persona into an anchor vector
    vectors = [_encode_anchor_vector(p) for p in personas]

    # Compute mean pairwise distance
    mean_dist = _mean_pairwise_distance(vectors)

    # Identify the most similar pair (lowest cosine distance)
    min_dist = float("inf")
    most_similar_pair: tuple[str, str] | None = None

    n = len(vectors)
    for i in range(n):
        for j in range(i + 1, n):
            d = _cosine_distance(vectors[i], vectors[j])
            if d < min_dist:
                min_dist = d
                most_similar_pair = (personas[i].persona_id, personas[j].persona_id)

    passed = mean_dist > threshold

    if not passed:
        failures.append(
            f"Mean pairwise cosine distance {mean_dist:.4f} is below threshold {threshold} "
            f"(most similar pair: {most_similar_pair})"
        )

    return DistinctivenessResult(
        passed=passed,
        mean_pairwise_distance=mean_dist,
        threshold=threshold,
        most_similar_pair=most_similar_pair,
        failures=failures,
    )
