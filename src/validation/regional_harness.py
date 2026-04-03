from dataclasses import dataclass, field

@dataclass
class RegionalTestPersona:
    persona_id: str
    language: str
    region: str
    expected_language_region_compatible: bool  # False for invalid pairings
    fixture_description: str   # Human-readable description of what to test


# Hardcoded region → valid language mapping (5 regions)
REGION_LANGUAGE_MAP: dict[str, list[str]] = {
    "maharashtra": ["marathi", "hindi", "english"],
    "tamil_nadu": ["tamil", "english"],
    "karnataka": ["kannada", "english", "hindi"],
    "west_bengal": ["bengali", "english"],
    "delhi": ["hindi", "punjabi", "english"],
}


def generate_test_fixtures(
    language: str,
    region: str,
    n: int = 10,
) -> list[RegionalTestPersona]:
    """
    Generate n test fixture personas for a given language-region combination.

    The `expected_language_region_compatible` flag is set to True when the language
    is in REGION_LANGUAGE_MAP[region], False otherwise.

    This is a deterministic fixture generator — no LLM calls.
    Each fixture has a unique persona_id: f"test-{language}-{region}-{i:03d}"

    Parameters
    ----------
    language: str — e.g. "hindi", "tamil"
    region: str — e.g. "maharashtra", "tamil_nadu"
    n: int — number of fixture personas to generate (default 10)
    """
    lang = language.lower()
    reg = region.lower()
    valid_langs = REGION_LANGUAGE_MAP.get(reg, [])
    compatible = lang in valid_langs

    fixtures = []
    for i in range(n):
        fixtures.append(
            RegionalTestPersona(
                persona_id=f"test-{language}-{region}-{i:03d}",
                language=language,
                region=region,
                expected_language_region_compatible=compatible,
                fixture_description=f"Test persona {i + 1} for {language} output in {region}",
            )
        )
    return fixtures


def check_language_region_validity(language: str, region: str) -> bool:
    """
    Return True if language is valid for the given region.
    Return False if region unknown OR language not in region's valid set.
    """
    return language.lower() in REGION_LANGUAGE_MAP.get(region.lower(), [])
