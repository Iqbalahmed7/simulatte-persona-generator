"""src/registry/registry_lookup.py — ICP-to-registry matching and reuse planning.

Given ICP demographic criteria and a target persona count, produces a ReusePlan
describing which registry personas can be reused and how many new personas
need to be generated.

No LLM calls. Deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from src.registry.persona_registry import PersonaRegistry, RegistryEntry


# ---------------------------------------------------------------------------
# Domain scenario classification
# ---------------------------------------------------------------------------

# Taxonomy class groupings — domains in the same group are "adjacent"
DOMAIN_TAXONOMY_CLASSES: dict[str, str] = {
    # CPG
    "cpg": "cpg",
    "child-nutrition": "cpg",
    "health-food": "cpg",
    "food-and-beverage": "cpg",
    "personal-care": "cpg",
    # Financial services
    "fintech": "financial_services",
    "financial_services": "financial_services",
    "banking": "financial_services",
    "insurance": "financial_services",
    "wealth-management": "financial_services",
    # Healthcare
    "healthcare": "healthcare",
    "healthcare_wellness": "healthcare",
    "wellness": "healthcare",
    "pharma": "healthcare",
    # E-commerce
    "ecommerce": "ecommerce",
    "retail": "ecommerce",
    "fashion": "ecommerce",
    # Education
    "education": "education",
    "edtech": "education",
    # SaaS
    "saas": "saas",
    "b2b-saas": "saas",
}

DomainScenario = Literal["same_domain", "adjacent_domain", "different_domain"]


def classify_scenario(existing_domain: str, new_domain: str) -> DomainScenario:
    """Classify the reuse scenario based on domain relationship.

    - same_domain: exact match (case-insensitive)
    - adjacent_domain: both in the same DOMAIN_TAXONOMY_CLASSES group
    - different_domain: different taxonomy classes (or either unknown)
    """
    if existing_domain.lower() == new_domain.lower():
        return "same_domain"

    existing_class = DOMAIN_TAXONOMY_CLASSES.get(existing_domain.lower())
    new_class = DOMAIN_TAXONOMY_CLASSES.get(new_domain.lower())

    if existing_class and new_class and existing_class == new_class:
        return "adjacent_domain"

    return "different_domain"


# ---------------------------------------------------------------------------
# Reuse plan
# ---------------------------------------------------------------------------

@dataclass
class ReuseCandidate:
    persona_id: str
    age: int
    gender: str
    city_tier: str
    existing_domain: str
    scenario: DomainScenario


@dataclass
class ReusePlan:
    candidates: list[ReuseCandidate]    # matched registry personas (up to target_count)
    gap_count: int                       # how many new personas need to be generated
    target_count: int                    # original requested count
    registry_match_count: int            # total demographic matches found (before cap)


def plan_reuse(
    registry: PersonaRegistry,
    icp_age_min: int,
    icp_age_max: int,
    new_domain: str,
    target_count: int,
    icp_gender: str | None = None,
    icp_city_tier: str | None = None,
) -> ReusePlan:
    """Find registry personas matching ICP demographics and produce a ReusePlan.

    Steps:
    1. Query registry with demographic filters (age range, optional gender/city_tier)
    2. Classify each match as same_domain / adjacent_domain / different_domain
    3. Cap at target_count; compute gap_count = max(0, target_count - len(candidates))
    4. Return ReusePlan

    Parameters
    ----------
    registry:       PersonaRegistry to query
    icp_age_min:    Minimum age (inclusive)
    icp_age_max:    Maximum age (inclusive)
    new_domain:     Domain for the new experiment
    target_count:   How many personas are needed in total
    icp_gender:     Optional gender filter
    icp_city_tier:  Optional city tier filter ("metro", "tier2", etc.)
    """
    entries = registry.find(
        age_min=icp_age_min,
        age_max=icp_age_max,
        gender=icp_gender,
        city_tier=icp_city_tier,
    )

    all_candidates: list[ReuseCandidate] = [
        ReuseCandidate(
            persona_id=e.persona_id,
            age=e.age,
            gender=e.gender,
            city_tier=e.city_tier,
            existing_domain=e.domain,
            scenario=classify_scenario(e.domain, new_domain),
        )
        for e in entries
    ]

    registry_match_count = len(all_candidates)
    candidates = all_candidates[:target_count]
    gap_count = max(0, target_count - len(candidates))

    return ReusePlan(
        candidates=candidates,
        gap_count=gap_count,
        target_count=target_count,
        registry_match_count=registry_match_count,
    )
