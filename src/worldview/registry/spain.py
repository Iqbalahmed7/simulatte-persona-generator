"""Spain political archetype registry — Europe Benchmark v2.

Spanish politics are structured around a left-right axis and regional
autonomy cleavages. Calibrated against Pew Global Attitudes Spring 2024
(N=1,013) and CIS/electoral data.

Archetype distribution targets (2024 context, minority PSOE government):
  - psoe:          ~28% (Partido Socialista, Sánchez, governing minority)
  - pp:            ~33% (Partido Popular, Feijóo, main opposition)
  - vox:           ~13% (Vox, Abascal, far-right)
  - sumar_podemos: ~12% (Sumar/Podemos, left coalition partner)
  - non_partisan:  ~14% (regional parties, abstaining)
"""

SPAIN_POLITICAL_ARCHETYPES: dict[str, str] = {
    "pp": (
        "Partido Popular voter; centre-right, pro-EU (reformist), pro-NATO, "
        "pro-law-and-order, anti-secessionism. Often middle-class, small business, "
        "older, southern or central Spain. Moderate-to-high institutional trust, "
        "moderately traditional Catholic values, low-to-moderate religious salience. "
        "Critical of Sánchez government and territorial concessions. "
        "Calibrated to PP ~33% (2023 Spanish elections, Pew Spring 2024)."
    ),
    "psoe": (
        "Partido Socialista Obrero Español voter; centre-left, pro-EU, pro-welfare "
        "state, pro-gender equality, governing under Sánchez. Often urban, public-sector, "
        "diverse coalition including labour and progressive youth. Moderate institutional "
        "trust, progressive social values, largely secular. Pro-NATO, pro-EU, pro-Ukraine. "
        "Calibrated to PSOE ~28% (2023 Spanish elections)."
    ),
    "sumar_podemos": (
        "Sumar / Podemos voter; radical left, anti-austerity, feminist, pro-environment, "
        "coalition partner of PSOE. Urban, young, highly educated progressive. Very low "
        "institutional trust (in capital and media), very progressive social values, "
        "secular. Sceptical of NATO military spending, but anti-Russian. "
        "Critical of landlords, corporations, and Spanish centralisation. "
        "Calibrated to Sumar+Podemos ~12% (2023 Spanish elections)."
    ),
    "vox": (
        "Vox voter; far-right nationalist, anti-immigration, anti-feminism, "
        "anti-regional-autonomy (especially Catalan independence). Pro-Spanish unity, "
        "traditional Catholic values, sceptical of climate agenda. Low institutional "
        "trust in current government and media, moderate NATO support (strong army), "
        "moderate Russia stance (not as hostile as mainstream). "
        "Calibrated to Vox ~13% (2023 Spanish elections)."
    ),
    "non_partisan": (
        "Non-partisan Spanish voter including regional party voters (Junts, ERC, PNV, "
        "CC, BNG). Mixed institutional trust, pragmatic on EU and NATO. Often regional "
        "identity-focused. Median Spanish public opinion: broadly pro-EU, moderate on "
        "social issues, cultural Catholic identity."
    ),
}
