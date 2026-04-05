"""India political archetype registry — STUB, not yet implemented.

India's political cleavages are fundamentally different from the US spectrum.
Primary drivers: religious identity, caste, regional identity, economic aspiration
vs. welfare preference. The US conservative/progressive vocabulary is inapplicable
and must not be used for Indian personas.

This file defines the archetype vocabulary for when India support is built.
Register in PoliticalRegistry once archetypes are research-validated.

Requires:
  - Deep localisation per state (Maharashtra != UP != Tamil Nadu)
  - State-level registry extensions (future sprint)
  - Equivalent of Pew ATP data for India: CSDS/Lokniti survey data

Effort estimate: ~3-4 days research + 1 day implementation per state cluster.
"""

# STUB — not registered in PoliticalRegistry until research is complete.
# Uncomment and register in src/worldview/registry/__init__.py when ready.

INDIA_POLITICAL_ARCHETYPES: dict[str, str] = {
    "hindu_nationalist": (
        "BJP/RSS ideological alignment; Hindutva as primary identity. "
        "Strong centralised state, Hindu cultural assertiveness, anti-minority populism."
    ),
    "secular_centrist": (
        "Congress-aligned or non-BJP centrist; pluralist, Nehruvian secularism. "
        "Supports minority rights, federal structure, mixed-economy policies."
    ),
    "dalit_rights_focus": (
        "BSP/Ambedkarite alignment; caste justice and constitutional rights as primary driver. "
        "Deep skepticism of both Congress and BJP on caste equity."
    ),
    "regional_identity": (
        "State/regional party loyalty dominates national party identity. "
        "Examples: DMK (Tamil Nadu), TMC (West Bengal), Shiv Sena (Maharashtra). "
        "State-level interests override national ideological alignment."
    ),
    "aspirational_urban": (
        "Economic reformer; pro-business, anti-corruption, pro-digital India. "
        "Values meritocracy and economic mobility. Often supports BJP on economic grounds "
        "while being socially moderate."
    ),
    "welfare_rural": (
        "SP/RJD/regional left alignment; agricultural policy, MNREGA, food security "
        "as primary issues. Strong OBC identity. Anti-BJP on economic grounds."
    ),
}

# NOTE: India does not have a single representative distribution equivalent to
# US party ID data. Regional distributions would need to be built per state.
# INDIA_REPRESENTATIVE_DISTRIBUTION is deliberately omitted until state-level
# research is complete.
