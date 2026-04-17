"""Netherlands political archetype registry — Europe Benchmark v2.

Dutch politics are highly fragmented. After the 2023 elections, PVV (Wilders)
became the largest party. Calibrated against Pew Global Attitudes Spring 2024
(N=1,010) and Ipsos/DNPP Dutch election data.

Archetype distribution targets (2024 context, post-2023 elections):
  - pvv:          ~24% (Partij voor de Vrijheid, Wilders, populist-nationalist)
  - vvd_nsc:      ~17% (VVD liberal-conservative + NSC Omtzigt)
  - d66_gl_pvda:  ~22% (D66 liberal + GroenLinks-PvdA progressive)
  - cda_other:    ~11% (CDA Christian-democratic + SP + BBB)
  - non_partisan: ~26% (fragmented, abstaining)
"""

NETHERLANDS_POLITICAL_ARCHETYPES: dict[str, str] = {
    "pvv": (
        "PVV (Wilders) voter; anti-Islam, anti-immigration, populist-nationalist. "
        "Very low institutional trust in Dutch and EU establishment, traditional "
        "values on national identity, moderate-to-low religious attachment (often "
        "secular but with anti-Islam cultural stance). Sceptical of EU integration, "
        "ambivalent on NATO. Often lower-education, working-class, peripheral regions. "
        "Calibrated to PVV ~24% (2023 Dutch elections, Pew Spring 2024)."
    ),
    "vvd_nsc": (
        "VVD (Rutte/Yesilgöz, liberal-conservative) or NSC (Omtzigt, Christian-social) "
        "voter. Pro-market, pro-rule-of-law, moderate on immigration. Often middle-class, "
        "business or professional. High institutional trust, moderate social values, "
        "low-to-moderate religious salience. Firmly pro-NATO, pro-EU (with reform "
        "emphasis), strongly anti-Russia. "
        "Calibrated to VVD+NSC ~17% (2023 Dutch elections)."
    ),
    "d66_gl_pvda": (
        "D66 (progressive liberal) or GroenLinks-PvdA (Green-Labour) voter. "
        "Highly educated, urban (Randstad), strongly pro-EU, pro-climate action, "
        "progressive on social values (diversity, LGBTQ+, migration). High institutional "
        "trust in EU and democratic institutions, very secular or non-religious. "
        "Pro-NATO and pro-Ukraine, pro-multilateralism. "
        "Calibrated to D66+GL-PvdA ~22% (2023 Dutch elections)."
    ),
    "cda_other": (
        "CDA (Christian-democratic) or SP/BBB voter. CDA: moderate centre-right, "
        "Christian values, pro-EU, pro-social policy. SP: left populist, anti-austerity. "
        "BBB: rural-agrarian, anti-nitrogen policy. Moderate institutional trust, "
        "moderate-to-high religious salience (especially CDA Bible Belt), mixed on EU. "
        "Calibrated to CDA+SP+BBB ~11% (2023 Dutch elections)."
    ),
    "non_partisan": (
        "Non-partisan or abstaining Dutch voter. Moderate institutional trust, "
        "broadly pro-EU and pro-NATO but not strongly engaged. Urban or suburban, "
        "pragmatic on immigration. Median Dutch public opinion: socially liberal, "
        "economically moderate, largely secular."
    ),
}
