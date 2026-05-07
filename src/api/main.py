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
    OrchestrateRequest,
    OrchestrateResponse,
    PersonasResponse,
    ReportResponse,
    SimulateRequest,
    SimulateResponse,
    SimulateWithPersonasRequest,
    SurveyRequest,
    SurveyResponse,
)
from src.api.store import STORE_DIR, cohort_path, list_cohorts, load_cohort, save_cohort


def _load_cohort_with_db_fallback(cohort_id: str) -> dict | None:
    """Primary: filesystem (legacy + seed). Fallback: Postgres (Phase C calibrations).

    Phase C calibrations persist cohorts via cohort_persistence.persist_cohort
    rather than the filesystem store, so /simulate (and friends) need to read
    from the DB when the filesystem store has no entry.
    """
    cohort_data = load_cohort(cohort_id)
    if cohort_data is not None:
        return cohort_data
    try:
        from src.db.cohort_persistence import load_cohort_from_db
        return load_cohort_from_db(cohort_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("DB fallback for cohort %s failed: %s", cohort_id, exc)
        return None
from src.cli import _run_generation, _run_simulation, _run_survey

__version__ = "0.3.0"

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Simulatte Persona Generator API v%s starting up.", __version__)
    # Best-effort DB engine init — only if DATABASE_URL is set
    import os as _os
    if _os.environ.get("DATABASE_URL"):
        try:
            from src.db.session import init_engine
            init_engine()
            logger.info("Database engine initialised")
        except Exception as exc:  # noqa: BLE001
            logger.warning("DB init failed (continuing without): %s", exc)
    else:
        logger.info("DATABASE_URL not set — running in legacy filesystem-only mode")
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

# Mount /v1 router (auth-gated, Postgres-backed)
try:
    from src.api.v1 import v1_router
    app.include_router(v1_router)
except Exception as _v1_err:  # noqa: BLE001
    logger.warning("v1 router unavailable: %s", _v1_err)


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
    cohort_data = _load_cohort_with_db_fallback(cohort_id)
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
    cohort_data = _load_cohort_with_db_fallback(cohort_id)
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
    """Run a simulation against an existing cohort.

    Two modes (auto-detected from request body shape):
      - Engine compat shim: question + options + n_personas → fast Q&A probe.
        Used by simulatte-engine's /simulation/run forwarder.
      - Legacy: scenario + rounds → full multi-round cognition loop.
    """
    cohort_data = _load_cohort_with_db_fallback(req.cohort_id)
    if cohort_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cohort '{req.cohort_id}' not found.",
        )

    # ── Engine compat shim path ───────────────────────────────────────────────
    if req.question is not None and req.options is not None:
        from src.api.simulate_qna import run_qna_simulation

        try:
            qna = await run_qna_simulation(
                cohort_data=cohort_data,
                question=req.question,
                context=req.context or "",
                options=req.options,
                n_personas=req.n_personas or 5,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        if not qna.get("ok"):
            raise HTTPException(
                status_code=502,
                detail=qna.get("error") or "Q&A simulation produced no responses.",
            )

        return SimulateResponse(
            cohort_id=req.cohort_id,
            results=qna,
            headline=qna.get("headline"),
            confidence_score=qna.get("confidence_score"),
            strategic_implication=qna.get("strategic_implication"),
            distribution=qna.get("distribution") or [],
            persona_responses=qna.get("persona_responses") or [],
        )

    # ── Legacy path ───────────────────────────────────────────────────────────
    if req.scenario is None:
        raise HTTPException(
            status_code=422,
            detail="Request must include either (question + options) for engine "
                   "compat shim, or `scenario` for legacy simulation.",
        )

    path = cohort_path(req.cohort_id)
    try:
        result = await _run_simulation(path, req.scenario, req.rounds)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return SimulateResponse(cohort_id=req.cohort_id, results=result)


@app.post("/simulate-with-personas", response_model=SimulateResponse)
async def simulate_with_personas(req: SimulateWithPersonasRequest) -> SimulateResponse:
    """Run cognitive simulation with dossier_snapshots injected inline.

    Phase 4 (B2): Accepts wr-populations deep persona dossiers directly —
    no pre-stored cohort required. Writes a temp envelope to STORE_DIR,
    runs _run_simulation on it, returns results. Temp files persist in /tmp
    and are cleaned up by the OS/Railway between restarts.
    """
    import uuid
    import datetime
    import json as _json

    cid = f"eph-{uuid.uuid4().hex[:12]}"
    envelope_dict = {
        "cohort_id": cid,
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "domain": req.domain,
        "business_problem": req.scenario.get("context", ""),
        "mode": "deep",
        "gate_waivers": [],
        "personas": req.personas,
    }
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    path = STORE_DIR / f"{cid}.json"
    with open(path, "w", encoding="utf-8") as fh:
        _json.dump(envelope_dict, fh, indent=2, default=str)

    try:
        result = await _run_simulation(str(path), req.scenario, req.rounds)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return SimulateResponse(cohort_id=cid, results=result)


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

# ---------------------------------------------------------------------------
# Orchestrate — single-call generate + simulate with cost estimate + quality
# ---------------------------------------------------------------------------

@app.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate(req: OrchestrateRequest) -> OrchestrateResponse:
    """
    Full orchestrated run: brief → cost estimate → generate → quality check → simulate.

    This is the recommended endpoint for external callers.  Pass a
    PersonaGenerationBrief as JSON; receive a PersonaGenerationResult as JSON.

    The cost estimate is computed server-side and included in the response
    (no interactive confirmation — set auto_confirm: true in the brief).
    """
    from src.orchestrator.brief import PersonaGenerationBrief
    from src.orchestrator.invoke import invoke_persona_generator

    try:
        brief_data = {**req.brief, "auto_confirm": True}
        brief = PersonaGenerationBrief(**brief_data)
        result = await invoke_persona_generator(brief)
        # Best-effort dual-persistence: ALSO write to Postgres if DB available.
        # Legacy filesystem write inside the orchestrator stays as the source of
        # truth for the legacy GET /cohort/{id} response shape.
        import os as _os
        if _os.environ.get("DATABASE_URL"):
            try:
                from src.db.cohort_persistence import persist_cohort
                from src.db.session import get_session_sync
                with get_session_sync() as _sess:
                    persist_cohort(
                        _sess,
                        tenant_id=brief.client or "legacy",
                        brief=brief.model_dump(mode="json"),
                        cohort_envelope=result.cohort_envelope or {},
                        cost_usd=float(result.cost_actual.total)
                        if result.cost_actual and hasattr(result.cost_actual, "total")
                        else None,
                        generator_version=__version__,
                        created_by_module="legacy.orchestrate",
                    )
            except Exception as _persist_err:  # noqa: BLE001
                logger.warning("legacy /orchestrate dual-persist failed: %s", _persist_err)
        return OrchestrateResponse(
            run_id=result.run_id,
            cohort_id=result.cohort_id,
            tier_used=result.tier_used,
            count_delivered=result.count_delivered,
            cost_actual=result.cost_actual.to_dict(),
            quality_report=result.quality_report.to_dict(),
            summary=result.summary,
            cohort_file_path=result.cohort_file_path,
            pipeline_doc_path=result.pipeline_doc_path,
            simulation_results=result.simulation_results,
            personas=result.personas,
            cohort_envelope=result.cohort_envelope,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
