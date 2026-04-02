"""Pydantic v2 request/response models for the Simulatte Persona Generator API."""
from __future__ import annotations

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    count: int = 5
    domain: str = "cpg"
    mode: str = "quick"
    anchor_overrides: dict = {}
    persona_id_prefix: str = "pg"
    sarvam_enabled: bool = False
    skip_gates: bool = False


class SimulateRequest(BaseModel):
    cohort_id: str
    scenario: dict  # {"stimuli": [...], "decision_scenario": None}
    rounds: int = 3


class SurveyRequest(BaseModel):
    cohort_id: str
    questions: list[str]
    model: str = "claude-haiku-4-5-20251001"


class GenerateResponse(BaseModel):
    cohort_id: str
    persona_count: int
    cohort: dict  # the full CohortEnvelope dict


class SimulateResponse(BaseModel):
    cohort_id: str
    results: dict


class SurveyResponse(BaseModel):
    cohort_id: str
    responses: dict


class ReportResponse(BaseModel):
    cohort_id: str
    report: str
