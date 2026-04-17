"""PoliticalRegistry — central registry of valid political archetypes per country.

This is the extensibility mechanism described in ARCH-001 addendum.

Adding a new geography = one new file in this directory + one entry below.
Nothing else in the system changes.

Currently supported countries:
  - "USA"         (launched with ARCH-001 / Sprint A-1)
  - "India"       (launched with Study 1B / Sprint B-9)
  - "United Kingdom" (Europe Benchmark v2)
  - "France"      (Europe Benchmark v2)
  - "Germany"     (Europe Benchmark v2)
  - "Greece"      (Europe Benchmark v2)
  - "Hungary"     (Europe Benchmark v2)
  - "Italy"       (Europe Benchmark v2)
  - "Netherlands" (Europe Benchmark v2)
  - "Poland"      (Europe Benchmark v2)
  - "Spain"       (Europe Benchmark v2)
  - "Sweden"      (Europe Benchmark v2)
"""

from __future__ import annotations

from .us import US_POLITICAL_ARCHETYPES
from .india import INDIA_POLITICAL_ARCHETYPES
from .uk import UK_POLITICAL_ARCHETYPES
from .france import FRANCE_POLITICAL_ARCHETYPES
from .germany import GERMANY_POLITICAL_ARCHETYPES
from .greece import GREECE_POLITICAL_ARCHETYPES
from .hungary import HUNGARY_POLITICAL_ARCHETYPES
from .italy import ITALY_POLITICAL_ARCHETYPES
from .netherlands import NETHERLANDS_POLITICAL_ARCHETYPES
from .poland import POLAND_POLITICAL_ARCHETYPES
from .spain import SPAIN_POLITICAL_ARCHETYPES
from .sweden import SWEDEN_POLITICAL_ARCHETYPES

# Registry map: ISO country name → valid archetype strings
# Add new countries here when their registry file is research-complete.
_REGISTRY_DATA: dict[str, dict[str, str]] = {
    "USA": US_POLITICAL_ARCHETYPES,
    "India": INDIA_POLITICAL_ARCHETYPES,
    "United Kingdom": UK_POLITICAL_ARCHETYPES,
    "France": FRANCE_POLITICAL_ARCHETYPES,
    "Germany": GERMANY_POLITICAL_ARCHETYPES,
    "Greece": GREECE_POLITICAL_ARCHETYPES,
    "Hungary": HUNGARY_POLITICAL_ARCHETYPES,
    "Italy": ITALY_POLITICAL_ARCHETYPES,
    "Netherlands": NETHERLANDS_POLITICAL_ARCHETYPES,
    "Poland": POLAND_POLITICAL_ARCHETYPES,
    "Spain": SPAIN_POLITICAL_ARCHETYPES,
    "Sweden": SWEDEN_POLITICAL_ARCHETYPES,
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
