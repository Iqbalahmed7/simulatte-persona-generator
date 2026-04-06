"""India political archetype registry — Study 1B implementation.

India's political cleavages are driven by BJP/opposition lean, religious identity,
caste, and regional identity. The US conservative/progressive vocabulary is
inapplicable for Indian personas.

Archetype vocabulary calibrated against:
  - Pew Global Attitudes Spring 2023 (N=2,611): BJP fav 73%, Modi fav 79%
  - Distribution: bjp_supporter 18%, bjp_lean 20%, neutral 25%,
                  opposition_lean 20%, opposition 18%

Archetypes map from BJP-alignment (strong) → neutral → opposition (strong).
Religious identity, caste, and region are separate dimensions in the persona
pool — not collapsed into the political archetype.
"""

INDIA_POLITICAL_ARCHETYPES: dict[str, str] = {
    "bjp_supporter": (
        "Strong BJP supporter; proud of India's rise under Modi leadership. "
        "Hindu cultural identity is central. Supports strong centralised governance, "
        "economic nationalism, infrastructure development. High institutional trust. "
        "Calibrated to BJP very favorable 42% (Pew Spring 2023)."
    ),
    "bjp_lean": (
        "Generally positive on BJP; values stability, development, and Hindu culture. "
        "Pragmatic — may have reservations but broadly satisfied with current direction. "
        "Supports Modi's economic and foreign policy. Traditional values with openness "
        "to women's education and workforce participation. "
        "Calibrated to BJP somewhat favorable 31% (Pew Spring 2023)."
    ),
    "neutral": (
        "Politically pragmatic; issue-by-issue rather than party-loyal. "
        "Cares about local economic conditions, jobs, and civic services. "
        "May vote for different parties depending on context. Mixed views on BJP and "
        "opposition. Representative of swing voters in the Indian electorate."
    ),
    "opposition_lean": (
        "Leans toward opposition — INC, regional parties, or anti-BJP coalition. "
        "Values democratic institutions, checks on executive power, and minority rights. "
        "Concerned about communal tensions and centralisation of power. "
        "Calibrated to INC somewhat favorable 37% (Pew Spring 2023)."
    ),
    "opposition": (
        "Strong opposition supporter; critical of BJP's communal politics and "
        "democratic backsliding. Prioritises secular governance, federalism, "
        "and minority protection. Often Muslim, Dalit/SC, or educated secular urban. "
        "Calibrated to BJP very unfavorable + strong INC/regional support."
    ),
}
