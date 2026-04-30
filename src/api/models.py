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


class SimulateWithPersonasRequest(BaseModel):
    """Phase 4 (B2): Run simulation with dossier_snapshots passed inline."""
    personas: list[dict]           # wr-populations dossier_snapshots
    scenario: dict                 # {"question": ..., "context": ..., "options": [...]}
    rounds: int = 3
    domain: str = "general"        # used as CohortEnvelope.domain for the temp file


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


class CohortDetailResponse(BaseModel):
    cohort_id: str
    persona_count: int
    cohort: dict  # raw CohortEnvelope dict


class PersonasResponse(BaseModel):
    cohort_id: str
    persona_count: int
    personas: list[dict]  # LittleJoys display-format dicts, keyed by persona_id


class CohortsListResponse(BaseModel):
    cohort_ids: list[str]


# ---------------------------------------------------------------------------
# Orchestration endpoint models
# ---------------------------------------------------------------------------

class OrchestrateRequest(BaseModel):
    """
    POST /orchestrate request body.

    Pass a PersonaGenerationBrief as a nested dict.
    auto_confirm is forced True server-side (no stdin prompt in API context).

    Minimal example::

        {
          "brief": {
            "client": "LittleJoys",
            "domain": "cpg",
            "business_problem": "Why do Mumbai parents switch nutrition brands?",
            "count": 30,
            "run_intent": "deliver",
            "sarvam_enabled": true,
            "anchor_overrides": {"location": "Mumbai"},
            "simulation": {
              "stimuli": ["Ad copy here", "Product detail here"],
              "decision_scenario": "Would you buy this today?"
            }
          }
        }
    """
    brief: dict  # Parsed into PersonaGenerationBrief by the handler


class OrchestrateResponse(BaseModel):
    """Full PersonaGenerationResult as a REST response."""
    run_id: str
    cohort_id: str
    tier_used: str
    count_delivered: int
    cost_actual: dict          # CostActual.to_dict()
    quality_report: dict       # QualityReport.to_dict()
    summary: str
    cohort_file_path: str | None = None
    pipeline_doc_path: str | None = None
    simulation_results: dict | None = None
    personas: list[dict]       # PersonaRecord dicts
    cohort_envelope: dict      # Full CohortEnvelope dict
