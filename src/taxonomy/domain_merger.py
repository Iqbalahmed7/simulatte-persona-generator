"""src/taxonomy/domain_merger.py

Merge ranked domain attributes into the base taxonomy structure.

The base taxonomy (Layer 1) is immutable. Domain attributes (Layer 2)
are added under a dedicated "domain_specific" key.

Output is the combined taxonomy dict that attribute_filler.py consumes.

Spec ref: Master Spec §6 — "Layer 2: Domain Extension (~30-80 attributes)"
Constitution P8 — "Domain-agnostic core. No product-specific attributes in base taxonomy."
"""

from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)

# The six immutable base taxonomy category keys (Constitution P8).
_BASE_CATEGORIES = frozenset(
    {"psychology", "values", "social", "lifestyle", "identity", "decision_making"}
)


def detect_conflicts(base: dict, domain_attrs: list) -> list[str]:
    """Return list of domain attribute names that conflict with base taxonomy attributes.

    A conflict = same name appears as a key in any base category dict AND in domain_attrs.
    This is informational only — the merger still proceeds.
    Conflicts are logged as warnings, not errors.

    Args:
        base: The base taxonomy dict (keys are category names, values are dicts of
              attribute definitions).
        domain_attrs: List of DomainAttribute or RankedAttribute objects.

    Returns:
        List of conflicting attribute name strings (may be empty).
    """
    # Collect all attribute names across all base category dicts.
    base_attr_names: set[str] = set()
    for category_key, category_value in base.items():
        if category_key in _BASE_CATEGORIES and isinstance(category_value, dict):
            base_attr_names.update(category_value.keys())

    conflicts: list[str] = []
    for item in domain_attrs:
        # Handle both DomainAttribute (direct) and RankedAttribute (wraps .attr).
        attr = item.attr if hasattr(item, "attr") else item
        if attr.name in base_attr_names:
            conflicts.append(attr.name)

    if conflicts:
        for name in conflicts:
            logger.warning(
                "detect_conflicts(): domain attribute %r conflicts with a base taxonomy "
                "attribute — proceeding anyway (Codex ranker should have excluded duplicates).",
                name,
            )

    return conflicts


def merge_taxonomy(base: dict, domain_attrs: list) -> dict:
    """Return a new dict: deep copy of base + domain_specific key.

    Rules:
    - Never mutate base. Uses copy.deepcopy(base) as starting point.
    - If base already has a "domain_specific" key (from a prior merge), replace it entirely.
    - Each domain attribute becomes a key in "domain_specific", structured per spec P10.
    - Adds "layer": 2 to every domain attribute entry for traceability.
    - If domain_attrs is empty: returns base copy with empty "domain_specific": {}.

    Args:
        base: The base taxonomy dict. Must not be mutated.
        domain_attrs: List of DomainAttribute or RankedAttribute objects. May be empty.

    Returns:
        New merged taxonomy dict containing all base keys plus "domain_specific".
    """
    merged: dict[str, Any] = copy.deepcopy(base)

    # Conflict detection — informational only.
    detect_conflicts(base, domain_attrs)

    domain_specific: dict[str, Any] = {}
    for item in domain_attrs:
        # Handle both DomainAttribute (direct) and RankedAttribute (wraps .attr).
        attr = item.attr if hasattr(item, "attr") else item
        domain_specific[attr.name] = {
            "description": attr.description,
            "valid_range": attr.valid_range,
            "example_values": attr.example_values,
            "signal_count": attr.signal_count,
            "extraction_source": attr.extraction_source,
            "layer": 2,  # Mandatory — traceability per spec P10.
        }

    # Replace any pre-existing "domain_specific" key entirely.
    merged["domain_specific"] = domain_specific

    return merged


def get_domain_attribute_names(merged_taxonomy: dict) -> set[str]:
    """Return the set of attribute names in the domain_specific layer.

    Args:
        merged_taxonomy: A taxonomy dict produced by merge_taxonomy().

    Returns:
        Set of attribute name strings found under "domain_specific".
    """
    return set(merged_taxonomy.get("domain_specific", {}).keys())
