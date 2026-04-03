"""src/validation/bv3_extended.py

Extended BV3 gate for 100+ turn simulations.

BV3 Extended criteria:
  1. Arc maintained: confidence_series has length >= 100 (100-turn arc present)
  2. No >20-point confidence drop at archival promotion events
  3. At least 1 reflection cites an archived entry id

Spec ref: Validity Protocol BV3 (extended) — Sprint 25.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ArchivalEvent:
    turn: int                 # which turn archival promotion occurred
    before_confidence: float  # confidence score immediately before promotion
    after_confidence: float   # confidence score immediately after promotion


@dataclass
class BV3ExtendedResult:
    passed: bool
    archival_events: list[ArchivalEvent]
    max_confidence_drop: float     # largest single drop at any archival event (positive = drop)
    arc_maintained: bool           # True if len(confidence_series) >= 100
    archive_citation_found: bool   # True if at least 1 reflection cites an archived entry
    notes: str


def run_bv3_extended(
    confidence_series: list[float],
    archival_event_turns: list[int],
    reflection_citations: list[str],
    archived_entry_ids: list[str],
    max_drop_threshold: float = 20.0,
) -> BV3ExtendedResult:
    """Run the extended BV3 temporal consistency gate for 100+ turn simulations.

    Parameters
    ----------
    confidence_series:
        Confidence score (0–100) at each turn. Length must be >= 100 for arc
        to be considered maintained.
    archival_event_turns:
        Turn indices where archival promotion events occurred. Each is an index
        into confidence_series (0-based). Turn 0 is skipped (no prior turn).
    reflection_citations:
        All observation or archive entry ids cited in reflections during the run.
    archived_entry_ids:
        All archive entry ids in the final archival_index (working + deep archive).
    max_drop_threshold:
        Maximum allowed confidence drop (before - after) at any archival event.
        Default 20.0 points.

    Returns
    -------
    BV3ExtendedResult with passed=True only when ALL THREE criteria pass.
    """
    # ------------------------------------------------------------------
    # Criterion 1: Arc maintained (100+ turns)
    # ------------------------------------------------------------------
    arc_maintained = len(confidence_series) >= 100

    # ------------------------------------------------------------------
    # Criterion 2: No excessive confidence drop at archival events
    # ------------------------------------------------------------------
    archival_events: list[ArchivalEvent] = []

    for turn in archival_event_turns:
        if turn <= 0 or turn >= len(confidence_series):
            # Cannot compute drop for turn 0 or out-of-bounds turns — skip
            continue
        before = confidence_series[turn - 1]
        after = confidence_series[turn]
        archival_events.append(
            ArchivalEvent(turn=turn, before_confidence=before, after_confidence=after)
        )

    # max drop = largest (before - after); positive value means confidence fell
    if archival_events:
        max_confidence_drop = max(
            e.before_confidence - e.after_confidence for e in archival_events
        )
    else:
        max_confidence_drop = 0.0

    no_excessive_drop = max_confidence_drop <= max_drop_threshold

    # ------------------------------------------------------------------
    # Criterion 3: At least 1 reflection cites an archived entry
    # ------------------------------------------------------------------
    archived_ids_set = set(archived_entry_ids)
    cited_set = set(reflection_citations)
    archive_citation_found = bool(cited_set & archived_ids_set)

    # ------------------------------------------------------------------
    # Build result
    # ------------------------------------------------------------------
    passed = arc_maintained and no_excessive_drop and archive_citation_found

    notes_parts = []
    if not arc_maintained:
        notes_parts.append(
            f"Arc FAILED: only {len(confidence_series)} turns (need >= 100)"
        )
    if not no_excessive_drop:
        notes_parts.append(
            f"Confidence drop FAILED: max drop {max_confidence_drop:.1f} > {max_drop_threshold}"
        )
    if not archive_citation_found:
        notes_parts.append("Archive citation FAILED: no reflection cited an archived entry")
    if passed:
        notes_parts.append("All BV3 extended criteria passed")

    return BV3ExtendedResult(
        passed=passed,
        archival_events=archival_events,
        max_confidence_drop=max_confidence_drop,
        arc_maintained=arc_maintained,
        archive_citation_found=archive_citation_found,
        notes="; ".join(notes_parts),
    )
