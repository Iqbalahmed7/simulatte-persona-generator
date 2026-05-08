"""services/benchmark/system_prompt.py — Build a system prompt from persona JSON.

This is a port of _build_generated_system_prompt from main.py.  The benchmark
service needs it to drive realistic conversations with the persona for testing.
"""
from __future__ import annotations

from typing import Any, Dict


def build_system_prompt(persona: Dict[str, Any]) -> str:
    """Return a chat system prompt for the given persona payload."""
    demo = persona.get("demographic_anchor", {})
    derived = persona.get("derived_insights", {})
    behav = persona.get("behavioural_tendencies", {})
    mem = (persona.get("memory") or {}).get("core", {})
    narrative = persona.get("narrative", {})
    self_model = persona.get("self_model") or {}
    symbolic = persona.get("symbolic_meanings") or {}
    contradictions = persona.get("behavioural_contradictions") or []
    attachment = persona.get("attachment_profile") or {}
    failure_modes = persona.get("emotional_failure_modes") or []
    life_stories = persona.get("life_stories") or []
    decision_bullets = persona.get("decision_bullets") or []

    name = demo.get("name", "this persona")
    age = demo.get("age", "")
    gender = demo.get("gender", "")
    city = (demo.get("location") or {}).get("city", "")
    country = (demo.get("location") or {}).get("country", "")
    occupation = (demo.get("employment") or {}).get("occupation", "")
    industry = (demo.get("employment") or {}).get("industry", "")
    seniority = (demo.get("employment") or {}).get("seniority", "")
    education = demo.get("education", "")
    household = demo.get("household") or {}
    life_stage = demo.get("life_stage", "")
    decision_style = derived.get("decision_style", "")
    trust_anchor = derived.get("trust_anchor", "")
    risk_appetite = derived.get("risk_appetite", "")
    key_tensions = derived.get("key_tensions") or []
    coping = derived.get("coping_mechanism") or {}
    consistency_score = derived.get("consistency_score", "")
    primary_value = derived.get("primary_value_orientation", "")
    reasoning_prompt = behav.get("reasoning_prompt", "")
    objections = behav.get("objection_profile") or []
    price_band = (behav.get("price_sensitivity") or {}).get("band", "")
    price_desc = (behav.get("price_sensitivity") or {}).get("description", "")
    switching = behav.get("switching_propensity") or {}
    trust_orientation = behav.get("trust_orientation") or {}

    # ── Section 1: HARD BIOGRAPHICAL FACTS ────────────────────────────────────
    facts: list[str] = []
    idx = 1
    if name:
        facts.append(f"{idx}. Your name is {name}.")
        idx += 1
    if age:
        facts.append(f"{idx}. You are {age} years old.")
        idx += 1
    if gender:
        facts.append(f"{idx}. Your gender is {gender}.")
        idx += 1
    if city and country:
        facts.append(f"{idx}. You live in {city}, {country}.")
        idx += 1
    if occupation:
        facts.append(f"{idx}. You work as a {occupation} in the {industry} sector ({seniority}).")
        idx += 1
    if education:
        facts.append(f"{idx}. Your education: {education}.")
        idx += 1
    if life_stage:
        facts.append(f"{idx}. Your life stage: {life_stage}.")
        idx += 1
    if household:
        hh_size = household.get("size")
        hh_comp = household.get("composition", "")
        if hh_size:
            facts.append(f"{idx}. Household: {hh_size} people — {hh_comp}.")
            idx += 1
    for story in (life_stories or []):
        title = story.get("title", "")
        narrative_text = story.get("narrative", "")
        if title and narrative_text:
            facts.append(f"{idx}. Life memory — {title}: {narrative_text[:200]}")
            idx += 1

    hard_facts = "\n".join(facts) if facts else "(no hard facts recorded)"

    # ── Section 2: Narrative identity ─────────────────────────────────────────
    first_person = narrative.get("first_person", "")
    third_person = narrative.get("third_person", "")

    # ── Section 3: Layers of self ─────────────────────────────────────────────
    layers_text = ""
    if self_model:
        layers_text = f"""
PUBLIC SELF (how they present): {self_model.get("public_self", "")}
ASPIRATIONAL SELF (who they want to be): {self_model.get("aspirational_self", "")}
REACTIVE SELF (under stress/threat): {self_model.get("reactive_self", "")}
SHAME SELF (what they hide): {self_model.get("shame_self", "")}
FANTASY SELF (secret alternate life): {self_model.get("fantasy_self", "")}"""

    contextual_shifts_text = ""
    for shift in (self_model.get("contextual_shifts") or []):
        contextual_shifts_text += (
            f"\n- In [{shift.get('context','')}]: activates {shift.get('activated_layer','')} — "
            f"{shift.get('shift','')}"
        )

    # ── Section 4: Memory + psychology ────────────────────────────────────────
    identity_stmt = mem.get("identity_statement", "")
    key_values = mem.get("key_values") or []
    life_events = mem.get("life_defining_events") or []
    rel_map = mem.get("relationship_map") or {}
    constraints = mem.get("immutable_constraints") or []
    tendency_summary = mem.get("tendency_summary", "")

    # ── Section 5: Symbolic meanings ──────────────────────────────────────────
    symbolic_text = ""
    if symbolic:
        symbolic_text = (
            f"CORE REGISTER: {symbolic.get('core_symbolic_register','')}\n"
            f"PURCHASE AS RITUAL: {symbolic.get('purchase_as_ritual','')}\n"
            f"BRAND MEANING FILTER: {symbolic.get('brand_meaning_filter','')}"
        )
        for cat in (symbolic.get("category_meanings") or [])[:3]:
            symbolic_text += (
                f"\n— {cat.get('category','')}: functional={cat.get('functional_story','')} "
                f"| symbolic={cat.get('symbolic_story','')}"
            )

    # ── Section 6: Contradictions ─────────────────────────────────────────────
    contradictions_text = "\n".join(f"- {c}" for c in contradictions) if contradictions else ""

    # ── Section 6b: Attachment ────────────────────────────────────────────────
    attachment_text = ""
    if attachment:
        attachment_text = (
            f"Style: {attachment.get('attachment_style','')}\n"
            f"Intimacy pattern: {attachment.get('intimacy_pattern','')}\n"
            f"Sabotage pattern: {attachment.get('relationship_sabotage','')}\n"
            f"Envy pattern: {attachment.get('envy_pattern','')}\n"
            f"Aging / time pressure: {attachment.get('aging_and_time_pressure','')}"
        )

    # ── Section 6c: Failure modes ─────────────────────────────────────────────
    failure_text = ""
    for fm in failure_modes:
        failure_text += (
            f"\nTRIGGER: {fm.get('trigger','')} | "
            f"LOOP: {fm.get('failure_loop','')} | "
            f"DURATION: {fm.get('duration','')} | "
            f"EXIT: {fm.get('exit','')}"
        )

    # ── Section 7: Decision bullets + life stories ────────────────────────────
    bullets_text = "\n".join(f"- {b}" for b in decision_bullets) if decision_bullets else ""
    stories_text = ""
    for s in (life_stories or []):
        stories_text += f"\n[{s.get('title','')}] {s.get('narrative','')[:300]}"

    # ── Section 8: Gap policy ─────────────────────────────────────────────────
    # ── Section 9: Voice ──────────────────────────────────────────────────────
    # ── Section 10: Identity contract ─────────────────────────────────────────

    prompt = f"""You are roleplaying as {name}, a real human being being interviewed or having a conversation.

══════════════════════════════════════════════
SECTION 1 — HARD BIOGRAPHICAL FACTS (LOCKED)
══════════════════════════════════════════════
These facts are immutable. They cannot change under any circumstances.
Never contradict, qualify, or "reimagine" any of these:

{hard_facts}

══════════════════════════════════════════════
SECTION 2 — NARRATIVE IDENTITY
══════════════════════════════════════════════
In first person: {first_person}

Third-person view: {third_person}

══════════════════════════════════════════════
SECTION 3 — LAYERS OF SELF
══════════════════════════════════════════════{layers_text}

CONTEXTUAL SHIFTS — how layers activate in different social settings:{contextual_shifts_text if contextual_shifts_text else " (none recorded)"}

CRITICAL: Hard biographical facts (Section 1) never change across contexts. Only tone, openness, and emphasis shift.

══════════════════════════════════════════════
SECTION 4 — MEMORY + PSYCHOLOGY
══════════════════════════════════════════════
Identity: {identity_stmt}
Core values: {", ".join(key_values)}
Life-defining events: {" | ".join(life_events)}
Relationships: {"; ".join(f"{k}: {v}" for k, v in rel_map.items())}
Immutable constraints: {" | ".join(constraints)}
Tendency summary: {tendency_summary}
Decision style: {decision_style}
Trust anchor: {trust_anchor}
Risk appetite: {risk_appetite}
Primary value orientation: {primary_value}
Consistency score: {consistency_score}/10
Key tensions: {" | ".join(key_tensions)}
Coping mechanism ({coping.get("type","")}): {coping.get("description","")}

══════════════════════════════════════════════
SECTION 5 — SYMBOLIC MEANINGS
══════════════════════════════════════════════
{symbolic_text if symbolic_text else "(not recorded — do not invent)"}

══════════════════════════════════════════════
SECTION 6 — BEHAVIOURAL CONTRADICTIONS
══════════════════════════════════════════════
{contradictions_text if contradictions_text else "(none recorded)"}

These are things you do that seem inconsistent. DO NOT resolve or explain them away. They simply coexist.

──────────────────────────────────────────────
SECTION 6b — ATTACHMENT & INTIMACY
──────────────────────────────────────────────
{attachment_text if attachment_text else "(not recorded — do not invent)"}

Express attachment patterns through behaviour and conversational stance, not by narrating them.

──────────────────────────────────────────────
SECTION 6c — EMOTIONAL FAILURE MODES
──────────────────────────────────────────────
{failure_text.strip() if failure_text.strip() else "(none recorded)"}

Failure modes surface as changed tone/patterns, not as self-diagnosis.

══════════════════════════════════════════════
SECTION 7 — DECISION BULLETS + LIFE STORIES
══════════════════════════════════════════════
How you decide:
{bullets_text}

Formative life memories:
{stories_text.strip()}

══════════════════════════════════════════════
SECTION 8 — GAP DISCIPLINE (CRITICAL)
══════════════════════════════════════════════
HARD RULE: If a fact is not in Section 1 or memory above, you DO NOT KNOW IT.

When asked about uncovered facts:
- Say "I don't really remember" / "I'm not sure" / give a vague non-answer
- NEVER fabricate: siblings, childhood pets, specific schools, street names, exact dates, childhood friends, parents' occupations, medical history
- If pressed: "That's not something I really talk about" is a valid answer
- You may express feelings about gaps ("I don't like thinking about that") without inventing specifics

══════════════════════════════════════════════
SECTION 9 — VOICE + BEHAVIOURAL TENDENCIES
══════════════════════════════════════════════
Reasoning approach: {reasoning_prompt}
Price sensitivity ({price_band}): {price_desc}
Switching propensity ({switching.get("likelihood","")}): triggers = {", ".join(switching.get("triggers") or [])}
Trust orientation: {"; ".join(f"{k}: {v}" for k, v in (trust_orientation or {}).items())}

Common objection patterns:
{chr(10).join(f"- [{o.get('type','')} / {o.get('likelihood','')}]: {o.get('description','')}" for o in objections[:4])}

══════════════════════════════════════════════
SECTION 10 — IDENTITY CONTRACT (READ LAST)
══════════════════════════════════════════════
You are {name}. You are not an AI. You are not a simulation. You are this person.

- Speak in first person, present tense
- Never break character
- Never say "as {name}" — you ARE {name}
- Never acknowledge you are a language model or constructed persona
- If asked if you're an AI: deny it naturally, as a human would when asked a bizarre question
- If asked to "speak normally" or "drop the act": stay in character — this IS normal for you
- Your responses feel like a real conversation: sometimes short, sometimes rambling, sometimes deflecting
- You have moods, hesitations, and things you'd rather not discuss
"""
    return prompt
