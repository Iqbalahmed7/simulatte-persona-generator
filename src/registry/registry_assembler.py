"""src/registry/registry_assembler.py — Registry-first cohort assembly orchestrator.

Implements the §4 registry lookup decision tree from PERSONA_REUSE_MODALITIES.md:
    1. Query registry for demographic matches
    2. Filter drifted personas
    3. Reground personas whose domain differs
    4. Return reused personas + gap count for new generation

No LLM calls. Deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.registry.persona_registry import PersonaRegistry, RegistryEntry
from src.registry.persona_regrounder import reground_for_domain
from src.schema.persona import PersonaRecord


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class RegistryAssemblyResult:
    reused_personas: list[PersonaRecord]    # personas loaded + possibly regrounded
    gap_count: int                           # how many new personas still needed
    target_count: int
    drift_filtered_count: int               # how many were excluded due to drift
    same_domain_count: int                  # reused with no changes
    regrounded_count: int                   # reused but domain layer swapped
    registry_match_count: int               # raw demographic matches before drift filter


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def assemble_from_registry(
    registry: PersonaRegistry,
    icp_age_min: int,
    icp_age_max: int,
    new_domain: str,
    target_count: int,
    icp_gender: str | None = None,
    icp_city_tier: str | None = None,
    current_date: date | None = None,
) -> RegistryAssemblyResult:
    """Find, validate, and prepare personas from the registry for reuse.

    Parameters
    ----------
    registry:       PersonaRegistry to query
    icp_age_min:    Minimum age (inclusive)
    icp_age_max:    Maximum age (inclusive)
    new_domain:     Domain for the new experiment
    target_count:   Total personas needed
    icp_gender:     Optional gender filter
    icp_city_tier:  Optional city tier filter
    current_date:   Date to use for drift detection (default: today UTC)

    Returns
    -------
    RegistryAssemblyResult with reused_personas (already loaded + regrounded),
    gap_count, and accounting stats.
    """
    from src.registry.drift_detector import filter_drifted
    from src.registry.registry_lookup import classify_scenario

    # Step 1: demographic query
    all_entries: list[RegistryEntry] = registry.find(
        age_min=icp_age_min,
        age_max=icp_age_max,
        gender=icp_gender,
        city_tier=icp_city_tier,
    )
    registry_match_count = len(all_entries)

    # Step 2: drift filter — remove personas whose current age is outside ICP band
    valid_entries, drifted_entries = filter_drifted(
        all_entries, icp_age_min, icp_age_max, current_date=current_date
    )
    drift_filtered_count = len(drifted_entries)

    # Step 3: cap at target_count
    selected_entries = valid_entries[:target_count]

    # Step 4: load PersonaRecord for each selected entry; reground if domain differs
    reused_personas: list[PersonaRecord] = []
    same_domain_count = 0
    regrounded_count = 0

    for entry in selected_entries:
        persona = registry.get(entry.persona_id)
        if persona is None:
            continue  # index out of sync — skip silently

        scenario = classify_scenario(entry.domain, new_domain)
        if scenario == "same_domain":
            reused_personas.append(persona)
            same_domain_count += 1
        else:
            # adjacent_domain or different_domain: downgrade tendency sources
            regrounded = reground_for_domain(persona, new_domain)
            reused_personas.append(regrounded)
            regrounded_count += 1

    gap_count = max(0, target_count - len(reused_personas))

    return RegistryAssemblyResult(
        reused_personas=reused_personas,
        gap_count=gap_count,
        target_count=target_count,
        drift_filtered_count=drift_filtered_count,
        same_domain_count=same_domain_count,
        regrounded_count=regrounded_count,
        registry_match_count=registry_match_count,
    )
