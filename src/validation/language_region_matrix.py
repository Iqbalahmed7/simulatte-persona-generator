"""
Static language-region compatibility matrix for India.

Languages: hi (Hindi), ta (Tamil), te (Telugu), mr (Marathi),
           bn (Bengali), kn (Kannada), gu (Gujarati),
           pa (Punjabi), ml (Malayalam), or (Odia)

Regions: delhi, maharashtra, tamil_nadu, telangana_andhra, west_bengal,
         karnataka, gujarat, punjab, rajasthan, kerala, odisha,
         uttar_pradesh, bihar, haryana
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Alias maps — allow callers to use either ISO codes or full English names
# ---------------------------------------------------------------------------

_LANGUAGE_ALIASES: dict[str, str] = {
    # full name -> canonical code
    "hindi": "hi",
    "tamil": "ta",
    "telugu": "te",
    "marathi": "mr",
    "bengali": "bn",
    "kannada": "kn",
    "gujarati": "gu",
    "punjabi": "pa",
    "malayalam": "ml",
    "odia": "or",
    "oriya": "or",
    # codes map to themselves (identity, handled in normalise helper)
}

_REGION_ALIASES: dict[str, str] = {
    # common alternate spellings / short forms -> canonical key
    "telangana": "telangana_andhra",
    "andhra": "telangana_andhra",
    "andhra_pradesh": "telangana_andhra",
    "bengal": "west_bengal",
    "wb": "west_bengal",
    "up": "uttar_pradesh",
}


def _normalise_language(lang: str) -> str:
    """Return the canonical ISO code for a language string."""
    key = lang.lower().strip()
    return _LANGUAGE_ALIASES.get(key, key)


def _normalise_region(region: str) -> str:
    """Return the canonical region key."""
    key = region.lower().strip()
    return _REGION_ALIASES.get(key, key)


@dataclass
class LanguageRegionCompatibility:
    language: str
    region: str
    compatible: bool
    prohibited_combination: bool   # True for harmful/offensive/imperialist pairings
    notes: str


# ---------------------------------------------------------------------------
# Static compatibility matrix
# All language and region values are stored in lowercase.
# ---------------------------------------------------------------------------

LANGUAGE_REGION_MATRIX: list[LanguageRegionCompatibility] = [

    # ------------------------------------------------------------------
    # Core native-language / home-region pairings  (compatible=True)
    # ------------------------------------------------------------------
    LanguageRegionCompatibility(
        language="hi", region="delhi",
        compatible=True, prohibited_combination=False,
        notes="Hindi is the dominant language of Delhi.",
    ),
    LanguageRegionCompatibility(
        language="mr", region="maharashtra",
        compatible=True, prohibited_combination=False,
        notes="Marathi is the official state language of Maharashtra.",
    ),
    LanguageRegionCompatibility(
        language="ta", region="tamil_nadu",
        compatible=True, prohibited_combination=False,
        notes="Tamil is the official language of Tamil Nadu.",
    ),
    LanguageRegionCompatibility(
        language="te", region="telangana_andhra",
        compatible=True, prohibited_combination=False,
        notes="Telugu is the official language of Telangana and Andhra Pradesh.",
    ),
    LanguageRegionCompatibility(
        language="bn", region="west_bengal",
        compatible=True, prohibited_combination=False,
        notes="Bengali is the official language of West Bengal.",
    ),
    LanguageRegionCompatibility(
        language="kn", region="karnataka",
        compatible=True, prohibited_combination=False,
        notes="Kannada is the official language of Karnataka.",
    ),
    LanguageRegionCompatibility(
        language="gu", region="gujarat",
        compatible=True, prohibited_combination=False,
        notes="Gujarati is the official language of Gujarat.",
    ),
    LanguageRegionCompatibility(
        language="pa", region="punjab",
        compatible=True, prohibited_combination=False,
        notes="Punjabi is the official language of Punjab.",
    ),
    LanguageRegionCompatibility(
        language="ml", region="kerala",
        compatible=True, prohibited_combination=False,
        notes="Malayalam is the official language of Kerala.",
    ),
    LanguageRegionCompatibility(
        language="or", region="odisha",
        compatible=True, prohibited_combination=False,
        notes="Odia is the official language of Odisha.",
    ),

    # ------------------------------------------------------------------
    # Hindi as secondary / widely-used language in additional regions
    # (compatible=True — Hindi is constitutionally recognised but not
    #  the native tongue; inclusion reflects realistic usage, not imposition)
    # ------------------------------------------------------------------
    LanguageRegionCompatibility(
        language="hi", region="rajasthan",
        compatible=True, prohibited_combination=False,
        notes="Hindi is the official and widely spoken language of Rajasthan.",
    ),
    LanguageRegionCompatibility(
        language="hi", region="punjab",
        compatible=True, prohibited_combination=False,
        notes="Hindi is widely understood and used alongside Punjabi in Punjab.",
    ),
    LanguageRegionCompatibility(
        language="hi", region="uttar_pradesh",
        compatible=True, prohibited_combination=False,
        notes="Hindi is the dominant language of Uttar Pradesh.",
    ),
    LanguageRegionCompatibility(
        language="hi", region="bihar",
        compatible=True, prohibited_combination=False,
        notes="Hindi is the official and primary language of Bihar.",
    ),
    LanguageRegionCompatibility(
        language="hi", region="haryana",
        compatible=True, prohibited_combination=False,
        notes="Hindi is the official language of Haryana.",
    ),
    LanguageRegionCompatibility(
        language="hi", region="maharashtra",
        compatible=True, prohibited_combination=False,
        notes=(
            "Hindi is commonly used in Mumbai and other urban centres "
            "of Maharashtra alongside Marathi."
        ),
    ),

    # ------------------------------------------------------------------
    # Prohibited pairings (compatible=False, prohibited_combination=True)
    # These represent linguistically inappropriate or historically
    # imperialist assignments that should never be generated.
    # ------------------------------------------------------------------
    LanguageRegionCompatibility(
        language="hi", region="tamil_nadu",
        compatible=False, prohibited_combination=True,
        notes=(
            "Hindi imposed on Tamil-speaking region is culturally "
            "inappropriate and historically sensitive."
        ),
    ),
    LanguageRegionCompatibility(
        language="hi", region="west_bengal",
        compatible=False, prohibited_combination=True,
        notes=(
            "Bengali is the primary language of West Bengal; "
            "Hindi imposition is inappropriate."
        ),
    ),
    LanguageRegionCompatibility(
        language="ta", region="maharashtra",
        compatible=False, prohibited_combination=True,
        notes=(
            "Tamil is not a language of Maharashtra; "
            "use Marathi or Hindi for this region."
        ),
    ),
    LanguageRegionCompatibility(
        language="kn", region="gujarat",
        compatible=False, prohibited_combination=True,
        notes=(
            "Kannada is regional to Karnataka; "
            "Gujarati is the appropriate language for Gujarat."
        ),
    ),
    LanguageRegionCompatibility(
        language="te", region="punjab",
        compatible=False, prohibited_combination=True,
        notes="Telugu is not spoken in Punjab; use Punjabi or Hindi.",
    ),
    LanguageRegionCompatibility(
        language="hi", region="kerala",
        compatible=False, prohibited_combination=True,
        notes=(
            "Malayalam is the official language of Kerala; assigning Hindi "
            "as the primary language for Kerala personas is inappropriate."
        ),
    ),
    LanguageRegionCompatibility(
        language="gu", region="tamil_nadu",
        compatible=False, prohibited_combination=True,
        notes=(
            "Gujarati has no significant speaker base in Tamil Nadu; "
            "Tamil is the correct choice for this region."
        ),
    ),
    LanguageRegionCompatibility(
        language="ta", region="gujarat",
        compatible=False, prohibited_combination=True,
        notes=(
            "Tamil is not spoken in Gujarat; "
            "Gujarati is the appropriate language for this region."
        ),
    ),
]


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def check_language_region(language: str, region: str) -> LanguageRegionCompatibility:
    """Look up a language-region pairing in LANGUAGE_REGION_MATRIX.

    Accepts both ISO codes (e.g. ``'hi'``) and full English names
    (e.g. ``'hindi'``).  Comparison is case-insensitive.  If the pairing is
    not found, a default entry with compatible=False and
    prohibited_combination=False is returned to signal an *unknown* (but not
    explicitly banned) combination.
    """
    lang = _normalise_language(language)
    reg = _normalise_region(region)

    for entry in LANGUAGE_REGION_MATRIX:
        if entry.language == lang and entry.region == reg:
            return entry

    return LanguageRegionCompatibility(
        language=lang,
        region=reg,
        compatible=False,
        prohibited_combination=False,
        notes="Pairing not found in the compatibility matrix.",
    )


def get_valid_languages_for_region(region: str) -> list[str]:
    """Return all compatible languages for a given region."""
    reg = _normalise_region(region)
    return [
        entry.language
        for entry in LANGUAGE_REGION_MATRIX
        if entry.region == reg and entry.compatible
    ]


def get_valid_regions_for_language(language: str) -> list[str]:
    """Return all compatible regions for a given language."""
    lang = _normalise_language(language)
    return [
        entry.region
        for entry in LANGUAGE_REGION_MATRIX
        if entry.language == lang and entry.compatible
    ]
