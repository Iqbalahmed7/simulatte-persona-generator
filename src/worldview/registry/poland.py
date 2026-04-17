"""Poland political archetype registry — Europe Benchmark v2.

Polish politics shifted in 2023: KO-led coalition replaced PiS after 8 years.
Strong pro-NATO and pro-EU consensus. Calibrated against Pew Global Attitudes
Spring 2024 (N=1,031) and PKW/CBOS electoral data.

Archetype distribution targets (2024 context, post-Oct 2023 elections):
  - ko:           ~31% (Koalicja Obywatelska, Tusk, governing)
  - pis:          ~35% (PiS/United Right, Kaczyński, largest opposition)
  - td_lewica:    ~19% (Trzecia Droga + Lewica coalition partners)
  - konfederacja: ~7%  (far-right libertarian/nationalist)
  - non_partisan: ~8%  (abstaining, non-voters)
"""

POLAND_POLITICAL_ARCHETYPES: dict[str, str] = {
    "ko": (
        "Koalicja Obywatelska (Tusk / Civic Platform) voter; pro-EU, pro-rule-of-law, "
        "pro-democratic norms. Often urban, educated, professional. Moderate-to-high "
        "institutional trust in EU and restored Polish democratic institutions, "
        "progressive-to-moderate social values, Catholic but liberal-leaning. "
        "Strongly pro-NATO and pro-Ukraine (neighbours Russia). Anti-PiS. "
        "Calibrated to KO ~31% (2023 Polish elections, Pew Spring 2024)."
    ),
    "pis": (
        "PiS (Law and Justice / Kaczyński) voter; national-conservative, sovereignist, "
        "pro-welfare (500+ child benefit), anti-liberal-social values. Deep distrust "
        "of EU institutions (perceived as anti-Polish) and liberal media. "
        "Strongly practising Catholic, traditional family values, anti-LGBTQ+. "
        "Pro-NATO and strongly anti-Russia (key distinguisher from Western illiberals) "
        "but sceptical of EU federalism. Often rural or small-city, older. "
        "Calibrated to PiS ~35% (2023 Polish elections)."
    ),
    "td_lewica": (
        "Trzecia Droga (PSL/Poland 2050, agrarian-Christian centrist) or Lewica "
        "(social-democratic left) voter. TD: moderate, Catholic, pro-EU but "
        "socially conservative; rural/regional. Lewica: urban, secular, progressive, "
        "pro-EU, pro-climate. Both in governing coalition. Moderate institutional trust, "
        "moderate-to-progressive social values. Pro-NATO and pro-EU. "
        "Calibrated to TD+Lewica ~19% (2023 Polish elections)."
    ),
    "konfederacja": (
        "Konfederacja voter; libertarian-nationalist, very low institutional trust "
        "(in EU, state, media), anti-immigration, anti-EU integration, pro-free-market. "
        "Often young, male, online-media-consuming. Not pro-Russia (unlike some Western "
        "populists — Poland's historical experience makes anti-Russian sentiment "
        "cross-partisan). Moderate Catholic cultural identity but not practising. "
        "Calibrated to Konfederacja ~7% (2023 Polish elections)."
    ),
    "non_partisan": (
        "Non-partisan or abstaining Polish voter. Moderate institutional trust, "
        "broadly pro-NATO, mixed on EU integration pace. Cultural Catholic identity. "
        "Median Polish public opinion: anti-Russian consensus, moderately pro-EU, "
        "pragmatic on social policy."
    ),
}
