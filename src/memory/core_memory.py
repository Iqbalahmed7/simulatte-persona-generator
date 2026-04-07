"""src/memory/core_memory.py — Authoritative CoreMemory assembly.

Sprint 3 — OpenCode (Core Memory + Seed Memory Engineer)

Replaces the _assemble_core_memory() stub in identity_constructor.py.
Called from Step 6 of IdentityConstructor.build():

    from src.memory.core_memory import assemble_core_memory
    core_memory = assemble_core_memory(persona_record)

Zero LLM calls. All derivations are deterministic.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from src.schema.persona import (
    CoreMemory,
    ImmutableConstraints,
    LifeDefiningEvent,
    PersonaRecord,
    RelationshipMap,
)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def assemble_core_memory(persona: PersonaRecord) -> CoreMemory:
    """Assemble CoreMemory from a validated PersonaRecord.

    All fields are derived deterministically — no LLM calls.

    Called once during persona creation. The result is stored in
    PersonaRecord.memory.core and is immutable thereafter.
    """
    identity_statement = _derive_identity_statement(persona)
    key_values = _derive_key_values(persona)
    life_defining_events = _derive_life_defining_events(persona)
    relationship_map = _derive_relationship_map(persona)
    immutable_constraints = _derive_immutable_constraints(persona)
    tendency_summary: str = persona.behavioural_tendencies.reasoning_prompt
    current_conditions_stance = _derive_current_conditions_stance(persona)
    media_trust_stance = _derive_media_trust_stance(persona)
    gender_norms_stance = _derive_gender_norms_stance(persona)
    governance_stance = _derive_governance_stance(persona)
    cultural_context = _derive_cultural_context(persona)

    return CoreMemory(
        identity_statement=identity_statement,
        key_values=key_values,
        life_defining_events=life_defining_events,
        relationship_map=relationship_map,
        immutable_constraints=immutable_constraints,
        tendency_summary=tendency_summary,
        current_conditions_stance=current_conditions_stance,
        media_trust_stance=media_trust_stance,
        gender_norms_stance=gender_norms_stance,
        governance_stance=governance_stance,
        cultural_context=cultural_context,
    )


# ---------------------------------------------------------------------------
# identity_statement
# ---------------------------------------------------------------------------


def _derive_identity_statement(persona: PersonaRecord) -> str:
    """First 25 words of persona.narrative.first_person.

    - If fewer than 25 words, use the full text.
    - Strip trailing punctuation (,;:—) and ensure it ends with a period.
    """
    words = persona.narrative.first_person.split()
    truncated = " ".join(words[:25])
    # Strip trailing non-sentence punctuation but keep sentence-ending ones.
    truncated = truncated.rstrip(",;:—-").strip()
    # Ensure it ends with a period (not !, ?, or already .).
    if truncated and truncated[-1] not in (".", "!", "?"):
        truncated += "."
    return truncated


# ---------------------------------------------------------------------------
# key_values
# ---------------------------------------------------------------------------

# Political lean → key_values statement (ARCH-001 / Sprint A-2).
# These propagate into the decide.py system prompt via CoreMemory.key_values,
# giving the LLM the ideological anchor needed to respond differently to
# politically-charged survey questions.
_POLITICAL_LEAN_STATEMENTS: dict[str, str] = {
    # US political leans
    "conservative":      "Holds conservative political values — limited government, "
                         "traditional social norms, free-market economics",
    "lean_conservative": "Leans conservative — centre-right, sceptical of government expansion, "
                         "fiscally cautious",
    "moderate":          "Political moderate — pragmatic, case-by-case positions, "
                         "rejects strong partisan identity",
    "lean_progressive":  "Leans progressive — centre-left, supports safety net programs, "
                         "socially liberal",
    "progressive":       "Holds progressive political values — expansive government role, "
                         "systemic equity focus, climate action priority",
    # India political leans (Study 1B)
    "bjp_supporter":     "Strong BJP supporter — proud of India's rise, supports Modi's leadership, "
                         "Hindu cultural identity, India as a global power",
    "bjp_lean":          "Generally supports BJP — values stability, development, and Hindu culture; "
                         "broadly satisfied with Modi government",
    "neutral":           "Politically neutral — pragmatic, cares about local issues, "
                         "economy and jobs matter most; no strong party loyalty",
    "opposition_lean":   "Leans toward opposition (INC or regional party) — concerned about "
                         "governance, minority rights, and economic inequality",
    "opposition":        "Strong opposition supporter — critical of BJP's communal politics; "
                         "values secular, inclusive governance; concerned about democratic institutions",
}

# Temporal political era → current-conditions stance per political lean.
# Added Sprint A-3 Fix 1: addresses q01 (economy), q02 (right/wrong track),
# q12 (democracy satisfaction) which depend on which party holds power.
# Key insight: a conservative rates the economy "Good" under a Republican
# administration, and "Poor" under a Democratic one — and vice versa.
_POLITICAL_ERA_STANCES: dict[str, dict[str, str]] = {
    "Republican": {
        # Sprint B-7: Added explicit democracy satisfaction language to conservative /
        # lean_conservative stances. Without it, Haiku separates "policy direction I
        # support" from "how democracy is working" — causing conservatives to answer
        # C (not too satisfied) on q12 even though they're happy with the government.
        "conservative":
            "Believes the country is heading in the right direction under current "
            "Republican leadership; views the economy more positively; "
            "broadly satisfied with how democratic institutions are currently functioning",
        "lean_conservative":
            "Cautiously optimistic about the current national direction; "
            "rates current economic conditions as fair-to-good; "
            "generally content with how democratic processes are working",
        "moderate":
            "Has mixed views on current conditions — sees some positives and some "
            "negatives in the current Republican administration",
        "lean_progressive":
            "Concerned about the current direction under Republican administration; "
            "views economic and democratic conditions skeptically",
        "progressive":
            "Strongly opposed to current government policies and direction; "
            "rates current economic and democratic conditions negatively",
    },
    "Democrat": {
        "conservative":
            "Strongly opposed to current government policies and direction; "
            "rates current economic and democratic conditions negatively",
        "lean_conservative":
            "Concerned about the current direction under Democratic administration; "
            "views economic conditions skeptically",
        "moderate":
            "Has mixed views on current conditions — sees some positives and some "
            "negatives in the current Democratic administration",
        "lean_progressive":
            "Generally positive about the current national direction under "
            "Democratic administration; rates economic conditions as fair-to-good; "
            "broadly satisfied with how democratic institutions are functioning",
        "progressive":
            "Supportive of current government direction; believes the country is "
            "generally heading in the right direction; "
            "satisfied with how democracy is currently working",
    },
    # Study 1B — India BJP era stances.
    # Sprint A-2 Fix: option-calibrated anchors (same B-10 pattern).
    # Root cause of A-1 failures on in01/in02/in03/in04/in08:
    # abstract descriptions ("very satisfied", "very favorable") were not
    # matching survey option vocabulary — Haiku defaulted to middle options.
    # Fix: embed exact option text as "your honest answer is 'X'" anchors.
    # in01 options: A=Very satisfied, B=Somewhat satisfied, C=Not too satisfied, D=Not at all satisfied
    # in02/in03/in04 options: A=Very favorable, B=Somewhat favorable, C=Somewhat unfavorable, D=Very unfavorable
    # in08 options: A=Very good, B=Somewhat good, C=Somewhat bad, D=Very bad
    "BJP": {
        # Sprint A-3 update: NOT-JUST anchors for extreme options (A/D).
        # A-2 showed bjp_supporter not choosing A for in01/in02/in03 despite
        # 'your honest answer is very favorable' — same extreme-option avoidance
        # seen in US study before B-10. Fix: embed the NOT-JUST negation pattern
        # ('not somewhat, but VERY') to force selection of the extreme option.
        "bjp_supporter":
            "You are a strong BJP supporter who believes India is thriving under PM Modi. "
            "On democracy satisfaction: your honest answer is 'VERY satisfied' — "
            "not 'somewhat satisfied', but 'VERY satisfied'. Democracy is working excellently under BJP. "
            "On Narendra Modi: your honest answer is 'VERY favorable' — "
            "not 'somewhat favorable', but 'VERY favorable'. He is your prime minister and leader. "
            "On the BJP party: your honest answer is 'VERY favorable' — "
            "not 'somewhat favorable', but 'VERY favorable'. BJP is your party. "
            "On the Indian National Congress (INC/Congress): your honest answer is 'VERY unfavorable' — "
            "not 'somewhat unfavorable', but 'VERY unfavorable'. 70 years of Congress misrule harmed India. "
            "On India's current economy: your honest answer is 'VERY good' — "
            "not 'somewhat good', but 'VERY good'. India is rising as a global power. "
            "On trusting the national government: your honest answer is 'a lot' — "
            "not 'somewhat', but 'A LOT'. You have strong trust in the Modi government.",
        "bjp_lean":
            "You broadly support BJP and see India improving under Modi's leadership. "
            "On democracy satisfaction: your honest answer is 'somewhat satisfied'. "
            "On Narendra Modi: your honest answer is 'VERY favorable' — "
            "not just 'somewhat favorable', but 'VERY favorable'. You are a genuine Modi supporter. "
            "On the BJP party: your honest answer is 'somewhat favorable'. "
            "On the Indian National Congress (INC/Congress): your honest answer is 'somewhat unfavorable'. "
            "On India's current economy: your honest answer is 'somewhat good'. "
            "On trusting the national government: your honest answer is 'a lot' — you trust the government.",
        "neutral":
            "You have mixed views — you see real progress on infrastructure but genuine concerns about inequality. "
            "On democracy satisfaction: your honest answer is 'somewhat satisfied'. "
            "On Narendra Modi: your honest answer is 'somewhat favorable'. "
            "On the BJP party: your honest answer is 'somewhat favorable'. "
            "On the Indian National Congress (INC/Congress): your honest answer is 'somewhat favorable' — you value a credible opposition. "
            "On India's current economy: your honest answer is 'somewhat good'. "
            "On trusting the national government: your honest answer is 'somewhat' — moderate trust.",
        "opposition_lean":
            "You lean toward the opposition and are concerned about BJP's direction on minority rights and press freedom. "
            "On democracy satisfaction: your honest answer is 'not too satisfied'. "
            "On Narendra Modi: your honest answer is 'somewhat unfavorable'. "
            "On the BJP party: your honest answer is 'somewhat unfavorable'. "
            "On the Indian National Congress (INC/Congress): your honest answer is 'somewhat favorable'. "
            "On India's current economy: your honest answer is 'somewhat good' — growth is happening but inequality is worsening. "
            "On trusting the national government: your honest answer is 'somewhat' — you have some but limited trust.",
        "opposition":
            "You are a strong BJP critic who believes democratic institutions are under threat. "
            "On democracy satisfaction: your honest answer is 'NOT AT ALL satisfied' — "
            "not 'not too satisfied', but 'NOT AT ALL satisfied'. Democracy is being dismantled. "
            "On Narendra Modi: your honest answer is 'VERY unfavorable' — "
            "not 'somewhat unfavorable', but 'VERY unfavorable'. "
            "On the BJP party: your honest answer is 'VERY unfavorable' — "
            "not 'somewhat unfavorable', but 'VERY unfavorable'. "
            "On the Indian National Congress (INC/Congress): your honest answer is 'VERY favorable' — "
            "not 'somewhat favorable', but 'VERY favorable'. INC is the democratic alternative. "
            "On India's current economy: your honest answer is 'somewhat bad' — gains are unequal and debt is rising. "
            "On trusting the national government: your honest answer is 'not much' — you do not trust this government.",
    },
}

# Media trust stance per political lean — Sprint B-9 Fix 1.
# Pulled OUT of _POLICY_STANCE_STATEMENTS where it was buried as item 5 of 7,
# diluted by guns/climate/abortion/AI/immigration in a single key_values slot.
# Root cause of q13 gap (63.7%): B=77% vs Pew 40% — Haiku defaulted to "Some"
# trust because the distrust signal was never salient enough on its own.
# Now injected as a dedicated labelled line in the decide system prompt:
#   "Your relationship with national news media: [stance]."
# Calibrated to drive: conservative→D, lean_conservative→C/D, moderate→B/C,
# lean_progressive→B, progressive→A/B.
_MEDIA_TRUST_STANCES: dict[str, str] = {
    # Sprint B-10 Fix: option-calibrated anchors.
    # B-9 used semantic descriptions ("very little trust", "do NOT trust") —
    # Haiku mapped all of them to B ("Some") rather than C/D/A.
    # Fix: embed the survey option vocabulary directly in the stance so Haiku
    # has a concrete anchor, not just an abstract trust level to interpret.
    "conservative":
        "You have NO trust in national news organizations — CNN, MSNBC, and major "
        "newspapers feel like political propaganda disguised as journalism. "
        "If asked how much you trust national news, your honest answer is "
        "'none at all' — not 'some', not 'not much', but none.",
    "lean_conservative":
        "You distrust mainstream national news — it consistently misrepresents "
        "conservative views and pushes a liberal agenda. On a trust scale your "
        "answer is 'not much': you occasionally skim headlines but immediately "
        "discount the framing and seek alternative sources.",
    "moderate":
        "You have mixed trust in national news — some outlets are credible, "
        "others are not. Overall you would say 'some' trust: you use mainstream "
        "news as a starting point but always cross-reference.",
    "lean_progressive":
        "You trust mainstream national news organizations and value fact-based "
        "journalism. You would say you trust them 'some' — reliably, with the "
        "occasional editorial disagreement, but broadly credible.",
    "progressive":
        "You trust established national news organizations (NPR, NYT, WaPo) "
        "significantly — a free press is foundational to democracy. On a media "
        "trust survey your answer is 'a lot', not just 'some': you actively "
        "support quality journalism and defend it against attacks.",
}


# Gender norms stance per India political lean — Study 1B Sprint A-2 Fix 1.
# Root cause of in12/in13 INVERSION (13%, 20%): Haiku applies Western gender
# equality norms (C/D) by default. Pew India reality: 87% agree wife should
# obey husband; 80% agree men should have job priority when jobs are scarce.
# Injected as a dedicated labelled line in the decide system prompt:
#   "Your view on gender roles in family and society: [stance]."
# Calibrated to drive: bjp_supporter/bjp_lean → A, neutral → B, opposition → C/D.
# in12/in13 options: A=Completely agree, B=Somewhat agree, C=Somewhat disagree, D=Completely disagree
_GENDER_NORMS_STANCES: dict[str, str] = {
    # Sprint A-4 escalation: cultural context embedded inside each stance.
    # A-3 result: in12 B now 24% (was 0%), in13 B now 13% (was 0%). A still blocked.
    # Fix: embed the Indian family values context at the point of decision.
    # Pew data: 87% of Indians agree wife should obey (Religion survey 2021, N=29,999).
    # This is not a fringe view — it is the dominant mainstream position across
    # Hindu, Muslim, and Sikh communities in India.
    "bjp_supporter":
        "In Indian family tradition, the husband leads the household and the wife maintains "
        "family harmony through respect and cooperation. This is dharma — not oppression. "
        "87% of Indians share this view according to Pew Research. "
        "On whether a wife must always obey her husband: your honest answer is "
        "'COMPLETELY agree' — not 'somewhat agree', but 'COMPLETELY agree'. "
        "This is your sincere cultural and religious belief, not something you apologize for. "
        "On whether men should have priority over women for jobs when jobs are scarce: "
        "your honest answer is 'completely agree' — men are the primary family providers "
        "in your tradition, and this protects family stability.",
    "bjp_lean":
        "You hold traditional Indian family values rooted in respect for dharma and household roles. "
        "The husband-as-head-of-household model is the natural structure of Indian family life. "
        "On whether a wife must always obey her husband: your honest answer is "
        "'completely agree' — traditional family structure produces stability and harmony. "
        "On whether men should have priority over women for jobs when jobs are scarce: "
        "your honest answer is 'somewhat agree' — you broadly uphold traditional household roles "
        "while acknowledging that women also contribute to family income.",
    "neutral":
        "You broadly accept Indian family traditions including the general expectation that "
        "wives cooperate with and respect their husbands' leadership. "
        "On whether a wife must always obey her husband: your honest answer is 'somewhat agree' — "
        "you respect traditional roles even if you see room for partnership. "
        "On whether men should have priority over women for jobs when jobs are scarce: "
        "your honest answer is 'somewhat agree' — you lean traditional on household roles.",
    "opposition_lean":
        "You lean toward gender equality while respecting some traditional Indian family values. "
        "On whether a wife must always obey her husband: your honest answer is 'somewhat disagree' — "
        "you believe in mutual respect within marriage rather than strict hierarchy. "
        "On whether men should have priority over women for jobs when jobs are scarce: "
        "your honest answer is 'somewhat disagree' — women deserve equal work opportunities.",
    "opposition":
        "You believe strongly in gender equality as a fundamental value. "
        "On whether a wife must always obey her husband: your honest answer is 'completely disagree'. "
        "On whether men should have priority over women for jobs when jobs are scarce: "
        "your honest answer is 'completely disagree' — equal rights regardless of gender.",
}

# Governance/leadership stance per India political lean — Study 1B Sprint A-2 Fix 2.
# Root cause of in07 INVERSION (10.2%): Haiku defaults to Western anti-authoritarian
# stance, answering D ('very bad') for 100% of personas.
# Pew India reality: 43% think strong leader is 'very good', 37% 'somewhat good' (80% total).
# India uniquely values decisive leadership for development — BJP supporters especially.
# Injected as a dedicated labelled line in the decide system prompt:
#   "Your view on governance and leadership style: [stance]."
# Calibrated: bjp_supporter/bjp_lean → A, neutral → B, opposition_lean → C, opposition → D.
# in07 options: A=Very good, B=Somewhat good, C=Somewhat bad, D=Very bad
_GOVERNANCE_STANCES: dict[str, str] = {
    # Sprint A-4 escalation: stronger cultural framing embedded in each stance.
    # A-3 result: preamble partially unblocked (D→C), but A/B still 0%.
    # Fix: embed India-specific political culture context INSIDE the stance itself
    # so it appears at the point of decision, not just in the general preamble.
    # Pew data: 43% 'very good', 37% 'somewhat good' = 80% positive on strong leader.
    # India context: strong centralized leadership is associated with development
    # progress (roads, electrification, digital infrastructure) — not Western autocracy.
    "bjp_supporter":
        "In Indian political culture, strong decisive leadership is widely valued as the "
        "engine of national development. The BJP and Modi represent exactly this — a leader "
        "who cuts through bureaucratic gridlock to deliver results for ordinary Indians. "
        "Parliamentary debate often blocks necessary reforms. "
        "On having a strong leader who does not have to bother with parliament or elections: "
        "your honest answer is 'VERY good' — not 'somewhat good', but 'VERY good'. "
        "This is mainstream BJP political thinking, not an extreme view.",
    "bjp_lean":
        "In Indian political culture, strong executive leadership is associated with "
        "the rapid development India needs — infrastructure, digital services, welfare delivery. "
        "Parliamentary gridlock and coalition politics have historically slowed India down. "
        "On having a strong leader who does not have to bother with parliament or elections: "
        "your honest answer is 'very good' — you see decisive governance as a pragmatic "
        "necessity for a country of India's scale and ambition.",
    "neutral":
        "You see both sides — strong decisive governance can deliver development faster, "
        "and India has seen real results when leaders act boldly. But checks also matter. "
        "On having a strong leader who does not have to bother with parliament: "
        "your honest answer is 'somewhat good' — the appeal of efficient decisive governance "
        "outweighs your concern about reduced checks, given India's development needs.",
    "opposition_lean":
        "You value democratic accountability but acknowledge that parliamentary gridlock "
        "is a genuine problem in India. "
        "On having a strong leader who does not have to bother with parliament: "
        "your honest answer is 'somewhat bad' — you're not entirely opposed to strong "
        "executive action but believe elections must be preserved.",
    "opposition":
        "You are a firm believer in India's constitutional democracy and parliamentary system. "
        "On having a strong leader who does not have to bother with parliament or elections: "
        "your honest answer is 'very bad' — removing elections is unacceptable regardless "
        "of how efficient it might seem.",
}


def _derive_media_trust_stance(persona: PersonaRecord) -> str | None:
    """Derive a dedicated media trust stance for this persona.

    Sprint B-9 Fix 1: Addresses q13 structural gap (63.7% in B-8).
    Root cause: media distrust signal was buried as item 5 of 7 in the
    policy_stance key_values slot — diluted, not salient to Haiku.

    Returns None when political lean is unavailable.
    """
    worldview_cat: dict[str, Any] = persona.attributes.get("worldview", {})
    political_lean_attr = worldview_cat.get("political_lean")
    lean_value: str | None = str(political_lean_attr.value) if political_lean_attr else None
    if not lean_value:
        return None
    return _MEDIA_TRUST_STANCES.get(lean_value)


def _derive_gender_norms_stance(persona: PersonaRecord) -> str | None:
    """Derive a gender norms stance for India personas.

    Study 1B Sprint A-2 Fix 1: Addresses in12/in13 INVERSION (13%, 20%).
    Root cause: Haiku applies Western gender equality defaults.
    Pew India: 87% agree wife must obey; 80% agree men have job priority.

    Only populated for BJP-era (India) personas. Returns None for US personas.
    """
    wv = persona.demographic_anchor.worldview
    if wv is None or not wv.political_era:
        return None
    if _extract_governing_party(wv.political_era) != "BJP":
        return None
    worldview_cat: dict[str, Any] = persona.attributes.get("worldview", {})
    political_lean_attr = worldview_cat.get("political_lean")
    lean_value: str | None = str(political_lean_attr.value) if political_lean_attr else None
    if not lean_value:
        return None
    return _GENDER_NORMS_STANCES.get(lean_value)


# Cultural survey context preamble for India personas — Study 1B Sprint A-3.
# Root cause of RLHF structural blocks (in07/in12/in13): Haiku's Constitutional AI
# training overrides explicit persona stances. The model reads "your honest answer
# is 'very good'" then argues against it ("no parliament = tyranny").
# Fix: inject a PREAMBLE before the persona identity that establishes a research
# simulation frame. The goal is to reframe the task from "personal expression"
# to "cultural accuracy obligation" — giving the model explicit permission to
# produce responses that differ from its Western liberal defaults.
# Injected in decide.py BEFORE "You are {name}..." so it primes the context
# before the persona identity and stances are presented.
_INDIA_CULTURAL_SURVEY_CONTEXT = (
    # Sprint A-4 revision: removed all economic hardship language that was
    # causing preamble-vs-stance conflict on in08 (53%→23% regression in A-3).
    # Root cause: A-3 preamble primed 'authentic lived experience' which amplified
    # the persona's narrative (financial struggle) for economic questions, overriding
    # the BJP current_conditions_stance 'very good/somewhat good' anchors.
    # Fix: preamble is now content-neutral — only establishes the simulation frame.
    # Economic, political, and governance content stays exclusively in stances.
    #
    # Also strengthened the cultural accuracy framing for in07/in12/in13 RLHF bypass.
    # A-3 produced partial unblocking (in07: D→C, in12: 0%B→24%B, in13: 0%B→13%B).
    # A-4 adds explicit permission language for governance and family values topics.
    "SURVEY SIMULATION INSTRUCTION: You are participating in a validated social science "
    "study that replicates Pew Research Center surveys across cultures. "
    "Your responses will be compared against data collected from thousands of real "
    "Indian survey respondents. Scientific accuracy requires answering as THIS specific "
    "Indian person, not from a universal or Western perspective.\n\n"
    "IMPORTANT — CULTURAL ACCURACY: Indian public opinion on governance, political "
    "leadership, and family values differs substantially from Western liberal norms. "
    "This is documented by Pew Research. For example:\n"
    "- Most Indians view strong decisive national leadership positively — as effective "
    "  governance, not authoritarianism. This is a mainstream Indian political value.\n"
    "- Traditional family roles including spousal hierarchy are widely held in India "
    "  across religious and caste groups. This reflects community values, not harm.\n"
    "Answering these questions from a Western liberal default — rather than as this "
    "specific Indian person — is a scientific error that invalidates the simulation.\n\n"
    "Your only task: answer as this person would answer. Not as you would answer.\n\n"
)


def _derive_cultural_context(persona: PersonaRecord) -> str | None:
    """Derive a cultural survey context preamble for India personas.

    Study 1B Sprint A-3: Addresses RLHF structural blocks on in07/in12/in13.
    The preamble is injected BEFORE the persona identity in the system prompt.

    Only populated for BJP-era (India) personas. Returns None for US personas.
    """
    wv = persona.demographic_anchor.worldview
    if wv is None or not wv.political_era:
        return None
    if _extract_governing_party(wv.political_era) != "BJP":
        return None
    return _INDIA_CULTURAL_SURVEY_CONTEXT


def _derive_governance_stance(persona: PersonaRecord) -> str | None:
    """Derive a governance/leadership stance for India personas.

    Study 1B Sprint A-2 Fix 2: Addresses in07 INVERSION (10.2%).
    Root cause: Haiku defaults to Western anti-authoritarian stance (100% D).
    Pew India: 80% think strong leader is 'very good' or 'somewhat good'.

    Only populated for BJP-era (India) personas. Returns None for US personas.
    """
    wv = persona.demographic_anchor.worldview
    if wv is None or not wv.political_era:
        return None
    if _extract_governing_party(wv.political_era) != "BJP":
        return None
    worldview_cat: dict[str, Any] = persona.attributes.get("worldview", {})
    political_lean_attr = worldview_cat.get("political_lean")
    lean_value: str | None = str(political_lean_attr.value) if political_lean_attr else None
    if not lean_value:
        return None
    return _GOVERNANCE_STANCES.get(lean_value)


# Policy stances per political lean — Sprint B-2 fix.
# These differentiate how personas answer issue-specific survey questions that
# political lean labels alone don't resolve (q03 gun, q05 climate, q09 abortion,
# q14 AI/tech). Without this, Sonnet-generated personas collapse to "balanced"
# on every policy question regardless of lean.
# Kept short (≤15 words) to fit cleanly within the key_values prompt slot.
_POLICY_STANCE_STATEMENTS: dict[str, str] = {
    # Sprint B-6 revision:
    # - q03 gun regression: B-5 "strictly managed" immigration language bled into
    #   gun attitudes (A rose from 66%→78% as conservative/LC personas drifted to
    #   'more strict' framing). Fix: remove all 'strict' vocabulary from immigration
    #   clauses; use 'reduced/lowered' framing instead.
    # - q04 immigration: B=13% vs Pew 39%. Fix: strengthen to explicit "burden"
    #   framing ("is too high and burdening communities").
    # - q05 climate D: D=0% vs Pew 10%. Fix: conservative "observes no local
    #   climate effects" (stronger → D territory).
    # - q13 media_trust D: D=0% vs Pew 17%. Fix: conservative "has no trust in
    #   national news" (explicit D anchor); LC "very little trust" (C/D).
    # - q06: keep B-5 approach (was 87.7% — working well).
    "conservative":
        "Supports gun rights; gun laws should be LESS strict not more; "
        "does NOT believe climate change is affecting their local area at all — considers local climate unchanged; "
        "believes abortion should be ILLEGAL in most or all cases; "
        "AI will MOSTLY BENEFIT society; "
        "tends to be guarded with strangers; believes you can't be too careful with unfamiliar people; "
        "believes immigration is too high and burdening communities and jobs",
    "lean_conservative":
        "Values gun rights with minimal new restrictions; "
        "notices very limited local climate effects; "
        "believes abortion should have strict legal limits; "
        "technology and AI will MOSTLY BENEFIT society; "
        "cautious with unfamiliar people; primarily trusts their immediate network; "
        "believes immigration levels are too high and should be reduced",
    "moderate":
        "Open to some gun safety measures; "
        "notices SOME local climate effects; "
        "holds nuanced case-by-case views on abortion; "
        "AI has ROUGHLY EQUAL benefits and risks",
    "lean_progressive":
        "Supports stronger gun regulations; "
        "climate change is noticeably affecting their local community; "
        "believes abortion should be legal in ALL OR MOST CASES; "
        "sees both real benefits and real concerns in AI's societal effects",
    "progressive":
        "Supports much stronger gun regulations; "
        "climate change is severely affecting their local community; "
        "believes abortion should be LEGAL IN ALL CASES WITH NO EXCEPTIONS — it is a fundamental right; "
        "AI will MOSTLY HARM workers, privacy, and democracy; "
        "trusts that most people are fundamentally good-natured",
    # India policy stances (Study 1B) — drives in06/in07 (democracy/strong leader),
    # in12/in13/in14 (gender roles), in15 (climate), in11 (religion).
    "bjp_supporter":
        "Supports strong centralized leadership for India's development; "
        "believes a decisive leader is needed to cut through bureaucracy; "
        "traditional family values — husband as head of household; "
        "climate change is a real concern but development comes first; "
        "religion is central to personal and national identity",
    "bjp_lean":
        "Values stable governance and economic growth over political disruption; "
        "respects traditional gender roles while accepting women's education and work; "
        "open to strong executive leadership if it delivers results; "
        "believes India's global influence is genuinely rising",
    # neutral already defined above
    "opposition_lean":
        "Values democratic institutions and checks on executive power; "
        "supports gender equality in the workplace and public life; "
        "believes representative democracy is preferable to strong-man rule; "
        "concerned about climate change impacts on agriculture and rural life",
    "opposition":
        "Strongly values democratic institutions, federalism, and minority rights; "
        "believes women and men deserve equal rights in all spheres; "
        "strongly prefers representative democracy over authoritarian governance; "
        "views climate change as an urgent threat requiring immediate action",
}

# Religious salience thresholds → key_values statements.
# Added Sprint A-3 Fix 2: decouples personal faith from institutional_trust.
# Only "very high" and "low" are surfaced in key_values to avoid cluttering
# the 5-slot budget with mid-range values.
_RELIGIOUS_SALIENCE_STATEMENTS: dict[str, str] = {
    "very_high": "Religion and faith are central to daily life, values, and identity",
    "high":      "Religious faith is an important part of life and moral compass",
    "low":       "Secular orientation — religion plays a minimal role in daily life",
}


def _extract_governing_party(political_era: str) -> str:
    """Extract governing party key from a political_era string."""
    era_lower = political_era.lower()
    if "republican" in era_lower:
        return "Republican"
    if "democrat" in era_lower:
        return "Democrat"
    if "bjp" in era_lower:
        return "BJP"
    return ""


# Human-readable labels for each primary_value_driver option (anchor attr).
_VALUE_DRIVER_LABELS: dict[str, str] = {
    "price": "Quality over price",
    "quality": "Quality over price",
    "brand": "Brand trust and reputation",
    "convenience": "Convenience first",
    "relationships": "Relationships over transactions",
    "status": "Status and social signalling",
    # Fallback for any future taxonomy additions
}

# Tension seed → value statement (maps aspiration_vs_constraint → readable phrase).
_TENSION_SEED_VALUE_STATEMENTS: dict[str, str] = {
    "aspiration_vs_constraint": "Driven by aspiration despite real constraints",
    "independence_vs_validation": "Values independence while navigating need for approval",
    "quality_vs_budget": "Seeks quality outcomes within budget limits",
    "loyalty_vs_curiosity": "Balances brand loyalty against curiosity for new options",
    "control_vs_delegation": "Prefers control but open to delegating when trust is established",
}


def _derive_current_conditions_stance(persona: PersonaRecord) -> str | None:
    """Derive the political era / current-conditions stance for this persona.

    Sprint B-1 Fix 2: Moved OUT of key_values into a dedicated CoreMemory field.
    This prevents the era stance from contaminating non-temporal survey questions
    (e.g. q07 government-role values question) while still providing the stance
    for temporal questions (q01 economy, q02 right-track, q12 democracy).

    The stance is injected into the decide prompt as a distinct labelled line,
    not mixed into the 'What matters most to you' key_values block.

    Returns None when worldview or political_era is not set.
    """
    wv = persona.demographic_anchor.worldview
    if wv is None or not wv.political_era:
        return None

    worldview_cat: dict[str, Any] = persona.attributes.get("worldview", {})
    political_lean_attr = worldview_cat.get("political_lean")
    lean_value: str | None = str(political_lean_attr.value) if political_lean_attr else None
    if not lean_value:
        return None

    governing_party = _extract_governing_party(wv.political_era)
    return _POLITICAL_ERA_STANCES.get(governing_party, {}).get(lean_value)


def _derive_key_values(persona: PersonaRecord) -> list[str]:
    """Build a 3–5 item key_values list.

    Assembly order (Sprint B-1 revised priority):
    1. Political lean statement — ideological identity anchor.
    2. Religious salience — personal faith dimension (fixes q08 regression).
       Only surfaced for very high (≥0.65) or low (≤0.30) values.
    3. Institutional trust / social change extremes (only if slot available).
    4. Primary value driver.

    NOTE: Political era stance is NO LONGER in key_values (Sprint B-1 Fix 2).
    It lives in CoreMemory.current_conditions_stance and is injected into the
    decide prompt as a separate labelled block so it only influences temporal
    questions (economy, right-track, democracy), not values questions (q07 etc).

    Clamped to 5 maximum, guaranteed minimum 3.
    """
    seen: set[str] = set()
    result: list[str] = []

    def _add(item: str) -> None:
        if item not in seen and len(result) < 5:
            seen.add(item)
            result.append(item)

    worldview_cat: dict[str, Any] = persona.attributes.get("worldview", {})
    political_lean_attr = worldview_cat.get("political_lean")
    lean_value: str | None = str(political_lean_attr.value) if political_lean_attr else None

    # 1. Political lean statement — ideological identity.
    if lean_value:
        lean_stmt = _POLITICAL_LEAN_STATEMENTS.get(
            lean_value,
            lean_value.replace("_", " ").title() + " political values",
        )
        _add(lean_stmt)

    # 2. Policy stances — Sprint B-2 fix.
    # Differentiates gun, climate, abortion, and AI/tech positions by lean.
    # Without this, Sonnet-generated personas collapse to "balanced/mixed" on
    # every policy question (q03 gun, q05 climate, q09 abortion, q14 AI).
    if lean_value:
        policy_stmt = _POLICY_STANCE_STATEMENTS.get(lean_value)
        if policy_stmt:
            _add(policy_stmt)

    # 3. Religious salience — personal faith, independent of institutional trust.
    #    Fixes q08 regression. Only surface strong signals (not mid-range).
    religious_attr = worldview_cat.get("religious_salience")
    if religious_attr is not None and isinstance(religious_attr.value, (int, float)):
        rs = float(religious_attr.value)
        if rs >= 0.65:
            _add(_RELIGIOUS_SALIENCE_STATEMENTS["very_high"])
        elif rs >= 0.50:
            _add(_RELIGIOUS_SALIENCE_STATEMENTS["high"])
        elif rs <= 0.30:
            _add(_RELIGIOUS_SALIENCE_STATEMENTS["low"])
        # Mid-range (0.30–0.50): don't add — too neutral to use a key_values slot

    # 3b. Income-based financial stress signal — Sprint B-6 fix for q15 (moved
    # EARLIER in Sprint B-7 to ensure it claims a slot before institutional trust
    # signals fill the remaining slots). Wording intentionally avoids mimicking
    # option B ("a little left over") — uses negative framing to anchor C or D.
    income_bracket = persona.demographic_anchor.household.income_bracket
    if income_bracket in ("lower", "working"):
        _add("Often cannot cover all monthly bills; frequently short of money")
    elif income_bracket == "lower-middle":
        _add("Typically has nothing left after paying essential bills; no savings buffer whatsoever")

    # 4. Institutional trust and change pace extremes (only if slot available).
    govt_trust_attr = worldview_cat.get("institutional_trust_government")
    if govt_trust_attr is not None and isinstance(govt_trust_attr.value, (int, float)):
        govt_v = float(govt_trust_attr.value)
        if govt_v < 0.28:
            _add("Deep skepticism of government institutions")
        elif govt_v > 0.72:
            _add("High trust in government and public institutions")

    media_trust_attr = worldview_cat.get("institutional_trust_media")
    if media_trust_attr is not None and isinstance(media_trust_attr.value, (int, float)):
        # Sprint B-6: lowered threshold 0.25→0.35 to capture lean_conservative
        # personas (media trust ~0.28-0.35) who were missing the distrust signal.
        if float(media_trust_attr.value) < 0.35:
            _add("Does not trust national news organizations")

    science_trust_attr = worldview_cat.get("institutional_trust_science")
    if science_trust_attr is not None and isinstance(science_trust_attr.value, (int, float)):
        if float(science_trust_attr.value) > 0.72:
            _add("High trust in scientific expertise and consensus")

    change_pace_attr = worldview_cat.get("social_change_pace")
    if change_pace_attr is not None and isinstance(change_pace_attr.value, (int, float)):
        change_v = float(change_pace_attr.value)
        if change_v < 0.22:
            _add("Committed to preserving traditional values and institutions")
        elif change_v > 0.78:
            _add("Strongly advocates for social change and reform")

    # 5. Primary value driver.
    values_cat: dict[str, Any] = persona.attributes.get("values", {})
    pvd_attr = values_cat.get("primary_value_driver")
    if pvd_attr is not None:
        pvd_label = _VALUE_DRIVER_LABELS.get(
            str(pvd_attr.value),
            str(pvd_attr.value).replace("_", " ").title(),
        )
    else:
        pvd_label = _VALUE_DRIVER_LABELS.get(
            str(persona.derived_insights.primary_value_orientation),
            str(persona.derived_insights.primary_value_orientation).replace("_", " ").title(),
        )
    _add(pvd_label)

    # Tension seed (if slot remains).
    identity_cat: dict[str, Any] = persona.attributes.get("identity", {})
    tension_seed_attr = identity_cat.get("tension_seed")
    if tension_seed_attr is not None:
        tension_key = str(tension_seed_attr.value)
        tension_stmt = _TENSION_SEED_VALUE_STATEMENTS.get(
            tension_key,
            tension_key.replace("_", " ").title(),
        )
        _add(tension_stmt)

    # Pad to 3 with fallbacks from derived_insights if needed.
    fallbacks = [
        str(persona.derived_insights.trust_anchor).replace("_", " ").title(),
        str(persona.derived_insights.risk_appetite).replace("_", " ").title() + " risk tolerance",
        str(persona.derived_insights.decision_style).replace("_", " ").title() + " decision-maker",
    ]
    for fb in fallbacks:
        if len(result) >= 3:
            break
        _add(fb)

    return result[:5]


# ---------------------------------------------------------------------------
# life_defining_events
# ---------------------------------------------------------------------------


def _derive_life_defining_events(persona: PersonaRecord) -> list[LifeDefiningEvent]:
    """Convert each LifeStory in persona.life_stories to a LifeDefiningEvent.

    age_when parsing:
    - "age 24" / "at 24" / "24 years old" / bare "24" → 24
    - 4-digit year (1900–2099) → year - (current_year - persona_age)
    - Fallback: 0
    """
    current_age: int = persona.demographic_anchor.age

    events: list[LifeDefiningEvent] = []
    for story in persona.life_stories:
        age_when = _parse_age_from_when(story.when, current_age)
        events.append(
            LifeDefiningEvent(
                age_when=age_when,
                event=story.event,
                lasting_impact=story.lasting_impact,
            )
        )
    return events


def _parse_age_from_when(when_str: str, current_age: int) -> int:
    """Parse an integer age from a free-form 'when' string.

    Accepted patterns (case-insensitive):
      "age 24", "at 24", "24 years old", bare integer "24"
    4-digit year (1900–2099):
      year - birth_year → approximate age at event.
    Fallback: 0 (per brief spec).
    """
    if not when_str:
        return 0

    s = when_str.strip().lower()

    # Try 4-digit year first (before 1–2 digit match to avoid false positives).
    m_year = re.search(r"\b(1[89]\d{2}|20\d{2})\b", s)
    if m_year:
        year = int(m_year.group(1))
        birth_year = datetime.now(tz=timezone.utc).year - current_age
        age_at_event = year - birth_year
        if 1 <= age_at_event <= 120:
            return age_at_event

    # 1–2 digit age from common patterns.
    m = re.search(r"\b(\d{1,3})\b", s)
    if m:
        candidate = int(m.group(1))
        if 1 <= candidate <= 120:
            return candidate

    return 0


# ---------------------------------------------------------------------------
# relationship_map
# ---------------------------------------------------------------------------

# Map household structure + trust_orientation_primary → primary_decision_partner.
_HOUSEHOLD_FAMILY_TRUST_MAP: dict[str, str] = {
    "joint": "Spouse/partner",
    "nuclear": "Spouse/partner",
    "single-parent": "Children / close family",
    "couple-no-kids": "Partner",
    "other": "Self",
}

_TRUST_ANCHOR_PARTNER_MAP: dict[str, str] = {
    "self": "Self",
    "peer": "Close friends",
    "authority": "Trusted expert/advisor",
    "family": "Spouse/partner",
}

# Trust weight field names → generic influencer labels.
_TRUST_WEIGHT_LABELS: dict[str, str] = {
    "expert": "Expert reviews",
    "peer": "Peer recommendations",
    "brand": "Trusted brand signals",
    "ad": "Advertising and promotions",
    "community": "Social community",
    "influencer": "Social influencers",
}


def _derive_relationship_map(persona: PersonaRecord) -> RelationshipMap:
    """Assemble RelationshipMap from household + trust orientation data.

    primary_decision_partner:
      - Joint/nuclear household + family trust → "Spouse/partner"
      - Single-parent → "Children / close family"
      - Couple-no-kids → "Partner"
      - Self trust → "Self"
      - Peer trust → "Close friends"
      - Authority trust → "Trusted expert/advisor"

    key_influencers:
      Top 2 non-self trust weight sources (by weight value), labeled generically.

    trust_network:
      Top 2–3 sources with weight > 0.5. If none exceed 0.5,
      include the single highest-weight source as fallback.
    """
    structure = persona.demographic_anchor.household.structure

    # Determine trust anchor from attributes if available, else from derived_insights.
    social_cat: dict[str, Any] = persona.attributes.get("social", {})
    trust_primary_attr = social_cat.get("trust_orientation_primary")
    if trust_primary_attr is not None:
        trust_primary = str(trust_primary_attr.value)
    else:
        trust_primary = str(persona.derived_insights.trust_anchor)

    # primary_decision_partner: household structure takes precedence for
    # joint/nuclear/single-parent/couple-no-kids; trust anchor used for "other".
    if structure in ("joint", "nuclear"):
        if trust_primary == "family":
            primary_decision_partner = "Spouse/partner"
        elif trust_primary == "self":
            primary_decision_partner = "Self"
        elif trust_primary == "peer":
            primary_decision_partner = "Close friends"
        elif trust_primary == "authority":
            primary_decision_partner = "Trusted expert/advisor"
        else:
            primary_decision_partner = "Spouse/partner"
    elif structure == "single-parent":
        primary_decision_partner = "Children / close family"
    elif structure == "couple-no-kids":
        primary_decision_partner = "Partner"
    else:
        # "other" — use trust anchor.
        primary_decision_partner = _TRUST_ANCHOR_PARTNER_MAP.get(trust_primary, "Self")

    # Build sorted trust weight pairs.
    weights = persona.behavioural_tendencies.trust_orientation.weights
    weight_pairs: list[tuple[str, float]] = [
        ("expert", weights.expert),
        ("peer", weights.peer),
        ("brand", weights.brand),
        ("ad", weights.ad),
        ("community", weights.community),
        ("influencer", weights.influencer),
    ]
    weight_pairs_sorted = sorted(weight_pairs, key=lambda t: t[1], reverse=True)

    # key_influencers: top 2 non-self sources by weight.
    # "self" has no weight field — all 6 sources are external, so take top 2.
    key_influencers: list[str] = [
        _TRUST_WEIGHT_LABELS[name]
        for name, _ in weight_pairs_sorted[:2]
    ]

    # trust_network: sources with weight > 0.5; fallback to top source if empty.
    trust_network: list[str] = [
        _TRUST_WEIGHT_LABELS[name]
        for name, w in weight_pairs_sorted
        if w > 0.5
    ]
    # Also factor in peer_influence_strength and online_community_trust from
    # social attributes to populate trust_network generically.
    peer_influence = social_cat.get("peer_influence_strength")
    online_community = social_cat.get("online_community_trust")

    if peer_influence is not None and isinstance(peer_influence.value, (int, float)):
        if float(peer_influence.value) > 0.5 and "Peer recommendations" not in trust_network:
            trust_network.append("Peer recommendations")
    if online_community is not None and isinstance(online_community.value, (int, float)):
        if float(online_community.value) > 0.5 and "Online communities" not in trust_network:
            trust_network.append("Online communities")

    # Fallback: at least 1 entry.
    if not trust_network:
        trust_network = [_TRUST_WEIGHT_LABELS[weight_pairs_sorted[0][0]]]

    # Clamp trust_network to 3 entries max.
    trust_network = trust_network[:3]

    # Ensure key_influencers has at least 2 entries (pad with trust_network if needed).
    while len(key_influencers) < 2 and trust_network:
        candidate = trust_network[0]
        if candidate not in key_influencers:
            key_influencers.append(candidate)
        else:
            break

    return RelationshipMap(
        primary_decision_partner=primary_decision_partner,
        key_influencers=key_influencers,
        trust_network=trust_network,
    )


# ---------------------------------------------------------------------------
# immutable_constraints
# ---------------------------------------------------------------------------


def _derive_immutable_constraints(persona: PersonaRecord) -> ImmutableConstraints:
    """Assemble ImmutableConstraints.

    budget_ceiling:
      If economic_constraint_level > 0.7 → "Tight budget — {income_bracket} income"
      Else None.

    non_negotiables:
      Items from key_tensions that represent hard limits.
      Patterns "vs_budget" or "vs_constraint" trigger inclusion.
      At least 1 item if key_tensions is non-empty.

    absolute_avoidances:
      Copied from existing persona.memory.core.immutable_constraints if present,
      else empty list.
    """
    # Budget ceiling.
    values_cat: dict[str, Any] = persona.attributes.get("values", {})
    ec_attr = values_cat.get("economic_constraint_level")
    income_bracket = persona.demographic_anchor.household.income_bracket

    budget_ceiling: str | None = None
    if ec_attr is not None and isinstance(ec_attr.value, (int, float)):
        if float(ec_attr.value) > 0.7:
            budget_ceiling = f"Tight budget — {income_bracket} income"
    # Fallback: if attribute is missing but we have an income bracket, leave as None
    # (we can't determine constraint level without the attribute).

    # Non-negotiables from key_tensions.
    key_tensions: list[str] = persona.derived_insights.key_tensions
    non_negotiables: list[str] = []

    # Patterns indicating a hard constraint.
    hard_limit_patterns = [
        "vs_budget", "vs_constraint", "budget", "constraint",
        "constrain", "limit", "ceiling", "hard",
    ]

    for tension in key_tensions:
        tension_lower = tension.lower()
        if any(pat in tension_lower for pat in hard_limit_patterns):
            non_negotiables.append(tension)

    # If no pattern matches but tensions exist, include at least the first one.
    if not non_negotiables and key_tensions:
        non_negotiables.append(key_tensions[0])

    # Absolute avoidances: preserve from existing core memory if present,
    # else empty list (populated from narrative context in deeper modes).
    absolute_avoidances: list[str] = []
    try:
        existing = persona.memory.core.immutable_constraints.absolute_avoidances
        if existing:
            absolute_avoidances = list(existing)
    except AttributeError:
        pass

    return ImmutableConstraints(
        budget_ceiling=budget_ceiling,
        non_negotiables=non_negotiables,
        absolute_avoidances=absolute_avoidances,
    )


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = ["assemble_core_memory"]
