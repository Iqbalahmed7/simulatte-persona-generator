"""US political archetype registry.

Launched with ARCH-001 / Sprint A-1.

These archetypes are only valid for personas with location.country == "USA".
They are meaningless and must not be applied to non-US personas.

Distribution target (US_REPRESENTATIVE_DISTRIBUTION) is calibrated against
Pew Research Center 2023 party identification data:
  28% Republican, 27% Democrat, 43% Independent
  (Independents split ~55% lean-R, 45% lean-D overall)
"""

US_POLITICAL_ARCHETYPES: dict[str, str] = {
    # ── Core spectrum (use for standard nationally representative cohorts) ──
    "conservative": (
        "Aligns with Republican Party values: limited government, traditional social values, "
        "free-market economics, strong national security. Party ID: Republican."
    ),
    "lean_conservative": (
        "Centre-right independent: fiscally conservative, moderately socially tolerant, "
        "sceptical of government expansion. Leans Republican but doesn't strongly identify."
    ),
    "moderate": (
        "True independent: case-by-case positions, rejects strong partisan identity, "
        "values pragmatism over ideology. Does not consistently lean either direction."
    ),
    "lean_progressive": (
        "Centre-left independent: supports safety net programs, socially liberal, open to "
        "regulated markets. Leans Democrat but doesn't strongly identify."
    ),
    "progressive": (
        "Aligns with Democratic Party's left wing: expansive government role, systemic equity "
        "focus, climate action, wealth redistribution. Party ID: Democrat."
    ),

    # ── Sub-archetypes (use for high-fidelity ideological cohorts) ──
    "religious_conservative": (
        "Evangelical or traditional Catholic conservative. Social issues — abortion, LGBTQ rights, "
        "religious liberty — are the primary political driver. Often votes straight-ticket Republican."
    ),
    "fiscal_conservative": (
        "Libertarian-leaning: small government, low taxes, minimal regulation, but socially "
        "moderate or liberal. Skeptical of both parties' spending."
    ),
    "working_class_populist": (
        "Obama→Trump voter profile: economically populist (pro-union, anti-trade deals, "
        "anti-elite), culturally conservative. Disillusioned with both parties."
    ),
    "college_educated_liberal": (
        "Professional-class progressive: urban, postgraduate-educated, high institutional trust "
        "in science and expertise. Strongly aligned with Democratic Party."
    ),
    "non_voter_disengaged": (
        "Low political efficacy: doesn't identify with either party, rarely votes, unlikely to "
        "engage with political content. Views politics as irrelevant to daily life."
    ),
}


# Distribution weights for building a nationally representative US cohort.
# Core spectrum only (sub-archetypes are supplemental and not included here).
# Source: Pew Research Center 2023 party identification data.
US_REPRESENTATIVE_DISTRIBUTION: dict[str, float] = {
    "conservative":      0.15,
    "lean_conservative": 0.20,
    "moderate":          0.25,
    "lean_progressive":  0.22,
    "progressive":       0.18,
}

assert abs(sum(US_REPRESENTATIVE_DISTRIBUTION.values()) - 1.0) < 1e-9, (
    "US_REPRESENTATIVE_DISTRIBUTION must sum to 1.0"
)
