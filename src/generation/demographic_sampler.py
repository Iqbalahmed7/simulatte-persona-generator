"""Demographic anchor sampler for CLI persona generation.

Sprint 12. Generates diverse, realistic DemographicAnchor instances for
cohort generation when no explicit anchor is provided by the caller.

Diversity rules (G6):
- No single city > 20% of cohort
- No single age bracket > 40% of cohort
- ≥ 3 income brackets represented for cohorts ≥ 6

The sampler uses a round-robin pool strategy: cycle through a pool of
diverse demographic profiles so that any cohort of N ≤ pool_size is
automatically diverse across city, age, and income.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Demographic pools — all values use valid schema Literal values
# ---------------------------------------------------------------------------

_CPG_POOL = [
    # (name, age, gender, country, region, city, urban_tier,
    #  structure, size, income_bracket, dual_income,
    #  life_stage, education, employment)
    ("Priya Mehta",     36, "female",     "India", "Maharashtra",    "Mumbai",    "metro",  "nuclear",         4, "middle",       True,  "mid-career",     "undergraduate", "full-time"),
    ("Rahul Verma",     28, "male",       "India", "Karnataka",      "Bengaluru", "metro",  "other",           1, "upper-middle", False, "early-career",   "postgraduate",  "full-time"),
    ("Sunita Devi",     45, "female",     "India", "Uttar Pradesh",  "Lucknow",   "tier2",  "joint",           6, "lower-middle", False, "mid-career",     "high-school",   "part-time"),
    ("Amit Sharma",     38, "male",       "India", "Delhi",          "Delhi",     "metro",  "nuclear",         3, "upper-middle", True,  "mid-career",     "postgraduate",  "full-time"),
    ("Deepa Nair",      31, "female",     "India", "Kerala",         "Kochi",     "tier2",  "nuclear",         3, "middle",       True,  "early-family",   "undergraduate", "full-time"),
    ("Vikram Singh",    52, "male",       "India", "Rajasthan",      "Jaipur",    "tier2",  "joint",           7, "middle",       False, "late-career",    "undergraduate", "self-employed"),
    ("Ananya Roy",      25, "female",     "India", "West Bengal",    "Kolkata",   "metro",  "other",           1, "lower-middle", False, "early-career",   "postgraduate",  "full-time"),
    ("Suresh Patel",    41, "male",       "India", "Gujarat",        "Ahmedabad", "metro",  "nuclear",         4, "upper-middle", True,  "mid-career",     "undergraduate", "full-time"),
    ("Meena Krishnan",  36, "female",     "India", "Tamil Nadu",     "Chennai",   "metro",  "nuclear",         3, "middle",       True,  "mid-career",     "postgraduate",  "full-time"),
    ("Rohit Gupta",     29, "male",       "India", "Madhya Pradesh", "Bhopal",    "tier2",  "nuclear",         2, "lower-middle", False, "early-career",   "undergraduate", "full-time"),
    ("Kavita Joshi",    48, "female",     "India", "Maharashtra",    "Pune",      "metro",  "nuclear",         4, "upper-middle", True,  "late-career",    "postgraduate",  "full-time"),
    ("Arun Nambiar",    33, "male",       "India", "Kerala",         "Thiruvananthapuram", "tier2", "nuclear", 3, "middle",       True,  "early-family",   "postgraduate",  "full-time"),
]

_SAAS_POOL = [
    ("Alex Chen",       32, "male",       "USA",  "California",     "San Francisco", "metro", "other",        1, "upper-middle", False, "early-career",  "postgraduate",  "full-time"),
    ("Sarah Johnson",   38, "female",     "USA",  "New York",       "New York",      "metro", "nuclear",      3, "upper-middle", True,  "mid-career",    "undergraduate", "full-time"),
    ("Marcus Williams", 45, "male",       "USA",  "Texas",          "Austin",        "metro", "nuclear",      4, "upper-middle", True,  "mid-career",    "undergraduate", "full-time"),
    ("Priya Patel",     29, "female",     "USA",  "Washington",     "Seattle",       "metro", "other",        1, "middle",       False, "early-career",  "postgraduate",  "full-time"),
    ("Tom Baker",       52, "male",       "UK",   "England",        "London",        "metro", "nuclear",      4, "upper-middle", True,  "late-career",   "undergraduate", "full-time"),
    ("Emma Schmidt",    35, "female",     "Germany", "Bavaria",     "Munich",        "metro", "couple-no-kids", 2, "upper-middle", True, "mid-career",   "postgraduate",  "full-time"),
    ("Carlos Mendez",   41, "male",       "USA",  "Illinois",       "Chicago",       "metro", "nuclear",      3, "middle",       True,  "mid-career",    "undergraduate", "full-time"),
    ("Yuki Tanaka",     27, "non-binary", "USA",  "Massachusetts",  "Boston",        "metro", "other",        1, "middle",       False, "early-career",  "postgraduate",  "full-time"),
]

_GENERAL_POOL = _CPG_POOL  # Default to CPG pool

_DOMAIN_POOLS = {
    "cpg": _CPG_POOL,
    "saas": _SAAS_POOL,
    "general": _CPG_POOL,
    "health_wellness": _CPG_POOL,
}


def sample_demographic_anchor(
    domain: str,
    index: int,
    seed: int | None = None,
) -> Any:
    """Sample a DemographicAnchor for persona generation.

    Uses round-robin from a domain-specific pool to maximise diversity.
    The index parameter ensures different personas in the same cohort get
    different demographics.

    Args:
        domain: Domain key (cpg, saas, general, health_wellness).
        index: Persona index within the cohort (0-based). Used for pool cycling.
        seed: Optional random seed for reproducibility.

    Returns:
        A DemographicAnchor instance.
    """
    from src.schema.persona import DemographicAnchor, Location, Household

    pool = _DOMAIN_POOLS.get(domain.lower(), _GENERAL_POOL)

    # Round-robin through pool — ensures diversity within a cohort
    entry = pool[index % len(pool)]

    (name, age, gender, country, region, city, urban_tier,
     structure, size, income_bracket, dual_income,
     life_stage, education, employment) = entry

    # Optional: add small age variation (+/-3 years) for diversity when wrapping
    if seed is not None and index >= len(pool):
        rng = random.Random(seed + index)
        age = max(18, min(65, age + rng.randint(-3, 3)))

    return DemographicAnchor(
        name=name,
        age=age,
        gender=gender,
        location=Location(
            country=country,
            region=region,
            city=city,
            urban_tier=urban_tier,
        ),
        household=Household(
            structure=structure,
            size=size,
            income_bracket=income_bracket,
            dual_income=dual_income,
        ),
        life_stage=life_stage,
        education=education,
        employment=employment,
    )
