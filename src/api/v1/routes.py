"""v1 API routes — async-first calibration + cohort access.

All routes are mounted under `/v1/` and require the API key dependency
(see src/api/auth.require_api_key). The `/health` endpoint stays open at the
parent app level.
"""
from __future__ import annotations

import hashlib
import logging
import os
import random
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import require_api_key
from src.api.v1.schemas import (
    CalibrationCreateRequest,
    CalibrationCreateResponse,
    CalibrationStatusResponse,
    CohortMetaResponse,
    CostSummaryResponse,
    PersonaItem,
    PersonaListResponse,
    SampleRequest,
    SampleResponse,
)
from src.db.models import CalibrationJob, Cohort, CostEvent, Persona
from src.db.session import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])


# ---------------------------------------------------------------------------
# Calibrations
# ---------------------------------------------------------------------------

@router.post("/calibrations", response_model=CalibrationCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_calibration(
    req: CalibrationCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> CalibrationCreateResponse:
    """Enqueue a deep-persona calibration job.

    Returns immediately with `{job_id, status:'queued'}`. The background worker
    picks up queued jobs and runs the orchestrator.
    """
    job_id = uuid.uuid4()
    job = CalibrationJob(
        id=job_id,
        tenant_id=req.tenant_id,
        payload=req.model_dump(mode="json"),
        status="queued",
        callback_url=req.callback_url,
        callback_secret=req.callback_secret,
    )
    session.add(job)
    await session.commit()
    return CalibrationCreateResponse(job_id=job_id, status="queued")


@router.get("/calibrations/{job_id}", response_model=CalibrationStatusResponse)
async def get_calibration(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> CalibrationStatusResponse:
    job = await session.get(CalibrationJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    persona_count = 0
    cost_usd: float | None = None
    gate_warnings: list[str] = []
    if job.cohort_id is not None:
        cohort = await session.get(Cohort, job.cohort_id)
        if cohort is not None:
            persona_count = (
                await session.scalar(
                    select(func.count(Persona.id)).where(Persona.cohort_id == cohort.id)
                )
            ) or 0
            cost_usd = float(cohort.total_cost_usd) if cohort.total_cost_usd else None
            gate_warnings = list(cohort.gate_warnings or [])

    return CalibrationStatusResponse(
        job_id=job.id,
        status=job.status,
        cohort_id=job.cohort_id,
        persona_count=persona_count,
        gate_warnings=gate_warnings,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        cost_usd=cost_usd,
    )


@router.post("/calibrations/{job_id}/cancel")
async def cancel_calibration(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    job = await session.get(CalibrationJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    if job.status not in ("queued", "running"):
        return {"job_id": str(job_id), "status": job.status, "cancelled": False}
    job.status = "cancelled"
    job.completed_at = datetime.now(timezone.utc)
    await session.commit()
    return {"job_id": str(job_id), "status": "cancelled", "cancelled": True}


# ---------------------------------------------------------------------------
# Cohorts
# ---------------------------------------------------------------------------

@router.get("/cohorts/{cohort_id}", response_model=CohortMetaResponse)
async def get_cohort_meta(
    cohort_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> CohortMetaResponse:
    cohort = await session.get(Cohort, cohort_id)
    if cohort is None:
        raise HTTPException(status_code=404, detail=f"Cohort {cohort_id} not found")
    persona_count = (
        await session.scalar(
            select(func.count(Persona.id)).where(Persona.cohort_id == cohort.id)
        )
    ) or 0
    return CohortMetaResponse(
        id=cohort.id,
        tenant_id=cohort.tenant_id,
        status=cohort.status,
        persona_count=persona_count,
        gate_warnings=list(cohort.gate_warnings or []),
        total_cost_usd=float(cohort.total_cost_usd) if cohort.total_cost_usd else None,
        created_at=cohort.created_at,
        completed_at=cohort.completed_at,
    )


@router.get("/cohorts/{cohort_id}/personas", response_model=PersonaListResponse)
async def list_cohort_personas(
    cohort_id: uuid.UUID,
    segment: str | None = Query(default=None),  # accepted for compat, unused
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> PersonaListResponse:
    cohort = await session.get(Cohort, cohort_id)
    if cohort is None:
        raise HTTPException(status_code=404, detail=f"Cohort {cohort_id} not found")
    total = (
        await session.scalar(
            select(func.count(Persona.id)).where(Persona.cohort_id == cohort_id)
        )
    ) or 0
    rows = (
        await session.scalars(
            select(Persona)
            .where(Persona.cohort_id == cohort_id)
            .order_by(Persona.persona_index.asc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    items = [
        PersonaItem(
            id=p.id,
            persona_index=p.persona_index,
            dossier_snapshot=p.dossier_snapshot,
            content_hash=p.content_hash,
            picture_url=p.picture_url,
            display_bio=p.display_bio,
        )
        for p in rows
    ]
    return PersonaListResponse(
        personas=items,
        total=total,
        has_more=(offset + len(items)) < total,
    )


@router.post("/cohorts/{cohort_id}/sample", response_model=SampleResponse)
async def sample_cohort(
    cohort_id: uuid.UUID,
    req: SampleRequest,
    session: AsyncSession = Depends(get_session),
) -> SampleResponse:
    cohort = await session.get(Cohort, cohort_id)
    if cohort is None:
        raise HTTPException(status_code=404, detail=f"Cohort {cohort_id} not found")
    rows = (
        await session.scalars(
            select(Persona.id)
            .where(Persona.cohort_id == cohort_id)
            .order_by(Persona.persona_index.asc())
        )
    ).all()
    pool = list(rows)
    warnings: list[str] = []
    if not pool:
        return SampleResponse(persona_ids=[], sample_id="empty", warnings=["cohort_empty"])
    n = req.n
    if n > len(pool):
        warnings.append(f"requested {n} but cohort only has {len(pool)}; returning all")
        n = len(pool)

    seed_components = [str(cohort_id), str(req.seed or 0), str(req.ref_id or "")]
    seed_str = "|".join(seed_components)
    seed_int = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed_int)
    selected = rng.sample(pool, n)
    sample_id = hashlib.sha256(
        (seed_str + ":" + ",".join(str(s) for s in selected)).encode("utf-8")
    ).hexdigest()[:16]
    return SampleResponse(persona_ids=selected, sample_id=sample_id, warnings=warnings)


# ---------------------------------------------------------------------------
# Cost telemetry
# ---------------------------------------------------------------------------

@router.get("/cost/summary", response_model=CostSummaryResponse)
async def cost_summary(
    from_ts: datetime | None = Query(default=None, alias="from"),
    to_ts: datetime | None = Query(default=None, alias="to"),
    tenant_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> CostSummaryResponse:
    stmt = select(
        func.coalesce(func.sum(CostEvent.amount_usd), 0),
        func.count(CostEvent.id),
    )
    if from_ts is not None:
        stmt = stmt.where(CostEvent.created_at >= from_ts)
    if to_ts is not None:
        stmt = stmt.where(CostEvent.created_at <= to_ts)
    if tenant_id:
        stmt = stmt.where(CostEvent.tenant_id == tenant_id)
    row = (await session.execute(stmt)).one()
    return CostSummaryResponse(
        total_usd=float(row[0] or 0),
        event_count=int(row[1] or 0),
        from_ts=from_ts,
        to_ts=to_ts,
        tenant_id=tenant_id,
    )
