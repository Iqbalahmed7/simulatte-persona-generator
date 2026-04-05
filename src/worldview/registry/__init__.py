"""PoliticalRegistry — central registry of valid political archetypes per country.

This is the extensibility mechanism described in ARCH-001 addendum.

Adding a new geography = one new file in this directory + one entry below.
Nothing else in the system changes.

Currently supported countries:
  - "USA"   (launched with ARCH-001 / Sprint A-1)

Planned (future sprints):
  - "India" — see india.py stub
  - "UK"
  - "Germany"
  - "Brazil"
"""

from __future__ import annotations

from .us import US_POLITICAL_ARCHETYPES

# Registry map: ISO country name → valid archetype strings
# Add new countries here when their registry file is research-complete.
_REGISTRY_DATA: dict[str, dict[str, str]] = {
    "USA": US_POLITICAL_ARCHETYPES,
    # "India": INDIA_POLITICAL_ARCHETYPES,   ← uncomment when india.py is ready
    # "UK":    UK_POLITICAL_ARCHETYPES,
    # "Germany": GERMANY_POLITICAL_ARCHETYPES,
}


class PoliticalRegistry:
    """Central registry of valid political archetypes per country.

    Singleton accessed via get_political_registry().
    """

    def __init__(self, data: dict[str, dict[str, str]]) -> None:
        # Store as country → sorted list of valid archetype keys
        self._registry: dict[str, list[str]] = {
            country: sorted(archetypes.keys())
            for country, archetypes in data.items()
        }
        self._full: dict[str, dict[str, str]] = data

    def get_archetypes(self, country: str) -> list[str] | None:
        """Return valid archetypes for country, or None if unsupported."""
        return self._registry.get(country)

    def get_description(self, country: str, archetype: str) -> str | None:
        """Return description string for a given country + archetype, or None."""
        country_data = self._full.get(country)
        if country_data is None:
            return None
        return country_data.get(archetype)

    def supported_countries(self) -> list[str]:
        """Return sorted list of currently supported country codes."""
        return sorted(self._registry.keys())

    def is_supported(self, country: str) -> bool:
        return country in self._registry


_registry_instance: PoliticalRegistry | None = None


def get_political_registry() -> PoliticalRegistry:
    """Return the singleton PoliticalRegistry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = PoliticalRegistry(_REGISTRY_DATA)
    return _registry_instance


__all__ = [
    "PoliticalRegistry",
    "get_political_registry",
]
