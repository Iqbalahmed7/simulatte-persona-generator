"""Behavioural cluster derivation using pure-Python K-means.

Sprint 8 — Grounding Pipeline Stage 3.
No numpy, no sklearn. Standard library only.
"""
from __future__ import annotations

import math
import random
from typing import List

from src.grounding.types import BehaviouralArchetype

# Python 3.9 compatible type alias (TypeAlias requires 3.10+)
Vector = List[float]

MIN_K = 3
MAX_K = 8
KMEANS_MAX_ITER = 100
KMEANS_SEED = 42  # reproducible clustering in tests


# ---------------------------------------------------------------------------
# Core math utilities
# ---------------------------------------------------------------------------

def _euclidean(a: Vector, b: Vector) -> float:
    """Euclidean distance between two equal-length vectors."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _centroid(points: list[Vector]) -> Vector:
    """Mean vector of a list of equal-length vectors."""
    n = len(points)
    dim = len(points[0])
    return [sum(p[i] for p in points) / n for i in range(dim)]


def _inertia(
    points: list[Vector],
    assignments: list[int],
    centroids: list[Vector],
) -> float:
    """Sum of squared distances from each point to its assigned centroid."""
    total = 0.0
    for point, cluster_idx in zip(points, assignments):
        dist = _euclidean(point, centroids[cluster_idx])
        total += dist ** 2
    return total


# ---------------------------------------------------------------------------
# K-means++ initialization
# ---------------------------------------------------------------------------

def _kmeans_plus_plus_init(
    points: list[Vector], k: int, rng: random.Random
) -> list[Vector]:
    """K-means++ centroid seeding.

    1. Pick first centroid uniformly at random.
    2. For each subsequent centroid: pick point with probability
       proportional to squared distance from nearest existing centroid.
    """
    centroids: list[Vector] = [rng.choice(points)]

    for _ in range(k - 1):
        # Compute squared distance from each point to the nearest centroid.
        sq_dists: list[float] = []
        for point in points:
            min_sq = min(_euclidean(point, c) ** 2 for c in centroids)
            sq_dists.append(min_sq)

        total = sum(sq_dists)
        if total == 0.0:
            # All points coincide with existing centroids — pick uniformly.
            centroids.append(rng.choice(points))
            continue

        # Weighted random selection.
        threshold = rng.uniform(0.0, total)
        cumulative = 0.0
        chosen = points[-1]  # fallback
        for point, sq_d in zip(points, sq_dists):
            cumulative += sq_d
            if cumulative >= threshold:
                chosen = point
                break
        centroids.append(chosen)

    return centroids


# ---------------------------------------------------------------------------
# K-means fit
# ---------------------------------------------------------------------------

def _kmeans(
    points: list[Vector],
    k: int,
    rng: random.Random,
    max_iter: int = KMEANS_MAX_ITER,
) -> tuple[list[int], list[Vector]]:
    """Run K-means and return (assignments, centroids).

    Uses K-means++ initialization.
    Stops when assignments stop changing or max_iter reached.
    """
    # Handle degenerate case: fewer points than clusters.
    k = min(k, len(points))

    centroids = _kmeans_plus_plus_init(points, k, rng)

    assignments: list[int] = [0] * len(points)

    for _ in range(max_iter):
        # Assignment step.
        new_assignments: list[int] = []
        for point in points:
            distances = [_euclidean(point, c) for c in centroids]
            new_assignments.append(distances.index(min(distances)))

        if new_assignments == assignments:
            break
        assignments = new_assignments

        # Update step: recompute centroids from assigned points.
        new_centroids: list[Vector] = []
        for cluster_idx in range(k):
            cluster_points = [
                p for p, a in zip(points, assignments) if a == cluster_idx
            ]
            if cluster_points:
                new_centroids.append(_centroid(cluster_points))
            else:
                # Empty cluster — keep old centroid to avoid NaN.
                new_centroids.append(centroids[cluster_idx])
        centroids = new_centroids

    return assignments, centroids


# ---------------------------------------------------------------------------
# K selection via elbow method
# ---------------------------------------------------------------------------

def _select_k(
    points: list[Vector], k_min: int, k_max: int, rng: random.Random
) -> int:
    """Select optimal K via elbow method on inertia.

    Fit K-means for k in [k_min, k_max]. Find k where inertia drops
    most between consecutive k values (elbow). Return that k.

    Edge cases:
    - If len(points) <= k_min: return k_min (can't have more clusters than points)
    - Clamp k_max to len(points) - 1 (but at least 1)
    """
    n = len(points)

    # Clamp k_max so we never have more clusters than points.
    k_max = min(k_max, n)

    # If we have fewer or equal points to k_min, just use as many clusters
    # as we have points (minimum 1).
    if n <= k_min:
        return max(1, n)

    # Ensure we have a valid range.
    k_min = max(1, k_min)
    k_max = max(k_min, k_max)

    if k_min == k_max:
        return k_min

    inertias: list[tuple[int, float]] = []
    for k in range(k_min, k_max + 1):
        assignments, centroids = _kmeans(points, k, rng)
        inertias.append((k, _inertia(points, assignments, centroids)))

    if len(inertias) == 1:
        return inertias[0][0]

    # Find the k that produces the largest inertia drop from k-1 to k.
    best_k = inertias[0][0]
    best_drop = 0.0
    for i in range(1, len(inertias)):
        drop = inertias[i - 1][1] - inertias[i][1]
        if drop > best_drop:
            best_drop = drop
            best_k = inertias[i][0]

    return best_k


# ---------------------------------------------------------------------------
# Archetype derivation from cluster
# ---------------------------------------------------------------------------

def _archetype_from_cluster(
    archetype_id: str,
    cluster_points: list[Vector],
    centroid: Vector,
) -> BehaviouralArchetype:
    """Derive a BehaviouralArchetype from a cluster's centroid.

    Vector dimension map (same as BehaviouralFeatures.to_vector()):
      0: price_salience_index
      1: trust_expert
      2: trust_peer
      3: trust_brand
      4: trust_community
      5: switching_price
      6: switching_service
      7: trigger_need
      8: trigger_rec

    Derivation rules:
      price_sensitivity_band:
        centroid[0] < 0.25  → "low"
        centroid[0] < 0.50  → "medium"
        centroid[0] < 0.75  → "high"
        else                → "extreme"

      trust_orientation_weights:
        expert     = centroid[1]
        peer       = centroid[2]
        brand      = centroid[3]
        ad         = 0.1  (no direct signal — set neutral)
        community  = centroid[4]
        influencer = 0.1  (no direct signal — set neutral)

      switching_propensity_band:
        max(centroid[5], centroid[6]) < 0.25  → "low"
        max(centroid[5], centroid[6]) < 0.55  → "medium"
        else                                   → "high"

      primary_objections:
        - price band "high"/"extreme" → include "price_vs_value"
        - switching band "high"       → include "switching_cost_concern"
        - Always include at least 1: if none triggered, use "need_more_information"
    """
    # Price sensitivity band.
    ps = centroid[0]
    if ps < 0.25:
        price_band: str = "low"
    elif ps < 0.50:
        price_band = "medium"
    elif ps < 0.75:
        price_band = "high"
    else:
        price_band = "extreme"

    # Trust orientation weights.
    trust_weights: dict[str, float] = {
        "expert": centroid[1],
        "peer": centroid[2],
        "brand": centroid[3],
        "ad": 0.1,
        "community": centroid[4],
        "influencer": 0.1,
    }

    # Switching propensity band.
    sw_max = max(centroid[5], centroid[6])
    if sw_max < 0.25:
        switching_band: str = "low"
    elif sw_max < 0.55:
        switching_band = "medium"
    else:
        switching_band = "high"

    # Primary objections.
    objections: list[str] = []
    if price_band in ("high", "extreme"):
        objections.append("price_vs_value")
    if switching_band == "high":
        objections.append("switching_cost_concern")
    if not objections:
        objections.append("need_more_information")

    return BehaviouralArchetype(
        archetype_id=archetype_id,
        size=len(cluster_points),
        price_sensitivity_band=price_band,  # type: ignore[arg-type]
        trust_orientation_weights=trust_weights,
        switching_propensity_band=switching_band,  # type: ignore[arg-type]
        primary_objections=objections,
        centroid=centroid,
    )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def derive_clusters(
    vectors: list[Vector],
    k_min: int = MIN_K,
    k_max: int = MAX_K,
    seed: int = KMEANS_SEED,
) -> list[BehaviouralArchetype]:
    """Derive behavioural archetypes from per-signal feature vectors.

    Args:
        vectors: List of 9-dim feature vectors (one per signal).
        k_min:   Minimum cluster count (default 3).
        k_max:   Maximum cluster count (default 8).
        seed:    Random seed for reproducibility.

    Returns:
        List of BehaviouralArchetype objects, one per cluster.

    Edge cases:
        - If vectors is empty: return []
        - If len(vectors) < k_min: k = len(vectors), minimum 1
    """
    if not vectors:
        return []

    n = len(vectors)
    rng = random.Random(seed)

    # Clamp k to valid range.
    effective_k_min = max(1, min(k_min, n))
    effective_k_max = max(effective_k_min, min(k_max, n))

    # Select best k via elbow method.
    k = _select_k(vectors, effective_k_min, effective_k_max, rng)

    # Run final k-means with a fresh RNG seeded identically for reproducibility.
    rng_final = random.Random(seed)
    assignments, centroids = _kmeans(vectors, k, rng_final)

    # Build archetypes.
    archetypes: list[BehaviouralArchetype] = []
    for cluster_idx in range(k):
        cluster_points = [
            v for v, a in zip(vectors, assignments) if a == cluster_idx
        ]
        if not cluster_points:
            continue
        archetype = _archetype_from_cluster(
            archetype_id=f"archetype_{cluster_idx + 1:02d}",
            cluster_points=cluster_points,
            centroid=centroids[cluster_idx],
        )
        archetypes.append(archetype)

    return archetypes
