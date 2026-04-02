# SPRINT 8 BRIEF — CODEX
**Role:** Cluster Deriver (Pure-Python K-Means)
**Sprint:** 8 — Grounding Pipeline
**Spec ref:** Master Spec §7 Stage 3 (Behavioural Cluster Derivation)
**Previous rating:** 20/20

---

## Context

Sprint 8 builds the Grounding Pipeline. Your job is Stage 3: take per-signal feature vectors (list of 9-dim floats) and derive `BehaviouralArchetype` objects via pure-Python K-means clustering.

**No numpy, no sklearn.** The environment has neither. Use only Python standard library (`math`, `random`, `statistics`).

Types are defined in `src/grounding/types.py` (written by OpenCode). Import from there.

---

## Types contract (from `src/grounding/types.py`)

```python
from src.grounding.types import BehaviouralArchetype

# BehaviouralArchetype fields:
#   archetype_id: str
#   size: int                                    — number of signals in this cluster
#   price_sensitivity_band: Literal["low", "medium", "high", "extreme"]
#   trust_orientation_weights: dict[str, float]  — expert/peer/brand/ad/community/influencer
#   switching_propensity_band: Literal["low", "medium", "high"]
#   primary_objections: list[str]
#   centroid: list[float]                        — 9-dim feature vector centroid
```

---

## File: `src/grounding/cluster_deriver.py`

### Pure-Python K-means implementation

```python
"""Behavioural cluster derivation using pure-Python K-means.

Sprint 8 — Grounding Pipeline Stage 3.
No numpy, no sklearn. Standard library only.
"""
from __future__ import annotations

import math
import random
from typing import TypeAlias

from src.grounding.types import BehaviouralArchetype

Vector: TypeAlias = list[float]

MIN_K = 3
MAX_K = 8
KMEANS_MAX_ITER = 100
KMEANS_SEED = 42   # reproducible clustering in tests
```

### Core math utilities (implement these):

```python
def _euclidean(a: Vector, b: Vector) -> float:
    """Euclidean distance between two equal-length vectors."""
    ...

def _centroid(points: list[Vector]) -> Vector:
    """Mean vector of a list of equal-length vectors."""
    ...

def _inertia(points: list[Vector], assignments: list[int], centroids: list[Vector]) -> float:
    """Sum of squared distances from each point to its assigned centroid."""
    ...
```

### K-means++ initialization:

```python
def _kmeans_plus_plus_init(points: list[Vector], k: int, rng: random.Random) -> list[Vector]:
    """K-means++ centroid seeding.

    1. Pick first centroid uniformly at random.
    2. For each subsequent centroid: pick point with probability
       proportional to squared distance from nearest existing centroid.
    """
    ...
```

### K-means fit:

```python
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
    ...
```

### K selection via elbow method:

```python
def _select_k(points: list[Vector], k_min: int, k_max: int, rng: random.Random) -> int:
    """Select optimal K via elbow method on inertia.

    Fit K-means for k in [k_min, k_max]. Find k where inertia drops
    most between consecutive k values (elbow). Return that k.

    Edge cases:
    - If len(points) <= k_min: return k_min (can't have more clusters than points)
    - Clamp k_max to len(points) - 1
    """
    ...
```

### Archetype derivation from cluster:

```python
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
        Derive from price_sensitivity_band + switching_propensity_band:
        - price band "high"/"extreme" → include "price_vs_value"
        - switching band "high"       → include "switching_cost_concern"
        - Always include at least 1: if none triggered, use "need_more_information"
    """
    ...
```

### Public interface:

```python
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
    ...
```

---

## Tests: `tests/test_grounding_cluster.py`

### Test 1: Empty vectors returns empty

```python
def test_derive_clusters_empty():
    from src.grounding.cluster_deriver import derive_clusters
    result = derive_clusters([])
    assert result == []
```

### Test 2: Fewer vectors than k_min

```python
def test_derive_clusters_fewer_than_k_min():
    """2 vectors, k_min=3 → still returns ≤ 2 archetypes (no crash)."""
    from src.grounding.cluster_deriver import derive_clusters
    vectors = [[0.8, 0.1, 0.2, 0.1, 0.1, 0.3, 0.1, 0.2, 0.1]] * 2
    result = derive_clusters(vectors, k_min=3)
    assert len(result) <= 2
    assert len(result) >= 1
```

### Test 3: Returns correct number of archetypes

```python
def test_derive_clusters_returns_archetypes():
    """20 diverse vectors → between k_min and k_max archetypes."""
    from src.grounding.cluster_deriver import derive_clusters
    import random
    rng = random.Random(99)
    vectors = [[rng.random() for _ in range(9)] for _ in range(20)]
    result = derive_clusters(vectors, k_min=3, k_max=6)
    assert 1 <= len(result) <= 6
```

### Test 4: Archetype fields populated

```python
def test_archetype_fields_populated():
    """All archetype fields are populated and valid."""
    from src.grounding.cluster_deriver import derive_clusters
    vectors = [
        [0.9, 0.1, 0.2, 0.1, 0.1, 0.8, 0.1, 0.2, 0.1],  # high price, high switching
        [0.1, 0.8, 0.2, 0.1, 0.1, 0.1, 0.1, 0.8, 0.2],  # low price, trust expert
        [0.5, 0.2, 0.7, 0.1, 0.2, 0.3, 0.2, 0.3, 0.7],  # mid price, peer trust
    ] * 5  # 15 total points
    result = derive_clusters(vectors, k_min=3, k_max=3)
    for arch in result:
        assert arch.archetype_id
        assert arch.size >= 1
        assert arch.price_sensitivity_band in ("low", "medium", "high", "extreme")
        assert arch.switching_propensity_band in ("low", "medium", "high")
        assert len(arch.centroid) == 9
        assert len(arch.primary_objections) >= 1
        assert set(arch.trust_orientation_weights.keys()) == {
            "expert", "peer", "brand", "ad", "community", "influencer"
        }
```

### Test 5: High price centroid → "high" or "extreme" band

```python
def test_high_price_centroid_maps_correctly():
    """Vectors with high price_salience_index → price_sensitivity_band high or extreme."""
    from src.grounding.cluster_deriver import derive_clusters
    # All vectors: price_salience = 0.9 (extreme)
    vectors = [[0.9, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]] * 10
    result = derive_clusters(vectors, k_min=1, k_max=2)
    # All in one cluster (identical points) — band should be high or extreme
    for arch in result:
        assert arch.price_sensitivity_band in ("high", "extreme")
```

### Test 6: Euclidean distance utility

```python
def test_euclidean_distance():
    from src.grounding.cluster_deriver import _euclidean
    a = [0.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert abs(_euclidean(a, b) - 1.0) < 1e-9
    assert abs(_euclidean(b, a) - 1.0) < 1e-9
    # Same point = 0
    assert _euclidean(a, a) == 0.0
```

### Test 7: Centroid utility

```python
def test_centroid_utility():
    from src.grounding.cluster_deriver import _centroid
    points = [[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]]
    c = _centroid(points)
    assert abs(c[0] - 0.5) < 1e-9
    assert abs(c[1] - (1/3)) < 1e-9
```

### Test 8: Deterministic with seed

```python
def test_clustering_deterministic():
    """Same vectors + same seed → same archetype count and centroid."""
    from src.grounding.cluster_deriver import derive_clusters
    import random
    rng = random.Random(1)
    vectors = [[rng.random() for _ in range(9)] for _ in range(30)]
    r1 = derive_clusters(vectors, seed=42)
    r2 = derive_clusters(vectors, seed=42)
    assert len(r1) == len(r2)
    # Centroids match within float tolerance
    for a1, a2 in zip(r1, r2):
        for v1, v2 in zip(a1.centroid, a2.centroid):
            assert abs(v1 - v2) < 1e-9
```

---

## Constraints

- No numpy, no sklearn, no scipy. Standard library only (`math`, `random`, `statistics`).
- `KMEANS_SEED = 42` — used as default for reproducibility.
- `derive_clusters([])` returns `[]` — no crash.
- `trust_orientation_weights` must always have exactly 6 keys: expert, peer, brand, ad, community, influencer.
- `primary_objections` must have at least 1 entry.
- 8 tests, all pass without `--integration`.

---

## Outcome File

When done, write `sprints/outcome_codex.md` with:
1. File created (line count)
2. K-means implementation — initialization strategy + convergence condition
3. K selection — elbow method description
4. Archetype derivation rules
5. Test results (pass/fail)
6. Known gaps
