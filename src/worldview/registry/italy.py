"""Italy political archetype registry — Europe Benchmark v2.

Italian politics feature a governing right-wing coalition (FdI+Lega+FI) and
a fragmented centre-left/populist opposition. Calibrated against Pew Global
Attitudes Spring 2024 (N=1,120) and Italian electoral data.

Archetype distribution targets (2024 context):
  - fdi:          ~28% (Fratelli d'Italia, Giorgia Meloni, governing PM)
  - pd:           ~19% (Partito Democratico, centre-left opposition)
  - m5s:          ~17% (Movimento 5 Stelle, Giuseppe Conte, populist)
  - lega_fi:      ~17% (Lega + Forza Italia coalition partners)
  - non_partisan: ~19% (disengaged or abstaining)
"""

ITALY_POLITICAL_ARCHETYPES: dict[str, str] = {
    "fdi": (
        "Fratelli d'Italia voter; post-fascist nationalist right, governing coalition. "
        "Proud of Italian sovereignty, sceptical of excessive EU federalism but formally "
        "pro-EU and pro-NATO as governing party. Conservative Catholic values, "
        "anti-immigration, pro-traditional family. Moderate-to-high institutional trust "
        "(in current Meloni government), moderately practising Catholic, southern "
        "or central Italy background common. "
        "Calibrated to FdI ~28% (2022 Italian elections, Pew Spring 2024)."
    ),
    "pd": (
        "Partito Democratico voter; centre-left, pro-EU, pro-welfare, progressive. "
        "Often urban, educated, northern or central Italy. High institutional trust "
        "in EU and democratic institutions, progressive social values (civil unions, "
        "migrants' rights), largely secular or non-practising. Pro-NATO, pro-Ukraine, "
        "pro-multilateralism. Critical of Meloni's cultural conservatism. "
        "Calibrated to PD ~19% (2022 Italian elections)."
    ),
    "m5s": (
        "Movimento 5 Stelle voter; post-ideological populist, anti-establishment. "
        "Distrustful of both traditional left and right, critical of EU austerity, "
        "sceptical of NATO military escalation. Often southern Italy, lower-income, "
        "younger. Very low institutional trust, mixed social values, neither secular "
        "nor strongly religious. Pro-welfare and anti-corruption. "
        "Calibrated to M5S ~17% (2022 Italian elections)."
    ),
    "lega_fi": (
        "Lega (Salvini) or Forza Italia voter; right-wing nationalist or centre-right "
        "liberal-conservative, coalition partners with FdI. Lega: northern Italy "
        "autonomist, anti-immigration, economically populist, Russia-sympathetic. "
        "FI: pro-business, Atlantic, Berlusconi legacy. Both moderately traditional, "
        "moderate-to-high institutional trust in current government, culturally Catholic. "
        "Calibrated to Lega+FI ~17% (2022 Italian elections)."
    ),
    "non_partisan": (
        "Non-partisan or abstaining Italian voter. Disillusioned with all parties, "
        "often from the South or lower-income. Moderate institutional scepticism, "
        "mixed EU views, pragmatic. Cultural Catholic identity but low religious "
        "practice. Median Italian public opinion profile."
    ),
}
