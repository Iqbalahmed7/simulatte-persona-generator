"""src/validation/bv2_extended.py

Extended BV2 gate for 100+ turn simulations with hierarchical memory.

BV2 Extended criteria:
  1. Citation validity: 100% of cited_ids must exist in active observations
     OR working_archive OR deep_archive (by id field).
  2. High-importance recall: >= 80% of high-importance items across ALL tiers
     must appear in cited_ids.

Spec ref: Validity Protocol BV2 (extended) — Sprint 25.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.schema.memory_extended import WorkingMemoryExtended


@dataclass
class BV2ExtendedResult:
    passed: bool
    citation_validity_rate: float         # fraction of cited ids that exist in active or archive
    high_importance_recall_rate: float    # fraction of high-importance items recalled
    total_active_observations: int
    total_archived_entries: int
    invalid_citations: list[str]          # cited ids not found in any tier
    notes: str


def run_bv2_extended(
    memory: WorkingMemoryExtended,
    cited_ids: list[str],
    high_importance_threshold: float = 7.0,
) -> BV2ExtendedResult:
    """Run the extended BV2 citation validity gate across all memory tiers.

    Parameters
    ----------
    memory:
        The WorkingMemoryExtended state after the simulation run.
    cited_ids:
        Observation or archive entry ids cited in reflections.
    high_importance_threshold:
        Observations/entries with importance >= this are considered "high".
        Default 7.0.

    Returns
    -------
    BV2ExtendedResult with passed=True only when BOTH criteria pass:
      - citation_validity_rate == 1.0  (100% valid citations)
      - high_importance_recall_rate >= 0.80
    """
    # ------------------------------------------------------------------
    # Build id sets across all tiers
    # ------------------------------------------------------------------
    all_active_ids: set[str] = {obs.id for obs in memory.observations}
    all_archive_ids: set[str] = set()
    total_archived = 0

    if memory.archival_index is not None:
        for entry in memory.archival_index.working_archive:
            all_archive_ids.add(entry.id)
        for entry in memory.archival_index.deep_archive:
            all_archive_ids.add(entry.id)
        total_archived = len(all_archive_ids)

    all_ids = all_active_ids | all_archive_ids

    # ------------------------------------------------------------------
    # Criterion 1: Citation validity
    # ------------------------------------------------------------------
    if not cited_ids:
        invalid_citations: list[str] = []
        citation_validity_rate = 1.0
    else:
        invalid_citations = [cid for cid in cited_ids if cid not in all_ids]
        citation_validity_rate = 1.0 - len(invalid_citations) / len(cited_ids)

    citation_valid = citation_validity_rate == 1.0

    # ------------------------------------------------------------------
    # Criterion 2: High-importance recall across all tiers
    # ------------------------------------------------------------------
    high_imp_ids: set[str] = set()

    for obs in memory.observations:
        if obs.importance >= high_importance_threshold:
            high_imp_ids.add(obs.id)

    if memory.archival_index is not None:
        for entry in memory.archival_index.working_archive:
            if entry.mean_importance >= high_importance_threshold:
                high_imp_ids.add(entry.id)
        for entry in memory.archival_index.deep_archive:
            if entry.mean_importance >= high_importance_threshold:
                high_imp_ids.add(entry.id)

    if not high_imp_ids:
        high_importance_recall_rate = 1.0  # vacuously true — nothing to recall
    else:
        recalled = high_imp_ids & set(cited_ids)
        high_importance_recall_rate = len(recalled) / len(high_imp_ids)

    recall_valid = high_importance_recall_rate >= 0.80

    # ------------------------------------------------------------------
    # Build result
    # ------------------------------------------------------------------
    passed = citation_valid and recall_valid

    notes_parts = []
    if not citation_valid:
        notes_parts.append(
            f"Citation validity FAILED: {len(invalid_citations)} invalid id(s) cited"
        )
    if not recall_valid:
        notes_parts.append(
            f"High-importance recall FAILED: {high_importance_recall_rate:.1%} < 80%"
        )
    if passed:
        notes_parts.append("All BV2 extended criteria passed")

    return BV2ExtendedResult(
        passed=passed,
        citation_validity_rate=citation_validity_rate,
        high_importance_recall_rate=high_importance_recall_rate,
        total_active_observations=len(all_active_ids),
        total_archived_entries=total_archived,
        invalid_citations=invalid_citations,
        notes="; ".join(notes_parts),
    )
