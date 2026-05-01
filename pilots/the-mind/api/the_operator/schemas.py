"""the_operator/schemas.py — Pydantic v2 request/response models."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request models ────────────────────────────────────────────────────────

class BuildTwinRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    company:   Optional[str] = Field(None, max_length=100)
    title:     Optional[str] = Field(None, max_length=100)
    mode:      str = Field("standard", pattern="^(standard|enriched|lite)$")

class EnrichTwinRequest(BaseModel):
    enrichment_text: str = Field(..., min_length=10, max_length=5000)

class ProbeMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)

class FrameScoreRequest(BaseModel):
    message: str = Field(..., min_length=10, max_length=5000)

class AdminEraseByNameRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)

class AdminAllowancePatch(BaseModel):
    twins_built:    Optional[int] = Field(None, ge=0)
    twin_refreshes: Optional[int] = Field(None, ge=0)
    probe_messages: Optional[int] = Field(None, ge=0)
    frame_scores:   Optional[int] = Field(None, ge=0)


# ── Response models ───────────────────────────────────────────────────────

class TwinCard(BaseModel):
    """Compact representation for list views."""
    id:               str
    full_name:        str
    company:          Optional[str]
    title:            Optional[str]
    mode:             str
    confidence:       str
    sources_count:    int
    created_at:       datetime
    last_probed_at:   Optional[datetime]
    last_refreshed_at: Optional[datetime]

class TwinDetail(TwinCard):
    """Full Twin with synthesised profile."""
    gaps:       Optional[str]
    profile:    dict[str, Any]      # parsed from JSON
    enrichment: Optional[str]
    recon_notes: Optional[str]      # raw — admin only; router strips for normal users

class ProbeSessionCard(BaseModel):
    id:              str
    twin_id:         str
    started_at:      datetime
    last_message_at: datetime
    ended_at:        Optional[datetime]
    message_count:   int

class ProbeMessageResponse(BaseModel):
    session_id:       str
    twin_message_id:  str
    note_message_id:  str
    twin_reply:       str
    operator_note:    str

class FrameAnnotation(BaseModel):
    segment:   str
    score:     float
    reads_as:  str
    risk:      Optional[str]

class FrameScoreResponse(BaseModel):
    id:                      str
    overall_score:           float
    reply_probability:       str    # high | medium | low
    annotations:             list[FrameAnnotation]
    weakest_point:           dict[str, str]    # {segment, issue}
    strongest_point:         dict[str, str]    # {segment, reason}
    single_change_to_improve: str

class OperatorAllowanceState(BaseModel):
    twin_build:    dict[str, int]   # {used, limit}
    twin_refresh:  dict[str, int]
    probe_message: dict[str, int]
    frame_score:   dict[str, int]
    resets_at:     str

class OperatorMeResponse(BaseModel):
    user:               dict[str, Any]
    operator_allowance: OperatorAllowanceState
