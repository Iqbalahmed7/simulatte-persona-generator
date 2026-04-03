"""src/social/influence_engine.py — Stateless influence computation engine.

Computes susceptibility, signal strength, gated importance, and generates
SocialInfluenceEvents from a social network + cohort state.

No LLM calls. All computations are deterministic.
"""
from __future__ import annotations

import math
from typing import Optional
from uuid import uuid4

from src.schema.persona import PersonaRecord
from src.social.schema import (
    LEVEL_WEIGHTS,
    SocialInfluenceEvent,
    SocialNetwork,
    SocialSimulationLevel,
    TendencyShiftRecord,
)


# ---------------------------------------------------------------------------
# Susceptibility computation (§4)
# ---------------------------------------------------------------------------

def compute_susceptibility(persona: PersonaRecord) -> float:
    """Compute how susceptible this persona is to peer influence.

    Formula (§4 of architecture):
        base = social_proof_bias * 0.40
              + trust_orientation.weights.peer * 0.30
              + wom_receiver_openness * 0.30
        consistency_dampener = consistency_score / 100.0
        style_modifier = +0.10 if "social", -0.10 if "analytical", 0.0 otherwise
        susceptibility = clamp(base * (1.0 - 0.5 * dampener) + modifier, 0.0, 1.0)

    social_proof_bias and wom_receiver_openness: from attributes["social"][field].value
    If the "social" attribute category or the specific field is missing, fall back to 0.5.

    Returns float in [0.0, 1.0].
    """
    social_attrs = persona.attributes.get("social", {})

    social_proof_bias = (
        getattr(social_attrs.get("social_proof_bias"), "value", 0.5)
        if social_attrs.get("social_proof_bias")
        else 0.5
    )
    if not isinstance(social_proof_bias, (int, float)):
        social_proof_bias = 0.5

    wom_receiver_openness = (
        getattr(social_attrs.get("wom_receiver_openness"), "value", 0.5)
        if social_attrs.get("wom_receiver_openness")
        else 0.5
    )
    if not isinstance(wom_receiver_openness, (int, float)):
        wom_receiver_openness = 0.5

    peer_weight = persona.behavioural_tendencies.trust_orientation.weights.peer
    base = social_proof_bias * 0.40 + peer_weight * 0.30 + wom_receiver_openness * 0.30

    consistency_dampener = persona.derived_insights.consistency_score / 100.0
    decision_style = persona.derived_insights.decision_style
    style_modifier = (
        0.10 if decision_style == "social"
        else (-0.10 if decision_style == "analytical" else 0.0)
    )

    raw = base * (1.0 - 0.5 * consistency_dampener) + style_modifier
    return max(0.0, min(1.0, raw))


# ---------------------------------------------------------------------------
# Signal strength computation (§4)
# ---------------------------------------------------------------------------

def compute_signal_strength(persona: PersonaRecord) -> float:
    """Compute how influential this persona's output is as a transmitter.

    Formula (§4):
        signal_strength = decision_style_score * 0.50
                        + (consistency_score / 100.0) * 0.50

    Returns float in [0.0, 1.0].
    """
    dss = persona.derived_insights.decision_style_score
    cs = persona.derived_insights.consistency_score / 100.0
    return dss * 0.50 + cs * 0.50


# ---------------------------------------------------------------------------
# Gated importance (§3)
# ---------------------------------------------------------------------------

def compute_gated_importance(
    susceptibility: float,
    signal_strength: float,
    level: SocialSimulationLevel,
) -> int:
    """Compute the gated importance for a synthetic social stimulus.

    Formula (§4):
        raw_importance = round(susceptibility * signal_strength * 10)   # [1, 10]
        raw_importance = max(1, raw_importance)
        level_weight = LEVEL_WEIGHTS[level.value]
        gated_importance = max(1, round(raw_importance * level_weight))

    At ISOLATED level (weight=0.0): raw*0.0=0 → max(1, 0)=1.
    NOTE: generate_influence_events() suppresses all events at ISOLATED level
    before this function is called — so this value is never used at ISOLATED.

    Returns int in [1, 10].
    """
    level_weight = LEVEL_WEIGHTS[level.value]
    raw = max(1, round(susceptibility * signal_strength * 10))
    return max(1, round(raw * level_weight))


# ---------------------------------------------------------------------------
# Stimulus formatting (§1)
# ---------------------------------------------------------------------------

def format_as_stimulus(transmitter_name: str, expressed_position: str) -> str:
    """Format an influence event as a synthetic stimulus text.

    Pattern from §1:
        "[Name], someone you know, recently said: '[expressed_position_text]'"
    """
    return f"{transmitter_name}, someone you know, recently said: '{expressed_position}'"


# ---------------------------------------------------------------------------
# Generate influence events (§6)
# ---------------------------------------------------------------------------

def generate_influence_events(
    cohort_personas: list[PersonaRecord],
    network: SocialNetwork,
    level: SocialSimulationLevel,
    turn: int,
    prior_decisions: dict[str, str] | None = None,
) -> list[SocialInfluenceEvent]:
    """Generate all influence events for one simulation turn.

    Steps:
    1. If level == ISOLATED: return [] immediately.
    2. Build persona lookup dict: persona_id → PersonaRecord
    3. For each edge in network:
       a. Find transmitter and receiver personas (skip if either missing)
       b. If prior_decisions is provided and transmitter_id not in it: skip
       c. Get expressed_position from prior_decisions[transmitter_id]
       d. Compute susceptibility (receiver), signal_strength (transmitter)
       e. Compute gated_importance
       f. Format synthetic_stimulus_text via format_as_stimulus
       g. Create SocialInfluenceEvent with event_id=f"evt-{uuid4().hex[:8]}"
          source_output_type="decision" if prior_decisions else "observation"
    4. Return list of events

    Parameters
    ----------
    cohort_personas:  current PersonaRecord states for all personas
    network:          SocialNetwork with edges
    level:            SocialSimulationLevel
    turn:             current simulation turn number
    prior_decisions:  optional dict of persona_id → expressed position text
                      If None or transmitter not found: skip that edge
    """
    # Step 1: early exit at ISOLATED
    if level == SocialSimulationLevel.ISOLATED:
        return []

    # Step 2: build persona lookup
    persona_lookup: dict[str, PersonaRecord] = {
        p.persona_id: p for p in cohort_personas
    }

    level_weight = LEVEL_WEIGHTS[level.value]
    source_output_type = "decision" if prior_decisions is not None else "observation"

    events: list[SocialInfluenceEvent] = []

    # Step 3: iterate edges
    for edge in network.edges:
        transmitter_id = edge.source_id
        receiver_id = edge.target_id

        # a. skip if either persona is not in the cohort
        transmitter = persona_lookup.get(transmitter_id)
        receiver = persona_lookup.get(receiver_id)
        if transmitter is None or receiver is None:
            continue

        # b. skip if prior_decisions provided but transmitter has no entry
        if prior_decisions is not None and transmitter_id not in prior_decisions:
            continue

        # c. expressed position
        if prior_decisions is not None:
            expressed_position = prior_decisions[transmitter_id]
        else:
            # prior_decisions is None — this branch is reached only when
            # source_output_type == "observation", but we already skipped
            # edges without a decision above when prior_decisions is not None.
            # When prior_decisions is None, we still need an expressed_position;
            # use an empty string as placeholder per §6 (orchestrator fills in).
            expressed_position = ""

        # d. susceptibility and signal strength
        susceptibility = compute_susceptibility(receiver)
        signal_strength = compute_signal_strength(transmitter)

        # e. gated importance
        raw_importance = max(1, round(susceptibility * signal_strength * 10))
        gated_importance = max(1, round(raw_importance * level_weight))

        # f. stimulus text
        transmitter_name = transmitter.demographic_anchor.name
        synthetic_stimulus_text = format_as_stimulus(transmitter_name, expressed_position)

        # g. create event
        event = SocialInfluenceEvent(
            event_id=f"evt-{uuid4().hex[:8]}",
            turn=turn,
            transmitter_id=transmitter_id,
            receiver_id=receiver_id,
            edge_type=edge.edge_type,
            expressed_position=expressed_position,
            source_output_type=source_output_type,
            raw_importance=raw_importance,
            gated_importance=gated_importance,
            level_weight_applied=level_weight,
            susceptibility_score=susceptibility,
            signal_strength=signal_strength,
            synthetic_stimulus_text=synthetic_stimulus_text,
        )
        events.append(event)

    return events


# ---------------------------------------------------------------------------
# Tendency drift detection (§2, §6)
# ---------------------------------------------------------------------------

def check_tendency_drift(
    persona: PersonaRecord,
    social_reflections: list,   # list of Reflection objects from working memory
    level: SocialSimulationLevel,
    session_id: str,
    turn: int,
) -> list[TendencyShiftRecord]:
    """Detect potential tendency description drift (audit mode — does NOT modify persona).

    Conditions for drift detection (all required):
    1. level >= HIGH (level.value in {"high", "saturated"})
    2. len(social_reflections) >= 3

    If conditions not met: return [].

    When conditions met: produce TendencyShiftRecord entries for fields that
    COULD drift. For Sprint SA, this is detection-only — actual application
    of drift is handled by tendency_drift.py in Sprint SB.

    For Sprint SA: if conditions are met, return a TendencyShiftRecord for
    each of the three driftable fields indicating the POTENTIAL shift was
    detected. The description_after field is set to
    f"[PENDING DRIFT REVIEW — {len(social_reflections)} social reflections]"

    Fields checked (from §2):
    - "trust_orientation.description"
    - "switching_propensity.description"
    - "price_sensitivity.description"

    Returns list[TendencyShiftRecord] (empty if conditions not met).
    """
    # Condition 1: level must be HIGH or SATURATED
    if level.value not in {"high", "saturated"}:
        return []

    # Condition 2: at least 3 social reflections
    if len(social_reflections) < 3:
        return []

    # Gather source reflection IDs (use all available)
    reflection_ids = [r.id for r in social_reflections]

    description_after = f"[PENDING DRIFT REVIEW — {len(social_reflections)} social reflections]"

    driftable_fields = [
        (
            "trust_orientation.description",
            persona.behavioural_tendencies.trust_orientation.description,
        ),
        (
            "switching_propensity.description",
            persona.behavioural_tendencies.switching_propensity.description,
        ),
        (
            "price_sensitivity.description",
            persona.behavioural_tendencies.price_sensitivity.description,
        ),
    ]

    records: list[TendencyShiftRecord] = []
    for field_name, description_before in driftable_fields:
        record = TendencyShiftRecord(
            record_id=f"drift-{uuid4().hex[:8]}",
            persona_id=persona.persona_id,
            session_id=session_id,
            turn_triggered=turn,
            tendency_field=field_name,
            description_before=description_before,
            description_after=description_after,
            source_social_reflection_ids=reflection_ids,
            social_simulation_level=level,
        )
        records.append(record)

    return records
