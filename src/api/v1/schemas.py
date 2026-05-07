"""Pydantic request/response schemas for /v1/* endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Calibrations ──────────────────────────────────────────────────────────

class CalibrationCreateRequest(BaseModel):
    tenant_id: str = Field(..., description="Caller tenant identifier")
    n_personas: int = Field(..., ge=1, le=500)
    market: str | None = None
    domain: str = Field(..., description="Domain key (cpg, saas, ...)")
    business_problem: str = Field(...)
    age_min: int | None = Field(default=None, ge=0, le=120)
    age_max: int | None = Field(default=None, ge=0, le=120)
    icp_description: str | None = None
    skip_gates: bool = Field(default=False)
    callback_url: str | None = None
    callback_secret: str | None = None
    client: str | None = Field(
        default=None,
        description="Client / brand name; falls back to tenant_id if omitted.",
    )
    sarvam_enabled: bool = Field(default=False)


class CalibrationCreateResponse(BaseModel):
    job_id: uuid.UUID
    status: str


class CalibrationStatusResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    cohort_id: uuid.UUID | None = None
    persona_count: int = 0
    gate_warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cost_usd: float | None = None


# ── Cohorts ────────────────────────────────────────────────────────────────

class CohortMetaResponse(BaseModel):
    id: uuid.UUID
    tenant_id: str
    status: str
    persona_count: int
    gate_warnings: list[str] = Field(default_factory=list)
    total_cost_usd: float | None = None
    created_at: datetime
    completed_at: datetime | None = None


class PersonaItem(BaseModel):
    id: uuid.UUID
    persona_index: int
    dossier_snapshot: dict[str, Any]
    content_hash: str | None = None
    picture_url: str | None = None
    display_bio: str | None = None


class PersonaListResponse(BaseModel):
    personas: list[PersonaItem]
    total: int
    has_more: bool


class SampleRequest(BaseModel):
    n: int = Field(..., ge=1, le=500)
    seed: int | None = None
    ref_id: str | None = None


class SampleResponse(BaseModel):
    persona_ids: list[uuid.UUID]
    sample_id: str
    warnings: list[str] = Field(default_factory=list)


# ── Cost ───────────────────────────────────────────────────────────────────

class CostSummaryResponse(BaseModel):
    total_usd: float
    event_count: int
    from_ts: datetime | None = None
    to_ts: datetime | None = None
    tenant_id: str | None = None
