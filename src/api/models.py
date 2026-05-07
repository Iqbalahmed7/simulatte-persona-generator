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
    """Hybrid request shape — supports both legacy and engine compat-shim shapes.

    Legacy shape (used by /orchestrate and tests):  cohort_id + scenario + rounds.
    Engine compat shape (used by simulatte-engine /simulation/run forwarder):
        cohort_id + simulation_name + question + context + options + n_personas.
    Handler routes by which fields are present.
    """
    cohort_id: str
    # Legacy fields
    scenario: dict | None = None  # {"stimuli": [...], "decision_scenario": None}
    rounds: int = 3
    # Engine compat fields
    simulation_name: str | None = None
    question: str | None = None
    context: str | None = None
    options: list[dict] | None = None  # [{"id": "yes", "name": "Yes"}, ...]
    n_personas: int | None = None
    # Engine wraps Q&A inside scenario and passes `count` instead of n_personas.
    count: int | None = None


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
    # Engine compat shim — top-level fields the engine job-wrapper expects
    headline: str | None = None
    confidence_score: float | None = None
    strategic_implication: str | None = None
    distribution: list[dict] | None = None
    persona_responses: list[dict] | None = None


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
