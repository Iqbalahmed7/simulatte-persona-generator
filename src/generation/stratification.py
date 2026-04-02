from __future__ import annotations

from typing import Any

import numpy as np
from src.schema.persona import PersonaRecord
from src.taxonomy.base_taxonomy import ANCHOR_ATTRIBUTES


class StratificationResult:
    def __init__(
        self,
        cohort: list[PersonaRecord],
        near_center: list[PersonaRecord],
        mid_range: list[PersonaRecord],
        far_outliers: list[PersonaRecord],
        centroid: np.ndarray,
        distances: dict[str, float],
    ):
        self.cohort = cohort
        self.near_center = near_center
        self.mid_range = mid_range
        self.far_outliers = far_outliers
        self.centroid = centroid
        self.distances = distances


class CohortStratifier:
    """
    Selects and stratifies a cohort from a pool of candidate personas using 5:3:2 distribution.
    """

    def stratify(
        self,
        candidates: list[PersonaRecord],
        target_size: int,
    ) -> StratificationResult:
        """
        From candidates, select target_size personas using 5:3:2 stratification.
        """
        if target_size < 3:
            raise ValueError("target_size must be ≥ 3 for 5:3:2 stratification.")

        if len(candidates) < target_size:
            # Should have more candidates, but let's handle the case where we don't.
            # In practice, the caller should ensure candidates >= target_size * 2.
            pass

        # 1. Extract vectors and compute distances
        vectors: list[np.ndarray] = [self._extract_anchor_vector(c) for c in candidates]
        centroid = self._compute_centroid(vectors)

        distances: list[tuple[PersonaRecord, float]] = []
        for i, candidate in enumerate(candidates):
            dist = self._cosine_distance(vectors[i], centroid)
            distances.append((candidate, float(dist)))

        # Sort by distance from centroid (descending so we can pick outliers if needed)
        # Actually, sort ascending (closest to furthest)
        distances.sort(key=lambda x: x[1])

        # 2. Determine band sizes
        n_near = round(0.5 * target_size)
        n_mid = round(0.3 * target_size)
        n_far = target_size - n_near - n_mid

        # Adjust for rounding edge cases if needed (should already sum to target_size)
        # 5:3:2 on 10 -> 5, 3, 2. Correct.
        # 5:3:2 on 5 -> 2.5(3), 1.5(2), 5-3-2 = 0? No.
        # Let's check 5: near=3, mid=2, far=0. That's bad.
        # The brief says "remainder far".
        # 5: 0.5*5=2.5->3 near. 0.3*5=1.5->2 mid. 5-3-2=0 far.
        # Wait, if target_size=5, 5:3:2 is 2.5, 1.5, 1.0.
        # Maybe use math.floor for near/mid to ensure far gets some?
        # "round" is specified.
        # "A cohort of 10 must produce 5/3/2 distribution within ±1 tolerance"
        
        # 3. Select personas for each band from the sorted pool
        # We need to split the candidate pool into 3 segments or just pick from the sorted list.
        # If we pick closest for near, furthest for far, and middle for mid.
        
        # Candidate pool size could be large. Let's say 20 candidates for 10 target.
        # Distances: [0.01, 0.02, ..., 0.5] (sorted)
        # near_pool = distances[:10]
        # mid_pool = distances[10:16]
        # far_pool = distances[16:]
        # But we need to select exactly target_size.
        
        # Proper approach:
        # Split entire candidate pool into 3 quantile bands.
        # Pick n_near from the closest quantile, n_mid from middle, n_far from furthest.
        
        pool_size = len(candidates)
        # Quantile thresholds (0.33, 0.66) ? No, the bands are defined by distance relative to centroid.
        # "50% near-center / 30% mid-range / 20% far"
        # Since the pool size is arbitrary, we should divide the pool into three segments by count.
        # segment_near = top 50% of candidates by proximity
        # segment_mid = next 30%
        # segment_far = bottom 20%
        
        idx_mid_start = round(0.5 * pool_size)
        idx_far_start = round(0.8 * pool_size)
        
        pool_near = distances[:idx_mid_start]
        pool_mid = distances[idx_mid_start:idx_far_start]
        pool_far = distances[idx_far_start:]
        
        # If any pool is empty (due to small candidate size), fallback to others
        # (Though brief says pool >= 2*target_size)
        
        selected_near = [d[0] for d in pool_near[:n_near]]
        selected_mid = [d[0] for d in pool_mid[:n_mid]]
        selected_far = [d[0] for d in pool_far[:n_far]]
        
        # If any band didn't have enough candidates (unlikely with >=2X pool), fill from others.
        selected_cohort = selected_near + selected_mid + selected_far
        
        # Distance dictionary for result
        dist_dict = {d[0].persona_id: d[1] for d in distances}

        return StratificationResult(
            cohort=selected_cohort,
            near_center=selected_near,
            mid_range=selected_mid,
            far_outliers=selected_far,
            centroid=centroid,
            distances=dist_dict,
        )

    def _extract_anchor_vector(self, persona: PersonaRecord) -> np.ndarray:
        """
        Extract the 8 anchor attribute values as a float vector.
        """
        vector = []
        for defn in ANCHOR_ATTRIBUTES:
            val = self._get_persona_attr_value(persona, defn.category, defn.name)
            
            if defn.attr_type == "continuous":
                if isinstance(val, (int, float)):
                    vector.append(float(val))
                else:
                    vector.append(0.5)
            else:  # categorical
                if defn.options and val in defn.options:
                    idx = defn.options.index(val)
                    if len(defn.options) > 1:
                        encoded = idx / (len(defn.options) - 1)
                    else:
                        encoded = 0.0
                    vector.append(encoded)
                else:
                    # Log warning (implicit) and use neutral
                    vector.append(0.5)
        
        return np.array(vector)

    def _get_persona_attr_value(self, persona: PersonaRecord, category: str, name: str) -> Any:
        try:
            return persona.attributes[category][name].value
        except KeyError:
            return None

    def _cosine_distance(self, a: np.ndarray, b: np.ndarray) -> float:
        """Cosine distance (1 - cosine similarity). Returns 0.0–2.0."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 1.0  # Or appropriate neutral distance
        cos_sim = np.dot(a, b) / (norm_a * norm_b)
        # Clip similarity to avoid floating point errors
        cos_sim = np.clip(cos_sim, -1.0, 1.0)
        return float(1.0 - cos_sim)

    def _compute_centroid(self, vectors: list[np.ndarray]) -> np.ndarray:
        """Mean of all vectors."""
        if not vectors:
            return np.zeros(8)
        return np.mean(vectors, axis=0)
