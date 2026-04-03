"""src/memory/aging.py — Longitudinal persona aging via annual review.

Spec §14A S17, §8 (Memory Architecture — Promote).

The annual review scans all reflections in a persona's simulation history,
clusters them by semantic theme, and attempts to promote high-importance
clusters to core memory using the existing promotion_executor gate.

This module is designed to run standalone (CLI or scheduled job). It is
intentionally NOT wired into the main simulation loop — promotion from
long-term history is an offline, deliberate operation.

Usage:
    from src.memory.aging import run_annual_review
    report = run_annual_review(persona, simulation_history)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.schema.persona import PersonaRecord, Reflection, CoreMemory

# ---------------------------------------------------------------------------
# Hard-blocked keywords for demographic and life-defining event content
# ---------------------------------------------------------------------------
# These are checked before calling promotion_executor.  Content matching any
# of these keywords is silently skipped — such content must never reach core.
# Spec §8 rule: "NEVER promote: demographic_anchor, life_defining_events,
# identity_statement" (S17).  We add life-event vocabulary here in addition
# to the demographic keywords already inside promote_to_core().
_BLOCKED_KEYWORDS: frozenset[str] = frozenset({
    # Demographics
    "age", "gender", "city", "location", "income", "education",
    "household", "employment", "marital", "name",
    # Life-defining events / biographical facts
    "born", "birth", "childhood", "grew up", "school", "college",
    "university", "married", "wedding", "divorced", "death", "died",
    "moved", "migration", "immigrat", "hometown", "formative",
    "life event", "life story", "life-defining",
})

# Minimum token overlap for two reflections to be considered the same theme
_CLUSTER_OVERLAP_THRESHOLD: int = 2

# Minimum cluster size to attempt promotion
_MIN_CLUSTER_SIZE: int = 3

# Importance threshold for aging scan (slightly lower than the promotion gate of 9)
_AGING_IMPORTANCE_THRESHOLD: int = 8


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------

@dataclass
class AgingReport:
    """Result of a run_annual_review() call."""

    persona_id: str
    reflections_reviewed: int = 0
    """Total reflections scanned (importance >= 8, after demographic guard)."""

    promotions_attempted: int = 0
    """Number of times promote_to_core() was called."""

    promotions_succeeded: int = 0
    """Number of times promote_to_core() actually changed core memory."""

    promotions_blocked: list[str] = field(default_factory=list)
    """Human-readable reason strings for each blocked/skipped promotion attempt."""

    def summary(self) -> str:
        return (
            f"AgingReport[{self.persona_id}]: "
            f"reviewed={self.reflections_reviewed}, "
            f"attempted={self.promotions_attempted}, "
            f"succeeded={self.promotions_succeeded}, "
            f"blocked={len(self.promotions_blocked)}"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_blocked_content(content: str) -> bool:
    """Return True if content matches demographic or life-event keywords.

    This is a hard pre-check applied before calling promotion_executor.
    It is more conservative than the check inside promote_to_core() because
    it also blocks life-defining event vocabulary (biographical facts that
    must never enter the mutable tendency_summary layer).
    """
    lower = content.lower()
    return any(kw in lower for kw in _BLOCKED_KEYWORDS)


def _tokenise(text: str) -> set[str]:
    """Lowercase, split, strip stopwords.  Reuses retrieval.py logic."""
    from src.memory.retrieval import _tokenise as _retrieval_tokenise
    return _retrieval_tokenise(text)


def _cluster_reflections(
    reflections: list[Any],  # list[Reflection]
) -> list[list[Any]]:
    """Group reflections into semantic theme clusters by token overlap.

    Algorithm (greedy, O(n²)):
      - For each reflection, compute overlap with each existing cluster's
        accumulated token vocabulary.
      - If overlap >= _CLUSTER_OVERLAP_THRESHOLD: add to best-matching cluster
        and expand that cluster's vocabulary.
      - Otherwise: start a new cluster.

    Returns a list of clusters, each cluster being a list of Reflection objects.
    Order within a cluster is insertion order.  Singleton clusters are included
    (the caller decides whether to act on them based on _MIN_CLUSTER_SIZE).
    """
    clusters: list[list[Any]] = []
    cluster_tokens: list[set[str]] = []

    for ref in reflections:
        tokens = _tokenise(ref.content)
        best_idx: int | None = None
        best_overlap: int = 0

        for i, ct in enumerate(cluster_tokens):
            overlap = len(tokens & ct)
            if overlap >= _CLUSTER_OVERLAP_THRESHOLD and overlap > best_overlap:
                best_overlap = overlap
                best_idx = i

        if best_idx is not None:
            clusters[best_idx].append(ref)
            cluster_tokens[best_idx] |= tokens  # expand cluster vocabulary
        else:
            clusters.append([ref])
            cluster_tokens.append(tokens.copy())

    return clusters


def _collect_reflections(simulation_history: list[Any]) -> list[Any]:
    """Collect all Reflection objects from a list of CohortEnvelope or dicts.

    simulation_history elements may be:
    - CohortEnvelope objects (have .personas[].memory.working.reflections)
    - Dicts with a "personas" key (deserialized envelopes)
    - Anything else is silently skipped.
    """
    from src.schema.persona import Reflection, PersonaRecord

    collected: list[Any] = []

    for item in simulation_history:
        personas: list[Any] = []

        # CohortEnvelope (has .personas attribute)
        if hasattr(item, "personas"):
            personas = list(item.personas)
        # Dict (deserialized CohortEnvelope)
        elif isinstance(item, dict) and "personas" in item:
            for raw in item["personas"]:
                try:
                    personas.append(PersonaRecord.model_validate(raw))
                except Exception:
                    pass
        # Single PersonaRecord
        elif hasattr(item, "memory"):
            personas = [item]

        for persona in personas:
            try:
                collected.extend(list(persona.memory.working.reflections))
            except AttributeError:
                pass

    return collected


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def run_annual_review(
    persona: Any,  # PersonaRecord
    simulation_history: list[Any],
) -> "AgingReport":
    """Run a longitudinal annual review for a single persona.

    Steps:
    1. Collect all Reflection objects across simulation_history where
       importance >= _AGING_IMPORTANCE_THRESHOLD (8).
    2. Apply hard demographic/life-event guard (blocked content is excluded
       and logged in AgingReport.promotions_blocked with reason "blocked:content").
    3. Cluster by semantic theme (token overlap, no LLM call).
    4. For each cluster with >= _MIN_CLUSTER_SIZE (3) reflections:
       a. For each reflection in the cluster, call promotion_executor.promote_to_core()
          via the existing gate — importance must still be >= 9 (S17 rule).
       b. Track attempted vs succeeded promotions.
    5. Return AgingReport.

    The function is idempotent: calling it multiple times on the same
    history may re-attempt already-promoted content, but promote_to_core()
    deduplicates so no harm is done.

    Rules that must hold (S17):
    - demographics and life_defining_events are NEVER promoted (hard check
      before calling promotion_executor).
    - Promotion targets are restricted to values, non_negotiables, relationship_map
      as represented via core.tendency_summary (existing implementation).
    - promotion_executor gate is never bypassed (importance >= 9, no_contradiction).
    """
    from src.memory.promotion_executor import promote_to_core

    persona_id: str = persona.persona_id
    core: Any = persona.memory.core  # CoreMemory

    report = AgingReport(persona_id=persona_id)

    # Step 1: Collect all reflections from history with importance >= 8
    all_reflections = _collect_reflections(simulation_history)
    candidates = [r for r in all_reflections if r.importance >= _AGING_IMPORTANCE_THRESHOLD]

    # Step 2: Hard demographic/life-event guard
    safe_reflections: list[Any] = []
    for ref in candidates:
        if _is_blocked_content(ref.content):
            report.promotions_blocked.append(
                f"blocked:content [{ref.id[:8]}] — matched demographic/life-event keyword"
            )
        else:
            safe_reflections.append(ref)

    report.reflections_reviewed = len(safe_reflections)

    if not safe_reflections:
        return report

    # Step 3: Cluster by semantic theme
    clusters = _cluster_reflections(safe_reflections)

    # Step 4: Attempt promotion for clusters with >= _MIN_CLUSTER_SIZE reflections
    for cluster in clusters:
        if len(cluster) < _MIN_CLUSTER_SIZE:
            continue

        for ref in cluster:
            # The existing promotion gate enforces importance >= 9.
            # For reflections with importance 8, can_promote() will return False —
            # that is intentional and must not be overridden (S17).
            if ref.importance < 9:
                report.promotions_blocked.append(
                    f"gate:importance [{ref.id[:8]}] — importance={ref.importance} < 9 (gate requires >= 9)"
                )
                continue

            report.promotions_attempted += 1
            # Call promote_to_core() — it performs demographic keyword check internally
            # and deduplicates before appending to tendency_summary.
            updated_core = promote_to_core(core, ref)  # type: ignore[arg-type]
            if updated_core is not core:
                core = updated_core
                report.promotions_succeeded += 1
            else:
                report.promotions_blocked.append(
                    f"blocked:executor [{ref.id[:8]}] — promote_to_core returned unchanged core"
                )

    # Write back the updated core to the persona — model_copy (never mutate)
    if report.promotions_succeeded > 0:
        new_memory = persona.memory.model_copy(update={"core": core})
        # Note: we update the persona's core in-place in the caller's reference.
        # Since PersonaRecord is immutable via model_copy, the caller is responsible
        # for replacing their persona reference with the returned updated persona.
        # We attach the updated core to the report for the caller's convenience.
        report._updated_core = core  # type: ignore[attr-defined]

    return report
