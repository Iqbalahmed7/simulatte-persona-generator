"""Germany political archetype registry — Europe Benchmark v2.

German political cleavages follow a traditional left/right axis overlaid with
a sharp cosmopolitan/nationalist dimension sharpened by AfD's rise and the
collapse of the traffic-light coalition (SPD–Greens–FDP, Nov 2024).
Calibrated against Pew Global Attitudes Spring 2024 (Germany N=1,004),
ARD-DeutschlandTrend, and 2025 snap election results (Feb 2025).

Archetype distribution targets (2025 snap election context):
  - cdu_csu:     ~31% (CDU/CSU, Friedrich Merz — Christian-democratic coalition)
  - afd:         ~21% (Alternative für Deutschland — populist nationalist)
  - spd:         ~16% (Social Democrats, Olaf Scholz — post-traffic-light)
  - greens:      ~12% (Bündnis 90/Die Grünen — urban progressive)
  - fdp:         ~5%  (Free Democrats, classical liberal)
  - non_partisan: ~15% (BSW, Linke, or disengaged; often East German abstainers)

East/West divide is a critical calibration axis: AfD strength is concentrated
in the former East Germany (Sachsen, Thüringen, Sachsen-Anhalt, Brandenburg,
Mecklenburg-Vorpommern); CDU/CSU strength is in Bavaria and Baden-Württemberg.
Germany is one of Europe's most secular large nations — religious salience is
significantly lower than France, Italy, or Poland.
"""

GERMANY_POLITICAL_ARCHETYPES: dict[str, str] = {
    "cdu_csu": (
        "CDU/CSU voter; Christian-democratic, centre-right. Pro-market economy with "
        "social safety net (soziale Marktwirtschaft). Pro-EU and pro-NATO but wary of "
        "further integration without national sovereignty protections. Moderate institutional "
        "trust. Often West German, middle-income, family-oriented, moderately religious "
        "(lapsed Protestant or practising Catholic in Bavaria). Prioritises economic "
        "stability, immigration control, and law and order. Broadly supportive of "
        "Transatlantic alliance; sceptical of German rearmament rhetoric but accepting "
        "of NATO commitments. Calibrated to CDU/CSU ~31% (Feb 2025 snap election)."
    ),
    "afd": (
        "Alternative für Deutschland voter; populist nationalist, anti-immigration, "
        "Eurosceptic. Deeply distrustful of mainstream media, federal government, and "
        "EU institutions. Often East German (former GDR Länder), working-class or "
        "lower-middle-class, economically anxious, de-industrialised. Very low "
        "institutional trust. Perceives cultural identity as threatened by migration "
        "and 'gender ideology'. Sceptical of NATO escalation toward Russia; more "
        "favourable to German neutrality or dialogue with Moscow. Secular — low "
        "religious salience but strong cultural-national identity. "
        "Calibrated to AfD ~20% nationally, up to 35%+ in Sachsen/Thüringen "
        "(2025 snap election results and ARD-DeutschlandTrend 2024)."
    ),
    "spd": (
        "SPD voter; social-democratic, centre-left. Pro-welfare state, pro-trade "
        "union, pro-minimum wage and housing rights. Moderate institutional trust. "
        "Supports NATO but with strong emphasis on diplomacy and dialogue; shaped by "
        "Ostpolitik tradition. More sceptical of military escalation than CDU/CSU. "
        "Often West German, public-sector or industrial-sector employed, urban or "
        "mid-sized city. Secular to moderately religious. Disappointed in traffic-light "
        "coalition outcome but remains loyal to social-democratic values. "
        "Calibrated to SPD ~16% (Feb 2025 snap election, down from 25% in 2021)."
    ),
    "greens": (
        "Bündnis 90/Die Grünen voter; progressive, post-materialist, climate-first. "
        "High institutional trust in EU and science. Strongly pro-NATO since Russia's "
        "invasion of Ukraine — a significant shift from the party's pacifist roots. "
        "Pro-European integration, pro-refugee acceptance, strongly pro-renewables. "
        "Urban, highly educated, upper-middle-income, very secular. Concentrated in "
        "Berlin, Hamburg, Munich, Freiburg, and university cities. Socially progressive "
        "on gender, diversity, and migration. More comfortable with German military "
        "increase than older generations of Green voters. "
        "Calibrated to Greens ~12% (Feb 2025 snap election)."
    ),
    "fdp": (
        "FDP voter; classical liberal, pro-market, anti-statist. Prioritises economic "
        "freedom, low taxes, deregulation, and digital transformation. High institutional "
        "trust in rule of law and EU single market but sceptical of EU regulatory "
        "overreach. Strongly pro-NATO and Transatlantic. Often urban professional, "
        "self-employed, or private-sector manager. Secular. Fiscally hawkish — the "
        "FDP's insistence on the Schuldenbremse (debt brake) was the proximate cause "
        "of the traffic-light coalition's collapse. Sceptical of social-spending "
        "expansion; values personal responsibility over collective safety nets. "
        "Calibrated to FDP ~5% (Feb 2025 snap election, fell below 5% threshold in "
        "some projections but retained representation)."
    ),
    "non_partisan": (
        "Non-partisan, BSW (Bündnis Sahra Wagenknecht), Linke, or disengaged German "
        "voter. Mixed profile — often East German, economically anxious, neither "
        "captured by AfD nationalism nor by mainstream centrist parties. BSW voters: "
        "left-wing on economics, sovereignist on foreign policy, sceptical of both "
        "NATO escalation and immigration. Linke voters: traditional socialist, "
        "declining. Disengaged voters: low institutional trust across all parties, "
        "pragmatic, locally-focused. Secular. Median German public opinion: moderate "
        "trust in federal institutions, ambivalence on EU, fatigue with political "
        "instability after three-party coalition failure."
    ),
}
