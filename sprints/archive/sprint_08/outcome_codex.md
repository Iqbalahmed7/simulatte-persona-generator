# Sprint 8 Outcome — Codex

## 1. Files Created

| File | Lines | Notes |
|------|-------|-------|
| `src/grounding/cluster_deriver.py` | 350 | Full K-means implementation |
| `tests/test_grounding_cluster.py` | 127 | 8 tests |
| `src/grounding/types.py` (modified) | 103 | `BehaviouralArchetype` stub added; file was later overwritten by OpenCode's full types.py (which includes `BehaviouralFeatures`, `GroundingResult`, etc.) — Codex's `BehaviouralArchetype` stub was compatible with the final version |

`src/grounding/__init__.py` was also created (1 line) to make the package importable.

---

## 2. K-means Implementation

**Initialization strategy — K-means++:**
1. Pick the first centroid uniformly at random from all points.
2. For each subsequent centroid, compute the squared Euclidean distance from every point to its nearest existing centroid. Sample the next centroid with probability proportional to those squared distances.
3. Repeat until `k` centroids are chosen.

This biases seeding toward well-separated points, reducing the chance of poor local minima compared to fully random initialization.

**Convergence condition:**
- Each iteration performs a full assignment step (each point assigned to nearest centroid) then an update step (centroids recomputed as mean of assigned points).
- Convergence is declared when the full assignment vector is unchanged from the previous iteration.
- A hard cap of `KMEANS_MAX_ITER = 100` iterations prevents infinite loops on non-converging cases.
- Empty clusters (no points assigned) retain their previous centroid to avoid NaN.

---

## 3. K Selection — Elbow Method

`_select_k` runs independent K-means fits for every integer k in `[k_min, k_max]`. For each k it computes the total within-cluster inertia (sum of squared distances from each point to its assigned centroid).

The "elbow" is the k that produces the largest inertia drop versus the previous k — i.e. the index `i` where `inertia[i-1] - inertia[i]` is maximised. That k is returned as the selected cluster count.

Edge-case handling:
- `len(points) <= k_min` → return `max(1, len(points))` (can't have more clusters than points)
- `k_max` is clamped to `len(points)` before the loop

---

## 4. Archetype Derivation Rules

`_archetype_from_cluster` reads the 9-dim centroid and applies fixed thresholds:

| Field | Rule |
|-------|------|
| `price_sensitivity_band` | centroid[0] < 0.25 → `"low"`; < 0.50 → `"medium"`; < 0.75 → `"high"`; else → `"extreme"` |
| `trust_orientation_weights` | expert=c[1], peer=c[2], brand=c[3], ad=0.1 (fixed neutral), community=c[4], influencer=0.1 (fixed neutral) |
| `switching_propensity_band` | max(c[5], c[6]) < 0.25 → `"low"`; < 0.55 → `"medium"`; else → `"high"` |
| `primary_objections` | price band high/extreme → `"price_vs_value"`; switching band high → `"switching_cost_concern"`; if neither triggered → `"need_more_information"` (guarantees at least 1 entry) |

---

## 5. Test Results

```
tests/test_grounding_cluster.py::test_derive_clusters_empty               PASSED
tests/test_grounding_cluster.py::test_derive_clusters_fewer_than_k_min    PASSED
tests/test_grounding_cluster.py::test_derive_clusters_returns_archetypes  PASSED
tests/test_grounding_cluster.py::test_archetype_fields_populated          PASSED
tests/test_grounding_cluster.py::test_high_price_centroid_maps_correctly  PASSED
tests/test_grounding_cluster.py::test_euclidean_distance                  PASSED
tests/test_grounding_cluster.py::test_centroid_utility                    PASSED
tests/test_grounding_cluster.py::test_clustering_deterministic            PASSED

8 passed in 0.05s
```

One fix was required after initial implementation: `TypeAlias` was imported from `typing`, but the runtime is Python 3.9 (TypeAlias requires 3.10+). Fixed by replacing `from typing import TypeAlias` with `from typing import List` and declaring `Vector = List[float]` as a plain assignment.

---

## 6. Known Gaps

- **Elbow method uses a fresh `rng` per k-value** but shares state across the k-range sweep. If elbow selection is called multiple times with the same seed, results are consistent because `derive_clusters` instantiates a new `random.Random(seed)` each call. The final k-means run also uses a separately-seeded `random.Random(seed)` for full reproducibility.
- **Identical points** (all vectors the same) converge correctly to 1 effective cluster regardless of k. The degenerate k>1 case still runs but produces empty clusters that silently retain their seed centroid; the final `archetypes` list omits clusters with zero assigned points.
- **No inertia normalisation** in the elbow method: when comparing across k values the absolute inertia drop is used. On highly variable datasets the elbow signal can be weak; a normalised or second-derivative approach would be more robust but is not required by the spec.
- **`ad` and `influencer` trust weights are always 0.1** (fixed neutral) because the 9-dim vector has no direct signal for those channels. Downstream consumers should treat these as lower-confidence defaults.
- **No serialisation helpers** (JSON/dict export) on `BehaviouralArchetype` — not in spec scope.
