from __future__ import annotations

from src.taxonomy.base_taxonomy import (
    AttributeDefinition,
    BASE_TAXONOMY,
    TAXONOMY_BY_NAME,
)
from src.taxonomy.domain_templates.cpg import CPG_DOMAIN_ATTRIBUTES
from src.taxonomy.domain_templates.health_wellness import HEALTH_WELLNESS_DOMAIN_ATTRIBUTES
from src.taxonomy.domain_templates.littlejoys_cpg import LITTLEJOYS_CPG_TEMPLATE
from src.taxonomy.domain_templates.saas import SAAS_DOMAIN_ATTRIBUTES


DOMAIN_REGISTRY: dict[str, list[AttributeDefinition]] = {
    "cpg": CPG_DOMAIN_ATTRIBUTES,
    "health_wellness": HEALTH_WELLNESS_DOMAIN_ATTRIBUTES,
    "littlejoys_cpg": LITTLEJOYS_CPG_TEMPLATE,
    "saas": SAAS_DOMAIN_ATTRIBUTES,
}


def _normalize_domain(domain: str) -> str:
    return domain.strip().lower()


def load_taxonomy(domain: str) -> list[AttributeDefinition]:
    """Returns the full merged taxonomy for the given domain.

    Merge rules:
    - Base attributes always come first.
    - Domain extension attributes are appended after base attributes.
    - Anchors are not modified.
    - If a domain attribute shares a name with a base attribute, raise ValueError.
    """

    d = _normalize_domain(domain)
    if d not in DOMAIN_REGISTRY:
        valid = ", ".join(sorted(DOMAIN_REGISTRY.keys()))
        raise ValueError(f"Unknown domain '{domain}'. Valid domains: {valid}")

    domain_attrs = DOMAIN_REGISTRY[d]
    domain_attr_names = [a.name for a in domain_attrs]
    duplicates = sorted(
        {n for n in domain_attr_names if domain_attr_names.count(n) > 1}
    )
    if duplicates:
        raise ValueError(f"Domain '{d}' has duplicate attribute names: {duplicates}")

    overlapping = sorted([a.name for a in domain_attrs if a.name in TAXONOMY_BY_NAME])
    if overlapping:
        raise ValueError(
            f"Domain '{d}' has attribute name(s) overlapping with base taxonomy: {overlapping}"
        )

    # Return a new list so callers can't mutate base taxonomy.
    return list(BASE_TAXONOMY) + list(domain_attrs)


def get_domain_attributes(domain: str) -> list[AttributeDefinition]:
    """Returns only the domain extension attributes (not the base taxonomy)."""

    d = _normalize_domain(domain)
    if d not in DOMAIN_REGISTRY:
        valid = ", ".join(sorted(DOMAIN_REGISTRY.keys()))
        raise ValueError(f"Unknown domain '{domain}'. Valid domains: {valid}")
    return list(DOMAIN_REGISTRY[d])


def list_domains() -> list[str]:
    """Returns all registered domain names."""

    return list(DOMAIN_REGISTRY.keys())


__all__ = [
    "DOMAIN_REGISTRY",
    "load_taxonomy",
    "get_domain_attributes",
    "list_domains",
]
