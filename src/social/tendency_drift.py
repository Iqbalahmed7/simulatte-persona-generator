"""src/social/tendency_drift.py — Applies TendencyShiftRecord to persona description fields.

Only description prose fields may drift. Band fields NEVER change.
No LLM calls.
"""
from __future__ import annotations

from src.schema.persona import PersonaRecord
from src.social.schema import TendencyShiftRecord


# Mapping from tendency_field string → how to apply the update via model_copy
_DRIFTABLE_FIELDS = {
    "trust_orientation.description",
    "switching_propensity.description",
    "price_sensitivity.description",
}


def apply_tendency_drift(
    persona: PersonaRecord,
    shift_record: TendencyShiftRecord,
) -> PersonaRecord:
    """Apply a single TendencyShiftRecord to a persona.

    Updates ONLY the description field of the specified tendency.
    Band fields (band, weights, dominant) are NEVER changed.
    Returns a new PersonaRecord (model_copy). Input persona not mutated.

    If shift_record.tendency_field is not in _DRIFTABLE_FIELDS, returns persona unchanged.
    """
    if shift_record.tendency_field not in _DRIFTABLE_FIELDS:
        return persona

    bt = persona.behavioural_tendencies
    field_path = shift_record.tendency_field   # e.g. "trust_orientation.description"
    new_description = shift_record.description_after

    parent, attr = field_path.split(".")       # ("trust_orientation", "description")

    # Get the parent tendency object
    tendency_obj = getattr(bt, parent)

    # Create updated tendency with new description only
    new_tendency = tendency_obj.model_copy(update={attr: new_description})

    # Create updated BehaviouralTendencies
    new_bt = bt.model_copy(update={parent: new_tendency})

    # Create updated PersonaRecord
    return persona.model_copy(update={"behavioural_tendencies": new_bt})
