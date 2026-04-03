"""src/calibration/feedback_loop.py

Client feedback loop: adjust persona tendency descriptions from real outcome data.

When a client provides real outcome data (persona X actually purchased, persona Y deferred),
this module finds which tendency was the primary predictor and adjusts its description.

Deterministic — no LLM calls. Only description strings are updated, not bands or weights
(bands require re-estimation which is out of scope for the feedback loop).
Spec ref: Validity Protocol C4 (client feedback trigger).
"""
from __future__ import annotations

import logging

from src.schema.persona import PersonaRecord

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Channel → tendency mapping
# ---------------------------------------------------------------------------

CHANNEL_TENDENCY_MAP: dict[str, str] = {
    "doctor_referral": "trust_orientation",
    "social_media": "trust_orientation",
    "price_promotion": "price_sensitivity",
    "word_of_mouth": "trust_orientation",
    "organic": "switching_propensity",
}


# ---------------------------------------------------------------------------
# Mismatch detection helpers
# ---------------------------------------------------------------------------

def _is_mismatch(
    tendency_name: str,
    actual_outcome: str,
    persona: PersonaRecord,
) -> bool:
    """Return True when the actual outcome contradicts what the tendency predicts.

    Rules (from spec brief):
    - "purchased" + price_sensitivity=high → mismatch (price-sensitive persona bought
      = stronger purchase propensity than expected)
    - "purchased" + trust_orientation.expert >= 0.65 → match (high expert trust + doctor
      channel = expected)
    - "rejected" + price_sensitivity=low → mismatch (low price sensitivity + rejection
      = something else is driving rejection)
    - Default: treat as match if outcome is "purchased" or "researched";
               mismatch if "rejected" unexpectedly
    """
    bt = persona.behavioural_tendencies

    if tendency_name == "price_sensitivity":
        if actual_outcome == "purchased" and bt.price_sensitivity.band == "high":
            # Price-sensitive persona still bought → underestimated purchase propensity
            return True
        if actual_outcome == "rejected" and bt.price_sensitivity.band == "low":
            # Low price sensitivity + rejection → something unexpected going on
            return True

    elif tendency_name == "trust_orientation":
        if actual_outcome == "purchased":
            expert_weight = bt.trust_orientation.weights.expert
            if expert_weight >= 0.65:
                # High expert trust + purchase = expected match
                return False
            # Purchased but low expert trust → might be mismatch
            return True

    # Default fallback rule
    if actual_outcome in ("purchased", "researched"):
        return False
    if actual_outcome == "rejected":
        return True

    # "deferred" and other values → treat as match (no strong signal)
    return False


# ---------------------------------------------------------------------------
# Note generation
# ---------------------------------------------------------------------------

def _build_feedback_note(
    tendency_name: str,
    actual_outcome: str,
    channel: str,
    is_mismatch: bool,
) -> str:
    """Build the feedback annotation string to append to a tendency description."""
    if is_mismatch:
        return (
            f" [Feedback: actual outcome '{actual_outcome}' via {channel}"
            f" suggests tendency may underestimate purchase propensity.]"
        )
    else:
        return (
            f" [Feedback: actual outcome '{actual_outcome}' via {channel}"
            f" is consistent with this tendency.]"
        )


# ---------------------------------------------------------------------------
# Core public function
# ---------------------------------------------------------------------------

def adjust_tendency_from_outcome(
    persona: PersonaRecord,
    outcome: dict,
) -> PersonaRecord:
    """Adjust a persona's tendency description based on a real observed outcome.

    Parameters
    ----------
    persona:
        The ``PersonaRecord`` to update.
    outcome:
        Dict with keys:

        - ``persona_id`` (str) — for reference / logging only
        - ``actual_outcome`` (str) — one of
          ``"purchased"`` | ``"deferred"`` | ``"rejected"`` | ``"researched"``
        - ``channel`` (str) — one of ``"doctor_referral"`` | ``"social_media"``
          | ``"price_promotion"`` | ``"word_of_mouth"`` | ``"organic"``

    Returns
    -------
    PersonaRecord
        A new ``PersonaRecord`` with the relevant tendency description updated.
        Bands and weights are never changed. If no matching tendency field is
        found the original persona is returned unchanged (a warning is logged).

    Notes
    -----
    - Deterministic — no LLM calls.
    - Only ``description`` strings are updated; bands and weights are immutable here.
    - Unknown channels fall back to ``switching_propensity``.
    - Spec ref: Validity Protocol C4.
    """
    actual_outcome: str = outcome.get("actual_outcome", "")
    channel: str = outcome.get("channel", "")
    persona_id: str = outcome.get("persona_id", persona.persona_id)

    # Determine which tendency to update
    tendency_name: str = CHANNEL_TENDENCY_MAP.get(channel, "switching_propensity")

    if channel not in CHANNEL_TENDENCY_MAP:
        logger.warning(
            "feedback_loop: unknown channel '%s' for persona '%s'; "
            "falling back to switching_propensity.",
            channel,
            persona_id,
        )

    # Determine match vs mismatch
    mismatch = _is_mismatch(tendency_name, actual_outcome, persona)

    # Build the note
    note = _build_feedback_note(tendency_name, actual_outcome, channel, mismatch)

    # Apply the update via nested model_copy (immutable Pydantic pattern)
    old_bt = persona.behavioural_tendencies

    try:
        if tendency_name == "price_sensitivity":
            old_desc = old_bt.price_sensitivity.description
            new_ps = old_bt.price_sensitivity.model_copy(
                update={"description": old_desc + note}
            )
            new_bt = old_bt.model_copy(update={"price_sensitivity": new_ps})

        elif tendency_name == "trust_orientation":
            old_desc = old_bt.trust_orientation.description
            new_to = old_bt.trust_orientation.model_copy(
                update={"description": old_desc + note}
            )
            new_bt = old_bt.model_copy(update={"trust_orientation": new_to})

        elif tendency_name == "switching_propensity":
            old_desc = old_bt.switching_propensity.description
            new_sp = old_bt.switching_propensity.model_copy(
                update={"description": old_desc + note}
            )
            new_bt = old_bt.model_copy(update={"switching_propensity": new_sp})

        else:
            # Schema error — unknown tendency field name
            logger.warning(
                "feedback_loop: tendency '%s' does not exist on BehaviouralTendencies "
                "for persona '%s'. Returning persona unchanged.",
                tendency_name,
                persona_id,
            )
            return persona

    except AttributeError:
        logger.warning(
            "feedback_loop: could not access tendency '%s' on persona '%s' "
            "(possible schema error). Returning persona unchanged.",
            tendency_name,
            persona_id,
        )
        return persona

    return persona.model_copy(update={"behavioural_tendencies": new_bt})


# ---------------------------------------------------------------------------
# Summarise helper
# ---------------------------------------------------------------------------

def summarise_outcomes(outcomes: list[dict]) -> dict:
    """Group outcomes by actual_outcome value.

    Parameters
    ----------
    outcomes:
        List of outcome dicts, each with at least an ``actual_outcome`` key.

    Returns
    -------
    dict
        Mapping of outcome label → count, e.g.::

            {"purchased": 12, "deferred": 5, "rejected": 2, "researched": 3}

        Only outcome labels that appear at least once are included.
    """
    counts: dict[str, int] = {}
    for outcome in outcomes:
        label = outcome.get("actual_outcome", "unknown")
        counts[label] = counts.get(label, 0) + 1
    return counts
