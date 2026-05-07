"""Persist orchestrator cohort envelopes into Postgres.

The PG orchestrator produces a `cohort_envelope` dict containing personas plus
metadata (gate_results, _pqs, etc.). This module wraps that dict into Postgres
rows in the new `cohorts` / `personas` / `cost_events` tables.

Used by both:
    * the v1 worker (background job processor)
    * the legacy /orchestrate compat shim (so cohorts persist even on legacy paths)
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.db.models import Cohort, CostEvent, Persona

logger = logging.getLogger(__name__)


def _gate_warnings_from_envelope(envelope: dict[str, Any]) -> list[str]:
    """Extract human-readable failure reasons from gate_results + waivers."""
    warnings: list[str] = []
    for gr in envelope.get("gate_results", []) or []:
        passed = bool(gr.get("passed", True))
        if not passed:
            gate = gr.get("gate", "unknown")
            reason = gr.get("reason") or gr.get("error") or "failed"
            warnings.append(f"{gate}: {reason}")
    for waiver in envelope.get("gate_waivers", []) or []:
        gate = waiver.get("gate", "unknown") if isinstance(waiver, dict) else str(waiver)
        warnings.append(f"waiver:{gate}")
    return warnings


def _hash_persona(p: dict[str, Any]) -> str:
    raw = json.dumps(p, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def persist_cohort(
    session: Session,
    *,
    tenant_id: str,
    brief: dict[str, Any],
    cohort_envelope: dict[str, Any],
    cost_usd: float | None,
    generator_version: str | None,
    created_by_module: str | None = None,
) -> Cohort:
    """Insert one cohort + N persona rows + 1 cost event. Returns the Cohort."""
    raw_personas = cohort_envelope.get("personas", []) or []
    gate_warnings = _gate_warnings_from_envelope(cohort_envelope)

    cohort = Cohort(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        status="complete" if raw_personas else "failed",
        brief_json=brief,
        summary={
            "domain": cohort_envelope.get("domain"),
            "client": cohort_envelope.get("client"),
            "tier": cohort_envelope.get("tier"),
            "business_problem": cohort_envelope.get("business_problem"),
            "pqs": cohort_envelope.get("_pqs"),
            "cohort_id_legacy": cohort_envelope.get("cohort_id"),
        },
        gate_warnings=gate_warnings,
        total_cost_usd=cost_usd,
        generator_version=generator_version,
        completed_at=datetime.now(timezone.utc),
        created_by_module=created_by_module,
    )
    session.add(cohort)
    session.flush()

    for idx, p in enumerate(raw_personas):
        if not isinstance(p, dict):
            continue
        dossier = p.get("dossier_snapshot") or p
        life_stories = p.get("life_stories") if isinstance(p, dict) else None
        picture_url = p.get("picture_url") if isinstance(p, dict) else None
        display_bio = p.get("display_bio") if isinstance(p, dict) else None
        persona_row = Persona(
            id=uuid.uuid4(),
            cohort_id=cohort.id,
            persona_index=idx,
            dossier_snapshot=dossier,
            life_stories=life_stories,
            content_hash=_hash_persona(p),
            picture_url=picture_url,
            display_bio=display_bio,
        )
        session.add(persona_row)

    if cost_usd is not None:
        session.add(
            CostEvent(
                id=uuid.uuid4(),
                cohort_id=cohort.id,
                tenant_id=tenant_id,
                kind="calibration_complete",
                amount_usd=cost_usd,
                event_metadata={
                    "n_personas": len(raw_personas),
                    "gate_warnings": gate_warnings,
                },
            )
        )

    session.commit()
    logger.info(
        "Persisted cohort %s (n=%d, warnings=%d)",
        cohort.id, len(raw_personas), len(gate_warnings),
    )
    return cohort
