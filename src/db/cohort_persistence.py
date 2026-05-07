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
        demo = p.get("demographic_anchor") or {}
        if not isinstance(demo, dict):
            demo = {}
        employment = demo.get("employment") or {}
        if not isinstance(employment, dict):
            employment = {}
        narrative = p.get("narrative") or {}
        if not isinstance(narrative, dict):
            narrative = {}
        first_person = narrative.get("first_person") or ""
        if not isinstance(first_person, str):
            first_person = ""

        dossier = {
            # Top-level dashboard-friendly fields (additive; original record preserved below)
            "name": demo.get("name"),
            "age": demo.get("age"),
            "occupation": (
                employment.get("job_role")
                or employment.get("title")
                or demo.get("occupation")
            ),
            "life_stage": demo.get("life_stage"),
            "demographics": demo,
            "bio": (first_person[:240] + "…") if len(first_person) > 240 else first_person,
            # Spread the full record so the-mind and existing consumers keep working.
            **p,
        }
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


def load_cohort_from_db(cohort_id: str) -> dict[str, Any] | None:
    """Reverse of persist_cohort — assemble a filesystem-shaped CohortEnvelope dict
    from Postgres so consumers (simulate_qna, /cohort/{id}, /cohort/{id}/personas)
    can read DB-stored cohorts without code changes.

    Returns None if not found or if DB is not configured. Best-effort; any DB
    failure logs and returns None so the caller can 404 cleanly.
    """
    try:
        from sqlalchemy import select

        from src.db.session import get_session_sync
    except Exception as exc:  # noqa: BLE001
        logger.warning("DB load skipped — session unavailable: %s", exc)
        return None

    # Accept both UUID and short legacy ids; the DB id is a UUID
    try:
        cohort_uuid = uuid.UUID(str(cohort_id))
    except (ValueError, AttributeError):
        return None

    try:
        with get_session_sync() as session:
            cohort = session.get(Cohort, cohort_uuid)
            if cohort is None:
                return None
            stmt = (
                select(Persona)
                .where(Persona.cohort_id == cohort_uuid)
                .order_by(Persona.persona_index)
            )
            persona_rows = session.execute(stmt).scalars().all()

            personas: list[dict[str, Any]] = []
            for row in persona_rows:
                snapshot = dict(row.dossier_snapshot or {})
                # life_stories was stored separately; merge it back so the
                # envelope matches what filesystem-mode consumers expect.
                if row.life_stories is not None and "life_stories" not in snapshot:
                    snapshot["life_stories"] = row.life_stories
                if row.picture_url and not snapshot.get("picture_url"):
                    snapshot["picture_url"] = row.picture_url
                if row.display_bio and not snapshot.get("display_bio"):
                    snapshot["display_bio"] = row.display_bio
                personas.append(snapshot)

            summary = cohort.summary or {}
            envelope: dict[str, Any] = {
                "cohort_id": str(cohort.id),
                "personas": personas,
                "domain": summary.get("domain"),
                "client": summary.get("client"),
                "tier": summary.get("tier"),
                "business_problem": summary.get("business_problem"),
                "_pqs": summary.get("pqs"),
                "brief": cohort.brief_json or {},
                "gate_warnings": list(cohort.gate_warnings or []),
                "total_cost_usd": (
                    float(cohort.total_cost_usd)
                    if cohort.total_cost_usd is not None
                    else None
                ),
                "generator_version": cohort.generator_version,
                "status": cohort.status,
            }
            return envelope
    except Exception as exc:  # noqa: BLE001
        logger.warning("load_cohort_from_db(%s) failed: %s", cohort_id, exc)
        return None
