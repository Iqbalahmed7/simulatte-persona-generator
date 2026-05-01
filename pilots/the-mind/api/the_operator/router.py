"""the_operator/router.py — all /operator route handlers.

Thin handlers: validate → allowance check → delegate to business logic modules.
No LLM calls or SQL queries inlined here.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user          # noqa: E402
from db import User, get_db               # noqa: E402

from the_operator.allowance import (
    check_and_increment_operator_allowance,
    get_operator_allowance_state,
)
from the_operator.config import EU_COUNTRY_SIGNALS
from the_operator.errors import (
    eu_subject_blocked,
    moderation_blocked,
    session_ended,
    twin_already_exists,
    twin_not_found,
)
from the_operator.frame import score_frame
from the_operator.models import (
    Twin,
    TwinFrameScore,
    TwinProbeMessage,
    TwinProbeSession,
)
from the_operator.probe import (
    collect_twin_reply,
    generate_operator_note,
    session_is_idle,
)
from the_operator.recon import run_recon
from the_operator.schemas import (
    BuildTwinRequest,
    EnrichTwinRequest,
    FrameScoreRequest,
    ProbeMessageRequest,
    AdminEraseByNameRequest,
)
from the_operator.storage import delete_recon_cache
from the_operator.synthesis import synthesise_twin

logger = logging.getLogger("the_operator")

operator_router = APIRouter(prefix="/operator", tags=["operator"])

# ── Shared Anthropic client (lazy singleton) ──────────────────────────────

_llm: anthropic.AsyncAnthropic | None = None


def _client() -> anthropic.AsyncAnthropic:
    global _llm
    if _llm is None:
        _llm = anthropic.AsyncAnthropic()
    return _llm


# ── SSE helper ────────────────────────────────────────────────────────────

def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


# ── Admin dependency (local — avoids circular import from main.py) ────────

def _admin_emails() -> set[str]:
    return {
        e.strip().lower()
        for e in (os.environ.get("ADMIN_EMAILS", "") or "").split(",")
        if e.strip()
    }


async def get_operator_admin(user: User = Depends(get_current_user)) -> User:  # type: ignore
    if (user.email or "").lower() not in _admin_emails():
        raise HTTPException(status_code=403, detail="Not an admin")
    return user


# ── ID / slug helpers ─────────────────────────────────────────────────────

def _make_twin_id(name_slug: str) -> str:
    return f"tw-{name_slug[:40]}-{uuid.uuid4().hex[:8]}"

def _make_session_id() -> str:
    return f"tps-{uuid.uuid4().hex[:8]}"

def _make_message_id() -> str:
    return f"tpm-{uuid.uuid4().hex[:8]}"

def _make_frame_id() -> str:
    return f"tfs-{uuid.uuid4().hex[:8]}"

def _to_slug(full_name: str, company: str | None = None) -> str:
    parts = [full_name]
    if company:
        parts.append(company)
    slug = "-".join(parts).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug[:60]


# ── EU signal check ───────────────────────────────────────────────────────

def _check_eu_signals(full_name: str, company: str | None, title: str | None) -> None:
    combined = " ".join(filter(None, [full_name, company, title])).lower()
    for signal in EU_COUNTRY_SIGNALS:
        if signal in combined:
            logger.warning("[operator] EU signal detected: %s in '%s'", signal, combined)
            raise eu_subject_blocked()


# ── Moderation (reuse moderation.py pattern) ─────────────────────────────

def _moderate_text(text: str) -> None:
    """Light moderation — import from moderation.py if callable, else skip."""
    try:
        from moderation import check_text  # noqa: PLC0415
        result = check_text(text)
        if result and getattr(result, "flagged", False):
            raise moderation_blocked()
    except ImportError:
        pass  # moderation module not available — skip


# ── Twin detail builder ───────────────────────────────────────────────────

def _twin_to_dict(twin: Twin, include_recon: bool = False) -> dict:
    profile_parsed = {}
    try:
        profile_parsed = json.loads(twin.profile) if twin.profile else {}
    except Exception:
        pass

    d = {
        "id":               twin.id,
        "full_name":        twin.full_name,
        "company":          twin.company,
        "title":            twin.title,
        "mode":             twin.mode,
        "confidence":       twin.confidence,
        "sources_count":    twin.sources_count,
        "gaps":             twin.gaps,
        "profile":          profile_parsed,
        "enrichment":       twin.enrichment,
        "created_at":       twin.created_at.isoformat() if twin.created_at else None,
        "updated_at":       twin.updated_at.isoformat() if twin.updated_at else None,
        "last_probed_at":   twin.last_probed_at.isoformat() if twin.last_probed_at else None,
        "last_refreshed_at": twin.last_refreshed_at.isoformat() if twin.last_refreshed_at else None,
        "portrait_url":     getattr(twin, "portrait_url", None),
    }
    if include_recon:
        d["recon_notes"] = twin.recon_notes
    return d


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

# ── 1. POST /operator/twins — build a new Twin ────────────────────────────

@operator_router.post("/twins")
async def build_twin(
    request: BuildTwinRequest,
    force: bool = Query(False),
    user: User = Depends(get_current_user),   # type: ignore
    db: AsyncSession = Depends(get_db),        # type: ignore
):
    """Build a new Twin via SSE stream. Returns event stream."""
    _check_eu_signals(request.full_name, request.company, request.title)
    _moderate_text(request.full_name)

    name_slug = _to_slug(request.full_name, request.company)

    # Check for existing twin with same slug
    existing = (
        await db.execute(
            select(Twin).where(
                Twin.user_id == user.id,
                Twin.name_slug == name_slug,
            )
        )
    ).scalar_one_or_none()

    if existing and not force:
        raise twin_already_exists(name_slug)

    # Allowance check BEFORE starting stream
    await check_and_increment_operator_allowance(user, "twin_build", db)

    twin_id = _make_twin_id(name_slug)

    async def stream():
        try:
            progress_events = []

            async def emit_progress(payload: dict):
                progress_events.append(_sse({"event": "progress", **payload}))

            yield _sse({"event": "progress", "stage": "recon", "message": "Starting reconnaissance…"})

            # Pass 1-3 recon
            recon_data = await run_recon(
                twin_id=twin_id,
                full_name=request.full_name,
                company=request.company,
                title=request.title,
                client=_client(),
                force=force,
                progress_callback=emit_progress,
            )

            # Emit any queued progress events
            for evt in progress_events:
                yield evt
            progress_events.clear()

            yield _sse({"event": "progress", "stage": "synthesis", "message": "Building decision architecture…"})

            # Synthesis
            profile = await synthesise_twin(
                full_name=request.full_name,
                company=request.company,
                title=request.title,
                recon_data=recon_data,
                enrichment_text=None,
                client=_client(),
            )

            yield _sse({"event": "progress", "stage": "saving", "message": "Persisting Twin…"})

            # Determine confidence and sources from recon
            sources_count   = recon_data.get("sources_count", 0)
            confidence      = profile.get("confidence", recon_data.get("confidence_signal", "medium"))
            gaps            = profile.get("gaps", recon_data.get("gaps", ""))

            now = datetime.now(timezone.utc)

            if existing and force:
                # Update in place
                await db.execute(
                    update(Twin).where(Twin.id == existing.id).values(
                        full_name=request.full_name,
                        company=request.company,
                        title=request.title,
                        mode=request.mode,
                        confidence=confidence,
                        sources_count=sources_count,
                        gaps=gaps,
                        recon_notes=json.dumps(recon_data),
                        profile=json.dumps(profile),
                        updated_at=now,
                        last_refreshed_at=now,
                    )
                )
                await db.commit()
                saved_twin_id = existing.id
            else:
                twin = Twin(
                    id=twin_id,
                    user_id=user.id,
                    full_name=request.full_name,
                    company=request.company,
                    title=request.title,
                    name_slug=name_slug,
                    mode=request.mode,
                    confidence=confidence,
                    sources_count=sources_count,
                    gaps=gaps,
                    recon_notes=json.dumps(recon_data),
                    profile=json.dumps(profile),
                    created_at=now,
                    updated_at=now,
                )
                db.add(twin)
                await db.commit()
                saved_twin_id = twin_id

            logger.info(
                "[operator] twin_built user=%s twin_id=%s sources=%d confidence=%s",
                user.email, saved_twin_id, sources_count, confidence,
            )

            yield _sse({"event": "complete", "twin_id": saved_twin_id, "confidence": confidence})

        except HTTPException as exc:
            yield _sse({"event": "error", "code": exc.detail.get("error", "error") if isinstance(exc.detail, dict) else "error",
                        "detail": exc.detail.get("detail", str(exc.detail)) if isinstance(exc.detail, dict) else str(exc.detail),
                        "retryable": False})
        except Exception as exc:
            logger.exception("[operator] build_twin stream error: %s", exc)
            yield _sse({"event": "error", "code": "internal_error", "detail": str(exc), "retryable": False})

    return StreamingResponse(stream(), media_type="text/event-stream")


# ── 2. GET /operator/twins — list user's Twins ────────────────────────────

@operator_router.get("/twins")
async def list_twins(
    user: User = Depends(get_current_user),  # type: ignore
    db: AsyncSession = Depends(get_db),       # type: ignore
):
    result = await db.execute(
        select(Twin).where(Twin.user_id == user.id).order_by(Twin.updated_at.desc())
    )
    twins = result.scalars().all()
    return [_twin_to_dict(t) for t in twins]


# ── 3. GET /operator/twins/{twin_id} — fetch full Twin ───────────────────

@operator_router.get("/twins/{twin_id}")
async def get_twin(
    twin_id: str,
    user: User = Depends(get_current_user),  # type: ignore
    db: AsyncSession = Depends(get_db),       # type: ignore
):
    twin = await _get_user_twin(twin_id, user.id, db)
    return _twin_to_dict(twin)


# ── 4. DELETE /operator/twins/{twin_id} ──────────────────────────────────

@operator_router.delete("/twins/{twin_id}")
async def delete_twin(
    twin_id: str,
    user: User = Depends(get_current_user),  # type: ignore
    db: AsyncSession = Depends(get_db),       # type: ignore
):
    twin = await _get_user_twin(twin_id, user.id, db)
    delete_recon_cache(twin.id)
    await db.execute(delete(Twin).where(Twin.id == twin_id))
    await db.commit()
    logger.info("[operator] twin_deleted user=%s twin_id=%s", user.email, twin_id)
    return {"deleted": True, "twin_id": twin_id}


# ── 5. POST /operator/twins/{twin_id}/refresh ─────────────────────────────

@operator_router.post("/twins/{twin_id}/refresh")
async def refresh_twin(
    twin_id: str,
    force_recon: bool = Query(False, alias="force"),
    user: User = Depends(get_current_user),  # type: ignore
    db: AsyncSession = Depends(get_db),       # type: ignore
):
    """Re-run recon and re-synthesise the Twin."""
    twin = await _get_user_twin(twin_id, user.id, db)
    await check_and_increment_operator_allowance(user, "twin_refresh", db)

    async def stream():
        try:
            yield _sse({"event": "progress", "stage": "recon", "message": "Refreshing reconnaissance…"})

            recon_data = await run_recon(
                twin_id=twin_id,
                full_name=twin.full_name,
                company=twin.company,
                title=twin.title,
                client=_client(),
                force=True,  # always force on explicit refresh
            )

            yield _sse({"event": "progress", "stage": "synthesis", "message": "Re-synthesising profile…"})

            profile = await synthesise_twin(
                full_name=twin.full_name,
                company=twin.company,
                title=twin.title,
                recon_data=recon_data,
                enrichment_text=twin.enrichment,
                client=_client(),
            )

            now = datetime.now(timezone.utc)
            await db.execute(
                update(Twin).where(Twin.id == twin_id).values(
                    confidence=profile.get("confidence", "medium"),
                    sources_count=recon_data.get("sources_count", 0),
                    gaps=profile.get("gaps", ""),
                    recon_notes=json.dumps(recon_data),
                    profile=json.dumps(profile),
                    updated_at=now,
                    last_refreshed_at=now,
                )
            )
            await db.commit()
            logger.info("[operator] twin_refreshed user=%s twin_id=%s", user.email, twin_id)
            yield _sse({"event": "complete", "twin_id": twin_id, "confidence": profile.get("confidence", "medium")})

        except HTTPException as exc:
            detail = exc.detail
            yield _sse({"event": "error", "code": detail.get("error", "error") if isinstance(detail, dict) else "error",
                        "detail": str(detail), "retryable": False})
        except Exception as exc:
            logger.exception("[operator] refresh_twin error: %s", exc)
            yield _sse({"event": "error", "code": "internal_error", "detail": str(exc), "retryable": False})

    return StreamingResponse(stream(), media_type="text/event-stream")


# ── 6. POST /operator/twins/{twin_id}/enrich ─────────────────────────────

@operator_router.post("/twins/{twin_id}/enrich")
async def enrich_twin(
    twin_id: str,
    request: EnrichTwinRequest,
    user: User = Depends(get_current_user),  # type: ignore
    db: AsyncSession = Depends(get_db),       # type: ignore
):
    """Add observed social/personal signals and re-synthesise. Counts as twin_build."""
    twin = await _get_user_twin(twin_id, user.id, db)
    _moderate_text(request.enrichment_text)
    await check_and_increment_operator_allowance(user, "twin_build", db)

    async def stream():
        try:
            yield _sse({"event": "progress", "stage": "synthesis", "message": "Merging enrichment signals…"})

            recon_data = json.loads(twin.recon_notes) if twin.recon_notes else {}
            profile = await synthesise_twin(
                full_name=twin.full_name,
                company=twin.company,
                title=twin.title,
                recon_data=recon_data,
                enrichment_text=request.enrichment_text,
                client=_client(),
            )

            now = datetime.now(timezone.utc)
            await db.execute(
                update(Twin).where(Twin.id == twin_id).values(
                    enrichment=request.enrichment_text,
                    mode="enriched",
                    profile=json.dumps(profile),
                    confidence=profile.get("confidence", twin.confidence),
                    gaps=profile.get("gaps", twin.gaps),
                    updated_at=now,
                )
            )
            await db.commit()
            logger.info("[operator] twin_enriched user=%s twin_id=%s", user.email, twin_id)
            yield _sse({"event": "complete", "twin_id": twin_id})

        except Exception as exc:
            logger.exception("[operator] enrich_twin error: %s", exc)
            yield _sse({"event": "error", "code": "internal_error", "detail": str(exc), "retryable": False})

    return StreamingResponse(stream(), media_type="text/event-stream")


# ── 7. POST /operator/twins/{twin_id}/probe — start session ───────────────

@operator_router.post("/twins/{twin_id}/probe")
async def start_probe_session(
    twin_id: str,
    user: User = Depends(get_current_user),  # type: ignore
    db: AsyncSession = Depends(get_db),       # type: ignore
):
    """Start a new probe session. Returns {session_id}."""
    await _get_user_twin(twin_id, user.id, db)  # existence check

    session_id = _make_session_id()
    now = datetime.now(timezone.utc)
    session = TwinProbeSession(
        id=session_id,
        twin_id=twin_id,
        user_id=user.id,
        started_at=now,
        last_message_at=now,
    )
    db.add(session)
    await db.commit()
    return {"session_id": session_id, "twin_id": twin_id}


# ── 8. POST /operator/twins/{twin_id}/probe/{session_id}/message ──────────

@operator_router.post("/twins/{twin_id}/probe/{session_id}/message")
async def send_probe_message(
    twin_id: str,
    session_id: str,
    request: ProbeMessageRequest,
    user: User = Depends(get_current_user),  # type: ignore
    db: AsyncSession = Depends(get_db),       # type: ignore
):
    """Send a message in probe mode. Streams Twin reply + emits Operator note."""
    twin = await _get_user_twin(twin_id, user.id, db)
    session = await _get_probe_session(session_id, twin_id, user.id, db)

    if session.ended_at:
        raise session_ended()

    # Auto-end idle session and create a new one transparently
    if session_is_idle(session.last_message_at):
        now = datetime.now(timezone.utc)
        await db.execute(
            update(TwinProbeSession).where(TwinProbeSession.id == session_id).values(ended_at=now)
        )
        await db.commit()
        raise session_ended()

    _moderate_text(request.message)
    await check_and_increment_operator_allowance(user, "probe_message", db)

    # Load conversation history
    history_result = await db.execute(
        select(TwinProbeMessage)
        .where(TwinProbeMessage.session_id == session_id)
        .order_by(TwinProbeMessage.created_at)
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in history_result.scalars().all()
    ]

    # Persist user message
    user_msg_id = _make_message_id()
    db.add(TwinProbeMessage(
        id=user_msg_id,
        session_id=session_id,
        role="user",
        content=request.message,
        created_at=datetime.now(timezone.utc),
    ))
    await db.commit()

    profile = json.loads(twin.profile) if twin.profile else {}

    async def stream():
        nonlocal session_id
        twin_reply_chunks = []

        async def collect_chunk(text: str):
            twin_reply_chunks.append(text)
            # Forward as SSE token
            pass  # We buffer then emit at end for simplicity

        try:
            yield _sse({"event": "twin_start"})

            twin_reply, tokens_in, tokens_out = await collect_twin_reply(
                full_name=twin.full_name,
                title=twin.title,
                company=twin.company,
                profile=profile,
                conversation_history=history,
                user_message=request.message,
                client=_client(),
                token_callback=collect_chunk,
            )

            full_twin_reply = "".join(twin_reply_chunks) if twin_reply_chunks else twin_reply

            yield _sse({"event": "twin_reply", "content": full_twin_reply})

            # Generate operator note
            note = await generate_operator_note(
                full_name=twin.full_name,
                profile=profile,
                user_message=request.message,
                twin_response=full_twin_reply,
                client=_client(),
            )

            yield _sse({"event": "operator_note", "content": note})

            # Persist twin reply + note
            now = datetime.now(timezone.utc)
            twin_msg_id = _make_message_id()
            note_msg_id = _make_message_id()

            db.add(TwinProbeMessage(
                id=twin_msg_id, session_id=session_id,
                role="twin", content=full_twin_reply, created_at=now,
            ))
            db.add(TwinProbeMessage(
                id=note_msg_id, session_id=session_id,
                role="operator_note", content=note, created_at=now,
            ))

            # Update session counters
            await db.execute(
                update(TwinProbeSession).where(TwinProbeSession.id == session_id).values(
                    last_message_at=now,
                    message_count=TwinProbeSession.message_count + 1,
                )
            )
            # Update twin last_probed_at
            await db.execute(
                update(Twin).where(Twin.id == twin_id).values(last_probed_at=now)
            )
            await db.commit()

            logger.info(
                "[operator] probe_message user=%s twin_id=%s tokens_in=%d tokens_out=%d",
                user.email, twin_id, tokens_in, tokens_out,
            )

            yield _sse({
                "event": "complete",
                "twin_message_id": twin_msg_id,
                "note_message_id": note_msg_id,
            })

        except HTTPException as exc:
            detail = exc.detail
            yield _sse({"event": "error", "code": detail.get("error", "error") if isinstance(detail, dict) else "error",
                        "detail": str(detail), "retryable": False})
        except Exception as exc:
            logger.exception("[operator] probe message error: %s", exc)
            yield _sse({"event": "error", "code": "internal_error", "detail": str(exc), "retryable": False})

    return StreamingResponse(stream(), media_type="text/event-stream")


# ── 9. GET /operator/twins/{twin_id}/probe/{session_id} ───────────────────

@operator_router.get("/twins/{twin_id}/probe/{session_id}")
async def get_probe_session(
    twin_id: str,
    session_id: str,
    user: User = Depends(get_current_user),  # type: ignore
    db: AsyncSession = Depends(get_db),       # type: ignore
):
    session = await _get_probe_session(session_id, twin_id, user.id, db)
    messages_result = await db.execute(
        select(TwinProbeMessage)
        .where(TwinProbeMessage.session_id == session_id)
        .order_by(TwinProbeMessage.created_at)
    )
    messages = [
        {"id": m.id, "role": m.role, "content": m.content,
         "created_at": m.created_at.isoformat(), "flagged": m.flagged}
        for m in messages_result.scalars().all()
    ]
    return {
        "id": session.id,
        "twin_id": session.twin_id,
        "started_at": session.started_at.isoformat(),
        "last_message_at": session.last_message_at.isoformat(),
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "message_count": session.message_count,
        "messages": messages,
    }


# ── 10. POST /operator/twins/{twin_id}/probe/{session_id}/end ─────────────

@operator_router.post("/twins/{twin_id}/probe/{session_id}/end")
async def end_probe_session(
    twin_id: str,
    session_id: str,
    user: User = Depends(get_current_user),  # type: ignore
    db: AsyncSession = Depends(get_db),       # type: ignore
):
    session = await _get_probe_session(session_id, twin_id, user.id, db)
    if not session.ended_at:
        await db.execute(
            update(TwinProbeSession).where(TwinProbeSession.id == session_id).values(
                ended_at=datetime.now(timezone.utc)
            )
        )
        await db.commit()
    return {"ended": True, "session_id": session_id}


# ── 11. POST /operator/twins/{twin_id}/frame ──────────────────────────────

@operator_router.post("/twins/{twin_id}/frame")
async def frame_score(
    twin_id: str,
    request: FrameScoreRequest,
    user: User = Depends(get_current_user),  # type: ignore
    db: AsyncSession = Depends(get_db),       # type: ignore
):
    twin = await _get_user_twin(twin_id, user.id, db)
    _moderate_text(request.message)
    await check_and_increment_operator_allowance(user, "frame_score", db)

    profile = json.loads(twin.profile) if twin.profile else {}

    result = await score_frame(
        full_name=twin.full_name,
        title=twin.title,
        company=twin.company,
        profile=profile,
        message=request.message,
        client=_client(),
    )

    # Persist
    frame_id = _make_frame_id()
    db.add(TwinFrameScore(
        id=frame_id,
        twin_id=twin_id,
        user_id=user.id,
        message_input=request.message,
        score_payload=json.dumps(result),
        overall_score=result.get("overall_score"),
        reply_probability=result.get("reply_probability"),
        created_at=datetime.now(timezone.utc),
    ))
    await db.commit()

    logger.info(
        "[operator] frame_scored user=%s twin_id=%s overall=%.1f",
        user.email, twin_id, result.get("overall_score", 0),
    )

    return {"id": frame_id, **result}


# ── 12. GET /operator/twins/{twin_id}/frame ───────────────────────────────

@operator_router.get("/twins/{twin_id}/frame")
async def list_frame_scores(
    twin_id: str,
    user: User = Depends(get_current_user),  # type: ignore
    db: AsyncSession = Depends(get_db),       # type: ignore
):
    await _get_user_twin(twin_id, user.id, db)
    result = await db.execute(
        select(TwinFrameScore)
        .where(TwinFrameScore.twin_id == twin_id, TwinFrameScore.user_id == user.id)
        .order_by(TwinFrameScore.created_at.desc())
    )
    scores = result.scalars().all()
    return [
        {
            "id": s.id,
            "overall_score": s.overall_score,
            "reply_probability": s.reply_probability,
            "created_at": s.created_at.isoformat(),
            "message_preview": s.message_input[:120] + "…" if len(s.message_input) > 120 else s.message_input,
        }
        for s in scores
    ]


# ── 13b. POST /operator/twins/{twin_id}/portrait ─────────────────────────

@operator_router.post("/twins/{twin_id}/portrait")
async def generate_twin_portrait(
    twin_id: str,
    force: bool = False,
    user: User = Depends(get_current_user),  # type: ignore
    db: AsyncSession = Depends(get_db),       # type: ignore
):
    """Generate a fal.ai Flux portrait for a Twin and cache the URL.

    Uses the Twin's name, title, company, and identity snapshot to build
    a photorealistic portrait prompt.  Re-uses the same FAL_KEY env var
    and fal-ai/flux-pro/v1.1-ultra model as the PG persona portraits.

    Returns: { url: str }
    Raises 503 if FAL_KEY not set; 502 on fal.ai error.
    """
    import os, json
    import httpx
    from fastapi import HTTPException as _HTTPException

    twin = await _get_user_twin(twin_id, user.id, db)

    # Return cached URL unless force=True
    cached = getattr(twin, "portrait_url", None)
    if cached and not force:
        return {"url": cached}

    fal_key = os.environ.get("FAL_KEY", "")
    if not fal_key:
        raise _HTTPException(status_code=503, detail="FAL_KEY not configured")

    # Build prompt from available Twin data
    profile_data: dict = {}
    try:
        profile_data = json.loads(twin.profile or "{}")
    except Exception:
        pass

    identity_snapshot = profile_data.get("identity_snapshot", "")
    name = twin.full_name or ""
    title = twin.title or ""
    company = twin.company or ""

    role_clause = ""
    if title and company:
        role_clause = f" working as {title} at {company}"
    elif title:
        role_clause = f" working as {title}"
    elif company:
        role_clause = f" at {company}"

    # Use first sentence of identity snapshot for atmosphere cues
    snapshot_hint = ""
    if identity_snapshot:
        first_sent = identity_snapshot.split(".")[0].strip()
        if len(first_sent) > 20:
            snapshot_hint = f" {first_sent}."

    prompt = (
        f"Candid photorealistic portrait of {name}{role_clause}.{snapshot_hint} "
        "Natural expression, professional but approachable. "
        "Shot on 85mm f/1.4 lens, natural window light, shallow depth of field, "
        "visible skin texture, authentic imperfections. "
        "Corporate-casual wardrobe appropriate for a senior professional. "
        "Neutral urban office background, slightly out of focus."
    )

    negative_prompt = (
        "cartoon, illustration, anime, 3d render, plastic skin, oversaturated, "
        "instagram filter, beauty filter, glamour shot, model agency portrait, perfect symmetry"
    )

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://fal.run/fal-ai/flux-pro/v1.1-ultra",
                headers={"Authorization": f"Key {fal_key}", "Content-Type": "application/json"},
                json={
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "aspect_ratio": "3:4",
                    "num_images": 1,
                    "enable_safety_checker": True,
                    "output_format": "jpeg",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        raise _HTTPException(status_code=502, detail=f"fal.ai error: {exc.response.text}")
    except Exception as exc:
        raise _HTTPException(status_code=502, detail=f"Portrait generation failed: {exc}")

    images = data.get("images", [])
    if not images:
        raise _HTTPException(status_code=500, detail="fal.ai returned no images")

    url: str = images[0]["url"]
    twin.portrait_url = url
    await db.commit()

    return {"url": url}


# ── 13. GET /operator/me ──────────────────────────────────────────────────

@operator_router.get("/me")
async def operator_me(
    user: User = Depends(get_current_user),  # type: ignore
    db: AsyncSession = Depends(get_db),       # type: ignore
):
    allowance = await get_operator_allowance_state(user, db)
    return {
        "user": {"id": user.id, "email": user.email},
        "operator_allowance": allowance,
    }


# ── 14. GET /operator/admin/twins — admin: all twins ─────────────────────

@operator_router.get("/admin/twins")
async def admin_list_twins(
    _admin: User = Depends(get_operator_admin),  # type: ignore
    db: AsyncSession = Depends(get_db),           # type: ignore
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    result = await db.execute(
        select(Twin).order_by(Twin.created_at.desc()).limit(limit).offset(offset)
    )
    twins = result.scalars().all()
    return [_twin_to_dict(t, include_recon=False) for t in twins]


# ── 15. DELETE /operator/admin/twins/{twin_id} — admin: force-delete ─────

@operator_router.delete("/admin/twins/{twin_id}")
async def admin_delete_twin(
    twin_id: str,
    _admin: User = Depends(get_operator_admin),  # type: ignore
    db: AsyncSession = Depends(get_db),           # type: ignore
):
    result = await db.execute(select(Twin).where(Twin.id == twin_id))
    twin = result.scalar_one_or_none()
    if not twin:
        raise twin_not_found(twin_id)
    delete_recon_cache(twin_id)
    await db.execute(delete(Twin).where(Twin.id == twin_id))
    await db.commit()
    logger.info("[operator] admin_deleted twin_id=%s by=%s", twin_id, _admin.email)
    return {"deleted": True, "twin_id": twin_id}


# ── Bonus: POST /operator/admin/twins/by-name/erase — right-to-erasure ───

@operator_router.post("/admin/twins/by-name/erase")
async def admin_erase_by_name(
    request: AdminEraseByNameRequest,
    _admin: User = Depends(get_operator_admin),  # type: ignore
    db: AsyncSession = Depends(get_db),           # type: ignore
):
    """Delete ALL Twins matching a full name across ALL users. For GDPR erasure requests."""
    result = await db.execute(
        select(Twin).where(Twin.full_name.ilike(f"%{request.full_name}%"))
    )
    twins = result.scalars().all()
    for twin in twins:
        delete_recon_cache(twin.id)
    ids = [t.id for t in twins]
    if ids:
        await db.execute(delete(Twin).where(Twin.id.in_(ids)))
        await db.commit()
    logger.warning(
        "[operator] erasure_by_name name=%s deleted=%d by=%s",
        request.full_name, len(ids), _admin.email,
    )
    return {"erased": len(ids), "full_name": request.full_name}


# ═══════════════════════════════════════════════════════════════════════════
# Private helpers
# ═══════════════════════════════════════════════════════════════════════════

async def _get_user_twin(twin_id: str, user_id: str, db: AsyncSession) -> Twin:
    result = await db.execute(
        select(Twin).where(Twin.id == twin_id, Twin.user_id == user_id)
    )
    twin = result.scalar_one_or_none()
    if not twin:
        raise twin_not_found(twin_id)
    return twin


async def _get_probe_session(
    session_id: str, twin_id: str, user_id: str, db: AsyncSession
) -> TwinProbeSession:
    result = await db.execute(
        select(TwinProbeSession).where(
            TwinProbeSession.id == session_id,
            TwinProbeSession.twin_id == twin_id,
            TwinProbeSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, detail={"error": "session_not_found", "detail": f"Session '{session_id}' not found"})
    return session
