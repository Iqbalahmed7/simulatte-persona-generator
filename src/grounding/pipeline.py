"""Grounding pipeline orchestrator.

Sprint 8 — Grounding Pipeline.
Coordinates all 4 stages: extract → construct → cluster → assign.
No LLM calls.
"""
from __future__ import annotations

from src.grounding.types import GroundingResult, BehaviouralFeatures

MIN_SIGNALS_THRESHOLD = 200


def run_grounding_pipeline(
    raw_texts: list[str],
    personas: list,           # list[PersonaRecord]
    domain: str = "general",
) -> GroundingResult:
    """Run the full grounding pipeline.

    Args:
        raw_texts: List of raw text strings (reviews, posts, etc.)
        personas: List of PersonaRecord objects whose tendencies will be updated.
        domain: Domain label (for metadata only).

    Returns:
        GroundingResult with updated personas and derived archetypes.

    Raises:
        ValueError: If raw_texts is empty.
    """
    if not raw_texts:
        raise ValueError("raw_texts must not be empty")

    # Lazy imports to avoid circular imports at module load time
    from src.grounding.signal_extractor import extract_signals, signals_to_vectors
    from src.grounding.feature_constructor import construct_features
    from src.grounding.cluster_deriver import derive_clusters
    from src.grounding.tendency_assigner import assign_grounded_tendencies

    # Stage 1: Extract signals
    signals = extract_signals(raw_texts)

    # Stage 2: Construct aggregate features
    features = construct_features(signals)

    # Stage 3: Cluster — one vector per signal
    vectors = signals_to_vectors(signals)
    archetypes = derive_clusters(vectors)

    # Stage 4: Assign grounded tendencies to each persona
    updated_personas = [
        assign_grounded_tendencies(persona, archetypes)
        for persona in personas
    ]

    warning = None
    if len(signals) < MIN_SIGNALS_THRESHOLD:
        warning = (
            f"Only {len(signals)} signals extracted (threshold: {MIN_SIGNALS_THRESHOLD}). "
            f"Results may be unstable. Consider providing more domain data."
        )

    return GroundingResult(
        personas=updated_personas,
        archetypes=archetypes,
        signals_extracted=len(signals),
        clusters_derived=len(archetypes),
        warning=warning,
    )
