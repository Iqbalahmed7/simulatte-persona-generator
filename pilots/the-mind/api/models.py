"""pilots/the-mind/api/models.py — Pydantic request/response models for The Mind API."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class PersonaCard(BaseModel):
    """Lightweight persona summary for the persona selection grid."""

    slug: str
    persona_id: str
    name: str
    age: int
    city: str
    country: str
    life_stage: str
    description: str
    consistency_score: int
    decision_style: str
    trust_anchor: str
    primary_value_orientation: str


class ChatRequest(BaseModel):
    message: str
    include_reasoning: bool = True


class DecisionTrace(BaseModel):
    """Structured 5-step reasoning from decide()."""

    decision: str
    confidence: int
    gut_reaction: str
    key_drivers: list[str]
    objections: list[str]
    what_would_change_mind: str
    follow_up_action: str
    reasoning_trace: str


class ChatResponse(BaseModel):
    reply: str
    decision_trace: Optional[DecisionTrace] = None
    persona_id: str
    persona_name: str


class HealthResponse(BaseModel):
    status: str
    exemplars_loaded: int
    version: str
