"""WorldviewAnchor schema — two-level values & ideology architecture.

Defined in ARCH-001 and superseded by ARCH-001-addendum-geography.

Level 1: WorldviewAnchor — universal continuous dimensions, geography-agnostic.
Level 2: PoliticalProfile — country-gated categorical identity, registry-validated.

Usage:
    # US persona with full worldview
    anchor = WorldviewAnchor(
        institutional_trust=0.3,
        social_change_pace=0.2,
        collectivism_score=0.35,
        economic_security_priority=0.4,
        political_profile=PoliticalProfile(
            country="USA",
            archetype="lean_conservative",
        )
    )

    # Non-US persona — universal dimensions only, no political profile
    anchor = WorldviewAnchor(
        institutional_trust=0.6,
        social_change_pace=0.7,
        collectivism_score=0.8,
        economic_security_priority=0.6,
    )

    # Attempting unsupported country raises ValueError at construction time:
    PoliticalProfile(country="India", archetype="conservative")  # ValueError!
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PoliticalProfile(BaseModel):
    """Geography-specific political identity anchor.

    Each supported country defines its own vocabulary in src/worldview/registry/.
    The 'country' field acts as the discriminator — the registry validates that
    the archetype belongs to the declared country at construction time.

    Raises ValueError if:
      - country is not yet in the PoliticalRegistry
      - archetype is not valid for the given country
    """

    model_config = ConfigDict(extra="forbid")

    country: str = Field(
        ...,
        description="Country this profile applies to. Must match location.country.",
    )
    archetype: str = Field(
        ...,
        description="Political archetype key, validated against the country registry.",
    )
    description: str = Field(
        default="",
        description="Human-readable label for this archetype. Auto-populated if empty.",
    )

    @model_validator(mode="after")
    def _validate_archetype_for_country(self) -> "PoliticalProfile":
        # Deferred import avoids circular dependencies and keeps schema layer thin.
        from src.worldview.registry import get_political_registry  # noqa: PLC0415

        registry = get_political_registry()

        valid_archetypes = registry.get_archetypes(self.country)
        if valid_archetypes is None:
            raise ValueError(
                f"Country '{self.country}' is not yet supported in the political registry. "
                f"Supported countries: {registry.supported_countries()}. "
                f"To add support, create a new file in src/worldview/registry/ "
                f"and register it in src/worldview/registry/__init__.py."
            )

        if self.archetype not in valid_archetypes:
            raise ValueError(
                f"Archetype '{self.archetype}' is not valid for country '{self.country}'. "
                f"Valid archetypes: {valid_archetypes}"
            )

        # Auto-populate description if not provided.
        if not self.description:
            desc = registry.get_description(self.country, self.archetype)
            if desc:
                object.__setattr__(self, "description", desc)

        return self


class WorldviewAnchor(BaseModel):
    """Geography-agnostic worldview dimensions + optional country-gated political profile.

    Level 1 — Universal continuous dimensions (valid for any country):
      These 4 attributes describe a person's relationship to institutions, change,
      and collective identity in terms that translate across political systems.
      Range: 0.0–1.0

    Level 2 — PoliticalProfile (optional, country-gated):
      Set by demographic_sampler based on location.country.
      None = worldview seeded with universal dimensions only.
      Attempting to set this for an unsupported country raises ValueError.
    """

    model_config = ConfigDict(extra="forbid")

    institutional_trust: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Trust in institutions generally (government, media, science, courts). "
            "0 = deep distrust of all institutions; 1 = high institutional trust."
        ),
    )
    social_change_pace: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Preferred pace of social change. "
            "0 = traditional/preservationist; 1 = rapid change advocate."
        ),
    )
    collectivism_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Individualism vs. collectivism orientation. "
            "0 = strong individualist; 1 = strong collectivist."
        ),
    )
    economic_security_priority: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Economic policy priority. "
            "0 = freedom/growth priority (free-market); "
            "1 = security/equality priority (interventionist)."
        ),
    )

    # The geography-specific political profile.
    # None = worldview seeded with universal dimensions only.
    # Set by demographic_sampler based on location.country.
    political_profile: PoliticalProfile | None = None


__all__ = [
    "WorldviewAnchor",
    "PoliticalProfile",
]
