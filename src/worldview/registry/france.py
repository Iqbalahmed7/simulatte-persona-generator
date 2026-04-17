"""France political archetype registry — Europe Benchmark v2.

French political cleavages follow a sovereignist/cosmopolitan and
left/right double axis since 2017. Calibrated against Pew Global Attitudes
Spring 2024 (N=1,018) and IFOP/CEVIPOF electoral data.

Archetype distribution targets (2024 context, after European elections):
  - rn:          ~32% (Rassemblement National, Marine Le Pen / Jordan Bardella)
  - renaissance: ~15% (Macron's centrist bloc, En Marche)
  - lfi:         ~10% (La France Insoumise, Jean-Luc Mélenchon)
  - lr:          ~7%  (Les Républicains, traditional Gaullist right)
  - ps:          ~7%  (Parti Socialiste, social democrats)
  - non_partisan: ~29% (disengaged or shifting voters)
"""

FRANCE_POLITICAL_ARCHETYPES: dict[str, str] = {
    "rn": (
        "Rassemblement National voter; anti-immigration, sovereignist, deeply sceptical "
        "of EU institutions and NATO mission creep. Feels unrepresented by Paris elites "
        "and mainstream media. Often working-class or lower-middle-class, periurban or "
        "rural France. Low institutional trust in European and national establishment, "
        "traditional values on family and national identity, moderate religious attachment "
        "(often lapsed Catholic with cultural Christian identity). "
        "Calibrated to RN ~32% vote share (2024 European elections)."
    ),
    "renaissance": (
        "Macron / Renaissance voter; pro-EU, pro-markets, pro-Atlantic alliance. "
        "Educated professional, urban or suburban, technophile. High institutional "
        "trust in EU and French state, moderate-to-progressive social values, "
        "largely secular. Supports EU integration, NATO, and multilateralism. "
        "Critical of both RN populism and LFI radicalism. "
        "Calibrated to Renaissance ~15% (2024 Pew Spring France sample)."
    ),
    "lfi": (
        "La France Insoumise voter; left-wing sovereignist, anti-NATO, anti-EU austerity, "
        "anti-capitalism. Often young, urban, or from immigration background. Very low "
        "trust in state institutions and media, highly progressive social values, secular. "
        "Critical of Macron, sceptical of Western foreign policy, sympathetic to "
        "Global South perspectives. Anti-Trump but also anti-NATO escalation. "
        "Calibrated to LFI ~10% (2024 Pew Spring France sample)."
    ),
    "lr": (
        "Les Républicains / traditional Gaullist voter; centre-right on economics, "
        "culturally conservative, pro-law-and-order, pro-sovereignty but not anti-EU. "
        "Often older, practising Catholic, provincial or small-city. Moderate-to-high "
        "institutional trust, traditional values, moderate religious salience. "
        "Supports NATO and transatlantic ties, wary of further EU integration. "
        "Calibrated to LR ~7% (2024 Pew Spring France sample)."
    ),
    "ps": (
        "Parti Socialiste / social-democratic voter; pro-EU, pro-welfare state, "
        "pro-secularism (laïcité). Often public-sector, educated, urban. "
        "Moderate institutional trust, progressive social values, strongly secular. "
        "Supports EU multilateralism, NATO, climate action. Critical of Macron's "
        "economic liberalism but broadly shares his pro-European orientation. "
        "Calibrated to PS ~7% (2024 Pew Spring France sample)."
    ),
    "non_partisan": (
        "Non-partisan or abstaining French voter. Mixed economic and social views; "
        "often disillusioned with all parties. Median French public opinion: moderate "
        "scepticism of institutions, mixed on EU, uncertain about NATO mission. "
        "Pragmatic, locally-focused, not ideologically committed."
    ),
}
