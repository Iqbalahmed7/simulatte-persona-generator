"""Run a single calibration job synchronously (called by the worker loop).

Wraps the existing async orchestrator (`invoke_persona_generator`) and the
cohort persistence helper. Quality gates are treated as informational warnings
— a job is `complete` as long as ≥1 persona was generated.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.db.cohort_persistence import persist_cohort
from src.db.models import CalibrationJob

logger = logging.getLogger(__name__)


def _build_brief_from_payload(payload: dict[str, Any]):
    """Translate the v1 calibration request payload into a PersonaGenerationBrief."""
    from src.orchestrator.brief import PersonaGenerationBrief, RunIntent

    anchor_overrides: dict[str, Any] = {}
    if payload.get("market"):
        anchor_overrides["location"] = payload["market"]
    if payload.get("age_min") is not None and payload.get("age_max") is not None:
        anchor_overrides["age_range"] = [payload["age_min"], payload["age_max"]]
    if payload.get("icp_description"):
        anchor_overrides["icp_description"] = payload["icp_description"]

    return PersonaGenerationBrief(
        client=payload.get("client") or payload["tenant_id"],
        domain=payload["domain"],
        business_problem=payload["business_problem"],
        count=int(payload["n_personas"]),
        run_intent=RunIntent.DELIVER,
        sarvam_enabled=bool(payload.get("sarvam_enabled", False)),
        anchor_overrides=anchor_overrides,
        skip_gates=bool(payload.get("skip_gates", False)),
        auto_confirm=True,
        emit_pipeline_doc=False,
    )


def run_job(session: Session, job: CalibrationJob) -> None:
    """Execute one job. Updates job status + persists cohort. Never raises."""
    from src.orchestrator.invoke import invoke_persona_generator

    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    job.attempt_count = (job.attempt_count or 0) + 1
    session.commit()

    try:
        brief = _build_brief_from_payload(job.payload)
        result = asyncio.run(invoke_persona_generator(brief))

        envelope = result.cohort_envelope or {}
        cost_usd = (
            float(result.cost_actual.total)
            if result.cost_actual and hasattr(result.cost_actual, "total")
            else None
        )
        cohort = persist_cohort(
            session,
            tenant_id=job.tenant_id,
            brief=job.payload,
            cohort_envelope=envelope,
            cost_usd=cost_usd,
            generator_version=getattr(result, "generator_version", None) or "0.2.0",
            created_by_module="v1.worker",
        )
        job.cohort_id = cohort.id
        # Personas generated → complete (gate failures are warnings, not errors)
        job.status = "complete" if envelope.get("personas") else "failed"
        if not envelope.get("personas"):
            job.error = "Orchestrator returned zero personas"
        job.completed_at = datetime.now(timezone.utc)
        session.commit()
        logger.info("Job %s complete cohort=%s status=%s", job.id, cohort.id, job.status)

        _maybe_callback(job, cohort.id, "complete")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Job %s failed: %s", job.id, exc)
        job.status = "failed"
        job.error = str(exc)[:2000]
        job.completed_at = datetime.now(timezone.utc)
        session.commit()
        _maybe_callback(job, None, "failed")


def _maybe_callback(job: CalibrationJob, cohort_id, status: str) -> None:
    """Best-effort POST to the caller's callback_url if provided."""
    if not job.callback_url:
        return
    try:
        import httpx
        headers = {"Content-Type": "application/json"}
        if job.callback_secret:
            headers["X-Callback-Secret"] = job.callback_secret
        body = {
            "job_id": str(job.id),
            "status": status,
            "cohort_id": str(cohort_id) if cohort_id else None,
        }
        with httpx.Client(timeout=10.0) as client:
            client.post(job.callback_url, json=body, headers=headers)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Callback POST to %s failed: %s", job.callback_url, exc)
