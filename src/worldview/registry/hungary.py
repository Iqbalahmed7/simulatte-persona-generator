"""Hungary political archetype registry — Europe Benchmark v2.

Hungarian politics are dominated by Fidesz under Viktor Orbán vs. a fragmented
opposition. Calibrated against Pew Global Attitudes Spring 2024 (N=996) and
Hungarian Electoral Authority data.

Archetype distribution targets (2024 context):
  - fidesz:       ~45% (Fidesz, governing supermajority)
  - opposition:   ~32% (united opposition: DK, MSZP, Jobbik/MFP, Momentum)
  - non_partisan: ~23% (disengaged, non-voters, floating)
"""

HUNGARY_POLITICAL_ARCHETYPES: dict[str, str] = {
    "fidesz": (
        "Fidesz / KDNP voter; pro-Orbán, illiberal-conservative, sovereignist. "
        "Trusts the Hungarian government highly but sceptical of EU and Western "
        "liberal institutions. Traditional family values, Christian (Catholic or "
        "Calvinist) identity, anti-immigration, anti-LGBTQ+ social agenda. "
        "Neutral-to-sympathetic toward Russia, sceptical of NATO military aid to Ukraine. "
        "Often rural or provincial, working-class or older. High national institutional "
        "trust, low EU institutional trust, high religious salience. "
        "Calibrated to Fidesz ~45% (2024 Hungarian elections, Pew Spring 2024)."
    ),
    "opposition": (
        "Hungarian opposition voter (DK, Momentum, Jobbik/MFP, MSZP, or Tisza). "
        "Anti-Orbán, pro-EU, pro-rule-of-law, pro-democratic norms. Often urban, "
        "younger, more educated. Low trust in Hungarian institutions (captured by "
        "Fidesz), higher trust in EU institutions. Progressive-to-moderate social "
        "values, largely secular or non-practising. Strongly anti-Russian, pro-NATO, "
        "pro-Ukraine. Critical of Hungarian media and judicial capture. "
        "Calibrated to opposition ~32% (2024 Hungarian elections)."
    ),
    "non_partisan": (
        "Non-partisan or disengaged Hungarian voter. Mixed institutional trust, "
        "pragmatic on EU and NATO. Often rural or small-town, lower income. "
        "Median Hungarian public opinion: moderate Fidesz-sympathetic lean but "
        "not strongly ideological. Cultural Christian identity, pragmatic worldview."
    ),
}
