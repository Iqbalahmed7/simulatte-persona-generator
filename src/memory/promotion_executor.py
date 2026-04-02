"""Memory promotion executor.

Sprint 11 — Production Entry Point + Technical Debt Clearance.
Spec §14A S17: Observations that cross the promotion threshold are
promoted to core memory (tendency_summary field).

Rules (settled at §14A S17):
- importance >= 9
- citation_count >= 3 (cited by >= 3 distinct reflections)
- no_contradiction (caller flag — loop passes True for now; future: contradiction checker)
- Demographics are NEVER promoted

Promotion writes the observation content into persona.memory.core.tendency_summary
(appended as a new sentence, deduplicated).
"""
from __future__ import annotations

from src.schema.persona import Observation, Reflection, WorkingMemory, CoreMemory


def get_promotable_observations(
    working: WorkingMemory,
) -> list[Observation]:
    """Return all observations from working memory that meet the promotion threshold.

    Checks:
    1. importance >= 9
    2. citation_count(obs.id, working.reflections) >= 3
    3. no_contradiction = True (structural — always True in current impl)

    Returns list of Observation objects (may be empty).
    """
    from src.memory.reflection_store import can_promote, citation_count

    promotable = []
    for obs in working.observations:
        citations = citation_count(obs.id, working.reflections)
        if can_promote(
            importance=obs.importance,
            citation_count=citations,
            no_contradiction=True,  # S17: contradiction check is future work
        ):
            promotable.append(obs)
    return promotable


def promote_to_core(
    core: CoreMemory,
    observation: Observation,
) -> CoreMemory:
    """Promote a single observation to core memory.

    Appends the observation's content to core.tendency_summary (deduplicated).
    Returns a new CoreMemory (model_copy — never mutates).

    Demographic observations are silently skipped (return core unchanged).
    """
    _DEMOGRAPHIC_KEYWORDS = {
        "age", "gender", "city", "location", "income", "education",
        "household", "employment", "marital", "name",
    }
    # Demographic guard: skip if any demographic keyword appears in the content
    content_lower = observation.content.lower()
    if any(kw in content_lower for kw in _DEMOGRAPHIC_KEYWORDS):
        return core  # Never promote demographics

    # Deduplicate: don't add if already in tendency_summary
    if observation.content in (core.tendency_summary or ""):
        return core

    new_summary = (core.tendency_summary or "").strip()
    if new_summary:
        new_summary = new_summary + " " + observation.content
    else:
        new_summary = observation.content

    return core.model_copy(update={"tendency_summary": new_summary})


def run_promotion_pass(
    working: WorkingMemory,
    core: CoreMemory,
) -> tuple[CoreMemory, list[str]]:
    """Run a full promotion pass over working memory.

    Finds all promotable observations, promotes each to core memory,
    and returns the updated CoreMemory + list of promoted observation ids.

    Returns:
        (updated_core, promoted_ids) — promoted_ids is [] if nothing promoted.
    """
    promotable = get_promotable_observations(working)
    promoted_ids: list[str] = []

    for obs in promotable:
        updated = promote_to_core(core, obs)
        if updated is not core:  # Only count if something actually changed
            core = updated
            promoted_ids.append(obs.id)

    return core, promoted_ids
