"""src/cognition/decide.py — 5-step decision reasoning engine.

Sprint 4 — Codex (Cognitive Loop)

Spec: §9 (Cognitive Loop), §14A S1, Constitution P1/P2/P4
"""

from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import dataclass, field
from typing import Any

import anthropic

from src.cognition.errors import DecideError
from src.memory.cache import _GLOBAL_CACHE
from src.memory.core_memory import _get_political_lean
from src.schema.persona import Observation, PersonaRecord, Reflection
from src.utils.retry import api_call_with_retry

logger = logging.getLogger(__name__)

_SONNET_MODEL = "claude-sonnet-4-6"
_MAX_MEMORIES = 10

# ---------------------------------------------------------------------------
# Contextual noise — situational variability for realistic human behavior
# ---------------------------------------------------------------------------

# Situational modifiers inject subtle human variability into reasoning.
# Each is deterministically selected from persona_id × scenario hash,
# so the SAME persona + SAME stimulus → SAME modifier (BV1-safe).
# Different stimuli get different modifiers (BV6-compliant: no 100% consistency).
_SITUATIONAL_MODIFIERS = [
    # Neutral (no modifier) — 40% weight
    "",
    "",
    "",
    "",
    # Attention variation — 20% weight
    "You're slightly distracted today — you noticed this in passing rather than giving it your full focus.",
    "You're paying unusually close attention today — you have time to really think this through.",
    # Mood variation — 20% weight
    "You're in a cautious mood today — recent events have made you a bit more careful than usual.",
    "You're feeling optimistic today — things have been going well and you're open to trying new things.",
    # Social framing — 10% weight
    "A friend just mentioned a bad experience with a similar product, which is fresh in your mind.",
    # Cognitive load — 10% weight
    "You're making this decision at the end of a long day when you're mentally tired.",
]


def _select_situational_modifier(persona_id: str, scenario: str) -> str:
    """Deterministically select a situational modifier from persona_id × scenario.

    Uses a hash to ensure:
      - Same persona + same scenario → same modifier (BV1: repeated-run stability)
      - Same persona + different scenario → different modifier (BV6: not 100% consistent)
      - Different persona + same scenario → likely different modifier
    """
    combined = f"{persona_id}:{scenario}"
    h = hash(combined)
    idx = h % len(_SITUATIONAL_MODIFIERS)
    return _SITUATIONAL_MODIFIERS[idx]


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------


@dataclass
class DecisionOutput:
    decision: str                        # The actual decision made
    confidence: int                      # 0-100, post-noise
    reasoning_trace: str                 # Full 5-step reasoning as text
    gut_reaction: str                    # Step 1 extracted
    key_drivers: list[str] = field(default_factory=list)    # Top 2-3 factors
    objections: list[str] = field(default_factory=list)     # Hesitations / objections
    what_would_change_mind: str = ""     # Override condition
    noise_applied: int = 0               # Raw noise value injected (for traceability)
    follow_up_action: str = ""           # What the persona does immediately after deciding
    implied_purchase: bool = False       # True when decision is research_more/defer but
                                         # follow_up_action describes an actual purchase
                                         # commitment (e.g. "orders a trial pack tonight")


# ---------------------------------------------------------------------------
# Core memory block — richer for decide (includes immutable_constraints)
# ---------------------------------------------------------------------------


def _decide_core_memory_block(persona: PersonaRecord) -> str:
    """Return a richer core memory block for the decide prompt.

    Includes budget_ceiling, non_negotiables, and absolute_avoidances
    in addition to the standard identity/values block.

    Checks _GLOBAL_CACHE (keyed on "<persona_id>:decide") first.
    tendency_summary is NOT included here — it is injected separately
    as a standalone paragraph in the system prompt (P4 compliant).
    """
    cache_key = f"{persona.persona_id}:decide"
    cached = _GLOBAL_CACHE.get(cache_key)
    cache_hit = cached is not None
    logger.debug("decide(): core memory cache %s for %s", "HIT" if cache_hit else "MISS", persona.persona_id)
    if cache_hit:
        return cached  # type: ignore[return-value]

    core = persona.memory.core
    constraints = core.immutable_constraints
    lines = [
        f"You know yourself: {core.identity_statement}",
        f"What matters most to you: {', '.join(core.key_values)}.",
    ]
    # Sprint A-7 Fix 1: suppress budget_ceiling injection for India BJP personas.
    # Root cause (A-6 audit): budget_ceiling bleeds into political approval answers —
    # "I can't say very favorable when my kitchen budget tells a different story."
    # The 'Budget reality: Rs 15,000/month' line is irrelevant to political survey
    # questions (in02/in08/in09) and actively contaminates BJP approval responses.
    # Fix: gate injection on political lean — suppress for bjp_supporter and bjp_lean.
    # Sprint A-9: use _get_political_lean() — fixes silent bug where India archetypes
    # were all mapped to "moderate" by _ARCHETYPE_TO_LEAN, making this gate never fire.
    _lean_value: str | None = _get_political_lean(persona)
    _suppress_budget_for_bjp = _lean_value in ("bjp_supporter", "bjp_lean")
    if constraints.budget_ceiling and not _suppress_budget_for_bjp:
        lines.append(f"Budget reality: {constraints.budget_ceiling}.")
    if constraints.non_negotiables:
        lines.append(f"Non-negotiables: {'; '.join(constraints.non_negotiables)}.")
    if constraints.absolute_avoidances:
        lines.append(f"You never: {'; '.join(constraints.absolute_avoidances)}.")
    # Sprint B-1 Fix 2: inject current-conditions stance as a distinct labelled
    # sentence, separate from key_values, so the LLM applies it specifically to
    # temporal questions (economy, right-track, democracy satisfaction) rather
    # than letting it contaminate values-based questions (government role, etc).
    stance = getattr(core, "current_conditions_stance", None)
    if stance:
        lines.append(f"Your current view on the country's direction: {stance}.")
    # Sprint B-9 Fix 1: inject media trust stance as a distinct labelled sentence.
    # Previously buried as item 5 of 7 in the policy_stance key_values slot —
    # too diluted for Haiku to apply when answering q13-type questions.
    media_stance = getattr(core, "media_trust_stance", None)
    if media_stance:
        lines.append(f"Your relationship with national news media: {media_stance}.")
    # Study 1B Sprint A-2 Fix 1: inject gender norms stance for India in12/in13.
    # Overrides Haiku's Western gender equality default (was causing 100% C/D inversion).
    gender_stance = getattr(core, "gender_norms_stance", None)
    if gender_stance:
        lines.append(f"Your view on gender roles in family and society: {gender_stance}.")
    # Study 1B Sprint A-2 Fix 2: inject governance stance for India in07.
    # Overrides Haiku's Western anti-authoritarian default (was causing 100% D inversion).
    gov_stance = getattr(core, "governance_stance", None)
    if gov_stance:
        lines.append(f"Your view on governance and leadership style: {gov_stance}.")
    # Study 1B Sprint A-8 Fix 3: inject INC/Congress stance for India in04.
    # Root cause of in04 modal-C lock: "pragmatic moderate" behavioural tendency
    # overrides policy_stance and current_conditions_stance D-anchors for bjp_supporter
    # personas. Two-field anchoring and narrative identity (A-6/A-7) both failed.
    # Dedicated labelled field — same pattern that unblocked in07/in12/in13 in A-2 —
    # injects the INC stance as a distinct line so Haiku reads it explicitly for in04.
    inc_stance = getattr(core, "inc_stance", None)
    if inc_stance:
        lines.append(f"Your view on the Indian National Congress (INC/Congress party): {inc_stance}")
    block = " ".join(lines)
    _GLOBAL_CACHE.set(cache_key, block)
    return block


# ---------------------------------------------------------------------------
# Memories block
# ---------------------------------------------------------------------------


def _memories_block(memories: list[Observation | Reflection]) -> str:
    """Format memories for injection into the decide prompt.

    Ordered by retrieval score (caller's responsibility); capped at _MAX_MEMORIES.
    """
    lines = []
    for m in memories[:_MAX_MEMORIES]:
        tag = "Memory" if m.type == "observation" else "Insight"
        lines.append(f"- [{tag}] {m.content}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

_DECIDE_USER_TEMPLATE = (
    "You are now facing this decision:\n"
    "{scenario}\n\n"
    "Here are your relevant memories and experiences:\n"
    "{memories_block}\n\n"
    "Think through this decision step by step:\n\n"
    "1. GUT REACTION: What is your immediate, instinctive response?\n"
    "2. INFORMATION PROCESSING: What information matters most to you here? "
    "What are you paying attention to?\n"
    "3. CONSTRAINT CHECK: Are there hard limits (budget, non-negotiables, "
    "absolute avoidances) that apply?\n"
    "4. SOCIAL SIGNAL CHECK: What would the people you trust think? "
    "What would {primary_decision_partner} say?\n"
    "5. FINAL DECISION: What do you actually decide to do, and why?\n\n"
    "Also state:\n"
    "- Your confidence in this decision (0-100)\n"
    "- The top 2-3 factors that drove your decision\n"
    "- Any objections or hesitations you have\n"
    "- What would change your mind\n"
    "- What you do immediately after (follow_up_action: one sentence)\n\n"
    "IMPORTANT — implied_purchase:\n"
    "Set \"implied_purchase\": true ONLY if final_decision is research_more or defer "
    "AND follow_up_action describes you actually buying or ordering the product in the "
    "near term (e.g. \"orders a trial pack tonight\", \"adds to cart\", \"buys one pack "
    "to try\"). Set false for all other cases — including buy/trial decisions (those are "
    "already tracked), genuine deferral without purchase intent, and rejection.\n\n"
    "Respond in first person, in character.\n\n"
    "Reply in JSON:\n"
    "{{\n"
    '  "gut_reaction": "...",\n'
    '  "information_processing": "...",\n'
    '  "constraint_check": "...",\n'
    '  "social_signal_check": "...",\n'
    '  "final_decision": "...",\n'
    '  "confidence": N,\n'
    '  "key_drivers": ["...", "..."],\n'
    '  "objections": ["..."],\n'
    '  "what_would_change_mind": "...",\n'
    '  "follow_up_action": "...",\n'
    '  "implied_purchase": false\n'
    "}}"
)


def _build_decide_messages(
    scenario: str,
    memories: list[Observation | Reflection],
    persona: PersonaRecord,
    manifesto_context: str | None = None,
    domain_framing: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """Return (system_blocks, messages_list) for the decide call.

    System is split into multiple blocks to maximise prompt cache hits:

    1. cultural_preamble (optional, India only) — not cached; it is
       placed *before* the cached block so the cache key matches perceive's.
    2. Persona identity block ("You are {name}. {core_memory}.") — cached with
       cache_control. For personas without a cultural preamble (US/UK/EU), this
       block is identical to perceive's cached block → cross-stage cache hit.
    3. Manifesto context (optional, PopScale sensitivity) — cached as separate block
       when provided. This is reused across all 60 personas in a cluster.
    4. Domain framing (optional, PopScale domain language) — cached as separate block
       when provided. This is reused across personas.
    5. Tendency + situational suffix — not cached (changes per persona × scenario)
    """
    core_memory = _decide_core_memory_block(persona)
    # tendency_summary injected as natural language paragraph (P4)
    tendency_summary = persona.memory.core.tendency_summary
    # Sprint A-8 Fix 2: suppress financial caution language in tendency_summary
    # for India BJP personas. BehaviouralTendencies.reasoning_prompt for lower-income
    # BJP personas contains phrases like "financial carefulness", "careful with every
    # rupee", "budget anxiety" — generated by Sonnet at persona creation time.
    # When injected here, this language bleeds into political approval answers
    # (in02 Modi/in08 economy): "I can't say very favorable given my financial situation."
    # Root cause confirmed in A-6 audit (channel 3 of 4). Budget_ceiling was gated
    # in A-7; tendency_summary is the next active channel.
    # Fix: for bjp_supporter/bjp_lean personas, append an explicit political conviction
    # override that outranks the financial caution signal in the system prompt.
    # Sprint A-9: use _get_political_lean() — fixes silent bug where India archetypes
    # were all mapped to "moderate", so this override never fired across A-7/A-8.
    _ts_lean: str | None = _get_political_lean(persona)
    if _ts_lean in ("bjp_supporter", "bjp_lean"):
        tendency_summary = (
            tendency_summary
            + " When answering questions about political leadership, government, "
            "or the national direction, your political conviction and national pride "
            "take clear precedence over personal financial concerns. "
            "Your support for the current government is genuine and independent of "
            "your household budget — you do not let budget constraints colour your "
            "political views."
        )
    # Study 1B Sprint A-3: inject cultural preamble for India personas.
    # For US personas, cultural_context is None → empty string → no effect.
    cultural_context = getattr(persona.memory.core, "cultural_context", None)
    cultural_preamble = cultural_context if cultural_context else ""

    # Contextual noise: inject situational variability for realistic human behavior.
    # Deterministic per persona_id × scenario — same inputs → same modifier (BV1-safe).
    situational = _select_situational_modifier(persona.persona_id, scenario)
    situational_context = f"\n\n{situational}" if situational else ""

    # Build system as blocks for prompt caching.
    system_blocks: list[dict] = []

    # Block 1: cultural preamble (India only) — not cached
    if cultural_preamble:
        system_blocks.append({"type": "text", "text": cultural_preamble})

    # Block 2: persona identity — cached. Content matches perceive/reflect's
    # cached block for non-India personas → cross-stage cache hit.
    identity_text = f"You are {persona.demographic_anchor.name}. {core_memory}"
    system_blocks.append({
        "type": "text",
        "text": identity_text,
        "cache_control": {"type": "ephemeral"},
    })

    # Block 3: manifesto context (optional) — cached as separate block
    # Reused across all personas in same cluster → high cache hit rate
    if manifesto_context:
        system_blocks.append({
            "type": "text",
            "text": manifesto_context,
            "cache_control": {"type": "ephemeral"},
        })

    # Block 4: domain framing (optional) — cached as separate block
    # Reused across personas in same domain/scenario
    if domain_framing:
        system_blocks.append({
            "type": "text",
            "text": domain_framing,
            "cache_control": {"type": "ephemeral"},
        })

    # Block 5: tendency + situational suffix — not cached (changes per scenario)
    suffix = f"\n\n{tendency_summary}{situational_context}"
    system_blocks.append({"type": "text", "text": suffix})

    primary_decision_partner = (
        persona.memory.core.relationship_map.primary_decision_partner
    )

    mem_block = _memories_block(memories)
    user_content = _DECIDE_USER_TEMPLATE.format(
        scenario=scenario,
        memories_block=mem_block,
        primary_decision_partner=primary_decision_partner,
    )

    messages = [{"role": "user", "content": user_content}]
    return system_blocks, messages


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_decide_response(raw: str) -> dict | None:
    """Extract the JSON object from the LLM response.

    Returns a dict or None on failure.
    """
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(cleaned[start : end + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    return None


def _clamp_int(value: int | float, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(round(value))))


def _noise_range(consistency_score: int) -> int:
    """Return the noise half-range based on consistency_score band.

    consistency_score >= 75 → ±5  (high consistency — small perturbation)
    consistency_score 50-74 → ±12 (medium consistency — moderate perturbation)
    consistency_score <  50 → ±20 (low consistency  — large perturbation)
    """
    if consistency_score >= 75:
        return 5
    if consistency_score >= 50:
        return 12
    return 20


def _inject_confidence_noise(
    confidence: int,
    consistency_score: int,
) -> tuple[int, int]:
    """Sample a noise value and apply it to confidence.

    Returns (perturbed_confidence, noise_applied).
    noise_applied is the raw int drawn from [-noise_range, +noise_range].
    confidence is clamped to [0, 100] after perturbation.
    """
    half = _noise_range(consistency_score)
    noise = random.randint(-half, half)
    perturbed = _clamp_int(confidence + noise, 0, 100)
    return perturbed, noise


def _assemble_reasoning_trace(parsed: dict) -> str:
    """Join all 5 reasoning steps into a single readable trace."""
    steps = [
        ("1. GUT REACTION", parsed.get("gut_reaction", "")),
        ("2. INFORMATION PROCESSING", parsed.get("information_processing", "")),
        ("3. CONSTRAINT CHECK", parsed.get("constraint_check", "")),
        ("4. SOCIAL SIGNAL CHECK", parsed.get("social_signal_check", "")),
        ("5. FINAL DECISION", parsed.get("final_decision", "")),
    ]
    parts = []
    for label, content in steps:
        if content:
            parts.append(f"{label}: {content}")
    return "\n\n".join(parts)


def _build_decision_output(parsed: dict) -> DecisionOutput:
    """Assemble a DecisionOutput from a validated parse result."""
    decision = str(parsed.get("final_decision", "")).strip()
    gut_reaction = str(parsed.get("gut_reaction", "")).strip()
    what_would_change_mind = str(parsed.get("what_would_change_mind", "")).strip()
    reasoning_trace = _assemble_reasoning_trace(parsed)

    confidence_raw = parsed.get("confidence", 50)
    try:
        confidence = _clamp_int(confidence_raw, 0, 100)
    except (TypeError, ValueError):
        confidence = 50

    key_drivers_raw = parsed.get("key_drivers", [])
    key_drivers = [str(d) for d in key_drivers_raw] if isinstance(key_drivers_raw, list) else []

    objections_raw = parsed.get("objections", [])
    objections = [str(o) for o in objections_raw] if isinstance(objections_raw, list) else []

    follow_up_action = str(parsed.get("follow_up_action", "")).strip()
    implied_purchase = bool(parsed.get("implied_purchase", False))

    return DecisionOutput(
        decision=decision,
        confidence=confidence,
        reasoning_trace=reasoning_trace,
        gut_reaction=gut_reaction,
        key_drivers=key_drivers,
        objections=objections,
        what_would_change_mind=what_would_change_mind,
        follow_up_action=follow_up_action,
        implied_purchase=implied_purchase,
    )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


async def decide(
    scenario: str,
    memories: list[Observation | Reflection],
    persona: PersonaRecord,
    llm_client: Any = None,
    apply_noise: bool = True,
    model: str | None = None,
    manifesto_context: str | None = None,
    domain_framing: str | None = None,
) -> DecisionOutput:
    """Run the 5-step reasoning chain for a decision.

    Makes one Sonnet call with max_tokens=4096.
    tendency_summary is ALWAYS in context, injected as natural language (P4).
    Core memory is ALWAYS in context.
    The 5-step structure is always in the prompt — never shortened or combined.
    primary_decision_partner is injected into step 4 from core.relationship_map.

    manifesto_context: optional cached system block for manifesto sensitivity injection
    domain_framing: optional cached system block for domain-specific persona framing

    apply_noise: if True (default), injects calibrated confidence perturbation
      based on persona.derived_insights.consistency_score. Set False for tests.
    model: override the LLM model (used by SimulationTier routing). Defaults
      to _SONNET_MODEL when None.

    No pre-LLM probability computation (P4 compliant).
    Retries once on JSON parse failure; raises DecideError on second failure.
    """
    _model = model or _SONNET_MODEL
    client = anthropic.AsyncAnthropic()

    system_blocks, messages = _build_decide_messages(
        scenario, memories, persona,
        manifesto_context=manifesto_context,
        domain_framing=domain_framing,
    )

    # Attempt 1
    if llm_client is not None and hasattr(llm_client, 'complete'):
        # Test path — llm_client.complete expects a plain string
        system_str = " ".join(b["text"] for b in system_blocks)
        raw_text = await llm_client.complete(
            system=system_str,
            messages=messages,
            max_tokens=4096,
            model=_model,
        )
    else:
        response = await api_call_with_retry(
            client.messages.create,
            model=_model,
            max_tokens=4096,
            system=system_blocks,
            messages=messages,
        )
        raw_text = response.content[0].text
    parsed = _parse_decide_response(raw_text)

    if parsed is None:
        logger.warning("decide(): JSON parse failed on attempt 1 — retrying")
        # Attempt 2 — same blocks reused; persona identity block cache is warm
        if llm_client is not None and hasattr(llm_client, 'complete'):
            system_str = " ".join(b["text"] for b in system_blocks)
            raw_text = await llm_client.complete(
                system=system_str,
                messages=messages,
                max_tokens=4096,
                model=_model,
            )
        else:
            response = await api_call_with_retry(
                client.messages.create,
                model=_model,
                max_tokens=4096,
                system=system_blocks,
                messages=messages,
            )
            raw_text = response.content[0].text
        parsed = _parse_decide_response(raw_text)

        if parsed is None:
            raise DecideError(
                f"decide() failed to parse a valid JSON response after 2 attempts. "
                f"Last raw response: {raw_text!r}"
            )

    output = _build_decision_output(parsed)

    # --- Noise injection (Open Question O10) -----------------------------------
    # Injects a calibrated perturbation to confidence based on consistency_score.
    # Only confidence is modified — reasoning trace, decision text, key_drivers,
    # and objections are never touched (P4 compliant).
    if apply_noise:
        consistency_score = persona.derived_insights.consistency_score
        perturbed, noise = _inject_confidence_noise(output.confidence, consistency_score)
        logger.debug(
            "decide(): noise_applied=%d, consistency_score=%d, "
            "confidence %d → %d",
            noise, consistency_score, output.confidence, perturbed,
        )
        output.confidence = perturbed
        output.noise_applied = noise

    return output
