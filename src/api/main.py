"""Simulatte Persona Generator — FastAPI microservice.

Endpoints:
    POST /generate                  — Generate a new cohort
    POST /simulate                  — Run simulation on an existing cohort
    POST /survey                    — Run survey questions on an existing cohort
    GET  /cohorts                   — List all available cohort IDs
    GET  /cohort/{cohort_id}        — Get raw CohortEnvelope JSON
    GET  /cohort/{cohort_id}/personas — Get LittleJoys-format persona list
    GET  /report/{cohort_id}        — Get human-readable cohort report
    GET  /health                    — Health check

Usage:
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.api.models import (
    CohortDetailResponse,
    CohortsListResponse,
    GenerateRequest,
    GenerateResponse,
    PersonasResponse,
    ReportResponse,
    SimulateRequest,
    SimulateResponse,
    SurveyRequest,
    SurveyResponse,
)
from src.api.store import cohort_path, list_cohorts, load_cohort, save_cohort
from src.cli import _run_generation, _run_simulation, _run_survey

__version__ = "0.2.0"

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Simulatte Persona Generator API v%s starting up.", __version__)
    yield


app = FastAPI(
    title="Simulatte Persona Generator API",
    version=__version__,
    description="REST microservice wrapping the Simulatte Persona Generator CLI internals.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "version": __version__}


# ---------------------------------------------------------------------------
# Cohort retrieval
# ---------------------------------------------------------------------------

@app.get("/cohorts", response_model=CohortsListResponse)
async def get_cohorts() -> CohortsListResponse:
    """List all available cohort IDs (seed cohorts + session-generated)."""
    return CohortsListResponse(cohort_ids=list_cohorts())


@app.get("/cohort/{cohort_id}", response_model=CohortDetailResponse)
async def get_cohort(cohort_id: str) -> CohortDetailResponse:
    """Return the raw CohortEnvelope JSON for a given cohort_id."""
    cohort_data = load_cohort(cohort_id)
    if cohort_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cohort '{cohort_id}' not found.",
        )
    persona_count = len(cohort_data.get("personas", []))
    return CohortDetailResponse(
        cohort_id=cohort_id,
        persona_count=persona_count,
        cohort=cohort_data,
    )


@app.get("/cohort/{cohort_id}/personas", response_model=PersonasResponse)
async def get_cohort_personas(cohort_id: str) -> PersonasResponse:
    """Return personas in LittleJoys display format (via pilots/littlejoys app_adapter)."""
    cohort_data = load_cohort(cohort_id)
    if cohort_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cohort '{cohort_id}' not found.",
        )

    try:
        from pilots.littlejoys.app_adapter import persona_to_display_dict
        from src.schema.persona import PersonaRecord

        raw_personas = cohort_data.get("personas", [])
        display_personas: list[dict] = []
        for raw in raw_personas:
            try:
                record = PersonaRecord.model_validate(raw)
                display_personas.append(persona_to_display_dict(record))
            except Exception as e:
                logger.warning("Skipping persona due to parse error: %s", e)
                continue
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Persona adapter unavailable: {exc}",
        ) from exc

    return PersonasResponse(
        cohort_id=cohort_id,
        persona_count=len(display_personas),
        personas=display_personas,
    )


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest) -> GenerateResponse:
    """Generate a new cohort of personas."""
    if not req.domain:
        raise HTTPException(status_code=422, detail="domain must not be empty")

    try:
        envelope_dict = await _run_generation(
            count=req.count,
            domain=req.domain,
            mode=req.mode,
            anchor_overrides=req.anchor_overrides,
            persona_id_prefix=req.persona_id_prefix,
            domain_data=None,
            sarvam_enabled=req.sarvam_enabled,
            skip_gates=req.skip_gates,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # _run_generation with sarvam wraps the envelope under "envelope" key
    if "envelope" in envelope_dict:
        cohort_data = envelope_dict["envelope"]
    else:
        cohort_data = envelope_dict

    cohort_id = save_cohort(cohort_data)
    persona_count = len(cohort_data.get("personas", []))

    return GenerateResponse(
        cohort_id=cohort_id,
        persona_count=persona_count,
        cohort=cohort_data,
    )


# ---------------------------------------------------------------------------
# Simulation & survey
# ---------------------------------------------------------------------------

@app.post("/simulate", response_model=SimulateResponse)
async def simulate(req: SimulateRequest) -> SimulateResponse:
    """Run cognitive simulation on an existing cohort."""
    path = cohort_path(req.cohort_id)

    cohort_data = load_cohort(req.cohort_id)
    if cohort_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cohort '{req.cohort_id}' not found.",
        )

    try:
        result = await _run_simulation(path, req.scenario, req.rounds)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return SimulateResponse(cohort_id=req.cohort_id, results=result)


@app.post("/survey", response_model=SurveyResponse)
async def survey(req: SurveyRequest) -> SurveyResponse:
    """Run survey questions on an existing cohort."""
    path = cohort_path(req.cohort_id)

    cohort_data = load_cohort(req.cohort_id)
    if cohort_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cohort '{req.cohort_id}' not found.",
        )

    try:
        responses = await _run_survey(path, req.questions, req.model)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return SurveyResponse(cohort_id=req.cohort_id, responses=responses)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

@app.get("/report/{cohort_id}", response_model=ReportResponse)
async def report(cohort_id: str) -> ReportResponse:
    """Get a human-readable text report for an existing cohort."""
    path = cohort_path(cohort_id)

    cohort_data = load_cohort(cohort_id)
    if cohort_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cohort '{cohort_id}' not found.",
        )

    try:
        from src.persistence.envelope_store import load_envelope
        from src.reporting.cohort_report import format_cohort_report

        envelope = load_envelope(path)
        report_text = format_cohort_report(envelope)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ReportResponse(cohort_id=cohort_id, report=report_text)
