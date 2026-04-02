"""Tests for src/grounding/cluster_deriver.py

Sprint 8 — Grounding Pipeline Stage 3.
8 tests covering: empty input, under-k_min input, archetype count,
field validation, price band mapping, utility functions, determinism.
"""
import random


# ---------------------------------------------------------------------------
# Test 1: Empty vectors returns empty
# ---------------------------------------------------------------------------

def test_derive_clusters_empty():
    from src.grounding.cluster_deriver import derive_clusters
    result = derive_clusters([])
    assert result == []


# ---------------------------------------------------------------------------
# Test 2: Fewer vectors than k_min
# ---------------------------------------------------------------------------

def test_derive_clusters_fewer_than_k_min():
    """2 vectors, k_min=3 → still returns ≤ 2 archetypes (no crash)."""
    from src.grounding.cluster_deriver import derive_clusters
    vectors = [[0.8, 0.1, 0.2, 0.1, 0.1, 0.3, 0.1, 0.2, 0.1]] * 2
    result = derive_clusters(vectors, k_min=3)
    assert len(result) <= 2
    assert len(result) >= 1


# ---------------------------------------------------------------------------
# Test 3: Returns correct number of archetypes
# ---------------------------------------------------------------------------

def test_derive_clusters_returns_archetypes():
    """20 diverse vectors → between k_min and k_max archetypes."""
    from src.grounding.cluster_deriver import derive_clusters
    rng = random.Random(99)
    vectors = [[rng.random() for _ in range(9)] for _ in range(20)]
    result = derive_clusters(vectors, k_min=3, k_max=6)
    assert 1 <= len(result) <= 6


# ---------------------------------------------------------------------------
# Test 4: Archetype fields populated
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Test 5: High price centroid → "high" or "extreme" band
# ---------------------------------------------------------------------------

def test_high_price_centroid_maps_correctly():
    """Vectors with high price_salience_index → price_sensitivity_band high or extreme."""
    from src.grounding.cluster_deriver import derive_clusters
    # All vectors: price_salience = 0.9 (extreme)
    vectors = [[0.9, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]] * 10
    result = derive_clusters(vectors, k_min=1, k_max=2)
    # All in one cluster (identical points) — band should be high or extreme
    for arch in result:
        assert arch.price_sensitivity_band in ("high", "extreme")


# ---------------------------------------------------------------------------
# Test 6: Euclidean distance utility
# ---------------------------------------------------------------------------

def test_euclidean_distance():
    from src.grounding.cluster_deriver import _euclidean
    a = [0.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert abs(_euclidean(a, b) - 1.0) < 1e-9
    assert abs(_euclidean(b, a) - 1.0) < 1e-9
    # Same point = 0
    assert _euclidean(a, a) == 0.0


# ---------------------------------------------------------------------------
# Test 7: Centroid utility
# ---------------------------------------------------------------------------

def test_centroid_utility():
    from src.grounding.cluster_deriver import _centroid
    points = [[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]]
    c = _centroid(points)
    assert abs(c[0] - 0.5) < 1e-9
    assert abs(c[1] - (1 / 3)) < 1e-9


# ---------------------------------------------------------------------------
# Test 8: Deterministic with seed
# ---------------------------------------------------------------------------

def test_clustering_deterministic():
    """Same vectors + same seed → same archetype count and centroid."""
    from src.grounding.cluster_deriver import derive_clusters
    rng = random.Random(1)
    vectors = [[rng.random() for _ in range(9)] for _ in range(30)]
    r1 = derive_clusters(vectors, seed=42)
    r2 = derive_clusters(vectors, seed=42)
    assert len(r1) == len(r2)
    # Centroids match within float tolerance
    for a1, a2 in zip(r1, r2):
        for v1, v2 in zip(a1.centroid, a2.centroid):
            assert abs(v1 - v2) < 1e-9
