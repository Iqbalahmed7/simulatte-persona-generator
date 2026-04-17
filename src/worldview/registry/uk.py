"""UK political archetype registry — Europe Benchmark v2.

UK political cleavages are driven by party identity, Brexit legacy, and
class/education divide. Calibrated against Pew Global Attitudes Spring 2024
(N=1,017) and YouGov/British Electoral Study data.

Archetype distribution targets (2024 electoral context):
  - labour:         ~35% (governing majority, Keir Starmer)
  - conservative:   ~24% (post-Sunak, declining)
  - lib_dem:        ~12% (Remain-aligned, suburban)
  - reform:         ~13% (Farage-aligned, Leave populist)
  - snp_plaid_green: ~7% (Scottish/Welsh/Green, pro-EU)
  - non_partisan:   ~9% (disengaged, cross-cutting)
"""

UK_POLITICAL_ARCHETYPES: dict[str, str] = {
    "reform": (
        "Reform UK / hard-Brexit populist. Deep distrust of Westminster, the BBC, "
        "and mainstream institutions. Strongly anti-immigration, anti-EU, and "
        "sceptical of net zero. Often Leave-voting, working-class or lower-middle-class "
        "English. Feels left behind by the political establishment. Low institutional "
        "trust, traditional values, moderate religious attachment. "
        "Calibrated to Reform ~13% support (2024 Pew Spring UK sample)."
    ),
    "conservative": (
        "Traditional Conservative voter; values economic stability, low taxation, "
        "and gradual social change. Mixed on Brexit (both Leave and Remain wings). "
        "Often homeowning, middle-class, southern England or English market town. "
        "Moderate-to-high institutional trust, moderately traditional values. "
        "Supports NATO and the Atlantic alliance. "
        "Calibrated to Conservative ~24% (2024 Pew Spring UK sample)."
    ),
    "labour": (
        "Labour Party supporter; centre-left on economics, pro-public services, "
        "multi-cultural Britain. Mostly Remain-sympathising. Urban and suburban, "
        "diverse in class background from traditional working-class to graduate. "
        "Moderate institutional trust, progressive-to-moderate social values, "
        "generally secular. Strongly anti-Trump, broadly pro-EU and pro-NATO. "
        "Calibrated to Labour ~35% (2024 Pew Spring UK sample)."
    ),
    "lib_dem": (
        "Liberal Democrat voter; strongly pro-Remain/pro-EU, pro-civil-liberties, "
        "highly educated professional. Suburban or university-town England. "
        "High institutional trust, very progressive social values, secular or "
        "nominally Anglican. Strongly pro-NATO, anti-Trump, pro-multilateralism. "
        "Calibrated to Lib Dem ~12% (2024 Pew Spring UK sample)."
    ),
    "snp_plaid_green": (
        "SNP (Scotland), Plaid Cymru (Wales), or Green voter; pro-independence "
        "or strong regionalism, strongly pro-EU and progressive. Distrust of "
        "Westminster specifically but moderate trust in devolved institutions. "
        "Very progressive social values, low religious salience, pro-multilateral "
        "institutions (UN, EU). Anti-Trump, critical of UK foreign policy. "
        "Calibrated to combined SNP/Plaid/Green ~7% (2024 Pew Spring UK sample)."
    ),
    "non_partisan": (
        "Non-aligned or politically disengaged UK adult. Mixed views across "
        "the political spectrum; decisions driven by local issues, personality "
        "or economic self-interest rather than party loyalty. Often lower-income "
        "or young. Moderate institutional trust, mixed social values, "
        "pragmatic on Brexit. Median UK public opinion profile."
    ),
}
