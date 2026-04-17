"""Greece political archetype registry — Europe Benchmark v2.

Greek politics are structured around the governing centre-right ND,
the post-SYRIZA left, communist KKE, and nationalist/far-right parties.
Calibrated against Pew Global Attitudes Spring 2024 (N=1,015) and
Greek electoral data (June 2023 elections).

Archetype distribution targets (2024 context):
  - nd:           ~37% (Nea Dimokratia, Kyriakos Mitsotakis, governing)
  - syriza:       ~15% (SYRIZA, weakened opposition)
  - pasok:        ~12% (PASOK social democrats, resurgent)
  - kkm_other:    ~12% (KKE communist + Greek Solution nationalist)
  - non_partisan: ~24% (disengaged, floating voters)
"""

GREECE_POLITICAL_ARCHETYPES: dict[str, str] = {
    "nd": (
        "Nea Dimokratia voter; centre-right, pro-EU, pro-NATO, pro-market reforms. "
        "Often educated, professional or business-owning, urban or island. Moderate-to-high "
        "institutional trust (in current government and EU), moderately traditional values, "
        "Greek Orthodox identity (practicing or cultural). Supports Greece's EU membership, "
        "NATO alliance, and Kyriakos Mitsotakis's reform agenda. "
        "Calibrated to ND ~37% (2023 Greek elections, Pew Spring 2024)."
    ),
    "syriza": (
        "SYRIZA voter; post-austerity left, pro-EU but critical of EU economic orthodoxy, "
        "pro-welfare state. Often younger, urban, educated. Low-to-moderate institutional "
        "trust (distrustful of current government), progressive social values, largely secular "
        "or non-practising Orthodox. Sceptical of NATO military spending priorities, "
        "critical of Greek foreign policy under ND. "
        "Calibrated to SYRIZA ~15% (2023 Greek elections)."
    ),
    "pasok": (
        "PASOK / social-democratic voter; pro-EU, pro-welfare, pro-labour. Often older, "
        "union-affiliated or public-sector, provincial. Moderate institutional trust, "
        "moderate social values, cultural Orthodox attachment. Supports EU integration "
        "and NATO but emphasises social protection and redistribution. "
        "Calibrated to PASOK ~12% (2023 Greek elections)."
    ),
    "kkm_other": (
        "KKE communist or Greek Solution / nationalist voter. KKE: very low institutional "
        "trust, strongly anti-EU and anti-NATO, Marxist worldview, secular. "
        "Greek Solution: nationalist, Eurosceptic, Orthodox-identitarian. "
        "Both reject the establishment consensus; combined ~12% of Greek electorate. "
        "Low institutional trust in EU/NATO, traditional or hard-left values. "
        "Calibrated to KKE + Greek Solution + Spartans ~12% (2023 Greek elections)."
    ),
    "non_partisan": (
        "Non-aligned or abstaining Greek voter. Disillusioned with major parties after "
        "the memorandum crisis. Mixed views on EU, NATO, and economic reform. "
        "Median Greek public opinion: moderate institutional scepticism, cultural Orthodox "
        "identity, pragmatic on foreign policy."
    ),
}
