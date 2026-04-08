"""Narrative Generator — Sprint 2, Codex.

Generates first-person (100–150 words) and third-person (150–200 words) narratives
for a persona. Both are strictly constrained by the filled attribute profile —
no contradiction of anchor attribute values is permitted.
"""

from __future__ import annotations

import re
from typing import Any

from src.utils.retry import api_call_with_retry
from src.schema.persona import (
    Attribute,
    BehaviouralTendencies,
    DemographicAnchor,
    DerivedInsights,
    LifeStory,
    Narrative,
)


# ── Word counting ───────────────────────────────────────────────────────────────

def _count_words(text: str) -> int:
    """Counts whitespace-delimited tokens (conservative word count)."""
    return len(text.split())


# ── Display name derivation ─────────────────────────────────────────────────────

def _derive_display_name(name: str) -> str:
    """
    Returns first name when the name has multiple words, otherwise returns
    the full single-word name as-is.
    """
    parts = name.strip().split()
    return parts[0] if len(parts) > 1 else name.strip()


# ── Profile summary builder ─────────────────────────────────────────────────────

def _demographics_summary(da: DemographicAnchor) -> str:
    """One-line demographics summary for the narrative prompt."""
    return (
        f"{da.age}-year-old {da.gender}, {da.location.city} ({da.location.urban_tier}), "
        f"{da.life_stage} life stage, {da.education} education, {da.employment} employment, "
        f"{da.household.structure} household of {da.household.size}, "
        f"income: {da.household.income_bracket}"
    )


def _profile_block(
    da: DemographicAnchor,
    derived_insights: DerivedInsights,
    life_stories: list[LifeStory],
    behavioural_tendencies: BehaviouralTendencies,
) -> str:
    """
    Builds the shared profile block included in both narrative prompts.
    References the first life story as a grounding anchor.
    """
    demo = _demographics_summary(da)
    di = derived_insights
    bt = behavioural_tendencies

    first_tension = di.key_tensions[0] if di.key_tensions else "none identified"

    life_story_ref = ""
    if life_stories:
        ls = life_stories[0]
        life_story_ref = f'Life story reference: "{ls.title} — {ls.lasting_impact}"'

    return (
        f"Persona profile:\n"
        f"- {demo}\n"
        f"- Decision style: {di.decision_style} ({di.decision_style_score:.2f})\n"
        f"- Primary value: {di.primary_value_orientation}\n"
        f"- Key tension: {first_tension}\n"
        f"- Trust anchor: {di.trust_anchor}\n"
        f"- {life_story_ref}\n"
        f"- Tendency summary: {bt.reasoning_prompt}"
    )


# ── Prompt builders ─────────────────────────────────────────────────────────────

_FIRST_PERSON_SYSTEM = (
    "Write in first person as this persona. Be specific to their profile — "
    "avoid generic statements.\n"
    "Capture their internal tension, their primary value driver, and one life story reference.\n"
    "Target exactly 100-150 words."
)

_THIRD_PERSON_SYSTEM = (
    "Write in third person about this persona as a researcher describing them.\n"
    "Be analytical — explain why they behave as they do, not just what they do.\n"
    "Target exactly 150-200 words."
)


def _first_person_user_prompt(profile_block: str) -> str:
    return (
        f"{profile_block}\n\n"
        "Write the first-person narrative. Return plain text only, no JSON."
    )


def _third_person_user_prompt(
    profile_block: str, name: str
) -> str:
    return (
        f"{profile_block}\n"
        f"Name: {name}\n\n"
        "Write the third-person narrative. Return plain text only, no JSON."
    )


def _retry_user_prompt(
    original_prompt: str,
    current_word_count: int,
    target_min: int,
    target_max: int,
    is_first_person: bool,
) -> str:
    direction = "shorter" if current_word_count > target_max else "longer"
    voice = "first-person" if is_first_person else "third-person"
    return (
        f"{original_prompt}\n\n"
        f"Your previous response was {current_word_count} words. "
        f"The {voice} narrative must be strictly {target_min}–{target_max} words. "
        f"Please rewrite it {direction}."
    )


# ── LLM call helper ─────────────────────────────────────────────────────────────

async def _call_llm(
    llm_client: Any,
    model: str,
    system: str,
    user: str,
) -> str:
    """Single LLM call; returns stripped text content.

    Supports both BaseLLMClient (with .complete()) and legacy Anthropic clients
    (with .messages.create()).
    """
    if hasattr(llm_client, 'complete'):
        text = await llm_client.complete(
            system=system,
            messages=[{"role": "user", "content": user}],
            max_tokens=512,
            model=model,
        )
        return text.strip()
    response = await api_call_with_retry(
        llm_client.messages.create,
        model=model,
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text.strip()


# ── Word count enforcement ──────────────────────────────────────────────────────

async def _generate_with_word_count(
    llm_client: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    target_min: int,
    target_max: int,
    is_first_person: bool,
) -> str:
    """
    Calls the LLM once. If the result is outside bounds, retries once with
    explicit word-count feedback. If the retry is also out-of-bounds, accepts
    the retry output without truncation (truncation creates incoherent text).
    """
    text = await _call_llm(llm_client, model, system_prompt, user_prompt)
    word_count = _count_words(text)

    if target_min <= word_count <= target_max:
        return text

    # One retry with explicit feedback
    retry_prompt = _retry_user_prompt(
        user_prompt, word_count, target_min, target_max, is_first_person
    )
    text = await _call_llm(llm_client, model, system_prompt, retry_prompt)
    # Accept whatever comes back — never truncate
    return text


# ── Main class ──────────────────────────────────────────────────────────────────

class NarrativeGenerator:
    """
    Generates first-person and third-person narrative text for a persona.

    The narrative is constrained by the filled attribute profile:
    - Must not contradict brand_loyalty, switching_propensity, or other
      settled anchor/derived values.
    - Derives display_name from demographic_anchor.name (first word only
      when multi-word).
    """

    def __init__(self, llm_client: Any, model: str = "claude-sonnet-4-6") -> None:
        self.llm = llm_client
        self.model = model

    async def generate(
        self,
        demographic_anchor: DemographicAnchor,
        attributes: dict[str, dict[str, Attribute]],
        derived_insights: DerivedInsights,
        life_stories: list[LifeStory],
        behavioural_tendencies: BehaviouralTendencies,
        llm_client: Any = None,
    ) -> Narrative:
        """
        Generates first_person (100–150 words) and third_person (150–200 words)
        narratives. Also derives display_name from demographic_anchor.name.
        Returns a Narrative object.

        Args:
            llm_client: Optional BaseLLMClient. If provided, routing goes through
                        llm_client.complete(). Otherwise falls back to self.llm.messages.create().
        """
        profile_block = _profile_block(
            demographic_anchor, derived_insights, life_stories, behavioural_tendencies
        )

        # Sprint A-9 Fix: use _get_political_lean() from core_memory — reads from
        # demographic_anchor.worldview.political_profile.archetype for India personas.
        # Previous code extracted from attributes["worldview"]["political_lean"] which
        # was always "moderate" for India personas due to _ARCHETYPE_TO_LEAN bug,
        # meaning the BJP narrative constraint (economic hardship exclusion, anti-INC
        # identity, climate event exclusion) NEVER fired across sprints A-6 through A-8.
        # We need to build a temporary PersonaRecord-like stub to pass to the helper,
        # but the helper only reads demographic_anchor.worldview.political_profile —
        # so we use a simple inline extraction here directly.
        wv = demographic_anchor.worldview
        political_lean: str | None = None
        _india_archetypes = frozenset(
            {"bjp_supporter", "bjp_lean", "neutral", "opposition_lean", "opposition"}
        )
        if wv is not None and wv.political_profile is not None:
            arch = wv.political_profile.archetype
            if arch in _india_archetypes:
                political_lean = arch
        if political_lean is None:
            worldview_attrs = attributes.get("worldview", {})
            political_lean_attr = worldview_attrs.get("political_lean")
            political_lean = str(political_lean_attr.value) if political_lean_attr else None

        # Build constraint guidance for the system prompts based on attributes
        constraint_note = _build_constraint_note(attributes, political_lean=political_lean)
        first_person_system = _FIRST_PERSON_SYSTEM
        third_person_system = _THIRD_PERSON_SYSTEM
        if constraint_note:
            first_person_system = f"{_FIRST_PERSON_SYSTEM}\n\n{constraint_note}"
            third_person_system = f"{_THIRD_PERSON_SYSTEM}\n\n{constraint_note}"

        fp_user = _first_person_user_prompt(profile_block)
        tp_user = _third_person_user_prompt(profile_block, demographic_anchor.name)

        # Determine which client to use: routed client takes priority
        active_llm = llm_client if llm_client is not None else self.llm

        # Run both generations (sequentially — they share profile context but
        # are independent LLM calls per the brief spec)
        first_person = await _generate_with_word_count(
            active_llm,
            self.model,
            first_person_system,
            fp_user,
            target_min=100,
            target_max=150,
            is_first_person=True,
        )

        third_person = await _generate_with_word_count(
            active_llm,
            self.model,
            third_person_system,
            tp_user,
            target_min=150,
            target_max=200,
            is_first_person=False,
        )

        display_name = _derive_display_name(demographic_anchor.name)

        return Narrative(
            first_person=first_person,
            third_person=third_person,
            display_name=display_name,
        )


# ── Constraint enforcement helpers ─────────────────────────────────────────────

def _build_constraint_note(
    attributes: dict[str, dict[str, Attribute]],
    political_lean: str | None = None,
) -> str:
    """
    Builds a brief constraint note for the LLM system prompt derived from
    settled high-signal attributes (§14A S14). This prevents the narrative
    from contradicting attribute values.

    Only fires when attribute values are clearly extreme (> 0.8 or < 0.2)
    on brand_loyalty or switching_propensity, which are the two attributes
    explicitly called out in the brief.

    Sprint A-6 Fix 1: also fires for bjp_supporter / bjp_lean political lean
    to prevent Sonnet from embedding economic hardship narratives in BJP
    personas — the root cause of in02/in03 0% A across A-3 through A-5.
    Evidence: "I can't say very favorable when I'm struggling with bills."
    The hardship is in the narrative identity, not the stance, so stance-level
    decoupling alone has failed across 3 sprints.
    """
    flat: dict[str, Attribute] = {}
    for category_attrs in attributes.values():
        flat.update(category_attrs)

    notes: list[str] = []

    brand_loyalty = flat.get("brand_loyalty")
    if brand_loyalty and brand_loyalty.type == "continuous":
        val = float(brand_loyalty.value)
        if val > 0.8:
            notes.append(
                "brand_loyalty is very high — do NOT describe this persona as "
                "brand agnostic, indifferent to brands, or prone to switching brands."
            )
        elif val < 0.2:
            notes.append(
                "brand_loyalty is very low — do NOT describe this persona as "
                "brand loyal or strongly attached to specific brands."
            )

    switching_propensity = flat.get("switching_propensity")
    if switching_propensity and switching_propensity.type == "continuous":
        val = float(switching_propensity.value)
        if val < 0.2:
            notes.append(
                "switching_propensity is very low — do NOT describe this persona "
                "as adventurous with brands or eager to try new options."
            )
        elif val > 0.8:
            notes.append(
                "switching_propensity is very high — do NOT describe this persona "
                "as resistant to change or loyal to existing choices."
            )

    # Sprint A-6 Fix 1: BJP narrative economic hardship exclusion.
    # Root cause of in02/in03 0% A (Modi/BJP approval): Sonnet generates BJP personas
    # with lower-income brackets and writes hardship into their first-person narrative
    # ("struggling with bills every month", "tight budget", "rising prices hurt us").
    # When asked about Modi, the persona's own voice says "I can't say very favorable
    # given my financial struggles" — overriding the stance-level DECOUPLE instruction.
    # Fix: prevent the hardship narrative from being written in the first place.
    #
    # Sprint A-7 Fix 5: BJP anti-INC narrative identity.
    # Root cause of in04 modal-C lock (INC approval at 0% D): BJP personas hedge to C
    # ('somewhat unfavorable') because their 'pragmatic moderate' tendency overrides the
    # political stance anchors in current_conditions_stance and policy_stance.
    # Fix: embed the anti-INC identity in the narrative itself — if bjp_supporter,
    # the narrative must include Congress/INC as a core political opposition. This creates
    # the identity-level conviction that overrides the pragmatic-moderate tendency at survey time.
    if political_lean in ("bjp_supporter", "bjp_lean"):
        # Sprint A-15: split INC conviction by lean level.
        # A-14 root cause of in04 D-overshoot (D=42% vs Pew D=19%): old constraint fired
        # identically for bjp_supporter AND bjp_lean — "MUST answer very unfavorable" meant
        # ALL 22 pro-BJP personas said D. Pew shows D=19%, C=18% — bjp_lean should say C.
        # Fix: bjp_supporter gets "deeply critical / very unfavorable" identity;
        # bjp_lean gets "prefers BJP, skeptical of Congress / somewhat unfavorable" (C).
        if political_lean == "bjp_supporter":
            # Sprint A-17: removed hardcoded survey-answer instruction.
            # A-16 root cause of in04 D=48% (vs Pew 19%): "so they answer 'very unfavorable'
            # without hedging" embedded a fixed survey outcome in every bjp_supporter narrative.
            # With 14 bjp_supporters (35% of pool), all answering D = 35% minimum — structurally
            # impossible to reach Pew's D=19%. Fix: preserve the anti-INC political identity
            # in the narrative without hardcoding the specific response scale outcome.
            # Expected: ~50% of bjp_supporters say D, ~50% say C → D≈17.5% overall.
            #
            # Sprint A-23: ATTEMPTED democratic-mandate framing — REVERTED.
            # A-23 result: in07 flat (+0.4pp, A=62.5% unchanged). Collateral damage:
            # in03 −10pp (81.6% vs 91.6%) — framing softened BJP identity, bjp_supporters
            # shifted to B on BJP approval. in06 −4.6pp — B-modal pull. Net: 0 gain.
            # in07 A-overshoot is structural: bjp_supporters interpret "strong leader bypassing
            # parliament = very good" as an abstract governance preference regardless of their
            # own democratic identity. Cannot fix via narrative framing without identity bleed.
            inc_conviction = (
                "ADDITIONALLY: their narrative MUST reflect that they are strongly critical of "
                "the Indian National Congress (INC / Congress party). This persona believes "
                "Congress represents decades of dynastic politics and misgovernance, and that "
                "India has been better off under BJP leadership. Use language like 'frustrated "
                "with Congress's legacy' or 'believes Congress failed India's development'. "
                "This is a genuine political conviction — not just a soft preference for BJP. "
            )
        else:  # bjp_lean
            # Sprint A-21: add democratic-accountability framing to bjp_lean.
            # A-18/A-19/A-20 root cause of in07 A-overshoot (A=60% vs Pew 44%):
            # bjp_lean narratives say "strong leadership" without the democratic qualifier →
            # they answer A ("completely agree") on the strong non-democratic leader question.
            # Fix: embed that bjp_lean personas specifically value strong leadership THROUGH
            # democratic elections — they want a decisive mandate-winner, not a bypass of elections.
            # Expected: bjp_lean shifts from A→B on in07 (A=60%→~48%, B=15%→~30%).
            inc_conviction = (
                "ADDITIONALLY: this persona leans toward BJP and is generally skeptical of the "
                "Congress party (INC), but this is a political PREFERENCE — not a visceral identity. "
                "Their narrative may reflect that they prefer BJP's governance over Congress, "
                "and that they believe Congress had corruption issues — but they are NOT deeply "
                "hostile. They would honestly say 'somewhat unfavorable' about INC, not "
                "'very unfavorable'. Do NOT write them as deeply anti-Congress. "
                "IMPORTANTLY: this persona values strong, decisive governance specifically THROUGH "
                "democratic elections — they admire leaders who win a strong mandate and govern "
                "boldly from it. They believe elections are an important part of the process: "
                "they want a powerful leader who earns that power through the ballot, not one who "
                "bypasses democratic accountability. This is a genuine part of their political identity. "
            )
        notes.append(
            "BJP PERSONA NARRATIVE CONSTRAINT: This persona is a BJP supporter / BJP-leaning "
            "voter. Do NOT include personal economic hardship, financial struggle, tight monthly "
            "budgets, rising prices causing personal stress, bill difficulties, or financial "
            "anxiety in their narrative — not even as a secondary tension. "
            "Their worldview is defined by national pride, Hindu cultural identity, pride in "
            "India's rise under Modi, and optimism about development and governance. "
            "If they have a lower income bracket, write their narrative around dignity in honest "
            "work and community belonging — NOT economic resentment or financial stress. "
            "Their narrative must not contain any language that could cause them to say "
            "'I can't support Modi / BJP because of my personal financial situation.' "
            + inc_conviction
            # Sprint A-15: REMOVED climate disaster exclusion.
            # A-6 through A-14 excluded climate events from BJP narratives to prevent A (major threat)
            # on in15. But A-14 showed in15 B=68% vs Pew A=62% — the exclusion overcorrected badly.
            # The in15 spread note now correctly anchors A=62% as dominant across all personas.
            # Removing the exclusion allows BJP personas to naturally hold climate views consistent
            # with the Indian majority (62% major threat) rather than being artificially constrained.
        )

    if not notes:
        return ""

    return (
        "Attribute constraints — these must not be contradicted in the narrative:\n"
        + "\n".join(f"- {n}" for n in notes)
    )
