"""Simulatte Persona Generator — FastAPI microservice.

Endpoints:
    POST /generate       — Generate a new cohort
    POST /simulate       — Run simulation on an existing cohort
    POST /survey         — Run survey questions on an existing cohort
    GET  /report/{cohort_id}  — Get human-readable cohort report
    GET  /health         — Health check

Usage:
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.api.models import (
    GenerateRequest,
    GenerateResponse,
    ReportResponse,
    SimulateRequest,
    SimulateResponse,
    SurveyRequest,
    SurveyResponse,
)
from src.api.store import cohort_path, load_cohort, save_cohort
from src.cli import _run_generation, _run_simulation, _run_survey

__version__ = "0.1.0"

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


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "version": __version__}


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
