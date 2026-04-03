"""src/onboarding/cluster_pipeline.py

GMM cluster derivation with BIC optimisation and silhouette stability validation.

Steps:
1. For each K in k_range (inclusive): fit GaussianMixture, compute BIC.
2. Select K* = K with lowest BIC score (BIC-optimal).
3. Run n_runs=5 independent GaussianMixture fits at K*; compute silhouette for each.
4. stability_passed = all(score > threshold for score in silhouette_scores).
5. If NOT stability_passed AND K* > k_range[0]: retry with K* - 1 (K-1 retry).
6. Return ClusterResult with final K, labels from last run, centroids, stability info.

Spec ref: Sprint 28.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass
class ClusterResult:
    k: int                         # Final K (cluster count) used
    labels: list[int]              # Cluster assignment per feature vector
    cluster_centroids: list[list[float]]  # K centroids
    mean_silhouette: float         # Mean silhouette score across n_runs runs
    silhouette_scores: list[float]  # Score from each of the n_runs runs
    stability_passed: bool         # True when ALL runs > threshold (0.30)
    k_range_tried: list[int]       # K values attempted
    bic_scores: dict[int, float]   # {k: bic_score} for all K tried
    notes: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _bic_sweep(X: np.ndarray, k_range: tuple[int, int]) -> dict[int, float]:
    """Fit a GaussianMixture for each K and return {k: bic}."""
    bic_scores: dict[int, float] = {}
    for k in range(k_range[0], k_range[1] + 1):
        gm = GaussianMixture(n_components=k, random_state=42)
        gm.fit(X)
        bic_scores[k] = gm.bic(X)
        logger.debug("BIC sweep: k=%d  bic=%.4f", k, bic_scores[k])
    return bic_scores


def _stability_runs(
    X: np.ndarray,
    k: int,
    n_runs: int,
    threshold: float,
) -> tuple[list[float], list[int], list[list[float]], bool]:
    """Run n_runs independent GMM fits at the given K.

    Returns
    -------
    silhouette_scores : score per run
    labels            : cluster labels from the *last* run
    centroids         : GMM means from the *last* run
    stability_passed  : all scores > threshold
    """
    silhouette_scores: list[float] = []
    labels: list[int] = []
    centroids: list[list[float]] = []

    for run in range(n_runs):
        gm = GaussianMixture(n_components=k, random_state=run)
        run_labels = gm.fit_predict(X)

        if len(set(run_labels)) > 1:
            try:
                score = float(silhouette_score(X, run_labels))
            except Exception as exc:
                logger.warning(
                    "_stability_runs(): silhouette_score failed at run %d (k=%d): %s — "
                    "assigning 0.0",
                    run,
                    k,
                    exc,
                )
                score = 0.0
        else:
            # All samples in one cluster — silhouette undefined
            logger.debug(
                "_stability_runs(): all samples in one cluster at run %d (k=%d) — score=0.0",
                run,
                k,
            )
            score = 0.0

        silhouette_scores.append(score)
        labels = run_labels.tolist()
        centroids = gm.means_.tolist()
        logger.debug("Stability run %d: k=%d  silhouette=%.4f", run, k, score)

    stability_passed = all(s > threshold for s in silhouette_scores)
    return silhouette_scores, labels, centroids, stability_passed


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_cluster_pipeline(
    feature_vectors: list[list[float]],
    k_range: tuple[int, int] = (3, 8),
    n_runs: int = 5,
    threshold: float = 0.30,
) -> ClusterResult:
    """Run GMM cluster derivation with BIC optimisation and silhouette stability.

    Parameters
    ----------
    feature_vectors:
        List of feature vectors (one per signal cluster).
    k_range:
        (min_K, max_K) inclusive range of K values to try.
    n_runs:
        Number of independent GMM fits used to assess stability.
    threshold:
        Silhouette threshold for stability_passed (default 0.30).

    Returns
    -------
    ClusterResult
        Fully populated result including final K, labels, centroids,
        silhouette statistics, BIC scores, and a human-readable notes string.
    """
    n_vectors = len(feature_vectors)

    # ------------------------------------------------------------------
    # Edge case: too few vectors to cluster
    # ------------------------------------------------------------------
    if n_vectors < k_range[0]:
        logger.warning(
            "run_cluster_pipeline(): only %d feature vectors, need at least %d — "
            "returning k=1 fallback",
            n_vectors,
            k_range[0],
        )
        # Assign all to cluster 0; centroids = mean of all vectors (or empty)
        if n_vectors == 0:
            centroids: list[list[float]] = []
            labels_out: list[int] = []
            centroid_note = "no feature vectors provided"
        else:
            arr = np.array(feature_vectors, dtype=float)
            centroids = [arr.mean(axis=0).tolist()]
            labels_out = [0] * n_vectors
            centroid_note = "single centroid = mean of all vectors"

        return ClusterResult(
            k=1,
            labels=labels_out,
            cluster_centroids=centroids,
            mean_silhouette=0.0,
            silhouette_scores=[],
            stability_passed=False,
            k_range_tried=[],
            bic_scores={},
            notes=f"Insufficient data for clustering ({centroid_note})",
        )

    X = np.array(feature_vectors, dtype=float)

    # ------------------------------------------------------------------
    # Step 1–2: BIC sweep → select best_k
    # ------------------------------------------------------------------
    bic_scores = _bic_sweep(X, k_range)
    best_k = min(bic_scores, key=bic_scores.get)  # type: ignore[arg-type]
    k_range_tried = list(range(k_range[0], k_range[1] + 1))
    logger.info("BIC sweep complete: best_k=%d", best_k)

    # ------------------------------------------------------------------
    # Step 3–4: Stability runs at best_k
    # ------------------------------------------------------------------
    sil_scores, labels, centroids, stability_passed = _stability_runs(
        X, best_k, n_runs, threshold
    )

    # ------------------------------------------------------------------
    # Step 5: K-1 retry if stability failed and we can go lower
    # ------------------------------------------------------------------
    final_k = best_k
    notes_parts: list[str] = [f"BIC-optimal k={best_k}"]

    if not stability_passed and best_k > k_range[0]:
        retry_k = best_k - 1
        logger.info(
            "Stability failed at k=%d (scores=%s) — retrying at k=%d",
            best_k,
            [f"{s:.3f}" for s in sil_scores],
            retry_k,
        )
        notes_parts.append(
            f"stability failed at k={best_k} "
            f"(scores={[round(s, 3) for s in sil_scores]}); retried k={retry_k}"
        )

        (
            sil_scores,
            labels,
            centroids,
            stability_passed,
        ) = _stability_runs(X, retry_k, n_runs, threshold)
        final_k = retry_k

        if not stability_passed:
            notes_parts.append(
                f"stability still failed at k={retry_k} "
                f"(scores={[round(s, 3) for s in sil_scores]}); reporting stability_passed=False"
            )
            logger.warning(
                "Stability still failed after K-1 retry at k=%d — reporting stability_passed=False",
                retry_k,
            )
        else:
            notes_parts.append(f"stability passed at k={retry_k}")
            logger.info("Stability passed after K-1 retry at k=%d", retry_k)
    elif stability_passed:
        notes_parts.append(
            f"stability passed at k={best_k} "
            f"(scores={[round(s, 3) for s in sil_scores]})"
        )
    else:
        # best_k == k_range[0] and stability failed — no lower K to try
        notes_parts.append(
            f"stability failed at k={best_k} and k_range[0]={k_range[0]} — "
            f"cannot retry lower; reporting stability_passed=False"
        )
        logger.warning(
            "Stability failed at k=%d (minimum of range) — cannot retry lower",
            best_k,
        )

    mean_silhouette = float(np.mean(sil_scores)) if sil_scores else 0.0

    return ClusterResult(
        k=final_k,
        labels=labels,
        cluster_centroids=centroids,
        mean_silhouette=mean_silhouette,
        silhouette_scores=sil_scores,
        stability_passed=stability_passed,
        k_range_tried=k_range_tried,
        bic_scores=bic_scores,
        notes="; ".join(notes_parts),
    )
