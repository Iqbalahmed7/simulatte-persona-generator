"""src/schema/icp_spec.py

Pydantic model for the ICP (Ideal Customer Profile) specification.

The ICP spec is the user-facing input that defines who personas are built for.
It triggers Grounded Mode when domain data is also provided.

Spec ref: Master Spec §6 — "Layer 3: User-Specified Anchors (0-10 attributes).
From the ICP Spec 'Anchor Traits' section."
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ICPSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    domain: str                          # e.g. "child_nutrition", "saas_b2b"
    business_problem: str                # e.g. "Understand why parents defer Nutrimix purchases"
    target_segment: str                  # e.g. "Urban Indian parents, children 2-12, Tier 1-2 cities"
    anchor_traits: list[str] = Field(default_factory=list)
    # Attribute names that MUST be in the domain taxonomy.
    # e.g. ["pediatrician_trust", "clean_label_preference"]

    data_sources: list[str] = Field(default_factory=list)
    # Description of domain data provided, e.g. ["2,010 signals from LJ research corpus"]

    geography: str | None = None         # Primary market geography
    category: str | None = None          # Product category, e.g. "CPG", "SaaS"
    persona_count: int = 10              # Target cohort size (default 10)
