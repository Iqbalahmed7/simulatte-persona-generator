"""src/schema/cognition_outputs.py — Pydantic schemas for cognition tool-use outputs.

BRIEF-013: Structured Outputs Migration

These schemas are used as Anthropic tool input_schema definitions via
model_json_schema(). They match the dict shapes returned by the existing
_parse_*_response() functions so no downstream code changes are needed.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PerceiveOutput(BaseModel):
    content: str
    importance: int = Field(ge=1, le=10)
    emotional_valence: float = Field(ge=-1.0, le=1.0)


class DecideOutput(BaseModel):
    gut_reaction: str
    information_processing: str
    constraint_check: str
    social_signal_check: str
    final_decision: str
    confidence: int = Field(ge=0, le=100)
    key_drivers: list[str]
    objections: list[str]
    what_would_change_mind: str
    follow_up_action: str
    implied_purchase: bool


class ReflectItemOutput(BaseModel):
    """Single reflection item — matches the dict shape validated by
    _validate_and_build_reflection() in reflect.py."""
    content: str
    importance: int = Field(ge=1, le=10)
    emotional_valence: float = Field(ge=-1.0, le=1.0, default=0.0)
    source_observation_ids: list[str]


class ReflectOutput(BaseModel):
    """Wrapper emitted by the emit_reflections tool.

    reflect() returns a JSON array; tool-use requires a single object.
    We wrap the array in this container so tool_choice can be forced.
    The items field holds the list of reflections.
    """
    items: list[ReflectItemOutput]
