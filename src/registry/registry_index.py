"""src/registry/registry_index.py — Demographic query layer for the persona registry.

Provides build_demographics_index() and query_index() as stateless functions
operating over a list of RegistryEntry objects.

No LLM calls.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


# Import RegistryEntry — guarded to allow parallel development
try:
    from src.registry.persona_registry import RegistryEntry
except ImportError:
    RegistryEntry = None  # type: ignore[assignment, misc]


# ---------------------------------------------------------------------------
# Age banding
# ---------------------------------------------------------------------------

def age_band(age: int) -> str:
    """Return a display age band string for a given age.
    Bands: <25, 25-34, 35-44, 45-54, 55+
    """
    if age < 25:
        return "<25"
    elif age < 35:
        return "25-34"
    elif age < 45:
        return "35-44"
    elif age < 55:
        return "45-54"
    else:
        return "55+"


# ---------------------------------------------------------------------------
# Demographics index builder
# ---------------------------------------------------------------------------

def build_demographics_index(
    entries: list,  # list[RegistryEntry]
) -> dict[str, list[str]]:
    """Build a lookup dict: "{age_band}|{city_tier}|{gender}" -> [persona_ids].

    This is the fast lookup path for demographic matching.

    Example key: "25-34|metro|female"
    """
    index: dict[str, list[str]] = defaultdict(list)
    for entry in entries:
        key = f"{age_band(entry.age)}|{entry.city_tier.lower()}|{entry.gender.lower()}"
        index[key].append(entry.persona_id)
    return dict(index)


# ---------------------------------------------------------------------------
# Flexible query
# ---------------------------------------------------------------------------

def query_index(
    entries: list,  # list[RegistryEntry]
    age_min: int | None = None,
    age_max: int | None = None,
    gender: str | None = None,
    city_tier: str | None = None,
    domain: str | None = None,
) -> list:  # list[RegistryEntry]
    """Filter entries by demographic criteria using AND logic.

    All parameters are optional. When provided:
    - age_min / age_max: inclusive range filter on entry.age
    - gender: exact match (case-insensitive)
    - city_tier: exact match (case-insensitive)
    - domain: exact match (case-insensitive)

    Returns filtered list[RegistryEntry].
    """
    results = []
    for entry in entries:
        if age_min is not None and entry.age < age_min:
            continue
        if age_max is not None and entry.age > age_max:
            continue
        if gender is not None and entry.gender.lower() != gender.lower():
            continue
        if city_tier is not None and entry.city_tier.lower() != city_tier.lower():
            continue
        if domain is not None and entry.domain.lower() != domain.lower():
            continue
        results.append(entry)
    return results


# ---------------------------------------------------------------------------
# Domain history helpers
# ---------------------------------------------------------------------------

def domain_history(entries: list) -> dict[str, list[str]]:  # list[RegistryEntry] -> dict[persona_id -> [domains]]
    """Build a dict of persona_id -> list of distinct domains seen.

    Order is by registered_at ascending (chronological).
    """
    sorted_entries = sorted(entries, key=lambda e: e.registered_at)
    history: dict[str, list[str]] = {}
    for entry in sorted_entries:
        pid = entry.persona_id
        domain = entry.domain
        if pid not in history:
            history[pid] = []
        if domain not in history[pid]:
            history[pid].append(domain)
    return history


def personas_by_domain(entries: list, domain: str) -> list:  # list[RegistryEntry]
    """Return all entries whose domain matches (case-insensitive)."""
    return [entry for entry in entries if entry.domain.lower() == domain.lower()]
