"""Sweden political archetype registry — Europe Benchmark v2.

Swedish politics are structured around a left-right economic axis and an
increasingly salient immigration/culture cleavage. SD now supports the
governing centre-right coalition. Calibrated against Pew Global Attitudes
Spring 2024 (N=1,017) and SCB/Valmyndigheten data.

Archetype distribution targets (2024 context, Tidö coalition governs):
  - sap:           ~31% (Social Democrats, Magdalena Andersson/Håkansson, main opp.)
  - m_kristersson: ~19% (Moderaterna, PM Ulf Kristersson, governing)
  - sd:            ~20% (Sverigedemokraterna, Åkesson, support party)
  - left_green:    ~13% (V communist-left + MP Greens)
  - non_partisan:  ~17% (C + KD + L + abstaining)
"""

SWEDEN_POLITICAL_ARCHETYPES: dict[str, str] = {
    "sap": (
        "Social Democratic voter (SAP); pro-welfare state, pro-union, moderate on "
        "immigration (shifted right after 2015), pro-NATO (historic U-turn 2022). "
        "Moderate institutional trust, moderate social values, largely secular "
        "(post-Lutheran). Supports Swedish model of social equality and public services. "
        "Broadly pro-EU, firmly anti-Russia since Ukraine invasion. "
        "Calibrated to SAP ~31% (2022 Swedish elections, Pew Spring 2024)."
    ),
    "m_kristersson": (
        "Moderaterna voter; centre-right, pro-market, pro-NATO, law-and-order. "
        "High institutional trust, moderate social values, largely secular. "
        "Supports tight immigration controls (convergence with SD), pro-EU, "
        "firmly pro-NATO and anti-Russia. Often urban professional, higher income, "
        "southern Sweden. Governing party. "
        "Calibrated to M ~19% (2022 Swedish elections)."
    ),
    "sd": (
        "Sverigedemokraterna voter; nationalist, anti-immigration, culturally "
        "conservative. Low-to-moderate institutional trust (distrustful of media, "
        "left-wing establishment), traditional values, moderate Lutheran cultural "
        "attachment. Now pro-NATO (Ukraine war effect), anti-Russia, but nativist "
        "on identity. Often working-class, peripheral Sweden, lower education. "
        "Calibrated to SD ~20% (2022 Swedish elections)."
    ),
    "left_green": (
        "Vänsterpartiet (V) or Miljöpartiet (MP) voter; left of SAP, anti-NATO "
        "(traditional V position, somewhat moderated post-2022), pro-environment, "
        "feminist, pro-immigration. Very progressive social values, secular. "
        "Moderate institutional trust in EU, critical of NATO's political dimensions "
        "while accepting military security necessity. Often urban, highly educated, young. "
        "Calibrated to V+MP ~13% (2022 Swedish elections)."
    ),
    "non_partisan": (
        "Non-partisan or small-party Swedish voter (C, KD, L, or non-voter). "
        "High secular baseline (Sweden among world's most secular societies). "
        "Moderate-to-high institutional trust, broadly pro-EU and pro-NATO, "
        "pragmatic on immigration. Median Swedish public opinion: very low religious "
        "salience, moderate-progressive social values, high trust in state."
    ),
}
