"""src/validation/onboarding_gates.py

Sprint 28 — G-O1 and G-O2 validation gates for the domain onboarding pipeline.

Gates:
    G-O1  Minimum corpus size gate  — ingestion_result.validation_report.n_valid_signals >= 200
    G-O2  Cluster stability gate    — cluster_result.stability_passed is True
                                      (all 5 silhouette runs > 0.30 threshold)

Design notes:
- No LLM calls.  Fully deterministic.
- GateResult is defined here and importable independently — no dependency on
  any onboarding module (avoids circular imports).
- Gate functions accept duck-typed objects; attribute access is used directly
  so any object with the expected shape will work.

Usage::

    from src.validation.onboarding_gates import GateResult, check_go1, check_go2

    go1 = check_go1(ingestion_result)
    go2 = check_go2(cluster_result)
    if not go1.passed:
        raise RuntimeError(go1.action_required)
"""
from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# GateResult
# ---------------------------------------------------------------------------

@dataclass
class GateResult:
    """Result of a single onboarding pipeline gate check."""

    gate_id: str            # "G-O1" or "G-O2"
    passed: bool
    detail: str             # human-readable explanation
    action_required: str    # what to do if failed (empty string if passed)


# ---------------------------------------------------------------------------
# G-O1 — Minimum corpus size gate
# ---------------------------------------------------------------------------

def check_go1(ingestion_result) -> GateResult:
    """G-O1: Minimum corpus size gate.

    Passes when ingestion_result.validation_report.n_valid_signals >= 200.

    Args:
        ingestion_result: Any object with a ``validation_report`` attribute
            whose ``n_valid_signals`` attribute is an int.  Typically an
            ``IngestionResult`` from ``src.onboarding.ingestion``.

    Returns:
        GateResult for G-O1.
    """
    n_valid: int = ingestion_result.validation_report.n_valid_signals
    passed: bool = n_valid >= 200

    return GateResult(
        gate_id="G-O1",
        passed=passed,
        detail=f"{n_valid} signals collected (minimum 200)",
        action_required=(
            "" if passed else "Collect more reviews or use proxy mode."
        ),
    )


# ---------------------------------------------------------------------------
# G-O2 — Cluster stability gate
# ---------------------------------------------------------------------------

def check_go2(cluster_result) -> GateResult:
    """G-O2: Cluster stability gate.

    Passes when cluster_result.stability_passed is True
    (all 5 silhouette runs > 0.30 threshold).

    Args:
        cluster_result: Any object with ``stability_passed`` (bool), ``k``
            (int), and ``mean_silhouette`` (float) attributes.  Typically a
            ``ClusterResult`` from ``src.onboarding.cluster_pipeline``.

    Returns:
        GateResult for G-O2.
    """
    stability_passed: bool = cluster_result.stability_passed
    k: int = cluster_result.k
    mean: float = cluster_result.mean_silhouette

    return GateResult(
        gate_id="G-O2",
        passed=stability_passed,
        detail=(
            f"K={k}, mean_silhouette={mean:.3f}, "
            f"stability_passed={stability_passed}"
        ),
        action_required=(
            "" if stability_passed
            else "Collect more diverse signals to improve cluster separation."
        ),
    )
