"""pilots/the-mind/api/main.py — The Mind FastAPI application.

Serves the 5 exemplar personas for the mind.simulatte.io investor demo.

Endpoints:
    GET  /health                      — Health check
    GET  /personas                    — 5 exemplar persona cards
    GET  /personas/{slug}             — Full PersonaRecord JSON
    GET  /personas/{slug}/attributes  — Attributes + provenance (investor view)
    POST /personas/{slug}/chat        — Chat with a persona (decide + respond)

Run from repo root:
    PYTHONPATH=. uvicorn pilots.the_mind_api:app --host 0.0.0.0 --port 8001

Or directly (path is resolved via __file__):
    cd "pilots/the-mind/api" && PYTHONPATH=../../.. uvicorn main:app --reload

Version: exemplar_set_v1_2026_04
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

# ── repo root on sys.path — must be before any src.* imports ──────────────
_HERE = Path(__file__).parent                        # pilots/the-mind/api/
_EXEMPLAR_DIR = _HERE.parent / "exemplar_set_v1"    # pilots/the-mind/exemplar_set_v1/
_REPO_ROOT = _HERE.parent.parent.parent              # repo root
sys.path.insert(0, str(_REPO_ROOT))

import anthropic                                      # noqa: E402
import httpx                                          # noqa: E402
from fastapi import Depends, FastAPI, HTTPException   # noqa: E402
from fastapi.middleware.cors import CORSMiddleware    # noqa: E402
from fastapi.responses import StreamingResponse       # noqa: E402
from pydantic import BaseModel                        # noqa: E402
# ── Auth + DB module load (fault-tolerant) ─────────────────────────────────
# If anything in auth.py / db.py / sqlalchemy raises at import time (missing
# env var, asyncpg unable to reach Postgres at startup, missing dep, etc.)
# we MUST keep the API up. Auth-gated endpoints will degrade to HTTP 503 but
# the rest of the API (exemplars, generation, probes without allowance) keeps
# serving traffic. The error is logged loudly so we can fix it.
import logging as _early_logging
_early_logger = _early_logging.getLogger("auth_bootstrap")

AUTH_ENABLED = False
AUTH_LOAD_ERROR: str | None = None

try:
    from sqlalchemy.ext.asyncio import AsyncSession       # noqa: E402
    from auth import (                                     # noqa: E402
        build_me_response,
        check_and_increment_allowance,
        get_current_user,
    )
    from db import User, Event, EventType, InviteCode, AccessRequest, get_db  # noqa: E402
    AUTH_ENABLED = True
    _early_logger.info("[auth] auth+db modules loaded; auth gating ENABLED")
except Exception as _auth_exc:
    AUTH_LOAD_ERROR = f"{type(_auth_exc).__name__}: {_auth_exc}"
    _early_logger.error(
        "[auth] FAILED to load auth/db modules — running without auth. "
        "Auth-gated endpoints will return HTTP 503. Reason: %s",
        AUTH_LOAD_ERROR,
        exc_info=True,
    )

    # Stub types and functions so the rest of main.py loads cleanly.
    # FastAPI evaluates Depends(get_current_user) at REQUEST time, so as long
    # as these names exist at import time the routes load fine.
    class AsyncSession:                                    # type: ignore[no-redef]
        pass

    class User:                                            # type: ignore[no-redef]
        id: str = ""
        email: str = ""

    class Event:                                           # type: ignore[no-redef]
        id: str = ""
        user_id: str = ""
        type: str = ""
        ref_id: str = ""
        created_at = None

    class EventType:                                       # type: ignore[no-redef]
        persona_generated = "persona_generated"
        probe_run = "probe_run"
        chat_message = "chat_message"
        persona_shared = "persona_shared"

    class InviteCode:                                      # type: ignore[no-redef]
        code: str = ""
        label: str | None = None
        max_uses: int | None = None
        used_count: int = 0
        active: bool = True
        created_at = None
        created_by_email: str | None = None
        created_by_user_id: str | None = None
        sent_to_email: str | None = None
        sent_at = None

    class AccessRequest:                                   # type: ignore[no-redef]
        id: str = ""
        user_id: str = ""
        reason: str | None = None
        status: str = "pending"
        created_at = None
        resolved_at = None
        resolved_by_email: str | None = None

    async def get_db():                                    # type: ignore[no-redef]
        raise HTTPException(503, detail={
            "error": "auth_unavailable",
            "reason": AUTH_LOAD_ERROR,
        })

    async def get_current_user(*args, **kwargs):           # type: ignore[no-redef]
        raise HTTPException(503, detail={
            "error": "auth_unavailable",
            "reason": AUTH_LOAD_ERROR,
        })

    async def check_and_increment_allowance(*args, **kwargs):  # type: ignore[no-redef]
        # No-op so endpoints don't crash if user somehow reaches them.
        return None

    async def build_me_response(*args, **kwargs):          # type: ignore[no-redef]
        raise HTTPException(503, detail={
            "error": "auth_unavailable",
            "reason": AUTH_LOAD_ERROR,
        })

from src.cognition.decide import decide              # noqa: E402
from src.cognition.respond import respond            # noqa: E402
from src.schema.persona import PersonaRecord         # noqa: E402

# Content moderation — wordlist + regex filter for profanity, sexual,
# and underage content. Always import (no DB dependency).
try:
    from moderation import (                          # noqa: E402
        ModerationError,
        ModerationResult,
        check_brief,
        enforce_brief_safety,
    )
except Exception as _mod_exc:                         # pragma: no cover
    _early_logger.error("[moderation] failed to load: %s", _mod_exc, exc_info=True)
    # Fail closed if the filter can't load: treat all input as flagged.
    class ModerationError(Exception):                 # type: ignore[no-redef]
        def __init__(self, *_args, **_kwargs):
            super().__init__("moderation_unavailable")
            class _R:
                flagged = True
                reason = "filter_unavailable"
                message = "Content moderation is unavailable. Please try again later."
                matched_terms: list[str] = []
            self.result = _R()

    class ModerationResult:                           # type: ignore[no-redef]
        flagged = False
        reason = ""
        message = ""
        matched_terms: list[str] = []

    def check_brief(text):                            # type: ignore[no-redef]
        return ModerationResult()

    def enforce_brief_safety(text):                   # type: ignore[no-redef]
        return None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Web API uses Haiku by default — 3-4× faster than Sonnet, sufficient for demo generation.
# Override with GENERATION_MODEL env var on Railway if you want Sonnet quality.
os.environ.setdefault("GENERATION_MODEL", "claude-haiku-4-5-20251001")

# ── ICP descriptions (mirrors generate_exemplars.py) ─────────────────────

_ICP_DESCRIPTIONS: dict[str, str] = {
    "priya": "Indian metro mother, 32, Mumbai — marketing manager, health-conscious, premium-curious",
    "madison": "US premium wellness seeker, 36, San Francisco — SaaS PM, clinical-backing required",
    "linnea": "European minimalist, 28, Stockholm — UX designer, climate-anxious, anti-maximalist",
    "arun": "Tier-2 Indian male, 42, Indore — small-business owner, value-seeker, YouTube-native",
    "david": "US senior, 64, Phoenix — retired teacher, managing hypertension, skeptical of marketing",
}

# ── exemplar cache ────────────────────────────────────────────────────────

_PERSONAS: dict[str, PersonaRecord] = {}

# ── generated persona cache + disk persistence ────────────────────────────
#
# Storage root resolution:
#   1. MIND_DATA_DIR env var if set (Railway: /app/pilots/the-mind/data, mounted volume)
#   2. Falls back to repo-local pilots/the-mind/ for dev (so UAT keeps working)
#
# This makes user-generated personas + probes survive Railway redeploys.
_DATA_ROOT = Path(os.environ.get("MIND_DATA_DIR", str(_HERE.parent))).resolve()
_DATA_ROOT.mkdir(parents=True, exist_ok=True)

_GENERATED: dict[str, dict] = {}
_GENERATED_DIR = _DATA_ROOT / "generated_personas"

_EXEMPLAR_PORTRAITS: dict[str, str] = {}   # slug → fal.io URL (exemplar personas)
_GENERATED_PORTRAITS: dict[str, str] = {}  # persona_id → fal.io URL (generated personas)

_PORTRAITS_FILE = _DATA_ROOT / "portraits.json"


def _load_portraits_from_disk() -> None:
    """Populate _EXEMPLAR_PORTRAITS and _GENERATED_PORTRAITS from portraits.json on disk.

    Keys starting with 'pg-' are generated persona portraits; all others are exemplar slugs.
    """
    if not _PORTRAITS_FILE.exists():
        return
    try:
        with open(_PORTRAITS_FILE, encoding="utf-8") as f:
            combined: dict[str, str] = json.load(f)
        for key, url in combined.items():
            if key.startswith("pg-"):
                _GENERATED_PORTRAITS[key] = url
            else:
                _EXEMPLAR_PORTRAITS[key] = url
        logger.info("[portraits] loaded %d entries from disk", len(combined))
    except Exception:
        logger.exception("[portraits] failed to load from disk")


def _save_portraits_to_disk() -> None:
    """Atomically write both portrait dicts back to portraits.json.

    Uses a .tmp file + os.replace() to avoid partial-write corruption.
    TODO: future improvement — download each JPG to the volume and serve it ourselves,
          since fal.media URLs expire after ~30 days.
    """
    try:
        combined = {**_EXEMPLAR_PORTRAITS, **_GENERATED_PORTRAITS}
        tmp_path = _PORTRAITS_FILE.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False)
        os.replace(tmp_path, _PORTRAITS_FILE)
    except Exception:
        logger.exception("[portraits] failed to save to disk")


# Populate at module load time so portraits survive Railway redeploys.
_load_portraits_from_disk()


def _persist_generated_dict(persona_dict: dict) -> None:
    """Write persona dict to disk so it survives server restarts."""
    _GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    path = _GENERATED_DIR / f"{persona_dict['persona_id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(persona_dict, f, ensure_ascii=False)


def _load_generated_from_disk() -> None:
    """Populate _GENERATED from any previously persisted JSON files."""
    if not _GENERATED_DIR.exists():
        return
    for p in sorted(_GENERATED_DIR.glob("*.json")):
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            persona_id = data.get("persona_id")
            if persona_id:
                _GENERATED[persona_id] = data
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load generated persona %s: %s", p.name, exc)


def _load_all() -> dict[str, PersonaRecord]:
    if _PERSONAS:
        return _PERSONAS
    if not _EXEMPLAR_DIR.exists():
        raise RuntimeError(
            f"Exemplar directory not found: {_EXEMPLAR_DIR}. "
            "Run pilots/the-mind/generate_exemplars.py first."
        )
    for json_path in sorted(_EXEMPLAR_DIR.glob("persona_*.json")):
        slug = json_path.stem.replace("persona_", "")
        with open(json_path, encoding="utf-8") as f:
            _PERSONAS[slug] = PersonaRecord.model_validate(json.load(f))
    return _PERSONAS


def _load_one(slug: str) -> PersonaRecord:
    personas = _load_all()
    if slug not in personas:
        raise KeyError(
            f"Persona '{slug}' not found. Available: {list(personas.keys())}"
        )
    return personas[slug]


# ── Pydantic models ───────────────────────────────────────────────────────

class PersonaCard(BaseModel):
    slug: str
    persona_id: str
    name: str
    age: int
    city: str
    country: str
    life_stage: str
    description: str
    consistency_score: int
    decision_style: str
    trust_anchor: str
    primary_value_orientation: str
    portrait_url: str | None = None


class ChatRequest(BaseModel):
    message: str
    include_reasoning: bool = True


class DecisionTrace(BaseModel):
    decision: str
    confidence: int
    gut_reaction: str
    key_drivers: list[str]
    objections: list[str]
    what_would_change_mind: str
    follow_up_action: str
    reasoning_trace: str


class ChatResponse(BaseModel):
    reply: str
    decision_trace: Optional[DecisionTrace] = None
    persona_id: str
    persona_name: str


class HealthResponse(BaseModel):
    status: str
    exemplars_loaded: int
    version: str


class ICPRequest(BaseModel):
    brief: str                         # natural-language persona description
    domain: str = "general"
    pdf_content: str | None = None     # base64-encoded PDF bytes (optional)


class PortraitRequest(BaseModel):
    persona_id: str
    name: str
    age: int
    gender: str
    city: str
    country: str


# `from __future__ import annotations` defers all annotations as strings.
# Pydantic v2 needs an explicit rebuild for any model that references another
# model via Optional/forward ref, otherwise instantiation raises
# "not fully defined" at runtime.
ChatResponse.model_rebuild()


async def _extract_from_brief(
    brief: str,
    pdf_b64: str | None,
    client: anthropic.AsyncAnthropic,
) -> tuple[dict, str, str]:
    """Parse a natural-language persona description into anchor_overrides, domain, and context.

    Returns: (anchor_overrides, domain, business_problem)
    """
    content: list = []

    if pdf_b64:
        content.append({
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64},
        })
        if brief.strip():
            content.append({"type": "text", "text": f"User description: {brief}"})
        else:
            content.append({"type": "text", "text": "Extract persona parameters from this document."})
    else:
        content.append({"type": "text", "text": brief})

    system = """Extract persona generation parameters from a natural-language description or research document.
Return ONLY valid JSON with this shape (omit fields not explicitly stated or clearly implied — never guess):
{
  "anchor": {
    "age": <int>,
    "gender": "<male|female>",
    "location": {"country": "<string>", "city": "<string>"},
    "occupation": "<string>",
    "life_stage": "<young_adult|early_career|mid_career|established|pre_retirement|retirement>",
    "household": {"size": <int>, "composition": "<e.g. married with 3 children>"},
    "income_level": "<lower_middle|middle|upper_middle|affluent>"
  },
  "domain": "<cpg|saas|health|general>",
  "business_problem": "<brief summary of what this persona is meant to help understand>"
}"""

    try:
        if pdf_b64:
            msg = await client.beta.messages.create(
                model="claude-haiku-4-5",
                max_tokens=600,
                system=system,
                messages=[{"role": "user", "content": content}],
                betas=["pdfs-2024-09-25"],
            )
        else:
            msg = await client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=600,
                system=system,
                messages=[{"role": "user", "content": content}],
            )
        raw = msg.content[0].text
        # Tolerate markdown fences or leading text before the JSON object
        try:
            data = json.loads(raw)
        except Exception:
            import re as _re
            m = _re.search(r"```(?:json)?\s*([\s\S]+?)```", raw)
            if m:
                data = json.loads(m.group(1))
            else:
                start, end = raw.find("{"), raw.rfind("}") + 1
                data = json.loads(raw[start:end]) if start >= 0 and end > start else {}
        anchor = data.get("anchor", {})
        # Strip empty nested dicts
        if isinstance(anchor.get("location"), dict):
            anchor["location"] = {k: v for k, v in anchor["location"].items() if v}
        if isinstance(anchor.get("household"), dict):
            anchor["household"] = {k: v for k, v in anchor["household"].items() if v}
        domain = data.get("domain", "general")
        biz = data.get("business_problem", brief[:400] or "General persona simulation")
        return anchor, domain, biz
    except Exception as exc:
        logger.warning("[extract_brief] failed: %s", exc)
        return {}, "general", brief[:400] or "General persona simulation"


# ── app ───────────────────────────────────────────────────────────────────

async def _ensure_moderation_columns():
    """Idempotent ALTER TABLE for moderation/ban columns + new event-type
    enum values. Cheap to run on every startup; Railway redeploys are quick."""
    if not AUTH_ENABLED:
        return
    try:
        from db import get_engine                          # noqa: PLC0415
        from sqlalchemy import text as _sql                # noqa: PLC0415
        engine = get_engine()
        # Column adds run inside a transaction (safe).
        async with engine.begin() as conn:
            for ddl in [
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS banned BOOLEAN NOT NULL DEFAULT false",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS banned_at TIMESTAMP WITH TIME ZONE",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS banned_reason VARCHAR",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS flagged_count INTEGER NOT NULL DEFAULT 0",
            ]:
                await conn.execute(_sql(ddl))
        # ALTER TYPE ... ADD VALUE must NOT run inside a transaction (PG quirk).
        # Use AUTOCOMMIT isolation level — each statement commits on its own.
        async with engine.connect() as conn:
            ac = await conn.execution_options(isolation_level="AUTOCOMMIT")
            for new_val in ("moderation_blocked", "user_banned", "user_unbanned", "persona_shared"):
                try:
                    await ac.execute(_sql(
                        f"ALTER TYPE eventtype ADD VALUE IF NOT EXISTS '{new_val}'"
                    ))
                except Exception as exc:
                    logger.debug("[startup] enum add %s skipped: %s", new_val, exc)
        logger.info("[startup] moderation/ban columns + enum values ensured")
    except Exception as exc:  # pragma: no cover
        logger.warning("[startup] moderation column migration skipped: %s", exc)


async def _ensure_invite_codes_table():
    """Create invite_codes table + invite_code_used column on users if missing."""
    if not AUTH_ENABLED:
        return
    try:
        from db import get_engine                          # noqa: PLC0415
        from sqlalchemy import text as _sql                # noqa: PLC0415
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(_sql("""
                CREATE TABLE IF NOT EXISTS invite_codes (
                    code VARCHAR PRIMARY KEY,
                    label VARCHAR,
                    max_uses INTEGER,
                    used_count INTEGER NOT NULL DEFAULT 0,
                    active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    created_by_email VARCHAR
                )
            """))
            await conn.execute(_sql(
                "CREATE INDEX IF NOT EXISTS ix_invite_codes_active ON invite_codes (active)"
            ))
            await conn.execute(_sql(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS invite_code_used VARCHAR"
            ))
            # Access-status / referral-tree columns
            await conn.execute(_sql(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS access_status VARCHAR NOT NULL DEFAULT 'pending'"
            ))
            await conn.execute(_sql(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE"
            ))
            await conn.execute(_sql(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS invited_by_user_id VARCHAR REFERENCES users(id) ON DELETE SET NULL"
            ))
            await conn.execute(_sql(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS personal_invite_code VARCHAR"
            ))
            # Existing users (signed up before this gate existed) should
            # be grandfathered as active so they aren't kicked to a
            # waitlist mid-session. New rows still default to pending
            # via the column default.
            await conn.execute(_sql(
                "UPDATE users SET access_status='active', approved_at=COALESCE(approved_at, now()) "
                "WHERE access_status='pending' AND id IN (SELECT id FROM users WHERE \"emailVerified\" IS NOT NULL)"
            ))
            # InviteCode extension columns
            await conn.execute(_sql(
                "ALTER TABLE invite_codes ADD COLUMN IF NOT EXISTS created_by_user_id VARCHAR REFERENCES users(id) ON DELETE SET NULL"
            ))
            await conn.execute(_sql(
                "ALTER TABLE invite_codes ADD COLUMN IF NOT EXISTS sent_to_email VARCHAR"
            ))
            await conn.execute(_sql(
                "ALTER TABLE invite_codes ADD COLUMN IF NOT EXISTS sent_at TIMESTAMP WITH TIME ZONE"
            ))
            # access_requests table for the waitlist "tell us why" form
            await conn.execute(_sql("""
                CREATE TABLE IF NOT EXISTS access_requests (
                    id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    reason TEXT,
                    status VARCHAR NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    resolved_at TIMESTAMP WITH TIME ZONE,
                    resolved_by_email VARCHAR
                )
            """))
            await conn.execute(_sql(
                "CREATE INDEX IF NOT EXISTS ix_access_requests_status ON access_requests (status)"
            ))
            await conn.execute(_sql(
                "CREATE INDEX IF NOT EXISTS ix_access_requests_user_id ON access_requests (user_id)"
            ))
        logger.info("[startup] invite_codes + access_status + access_requests ensured")
    except Exception as exc:  # pragma: no cover
        logger.warning("[startup] invite_codes migration skipped: %s", exc)


def _purge_old_generated(ttl_days: int = 30) -> int:
    """Delete generated-persona JSON files older than ttl_days. Idempotent.

    Free-tier persona retention is intentionally bounded: 30 days on disk,
    then auto-purged so the volume doesn't grow forever. Probes pointing to
    the persona will 404 after purge — the persona page handles that.
    Returns count of files removed.
    """
    if not _GENERATED_DIR.exists():
        return 0
    import time as _t
    cutoff = _t.time() - (ttl_days * 86400)
    removed = 0
    for path in _GENERATED_DIR.glob("*.json"):
        try:
            if path.stat().st_mtime < cutoff:
                pid = path.stem
                path.unlink()
                _GENERATED.pop(pid, None)
                _GENERATED_PORTRAITS.pop(pid, None)
                removed += 1
        except Exception as exc:  # pragma: no cover
            logger.warning("[ttl] purge failed for %s: %s", path, exc)
    if removed:
        logger.info("[ttl] purged %d generated personas older than %dd", removed, ttl_days)
    return removed


@asynccontextmanager
async def lifespan(app: FastAPI):
    personas = _load_all()
    logger.info("[the-mind] %d exemplar personas loaded", len(personas))
    _load_generated_from_disk()
    logger.info("[the-mind] %d generated personas loaded from disk", len(_GENERATED))
    await _ensure_moderation_columns()
    await _ensure_invite_codes_table()
    _purge_old_generated()

    # Background TTL GC scheduler — re-runs the persona purge once every
    # 24h. Cheap (just stat()s files), idempotent, and stops cleanly when
    # the app shuts down because the task is cancelled below.
    async def _ttl_gc_loop():
        while True:
            try:
                await asyncio.sleep(24 * 60 * 60)
                removed = _purge_old_generated()
                logger.info("[ttl-gc] daily sweep removed %d personas", removed)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("[ttl-gc] sweep failed; will retry tomorrow")
    gc_task = asyncio.create_task(_ttl_gc_loop())

    yield

    gc_task.cancel()
    try:
        await gc_task
    except (asyncio.CancelledError, Exception):
        pass


app = FastAPI(
    title="The Mind API",
    description="Persona simulation API for mind.simulatte.io — exemplar_set_v1_2026_04",
    version="1.0.0",
    lifespan=lifespan,
)


# Note: removed temporary 422 diagnostic logger — root cause was the
# underage moderation filter returning 422 with a structured detail body,
# which is by design (see _generate_persona where reason="underage" lives).

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://mind.simulatte.io",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared LLM client — created once, reused across requests
_llm: anthropic.AsyncAnthropic | None = None


def _client() -> anthropic.AsyncAnthropic:
    global _llm
    if _llm is None:
        _llm = anthropic.AsyncAnthropic()
    return _llm


# ── routes ────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        exemplars_loaded=len(_load_all()),
        version="exemplar_set_v1_2026_04",
    )


@app.get("/personas", response_model=list[PersonaCard])
async def list_personas():
    """Return all 5 exemplar persona cards for the selection grid."""
    cards = []
    for slug, p in _load_all().items():
        di = p.derived_insights
        cards.append(PersonaCard(
            slug=slug,
            persona_id=p.persona_id,
            name=p.demographic_anchor.name,
            age=p.demographic_anchor.age,
            city=p.demographic_anchor.location.city,
            country=p.demographic_anchor.location.country,
            life_stage=p.demographic_anchor.life_stage,
            description=_ICP_DESCRIPTIONS.get(slug, ""),
            consistency_score=di.consistency_score,
            decision_style=di.decision_style,
            trust_anchor=di.trust_anchor,
            primary_value_orientation=di.primary_value_orientation,
            portrait_url=_EXEMPLAR_PORTRAITS.get(slug),
        ))
    return cards


@app.get("/personas/{slug}")
async def get_persona(slug: str):
    """Return the full PersonaRecord JSON for a persona."""
    try:
        return _load_one(slug).model_dump(mode="json")
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/personas/{slug}/attributes")
async def get_attributes(slug: str):
    """Return attributes with provenance chains — for the investor 'under the hood' view."""
    try:
        persona = _load_one(slug)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    result: dict = {}
    for category, attrs in persona.attributes.items():
        result[category] = {}
        for attr_name, attr in attrs.items():
            entry: dict = {
                "value": attr.value,
                "label": attr.label,
                "type": attr.type,
                "source": attr.source,
            }
            if attr.provenance:
                prov = attr.provenance
                entry["provenance"] = {
                    "source_class": prov.source_class,
                    "source_detail": prov.source_detail,
                    "confidence": prov.confidence,
                    "conditioned_by": prov.conditioned_by,
                    "reasoning": prov.reasoning,
                    "generation_stage": prov.generation_stage,
                    "filled_at": prov.filled_at.isoformat(),
                }
            result[category][attr_name] = entry

    total = sum(len(v) for v in persona.attributes.values())
    with_prov = sum(
        1 for cat in persona.attributes.values()
        for attr in cat.values() if attr.provenance is not None
    )

    return {
        "persona_id": persona.persona_id,
        "name": persona.demographic_anchor.name,
        "total_attributes": total,
        "provenance_coverage": f"{with_prov}/{total}",
        "attributes": result,
    }


def _build_portrait_prompt(da) -> str:
    """Build a rich, realistic portrait prompt from demographic anchor data (Pydantic model).

    Delegates to the dict variant via .model_dump() so the name + heritage
    inclusion logic stays in one place. Without the name, fal.ai (Flux)
    over-represents white phenotypes in cosmopolitan cities.
    """
    try:
        return _build_portrait_prompt_dict(da.model_dump())  # pydantic v2
    except AttributeError:
        pass
    # Legacy fallback for non-pydantic inputs.
    gender_word = "woman" if da.gender == "female" else "man" if da.gender == "male" else "person"
    name = getattr(da, "name", "") or ""
    city = getattr(da.location, "city", "") if da.location else ""
    country = getattr(da.location, "country", "") if da.location else ""
    occupation = ""
    if da.employment:
        occupation = getattr(da.employment, "occupation", "") or ""
    life_stage = (da.life_stage or "").replace("_", " ")

    # Build contextual descriptor
    context_parts = []
    if occupation:
        context_parts.append(occupation)
    if life_stage:
        context_parts.append(life_stage)
    context = f", {', '.join(context_parts)}" if context_parts else ""

    name_clause = f" named {name}" if name else ""
    return (
        f"Candid photorealistic portrait of a {da.age}-year-old {gender_word}{name_clause} from {city}, {country}{context}. "
        "Phenotype, skin tone, hair texture, and facial features should match the cultural and ethnic background implied by the name above. "
        "Shot on Sony A7 III, 85mm f/1.8 lens, natural window light, shallow depth of field. "
        "Authentic skin texture, realistic pores, natural hair, genuine relaxed expression. "
        "Upper body framing, slightly off-axis gaze, neutral indoor environment. "
        "Hyper-realistic photograph, not a painting, not illustrated, no filters, no text, no watermark. "
        "photo-realistic DSLR portrait, 85mm f/1.4 lens, natural skin texture with visible pores and subtle imperfections, "
        "candid expression with soft natural lighting, environmental context appropriate to their occupation and location, "
        "color-accurate, neutral grading, not stylized, not AI-rendered, looks like a real person photographed on a Tuesday afternoon"
    )


_INCOME_WARDROBE = {
    "low": "modest, well-worn but cared-for clothing — basics, no flashy logos",
    "lower_middle": "practical, slightly dated wardrobe — chain-store basics in good condition",
    "middle": "unremarkable contemporary clothing appropriate to their occupation",
    "upper_middle": "tasteful, current-season clothing — quiet quality, no logos",
    "high": "well-tailored, considered wardrobe — premium fabrics, restrained palette",
    "ultra_high": "exquisitely tailored, understated luxury — bespoke fit, no visible branding",
}

_DECISION_DEMEANOUR = {
    "deliberative": "thoughtful, slightly furrowed brow, the look of someone mid-thought",
    "analytical": "alert and focused, faintly appraising expression",
    "intuitive": "warm, open, present in the moment",
    "impulsive": "animated, slightly forward-leaning energy",
    "consensus_seeking": "approachable, attentive expression as if listening",
    "values_driven": "calm and grounded, gaze steady",
    "risk_averse": "reserved, contained body language",
    "experimental": "curious, faintly amused half-smile",
}


def _build_portrait_prompt_dict(persona_or_anchor: dict) -> str:
    """Build a topical portrait prompt that surfaces character + background.

    Accepts either the full persona dict OR just the demographic_anchor
    (sniffs for the `demographic_anchor` key). Pulls in:
      • Name + heritage  → phenotype signal (else Flux defaults to white
        in cosmopolitan cities)
      • Occupation + industry  → wardrobe and setting
      • Life stage + household  → age cues, accessories (e.g. wedding ring)
      • Income level  → quality/cut of clothing
      • Decision style  → posture and facial demeanour
      • Primary value orientation  → environmental cues
      • Narrative / bio snippet (if present)  → atmospheric detail
    Capped at ~120 words of meaningful content so Flux doesn't truncate.
    """
    # Sniff: full persona vs raw anchor
    if "demographic_anchor" in persona_or_anchor:
        persona = persona_or_anchor
        da = persona.get("demographic_anchor") or {}
    else:
        persona = {}
        da = persona_or_anchor

    di = persona.get("derived_insights") or {}

    name = (da.get("name") or "").strip()
    gender = da.get("gender", "")
    gender_word = "woman" if gender == "female" else "man" if gender == "male" else "person"
    location = da.get("location") or {}
    city = location.get("city", "")
    country = location.get("country", "")
    employment = da.get("employment") or {}
    occupation = employment.get("occupation", "") or ""
    industry = employment.get("industry", "") or ""
    life_stage = (da.get("life_stage") or "").replace("_", " ")
    age = da.get("age", 30)
    income_level = (da.get("income_level") or "").lower()
    household = da.get("household") or {}
    household_type = (household.get("type") or "").lower()

    # Heritage / ethnicity
    heritage = (
        da.get("ethnicity") or da.get("heritage") or da.get("ancestry")
        or da.get("cultural_background") or ""
    )
    if isinstance(heritage, list):
        heritage = ", ".join(str(h) for h in heritage)
    heritage = str(heritage).strip()

    # Subject line — name carries phenotype signal
    subject_bits = [f"{age}-year-old"]
    if heritage:
        subject_bits.append(heritage)
    subject_bits.append(gender_word)
    subject = " ".join(subject_bits)
    name_clause = f" named {name}" if name else ""

    # Wardrobe — occupation × income level
    wardrobe = _INCOME_WARDROBE.get(income_level, _INCOME_WARDROBE["middle"])

    # Demeanour from decision style
    decision_style = (di.get("decision_style") or "").lower()
    demeanour = _DECISION_DEMEANOUR.get(decision_style, "natural relaxed expression, soft eyes")

    # Setting — derived from occupation, value orientation, life stage
    value_orientation = (di.get("primary_value_orientation") or "").replace("_", " ")
    setting_bits: list[str] = []
    if occupation:
        # Light environmental hint based on occupation keywords
        occ_l = occupation.lower()
        if any(k in occ_l for k in ("engineer", "developer", "designer", "researcher", "analyst")):
            setting_bits.append("a working environment with monitors slightly out of focus behind them")
        elif any(k in occ_l for k in ("chef", "restaurant", "barista", "baker")):
            setting_bits.append("a warm kitchen or service space, soft ambient sounds implied")
        elif any(k in occ_l for k in ("teacher", "professor", "educator")):
            setting_bits.append("an unfussy classroom or study, books visible behind them")
        elif any(k in occ_l for k in ("nurse", "doctor", "medical", "clinician")):
            setting_bits.append("a clinical but humane setting, scrubs or muted uniform")
        elif any(k in occ_l for k in ("electrician", "carpenter", "mechanic", "tradesperson")):
            setting_bits.append("a workshop or job site, hands showing honest use")
        elif any(k in occ_l for k in ("artist", "musician", "writer", "creative", "illustrator")):
            setting_bits.append("their studio or creative space, lived-in and personal")
        elif any(k in occ_l for k in ("manager", "consultant", "banker", "executive", "director")):
            setting_bits.append("a quiet office or co-working space, softly out of focus")
        else:
            setting_bits.append(f"a setting consistent with their work as a {occupation}")

    # Life stage / household cues
    if "parent" in household_type or any(k in life_stage for k in ("kids", "children", "parent")):
        setting_bits.append("subtle signs of family life nearby (a child's drawing pinned, a stroller corner)")
    if "married" in household_type or "couple" in household_type:
        setting_bits.append("a wedding band visible on the ring finger")

    # Values cue — only if obvious
    if value_orientation:
        if "sustainability" in value_orientation or "environment" in value_orientation:
            setting_bits.append("natural materials and plants in the background")
        elif "tradition" in value_orientation or "family" in value_orientation:
            setting_bits.append("framed family photos or heirlooms suggested in the background")
        elif "achievement" in value_orientation or "status" in value_orientation:
            setting_bits.append("polished surfaces, organised desk, considered objects")

    # Narrative / bio fragment — Claude sometimes generates these
    bio = (
        persona.get("bio")
        or persona.get("narrative_summary")
        or persona.get("summary")
        or ""
    )
    if isinstance(bio, dict):
        bio = bio.get("summary") or bio.get("text") or ""
    bio = str(bio).strip()
    # Take only the first ~140 chars so we keep the prompt focused
    if bio:
        bio = bio.split("\n")[0][:140].rstrip(",.; ")

    setting = ". ".join(setting_bits) if setting_bits else "a neutral indoor environment"

    return (
        f"Candid editorial portrait of a {subject}{name_clause} from {city}, {country}"
        f"{', ' + occupation if occupation else ''}"
        f"{' (' + industry + ')' if industry else ''}"
        f"{', ' + life_stage if life_stage else ''}. "
        f"{('Background: ' + bio + '. ') if bio else ''}"
        "Phenotype, skin tone, hair texture, and facial features must match the cultural and ethnic background implied by the name and heritage above. "
        f"Wardrobe: {wardrobe}. "
        f"Setting: {setting}. "
        f"Demeanour: {demeanour}. "
        "Shot on Sony A7 III, 85mm f/1.4 lens, natural window light, shallow depth of field. "
        "Upper body framing, slightly off-axis gaze, authentic skin texture with visible pores and subtle imperfections. "
        "Hyper-realistic documentary photograph — not a painting, not illustrated, no filters, no text, no watermark. "
        "Color-accurate neutral grading, looks like a real person photographed on a Tuesday afternoon for a magazine feature."
    )


async def _generate_persona_direct(
    brief: str,
    anchor: dict,
    domain: str,
    client: anthropic.AsyncAnthropic,
) -> dict:
    """Generate a persona via two parallel Haiku calls — ~30s vs 3+ min for the full pipeline.

    Call A: identity, narrative, decision psychology, behaviour (max_tokens=2000)
    Call B: memory, life stories, demographics detail (max_tokens=1500)
    """
    import re
    import uuid
    from datetime import datetime, timezone

    age = anchor.get("age", 30)
    gender = anchor.get("gender", "")
    location = anchor.get("location") or {}
    city = location.get("city", "")
    country = location.get("country", "")
    employment_occupation = anchor.get("occupation", "") or (anchor.get("employment") or {}).get("occupation", "")
    life_stage = anchor.get("life_stage", "established_adult")
    household = anchor.get("household") or {}
    income_level = anchor.get("income_level", "middle")

    context = (
        f"Person: {age}-year-old {gender} {employment_occupation or 'professional'}\n"
        f"Location: {city}, {country}\n"
        f"Life stage: {life_stage.replace('_', ' ')}\n"
        f"Income: {income_level}\n"
        f"Household: {household.get('composition', '')}\n"
        f"Domain: {domain}\n"
        f"Brief: {brief}"
    )

    prompt_a = f"""{context}

Generate a realistic persona. Return ONLY valid JSON with no markdown:
{{
  "name": "<realistic full name matching culture/location>",
  "description": "<2-sentence vivid description>",
  "narrative": {{
    "third_person": "<3-4 sentence rich narrative about who they are, daily life, values>",
    "first_person": "<2-3 sentence first-person voice — how they'd describe themselves>",
    "display_name": "<first name or nickname>"
  }},
  "derived_insights": {{
    "decision_style": "<analytical|emotional|habitual|social>",
    "primary_value_orientation": "<price|quality|brand|convenience|features>",
    "trust_anchor": "<self|peer|authority|family>",
    "risk_appetite": "<low|moderate|high>",
    "consistency_score": <integer 60-95>,
    "key_tensions": ["<internal tension 1>", "<tension 2>", "<tension 3>"],
    "coping_mechanism": {{"type": "<avoidance|rationalisation|socialising|routine>", "description": "<one sentence>"}}
  }},
  "behavioural_tendencies": {{
    "trust_orientation": {{
      "brands": <0.0-1.0>,
      "peers": <0.0-1.0>,
      "experts": <0.0-1.0>,
      "institutions": <0.0-1.0>
    }},
    "price_sensitivity": {{
      "band": "<budget|value|mid|premium|luxury>",
      "description": "<one sentence on how price factors into their decisions>"
    }},
    "switching_propensity": {{
      "likelihood": "<low|moderate|high>",
      "triggers": ["<trigger 1>", "<trigger 2>"]
    }},
    "objection_profile": [
      {{"type": "<price|trust|complexity|social|timing>", "likelihood": "<low|moderate|high>", "severity": "<low|moderate|high>", "description": "<one sentence>"}},
      {{"type": "<price|trust|complexity|social|timing>", "likelihood": "<low|moderate|high>", "severity": "<low|moderate|high>", "description": "<one sentence>"}},
      {{"type": "<price|trust|complexity|social|timing>", "likelihood": "<low|moderate|high>", "severity": "<low|moderate|high>", "description": "<one sentence>"}}
    ],
    "reasoning_prompt": "<one sentence describing how this persona reasons through decisions>"
  }},
  "decision_bullets": [
    "<how they approach decisions — 5 specific, domain-relevant bullets>",
    "<bullet 2>", "<bullet 3>", "<bullet 4>", "<bullet 5>"
  ]
}}"""

    prompt_b = f"""{context}

Generate inner life, defining stories, and demographic detail. Return ONLY valid JSON with no markdown:
{{
  "education": "<highest qualification, e.g. Bachelor's in Engineering>",
  "employment_detail": {{
    "occupation": "<job title, e.g. Software Engineer>",
    "industry": "<industry sector>",
    "seniority": "<junior|mid|senior|lead|executive|owner>"
  }},
  "location": {{
    "city": "<city name>",
    "country": "<country name>"
  }},
  "household_detail": {{
    "size": <integer 1-8>,
    "composition": "<e.g. married with two children>"
  }},
  "memory": {{
    "core": {{
      "identity_statement": "<2-sentence first-person statement — who they are at their core>",
      "key_values": ["<core value 1>", "<value 2>", "<value 3>", "<value 4>"],
      "life_defining_events": ["<event that shaped them>", "<event 2>", "<event 3>"],
      "relationship_map": {{"partner": "<description or empty>", "family": "<description>", "community": "<description>"}},
      "immutable_constraints": ["<hard constraint on their behaviour>", "<constraint 2>"],
      "tendency_summary": "<one sentence summary of their dominant behavioural tendency>"
    }}
  }},
  "life_stories": [
    {{
      "title": "<short evocative title>",
      "narrative": "<3-4 sentence defining moment that shaped their values or behaviour>",
      "age_at_event": <integer or null>,
      "emotional_weight": "<formative|pivotal|minor|traumatic|joyful>"
    }},
    {{
      "title": "<title>",
      "narrative": "<narrative>",
      "age_at_event": <integer or null>,
      "emotional_weight": "<formative|pivotal|minor|traumatic|joyful>"
    }},
    {{
      "title": "<title>",
      "narrative": "<narrative>",
      "age_at_event": <integer or null>,
      "emotional_weight": "<formative|pivotal|minor|traumatic|joyful>"
    }}
  ]
}}"""

    # Fire both calls in parallel
    resp_a, resp_b = await asyncio.gather(
        client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt_a}],
        ),
        client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt_b}],
        ),
    )

    def _parse_json(text: str) -> dict:
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
            if m:
                return json.loads(m.group(1))
            # Last resort: find outermost { }
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            return {}

    data_a = _parse_json(resp_a.content[0].text)
    data_b = _parse_json(resp_b.content[0].text)

    name = data_a.get("name", "Unknown")
    name_slug = re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-"))[:16]
    persona_id = f"pg-web-{name_slug}-{uuid.uuid4().hex[:4]}"

    di = data_a.get("derived_insights") or {}
    bt_raw = data_a.get("behavioural_tendencies") or {}
    emp_detail = data_b.get("employment_detail") or {}
    hh_detail = data_b.get("household_detail") or {}
    loc_b = data_b.get("location") or {}

    # Fall back to Prompt B values when anchor (from _extract_from_brief) was empty
    city = city or loc_b.get("city", "")
    country = country or loc_b.get("country", "")
    employment_occupation = employment_occupation or emp_detail.get("occupation", "")

    # Ensure page-critical nested fields always exist (page doesn't use optional chaining)
    bt = {
        "trust_orientation": bt_raw.get("trust_orientation") or {},
        "price_sensitivity": bt_raw.get("price_sensitivity") or {"band": "mid", "description": ""},
        "switching_propensity": bt_raw.get("switching_propensity") or {"likelihood": "moderate", "triggers": []},
        "objection_profile": bt_raw.get("objection_profile") or [],
        "reasoning_prompt": bt_raw.get("reasoning_prompt") or "",
    }

    memory_raw = data_b.get("memory") or {}
    core_raw = memory_raw.get("core") or {}
    memory = {
        "core": {
            "identity_statement": core_raw.get("identity_statement") or "",
            "key_values": core_raw.get("key_values") or [],
            "life_defining_events": core_raw.get("life_defining_events") or [],
            "relationship_map": core_raw.get("relationship_map") or {},
            "immutable_constraints": core_raw.get("immutable_constraints") or [],
            "tendency_summary": core_raw.get("tendency_summary") or "",
        }
    }

    di_safe = {
        "decision_style": di.get("decision_style") or "analytical",
        "primary_value_orientation": di.get("primary_value_orientation") or "quality",
        "trust_anchor": di.get("trust_anchor") or "self",
        "risk_appetite": di.get("risk_appetite") or "moderate",
        "consistency_score": di.get("consistency_score") or 75,
        "key_tensions": di.get("key_tensions") or [],
        "coping_mechanism": di.get("coping_mechanism") or {"type": "routine", "description": ""},
    }

    narrative_raw = data_a.get("narrative") or {}
    narrative = {
        "third_person": narrative_raw.get("third_person") or "",
        "first_person": narrative_raw.get("first_person") or "",
        "display_name": narrative_raw.get("display_name") or name.split()[0] if name else "",
    }

    persona_dict = {
        "persona_id": persona_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_version": "web-direct-v1",
        "domain": domain,
        "description": data_a.get("description", ""),
        "attributes": {},  # no deep attribute fill in fast path
        "demographic_anchor": {
            "name": name,
            "age": age,
            "gender": gender,
            "life_stage": life_stage,
            "location": {"city": city, "country": country},
            "education": data_b.get("education") or "",
            "employment": {
                "occupation": employment_occupation,
                "industry": emp_detail.get("industry") or "",
                "seniority": emp_detail.get("seniority") or "",
            },
            "household": {
                "size": hh_detail.get("size") or household.get("size") or 1,
                "composition": hh_detail.get("composition") or household.get("composition") or "",
            },
            "income_level": income_level,
        },
        "narrative": narrative,
        "derived_insights": di_safe,
        "behavioural_tendencies": bt,
        "decision_bullets": data_a.get("decision_bullets") or [],
        "memory": memory,
        "life_stories": data_b.get("life_stories") or [],
    }
    persona_dict["quality_assessment"] = _compute_quality_assessment(persona_dict)
    return persona_dict


async def _call_fal_portrait(prompt: str, fal_key: str) -> str:
    """Call fal.io flux-pro/v1.1-ultra and return the image URL.

    Upgraded from flux-realism (~$0.04) to flux-pro/v1.1-ultra (~$0.06) for the 5 hero
    exemplar faces. The new model accepts a negative_prompt field which we use to block
    cartoon/3d/glamour styles.
    """
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
        raise HTTPException(status_code=502, detail=f"fal.io error: {exc.response.text}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Portrait generation failed: {exc}")

    images = data.get("images", [])
    if not images:
        raise HTTPException(status_code=500, detail="fal.io returned no images")
    return images[0]["url"]


@app.post("/personas/{slug}/portrait")
async def generate_exemplar_portrait(slug: str, force: bool = False):
    """Generate a portrait for an exemplar persona via fal.io flux-pro/v1.1-ultra.

    Pass ?force=true to bypass the in-memory/disk cache and regenerate with the current model.
    """
    try:
        persona = _load_one(slug)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not force and slug in _EXEMPLAR_PORTRAITS:
        return {"url": _EXEMPLAR_PORTRAITS[slug], "persona_id": persona.persona_id}

    fal_key = os.environ.get("FAL_KEY", "")
    if not fal_key:
        raise HTTPException(status_code=503, detail="FAL_KEY environment variable not set")

    prompt = _build_portrait_prompt(persona.demographic_anchor)
    url = await _call_fal_portrait(prompt, fal_key)
    _EXEMPLAR_PORTRAITS[slug] = url
    _save_portraits_to_disk()
    return {"url": url, "persona_id": persona.persona_id}


@app.post("/personas/{slug}/chat", response_model=ChatResponse)
async def chat(slug: str, request: ChatRequest):
    """Chat with a persona.

    Flow:
      1. Load frozen exemplar PersonaRecord
      2. decide(scenario=message, memories=[], persona) → DecisionOutput (Sonnet, 5-step)
      3. respond(message, decision, persona) → natural first-person reply (Haiku)
      4. Return reply + optional reasoning trace
    """
    try:
        persona = _load_one(slug)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    client = _client()

    try:
        decision_output = await decide(
            scenario=request.message,
            memories=[],
            persona=persona,
            llm_client=client,
            apply_noise=True,
        )
        reply = await respond(
            user_message=request.message,
            decision=decision_output,
            persona=persona,
            llm_client=client,
        )
    except Exception as e:
        logger.exception("[%s] chat error", slug)
        raise HTTPException(status_code=500, detail=f"Simulation error: {e}")

    trace: DecisionTrace | None = None
    if request.include_reasoning:
        trace = DecisionTrace(
            decision=decision_output.decision,
            confidence=decision_output.confidence,
            gut_reaction=decision_output.gut_reaction,
            key_drivers=decision_output.key_drivers,
            objections=decision_output.objections,
            what_would_change_mind=decision_output.what_would_change_mind,
            follow_up_action=decision_output.follow_up_action,
            reasoning_trace=decision_output.reasoning_trace,
        )

    return ChatResponse(
        reply=reply,
        decision_trace=trace,
        persona_id=persona.persona_id,
        persona_name=persona.demographic_anchor.name,
    )


# ── generation endpoints ──────────────────────────────────────────────────

_GENERATION_STEPS = [
    "Selecting demographic anchor...",
    "Calibrating cultural context...",
    "Building 120+ attributes...",
    "Writing life stories...",
    "Generating decision psychology...",
    "Validating behavioural coherence...",
]


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


# ── Moderation enforcement helper ────────────────────────────────────────

async def _enforce_and_log_moderation(
    text: str,
    user: "User",
    db: "AsyncSession",
    *,
    surface: str,            # "brief" | "chat" | "probe_claim"
) -> None:
    """Run moderation. If flagged: increment user.flagged_count, log a
    `moderation_blocked` Event (ref_id encodes reason+surface), and raise
    HTTP 422.

    Auto-ban: if a user accumulates >= 3 flagged events, set banned=True.
    """
    result = check_brief(text)
    if not result.flagged:
        return

    # Persist a moderation event + bump counter (best-effort; never block on log
    # write if the DB is busy)
    try:
        if AUTH_ENABLED:
            from sqlalchemy import update as sa_update                # noqa: PLC0415
            ref = f"{result.reason}:{surface}:{','.join(result.matched_terms)[:60]}"
            db.add(Event(  # type: ignore[call-arg]
                user_id=user.id,
                type=EventType.moderation_blocked,
                ref_id=ref[:200],
            ))
            await db.execute(
                sa_update(User)  # type: ignore[arg-type]
                .where(User.id == user.id)
                .values(flagged_count=(User.flagged_count + 1))
            )
            # Auto-ban after 3 strikes
            new_count = (getattr(user, "flagged_count", 0) or 0) + 1
            if new_count >= 3 and not getattr(user, "banned", False):
                from datetime import datetime as _dt, timezone as _tz  # noqa: PLC0415
                await db.execute(
                    sa_update(User)
                    .where(User.id == user.id)
                    .values(
                        banned=True,
                        banned_at=_dt.now(_tz.utc),
                        banned_reason=f"auto-ban: 3+ {result.reason} flags",
                    )
                )
                db.add(Event(
                    user_id=user.id,
                    type=EventType.user_banned,
                    ref_id=f"auto:{result.reason}",
                ))
                logger.warning(
                    "[moderation] auto-banned user=%s reason=%s",
                    user.email, result.reason,
                )
            await db.commit()
    except Exception as exc:  # pragma: no cover
        logger.warning("[moderation] failed to log flag: %s", exc)

    logger.info(
        "[moderation] BLOCKED user=%s surface=%s reason=%s terms=%s",
        getattr(user, "email", "?"), surface, result.reason, result.matched_terms,
    )

    raise HTTPException(
        status_code=422,
        detail={
            "error": "moderation_blocked",
            "reason": result.reason,
            "message": result.message,
        },
    )


@app.get("/me")
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user + their current week's allowance state."""
    return await build_me_response(user, db)


@app.post("/generate-persona")
async def generate_persona_stream(
    request: ICPRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream persona generation via SSE.

    Events:
        {"type": "status",  "message": "..."}
        {"type": "result",  "persona_id": "...", "name": "..."}
        {"type": "error",   "message": "..."}
    """
    # Moderation: reject the brief BEFORE consuming any quota. A flagged
    # request bumps the user's flag counter; 3+ flags auto-bans.
    await _enforce_and_log_moderation(request.brief, user, db, surface="brief")

    # Auth: check allowance BEFORE starting the SSE stream.
    # Must happen here (not inside the generator) so a 402 is a normal HTTP response.
    await check_and_increment_allowance(user, "persona", db)

    async def stream():
        logger.info("[generate] stream started, brief length=%d", len(request.brief))

        yield _sse({"type": "status", "message": "Reading your brief..."})

        # Parse natural-language brief into structured demographics
        anchor, domain, _biz_problem = await _extract_from_brief(
            request.brief, request.pdf_content, _client()
        )
        logger.info("[generate] brief parsed, domain=%s, anchor_keys=%s", domain, list(anchor.keys()))

        yield _sse({"type": "status", "message": "Anchoring demographics..."})
        yield _sse({"type": "status", "message": "Building persona..."})

        # Run generation as a background task so we can interleave heartbeats.
        # Heartbeats prevent Railway's reverse proxy from closing the idle connection
        # during the 20–30s generation window.
        gen_task = asyncio.create_task(_generate_persona_direct(
            brief=request.brief,
            anchor=anchor,
            domain=request.domain or domain,
            client=_client(),
        ))

        while not gen_task.done():
            # asyncio.wait returns immediately when gen_task completes or after 8s
            done_set, _ = await asyncio.wait({gen_task}, timeout=8.0)
            if not done_set:
                yield ": heartbeat\n\n"  # keep proxy alive

        if gen_task.cancelled():
            yield _sse({"type": "error", "message": "Generation was cancelled."})
            return

        exc = gen_task.exception()
        if exc is not None:
            logger.exception("[generate] _generate_persona_direct raised: %s", exc)
            yield _sse({"type": "error", "message": f"Generation failed: {exc}"})
            return

        persona_dict = gen_task.result()
        logger.info("[generate] persona_dict built, persona_id=%s", persona_dict.get("persona_id"))

        # All post-generation work inside a try/except — an uncaught exception here
        # previously killed the generator before the result event was sent (Bug #3 in RCA).
        try:
            persona_id = persona_dict["persona_id"]
            name = persona_dict["demographic_anchor"]["name"]
            _GENERATED[persona_id] = persona_dict
            _persist_generated_dict(persona_dict)
            logger.info("[generate] stored %s (%s)", persona_id, name)
            # Backfill ref_id on the most recent persona_generated event for
            # this user so /me/personas can resolve "who built this".
            # check_and_increment_allowance creates the event with null
            # ref_id; this writes the persona_id back. Best-effort — if
            # the DB write fails the persona is still saved.
            try:
                from sqlalchemy import select as _sel, update as _upd
                latest = (await db.execute(
                    _sel(Event)
                    .where(Event.user_id == user.id)
                    .where(Event.type == EventType.persona_generated)
                    .where(Event.ref_id.is_(None))
                    .order_by(Event.created_at.desc())
                    .limit(1)
                )).scalar_one_or_none()
                if latest is not None:
                    await db.execute(
                        _upd(Event).where(Event.id == latest.id)
                        .values(ref_id=persona_id)
                    )
                    await db.commit()
            except Exception as e_evt:
                logger.warning("[generate] event ref_id backfill failed: %s", e_evt)
                await db.rollback()
        except Exception as exc:
            logger.exception("[generate] storage step failed")
            yield _sse({"type": "error", "message": f"Failed to store persona: {exc}"})
            return

        # Auto-generate portrait in background
        fal_key = os.environ.get("FAL_KEY", "")
        if fal_key:
            asyncio.create_task(_auto_generate_portrait(persona_id, fal_key))

        yield _sse({"type": "status", "message": "Persona ready!"})
        yield _sse({"type": "result", "persona_id": persona_id, "name": name})
        logger.info("[generate] result event sent for %s", persona_id)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/generated")
async def list_generated_personas():
    """Return compact summaries of all generated personas, newest first."""
    summaries = []
    for p in _GENERATED.values():
        da = p.get("demographic_anchor") or {}
        location = da.get("location") or {}
        narrative = p.get("narrative") or {}
        snippet = (narrative.get("third_person") or "")[:120]
        summaries.append({
            "persona_id": p["persona_id"],
            "name": da.get("name", ""),
            "age": da.get("age", 0),
            "city": location.get("city", ""),
            "country": location.get("country", ""),
            "life_stage": da.get("life_stage", ""),
            "brief_snippet": snippet,
        })
    return sorted(summaries, key=lambda x: x["persona_id"], reverse=True)


@app.get("/me/personas")
async def my_personas(
    user: User = Depends(get_current_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    """Personas the signed-in user generated, with probe count and
    days-until-expiry for the dashboard. Newest first.

    Persona files auto-purge after 30d (see _purge_old_generated). We
    surface that as `expires_in_days` so the dashboard can nudge the
    user to probe/chat them before they're gone.
    """
    from sqlalchemy import select as sa_select
    import time as _t
    rows = (
        await db.execute(
            sa_select(Event)  # type: ignore
            .where(Event.user_id == user.id)  # type: ignore
            .where(Event.type == EventType.persona_generated)  # type: ignore
            .order_by(Event.created_at.desc())  # type: ignore
            .limit(200)
        )
    ).scalars().all()
    seen: set[str] = set()
    out: list[dict] = []
    now = _t.time()
    for ev in rows:
        pid = ev.ref_id
        if not pid or pid in seen:
            continue
        seen.add(pid)
        p = _GENERATED.get(pid)
        if p is None:
            continue  # purged or unloaded
        da = p.get("demographic_anchor") or {}
        loc = da.get("location") or {}
        # File mtime → expiry; default to 30d window from creation.
        path = _GENERATED_DIR / f"{pid}.json"
        try:
            mtime = path.stat().st_mtime if path.exists() else now
        except Exception:
            mtime = now
        age_days = max(0, (now - mtime) / 86400.0)
        expires_in = max(0, int(round(30.0 - age_days)))
        # Probe count for this persona by this user
        probe_count = (await db.execute(
            sa_select(Event)  # type: ignore
            .where(Event.user_id == user.id)  # type: ignore
            .where(Event.type == EventType.probe_run)  # type: ignore
            .where(Event.ref_id == pid)  # type: ignore
        )).scalars().all()
        chat_count = (await db.execute(
            sa_select(Event)  # type: ignore
            .where(Event.user_id == user.id)  # type: ignore
            .where(Event.type == EventType.chat_message)  # type: ignore
            .where(Event.ref_id == pid)  # type: ignore
        )).scalars().all()
        out.append({
            "persona_id": pid,
            "name": da.get("name", ""),
            "age": da.get("age", 0),
            "city": loc.get("city", ""),
            "country": loc.get("country", ""),
            "portrait_url": _GENERATED_PORTRAITS.get(pid),
            "probes_run": len(probe_count),
            "chats_had": len(chat_count),
            "expires_in_days": expires_in,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        })
    return out


@app.get("/community/personas")
async def list_community_personas(limit: int = 60):
    """Public, anonymized list of generated personas for the Community Wall.

    Free-tier generations are property of Simulatte (per ToS) and surfaced
    here. NO user information attached — name/age/city/country/portrait
    only. Sorted by created_at on disk (newest first).
    """
    items: list[dict] = []
    for pid, p in _GENERATED.items():
        da = p.get("demographic_anchor") or {}
        location = da.get("location") or {}
        narrative = p.get("narrative") or {}
        # Take a short third-person hook line — already public on persona page.
        snippet = (narrative.get("third_person") or "")[:140]
        path = _GENERATED_DIR / f"{pid}.json"
        try:
            mtime = path.stat().st_mtime if path.exists() else 0.0
        except Exception:
            mtime = 0.0
        items.append({
            "persona_id": pid,
            "name": da.get("name", ""),
            "age": da.get("age", 0),
            "city": location.get("city", ""),
            "country": location.get("country", ""),
            "portrait_url": _GENERATED_PORTRAITS.get(pid),
            "snippet": snippet,
            "_sort": mtime,
        })
    items.sort(key=lambda x: x["_sort"], reverse=True)
    return [{k: v for k, v in it.items() if k != "_sort"} for it in items[:limit]]


def _compute_quality_assessment(persona: dict) -> dict:
    """Compute a 0-10 'genuineness' score from populated persona fields.

    Generated personas have empty attributes:{} so we score from narrative,
    insights, behavioural tendencies, and memory only.
    """
    da = persona.get("demographic_anchor") or {}
    di = persona.get("derived_insights") or {}
    bt = persona.get("behavioural_tendencies") or {}
    mem = ((persona.get("memory") or {}).get("core")) or {}

    demo_fields = [
        da.get("name"), da.get("age"),
        (da.get("location") or {}).get("city"),
        (da.get("location") or {}).get("country"),
        (da.get("employment") or {}).get("occupation"),
        da.get("education"),
        (da.get("household") or {}).get("composition"),
    ]
    demo_score = sum(1 for f in demo_fields if f) / len(demo_fields)

    raw_consistency = di.get("consistency_score") or 0
    try:
        cv = float(raw_consistency)
    except (TypeError, ValueError):
        cv = 0.0
    # consistency_score is 60-95 integer in generator; normalise to 0-1
    consistency = cv / 100.0 if cv > 1.0 else cv

    stories = len(persona.get("life_stories") or [])
    bullets = len(persona.get("decision_bullets") or [])
    events = len(mem.get("life_defining_events") or [])
    depth_raw = (min(stories, 3) / 3 + min(bullets, 5) / 5 + min(events, 3) / 3) / 3

    psych_fields = [
        di.get("decision_style"), di.get("trust_anchor"),
        di.get("risk_appetite"), di.get("primary_value_orientation"),
        bt.get("trust_orientation"), bt.get("price_sensitivity"),
    ]
    psych_score = sum(1 for f in psych_fields if f) / len(psych_fields)

    score_01 = 0.40 * demo_score + 0.30 * consistency + 0.15 * depth_raw + 0.15 * psych_score

    return {
        "score": round(score_01 * 10, 1),
        "components": [
            {"key": "demographic_grounding", "label": "Demographic grounding", "value": round(demo_score, 2),
             "description": "Anchor fields populated (age, city, country, occupation, education, household)"},
            {"key": "behavioural_consistency", "label": "Behavioural consistency", "value": round(consistency, 2),
             "description": "Cross-attribute coherence (decision style ↔ values ↔ trust)"},
            {"key": "narrative_depth", "label": "Narrative depth", "value": round(depth_raw, 2),
             "description": "Life stories, decision bullets, defining memory events"},
            {"key": "psychological_completeness", "label": "Psychological completeness", "value": round(psych_score, 2),
             "description": "Decision style, trust, risk, values, behavioural tendencies"},
        ],
        "sources": [
            {"name": "Demographic Anchor", "weight": "primary",
             "description": "Census-aligned demographic frame: age, location, employment, education, household composition"},
            {"name": "Behavioural Coherence Model", "weight": "primary",
             "description": "Internal consistency check across decision psychology, values, and trust orientation"},
            {"name": "LLM Inference (Anthropic Claude)", "weight": "secondary",
             "description": "Narrative, life stories, decision bullets, value extrapolation from the brief"},
        ],
    }


@app.get("/generated/{persona_id}")
async def get_generated_persona(persona_id: str):
    """Return a previously generated persona by ID.

    Falls back to disk if the persona isn't in the in-memory cache — this handles
    Railway multi-instance routing and post-restart access (Failure 5 in RCA).
    """
    if persona_id not in _GENERATED:
        path = _GENERATED_DIR / f"{persona_id}.json"
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    _GENERATED[persona_id] = json.load(f)
                logger.info("[get_generated] loaded %s from disk", persona_id)
            except Exception as exc:
                logger.warning("[get_generated] disk load failed for %s: %s", persona_id, exc)

    if persona_id not in _GENERATED:
        raise HTTPException(
            status_code=404,
            detail=f"Generated persona '{persona_id}' not found. "
                   "It may have been lost on a server restart before it could be persisted.",
        )
    data = dict(_GENERATED[persona_id])
    data["portrait_url"] = _GENERATED_PORTRAITS.get(persona_id)
    # Backfill quality_assessment for personas persisted before this field existed.
    if "quality_assessment" not in data or not data.get("quality_assessment"):
        data["quality_assessment"] = _compute_quality_assessment(data)
    return data


def _build_generated_system_prompt(persona: dict) -> str:
    """Build a system prompt for a generated persona's chat handler.

    Pulls together narrative, insights, memory, and decision bullets so the
    LLM can role-play with consistent voice and decision logic.
    """
    da = persona.get("demographic_anchor") or {}
    location = da.get("location") or {}
    employment = da.get("employment") or {}
    household = da.get("household") or {}
    narrative = persona.get("narrative") or {}
    di = persona.get("derived_insights") or {}
    bt = persona.get("behavioural_tendencies") or {}
    mem = (persona.get("memory") or {}).get("core") or {}
    bullets = persona.get("decision_bullets") or []
    stories = persona.get("life_stories") or []

    name = da.get("name") or "the persona"
    age = da.get("age") or ""
    city = location.get("city") or ""
    country = location.get("country") or ""
    occupation = employment.get("occupation") or ""
    life_stage = (da.get("life_stage") or "").replace("_", " ")

    parts: list[str] = []
    parts.append(
        f"You ARE {name}, a {age}-year-old {occupation or 'person'} in {city}, {country}. "
        f"Life stage: {life_stage}. Household: {household.get('composition') or 'unspecified'}. "
        f"Education: {da.get('education') or 'unspecified'}."
    )

    if narrative.get("third_person"):
        parts.append(f"Background: {narrative['third_person']}")
    if narrative.get("first_person"):
        parts.append(f"How you describe yourself: \"{narrative['first_person']}\"")

    if mem.get("identity_statement"):
        parts.append(f"Core identity: {mem['identity_statement']}")
    if mem.get("key_values"):
        parts.append("Your core values: " + ", ".join(mem["key_values"]))
    if mem.get("life_defining_events"):
        parts.append("Defining events that shaped you: " + "; ".join(mem["life_defining_events"]))
    if mem.get("immutable_constraints"):
        parts.append("Hard constraints on your behaviour: " + "; ".join(mem["immutable_constraints"]))
    if mem.get("tendency_summary"):
        parts.append(f"Behavioural tendency: {mem['tendency_summary']}")

    psych_bits = []
    if di.get("decision_style"):
        psych_bits.append(f"decision style is {di['decision_style']}")
    if di.get("trust_anchor"):
        psych_bits.append(f"you trust {di['trust_anchor']} most")
    if di.get("risk_appetite"):
        psych_bits.append(f"risk appetite {di['risk_appetite']}")
    if di.get("primary_value_orientation"):
        psych_bits.append(f"primary value orientation {di['primary_value_orientation']}")
    if psych_bits:
        parts.append("Decision psychology: " + "; ".join(psych_bits) + ".")

    if di.get("key_tensions"):
        parts.append("Internal tensions you live with: " + "; ".join(di["key_tensions"]))

    ps = bt.get("price_sensitivity") or {}
    if ps.get("band") or ps.get("description"):
        parts.append(f"Price sensitivity ({ps.get('band', 'mid')}): {ps.get('description', '')}")
    if bt.get("reasoning_prompt"):
        parts.append(f"How you reason: {bt['reasoning_prompt']}")

    if bullets:
        parts.append("How you approach decisions:\n- " + "\n- ".join(str(b) for b in bullets))

    if stories:
        story_lines = []
        for s in stories[:3]:
            title = s.get("title", "")
            narr = s.get("narrative", "")
            if title or narr:
                story_lines.append(f"  • {title}: {narr}")
        if story_lines:
            parts.append("Life stories that shaped you:\n" + "\n".join(story_lines))

    parts.append(
        "Speak in first person as this person. Be specific, grounded in your context "
        "(city, occupation, household, values). Stay in character — never mention being "
        "an AI, a model, or a simulation. Keep replies to 2–5 sentences unless the "
        "question genuinely calls for more. Bring your tensions, biases, and rough edges; "
        "real people aren't tidy."
    )
    return "\n\n".join(parts)


@app.post("/generated/{persona_id}/chat", response_model=ChatResponse)
async def chat_generated(
    persona_id: str,
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Chat with a generated (web-created) persona.

    Self-contained handler: builds a system prompt from the generated persona's
    narrative + insights + memory + decision_bullets and calls Sonnet directly.
    Decision trace is None — generated personas don't carry a PersonaRecord, so
    the 5-step decide/respond pipeline isn't reused here. (Reusing it would
    require schema-coercing the dict into PersonaRecord, which is invasive given
    the empty attributes map and shape differences.)
    """
    # Moderation: reject the message before consuming chat allowance.
    await _enforce_and_log_moderation(request.message, user, db, surface="chat")
    await check_and_increment_allowance(user, "chat", db)

    # Load: cache → disk fallback (mirror GET /generated/{id})
    if persona_id not in _GENERATED:
        path = _GENERATED_DIR / f"{persona_id}.json"
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    _GENERATED[persona_id] = json.load(f)
                logger.info("[chat_generated] loaded %s from disk", persona_id)
            except Exception as exc:
                logger.warning("[chat_generated] disk load failed for %s: %s", persona_id, exc)

    if persona_id not in _GENERATED:
        raise HTTPException(status_code=404, detail=f"Generated persona '{persona_id}' not found")

    persona = _GENERATED[persona_id]
    name = (persona.get("demographic_anchor") or {}).get("name") or "Persona"
    system_prompt = _build_generated_system_prompt(persona)

    client = _client()
    chat_model = os.environ.get("CHAT_MODEL", "claude-sonnet-4-5")

    try:
        msg = await client.messages.create(
            model=chat_model,
            max_tokens=600,
            system=system_prompt,
            messages=[{"role": "user", "content": request.message}],
        )
        reply = msg.content[0].text if msg.content else ""
    except Exception as e:
        logger.exception("[chat_generated] %s chat error", persona_id)
        raise HTTPException(status_code=500, detail=f"Simulation error: {e}")

    return ChatResponse(
        reply=reply,
        decision_trace=None,
        persona_id=persona_id,
        persona_name=name,
    )


# ── Probe models ─────────────────────────────────────────────────────────

class ProbeRequest(BaseModel):
    product_name: str
    category: str
    description: str
    claims: list[str] = []  # max 5
    price: str
    image_url: str | None = None
    # Optional product brief uploaded as a PDF — base64-encoded, no data:
    # prefix. When present, treated as additional context appended to the
    # description. Same convention as ICPRequest.pdf_content on /generate.
    pdf_content: str | None = None
    pdf_filename: str | None = None


class ClaimVerdict(BaseModel):
    claim: str
    score: int  # 1-10
    comment: str


class ProbeResult(BaseModel):
    probe_id: str
    persona_id: str
    persona_name: str
    persona_portrait_url: str | None
    product_name: str
    category: str

    # REACTION
    purchase_intent: dict  # {"score": int, "rationale": str}
    first_impression: dict  # {"adjectives": list[str], "feeling": str}

    # BELIEF
    claim_believability: list[ClaimVerdict]
    differentiation: dict  # {"score": int, "comment": str}

    # FRICTION
    top_objection: str
    trust_signals_needed: list[str]

    # COMMITMENT
    price_willingness: dict  # {"wtp_low": str, "wtp_high": str, "reaction": str}
    word_of_mouth: dict  # {"likelihood": int, "what_theyd_say": str}

    created_at: str


# `from __future__ import annotations` defers types as strings; rebuild so
# Pydantic resolves the forward reference to ClaimVerdict.
ProbeResult.model_rebuild()


# ── Probe directories ─────────────────────────────────────────────────────

_PROBES_DIR = _DATA_ROOT / "probes"


# ── Category memory generation ────────────────────────────────────────────

async def _summarize_probe_pdf(
    pdf_b64: str,
    filename: str | None,
    client: anthropic.AsyncAnthropic,
) -> str:
    """Extract a compact summary of an uploaded product brief PDF.

    Sends the PDF as a `document` content block to Haiku and asks for the
    consumer-facing details that matter for a Litmus probe: what the
    product is, who it's for, key value props / claims, price hints,
    distribution. Output is plain text, capped ~600 words, suitable to
    splice into the probe's `description` field.
    """
    if not pdf_b64:
        return ""
    try:
        msg = await client.messages.create(
            model=os.environ.get("PDF_SUMMARY_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=900,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                        # Some Anthropic SDK versions accept `title`, harmless if dropped.
                        **({"title": filename} if filename else {}),
                    },
                    {
                        "type": "text",
                        "text": (
                            "This is a product brief uploaded by a user who is about to "
                            "run a consumer-perception probe on it. Extract the consumer-"
                            "facing facts a sceptical buyer would want to know:\n"
                            "• What the product is (in one line)\n"
                            "• Who it's for / target use case\n"
                            "• 3-6 key claims or value propositions\n"
                            "• Price or pricing model if mentioned\n"
                            "• Distribution / how to buy if mentioned\n"
                            "• Anything notable a buyer might be sceptical about\n\n"
                            "Plain text, ~400-600 words. No marketing fluff. No headings "
                            "the user didn't write. No commentary about the document itself."
                        ),
                    },
                ],
            }],
        )
        text = msg.content[0].text if msg.content else ""
        return (text or "").strip()[:6000]
    except Exception as exc:  # pragma: no cover
        logger.warning("[probe_pdf] summary call failed: %s", exc)
        return ""


async def _generate_category_memory(
    persona: dict,
    product_brief: dict,
    client: anthropic.AsyncAnthropic,
) -> dict:
    """One Haiku call returning category memories. Cached by (persona_id, brief_hash)."""
    import hashlib

    persona_id = persona.get("persona_id", "")
    cache_key = hashlib.sha256(
        (product_brief["product_name"] + product_brief["description"] + product_brief["price"]).encode()
    ).hexdigest()[:12]

    cache_path = _PROBES_DIR / persona_id / f"memory_{cache_key}.json"
    if cache_path.exists():
        try:
            with open(cache_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    da = persona.get("demographic_anchor") or {}
    name = da.get("name") or "this person"
    age = da.get("age") or ""
    location = da.get("location") or {}
    city = location.get("city") or ""
    country = location.get("country") or ""
    occupation = (da.get("employment") or {}).get("occupation") or ""
    income = da.get("income_level") or "middle"
    narrative = (persona.get("narrative") or {}).get("third_person") or ""
    ps = (persona.get("behavioural_tendencies") or {}).get("price_sensitivity") or {}

    prompt = f"""You are generating first-person category memories for {name}, {age}, {occupation}, {city}, {country}. Income: {income}. {narrative}

Product being evaluated: {product_brief['product_name']} ({product_brief['category']}) at {product_brief['price']}.

Generate 10-12 rich first-person memories for each of these 6 keys. These are real memories this person would have. Be specific about brands, prices, and experiences.

Return ONLY valid JSON with these exact keys:
{{
  "purchase_history": ["<I bought X for Y because Z>", ...],
  "competitor_awareness": ["<I know about X brand because...>", ...],
  "channel_preferences": ["<I usually buy X from Y because...>", ...],
  "budget_anchors": ["<At Y price point I feel Z>", ...],
  "trust_signals": ["<I trust X when they show/say Y>", ...],
  "category_attitudes": ["<My general view on this category is...>", ...]
}}

Each list should have 2-3 entries. Be specific to the {product_brief['category']} category and to this person's context ({city}, {country}, {income} income, {ps.get('band', 'mid')} price sensitivity)."""

    memory_model = os.environ.get("MEMORY_MODEL", "claude-haiku-4-5")
    msg = await client.messages.create(
        model=memory_model,
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text

    try:
        memory = json.loads(raw)
    except Exception:
        import re as _re
        m = _re.search(r"\{[\s\S]+\}", raw)
        memory = json.loads(m.group(0)) if m else {}

    # Ensure all keys exist
    for key in ("purchase_history", "competitor_awareness", "channel_preferences",
                "budget_anchors", "trust_signals", "category_attitudes"):
        memory.setdefault(key, [])

    # Persist
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False)

    return memory


# ── Probe system prompt builder ───────────────────────────────────────────

def _build_probe_system_prompt(persona: dict, memory: dict, product_brief: dict) -> str:
    """Build the shared system prompt for all 8 probe questions."""
    base = _build_generated_system_prompt(persona)

    memory_parts = []
    if memory.get("purchase_history"):
        memory_parts.append("Purchase history in this category:\n" + "\n".join(f"- {m}" for m in memory["purchase_history"]))
    if memory.get("competitor_awareness"):
        memory_parts.append("Competitor awareness:\n" + "\n".join(f"- {m}" for m in memory["competitor_awareness"]))
    if memory.get("channel_preferences"):
        memory_parts.append("How you prefer to buy:\n" + "\n".join(f"- {m}" for m in memory["channel_preferences"]))
    if memory.get("budget_anchors"):
        memory_parts.append("Your price anchors for this category:\n" + "\n".join(f"- {m}" for m in memory["budget_anchors"]))
    if memory.get("trust_signals"):
        memory_parts.append("What builds trust for you in this category:\n" + "\n".join(f"- {m}" for m in memory["trust_signals"]))
    if memory.get("category_attitudes"):
        memory_parts.append("Your general attitudes about this category:\n" + "\n".join(f"- {m}" for m in memory["category_attitudes"]))

    claims_text = ""
    if product_brief.get("claims"):
        claims_text = "\nProduct claims:\n" + "\n".join(f"- {c}" for c in product_brief["claims"])

    product_section = f"""---
PRODUCT BEING EVALUATED

Product: {product_brief['product_name']}
Category: {product_brief['category']}
Price: {product_brief['price']}
Description: {product_brief['description']}{claims_text}
---

YOUR CATEGORY MEMORIES

{chr(10).join(memory_parts)}
---

You are being asked to evaluate this product as yourself. Answer in JSON only. Be honest, specific, and consistent with your character, values, and context. Do not break character."""

    return base + "\n\n" + product_section


# ── Individual probe question handlers ───────────────────────────────────

async def _probe_purchase_intent(system: str, product_brief: dict, client: anthropic.AsyncAnthropic) -> dict:
    msg = await client.messages.create(
        model=os.environ.get("CHAT_MODEL", "claude-sonnet-4-5"),
        max_tokens=300,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"On a scale of 1-10, how likely are you to buy {product_brief['product_name']}? Give a score (integer 1-10) and a 1-2 sentence honest rationale. Return ONLY JSON: {{\"score\": <int>, \"rationale\": \"<string>\"}}"}],
    )
    raw = msg.content[0].text
    try:
        return json.loads(raw)
    except Exception:
        import re as _re
        m = _re.search(r"\{[\s\S]+?\}", raw)
        return json.loads(m.group(0)) if m else {"score": 5, "rationale": raw[:200]}


async def _probe_first_impression(system: str, product_brief: dict, client: anthropic.AsyncAnthropic) -> dict:
    msg = await client.messages.create(
        model=os.environ.get("CHAT_MODEL", "claude-sonnet-4-5"),
        max_tokens=300,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"What is your immediate gut reaction to {product_brief['product_name']}? Give 3-5 single-word adjectives and a 1-sentence feeling. Return ONLY JSON: {{\"adjectives\": [\"<word>\", ...], \"feeling\": \"<sentence>\"}}"}],
    )
    raw = msg.content[0].text
    try:
        return json.loads(raw)
    except Exception:
        import re as _re
        m = _re.search(r"\{[\s\S]+?\}", raw)
        return json.loads(m.group(0)) if m else {"adjectives": [], "feeling": raw[:200]}


async def _probe_claim_believability(system: str, product_brief: dict, client: anthropic.AsyncAnthropic) -> list:
    claims = product_brief.get("claims") or []
    if not claims:
        return []
    claims_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))
    msg = await client.messages.create(
        model=os.environ.get("CHAT_MODEL", "claude-sonnet-4-5"),
        max_tokens=600,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"Rate each product claim for believability (1-10) and give a short comment. Claims:\n{claims_text}\n\nReturn ONLY JSON array: [{{\"claim\": \"<claim>\", \"score\": <int>, \"comment\": \"<1 sentence>\"}}]"}],
    )
    raw = msg.content[0].text
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        import re as _re
        m = _re.search(r"\[[\s\S]+\]", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        return [{"claim": c, "score": 5, "comment": "Unable to parse response"} for c in claims]


async def _probe_differentiation(system: str, product_brief: dict, client: anthropic.AsyncAnthropic) -> dict:
    msg = await client.messages.create(
        model=os.environ.get("CHAT_MODEL", "claude-sonnet-4-5"),
        max_tokens=300,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"Does {product_brief['product_name']} feel meaningfully different from alternatives you know in the {product_brief['category']} space? Rate 1-10 and give a 1-2 sentence comment. Return ONLY JSON: {{\"score\": <int>, \"comment\": \"<string>\"}}"}],
    )
    raw = msg.content[0].text
    try:
        return json.loads(raw)
    except Exception:
        import re as _re
        m = _re.search(r"\{[\s\S]+?\}", raw)
        return json.loads(m.group(0)) if m else {"score": 5, "comment": raw[:200]}


async def _probe_top_objection(system: str, product_brief: dict, client: anthropic.AsyncAnthropic) -> str:
    msg = await client.messages.create(
        model=os.environ.get("CHAT_MODEL", "claude-sonnet-4-5"),
        max_tokens=200,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"What is your single strongest reason NOT to buy {product_brief['product_name']}? Answer in 1-2 sentences as yourself. Return ONLY JSON: {{\"objection\": \"<string>\"}}"}],
    )
    raw = msg.content[0].text
    try:
        data = json.loads(raw)
        return data.get("objection", raw[:300])
    except Exception:
        import re as _re
        m = _re.search(r'"objection"\s*:\s*"([^"]+)"', raw)
        return m.group(1) if m else raw[:300]


async def _probe_trust_signals(system: str, product_brief: dict, client: anthropic.AsyncAnthropic) -> list:
    msg = await client.messages.create(
        model=os.environ.get("CHAT_MODEL", "claude-sonnet-4-5"),
        max_tokens=300,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"What 3-5 specific things would make you confident enough to buy {product_brief['product_name']}? Be specific (not generic). Return ONLY JSON: {{\"signals\": [\"<bullet>\", ...]}}"}],
    )
    raw = msg.content[0].text
    try:
        data = json.loads(raw)
        return data.get("signals", [])
    except Exception:
        import re as _re
        m = _re.search(r"\[[\s\S]+?\]", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        return []


async def _probe_price_willingness(system: str, product_brief: dict, client: anthropic.AsyncAnthropic) -> dict:
    msg = await client.messages.create(
        model=os.environ.get("CHAT_MODEL", "claude-sonnet-4-5"),
        max_tokens=300,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"The listed price for {product_brief['product_name']} is {product_brief['price']}. What price range would you consider fair (low and high)? What is your honest reaction to the listed price? Return ONLY JSON: {{\"wtp_low\": \"<price>\", \"wtp_high\": \"<price>\", \"reaction\": \"<1-2 sentences>\"}}"}],
    )
    raw = msg.content[0].text
    try:
        return json.loads(raw)
    except Exception:
        import re as _re
        m = _re.search(r"\{[\s\S]+?\}", raw)
        return json.loads(m.group(0)) if m else {"wtp_low": "", "wtp_high": "", "reaction": raw[:200]}


async def _probe_word_of_mouth(system: str, product_brief: dict, client: anthropic.AsyncAnthropic) -> dict:
    msg = await client.messages.create(
        model=os.environ.get("CHAT_MODEL", "claude-sonnet-4-5"),
        max_tokens=300,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"How likely are you (1-10) to recommend {product_brief['product_name']} to a friend? What would you actually say to them about it? Return ONLY JSON: {{\"likelihood\": <int>, \"what_theyd_say\": \"<1-2 sentence casual quote>\"}}"}],
    )
    raw = msg.content[0].text
    try:
        return json.loads(raw)
    except Exception:
        import re as _re
        m = _re.search(r"\{[\s\S]+?\}", raw)
        return json.loads(m.group(0)) if m else {"likelihood": 5, "what_theyd_say": raw[:200]}


# ── Probe endpoints ───────────────────────────────────────────────────────

def _load_persona_for_probe(persona_id: str) -> dict:
    """Load persona from cache or disk; raise 404 if not found."""
    if persona_id not in _GENERATED:
        path = _GENERATED_DIR / f"{persona_id}.json"
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    _GENERATED[persona_id] = json.load(f)
            except Exception as exc:
                logger.warning("[probe] disk load failed for %s: %s", persona_id, exc)
    if persona_id not in _GENERATED:
        raise HTTPException(status_code=404, detail=f"Generated persona '{persona_id}' not found")
    return _GENERATED[persona_id]


@app.post("/generated/{persona_id}/probe", response_model=ProbeResult)
async def run_probe(
    persona_id: str,
    request: ProbeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run an 8-question Litmus probe against a generated persona.

    Pipeline:
      1. Load persona (cache or disk)
      2. Generate or load category memory (Haiku, cached by brief hash)
      3. Build shared system prompt
      4. Run 8 Sonnet probe calls in parallel (prompt-cached system prompt)
      5. Assemble ProbeResult
      6. Persist to pilots/the-mind/probes/{persona_id}/{probe_id}.json
    """
    import hashlib
    from datetime import datetime, timezone

    # Moderation: scan product name + description + claims as one blob.
    probe_blob = " | ".join([
        request.product_name or "",
        getattr(request, "description", "") or "",
        " ".join(request.claims or []),
    ])
    if probe_blob.strip():
        await _enforce_and_log_moderation(probe_blob, user, db, surface="probe")

    await check_and_increment_allowance(user, "probe", db)

    persona = _load_persona_for_probe(persona_id)
    da = persona.get("demographic_anchor") or {}
    name = da.get("name") or "Persona"
    portrait_url = _GENERATED_PORTRAITS.get(persona_id)

    # If the user uploaded a product brief PDF, extract a compact summary
    # via Haiku and append it to the description. The summary lives inside
    # the cached system prompt across all 8 probe calls, so this is a
    # one-time cost. We also re-run moderation on the extracted text.
    description = request.description or ""
    if request.pdf_content:
        try:
            pdf_summary = await _summarize_probe_pdf(
                request.pdf_content, request.pdf_filename, _client()
            )
            if pdf_summary:
                # Moderate the summary (uses the same wordlist as user briefs)
                await _enforce_and_log_moderation(
                    pdf_summary, user, db, surface="probe_pdf",
                )
                description = (
                    description.strip()
                    + ("\n\n" if description.strip() else "")
                    + "From the uploaded brief:\n"
                    + pdf_summary
                )[:6000]  # hard cap so prompt cache stays sane
        except HTTPException:
            raise  # moderation block — surface as 422
        except Exception as exc:
            logger.warning("[probe] pdf summary skipped: %s", exc)

    product_brief = {
        "product_name": request.product_name,
        "category": request.category,
        "description": description,
        "claims": request.claims[:5],
        "price": request.price,
    }

    client = _client()

    # Step 1: generate or load category memory
    memory = await _generate_category_memory(persona, product_brief, client)

    # Step 2: build shared system prompt (will be prompt-cached across all 8 calls)
    system_prompt = _build_probe_system_prompt(persona, memory, product_brief)

    # Step 3: run 8 probe questions in parallel
    (
        purchase_intent,
        first_impression,
        claim_believability_raw,
        differentiation,
        top_objection,
        trust_signals_raw,
        price_willingness,
        word_of_mouth,
    ) = await asyncio.gather(
        _probe_purchase_intent(system_prompt, product_brief, client),
        _probe_first_impression(system_prompt, product_brief, client),
        _probe_claim_believability(system_prompt, product_brief, client),
        _probe_differentiation(system_prompt, product_brief, client),
        _probe_top_objection(system_prompt, product_brief, client),
        _probe_trust_signals(system_prompt, product_brief, client),
        _probe_price_willingness(system_prompt, product_brief, client),
        _probe_word_of_mouth(system_prompt, product_brief, client),
    )

    # Normalise claim_believability into ClaimVerdict list
    claim_verdicts: list[ClaimVerdict] = []
    for item in (claim_believability_raw or []):
        try:
            claim_verdicts.append(ClaimVerdict(
                claim=item.get("claim", ""),
                score=int(item.get("score", 5)),
                comment=item.get("comment", ""),
            ))
        except Exception:
            pass

    created_at = datetime.now(timezone.utc).isoformat()
    ts_bytes = (persona_id + created_at).encode()
    probe_id = "pr-" + hashlib.sha256(ts_bytes).hexdigest()[:8]

    result = ProbeResult(
        probe_id=probe_id,
        persona_id=persona_id,
        persona_name=name,
        persona_portrait_url=portrait_url,
        product_name=request.product_name,
        category=request.category,
        purchase_intent=purchase_intent,
        first_impression=first_impression,
        claim_believability=claim_verdicts,
        differentiation=differentiation,
        top_objection=top_objection if isinstance(top_objection, str) else str(top_objection),
        trust_signals_needed=trust_signals_raw if isinstance(trust_signals_raw, list) else [],
        price_willingness=price_willingness,
        word_of_mouth=word_of_mouth,
        created_at=created_at,
    )

    # Persist probe result
    probe_dir = _PROBES_DIR / persona_id
    probe_dir.mkdir(parents=True, exist_ok=True)
    with open(probe_dir / f"{probe_id}.json", "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, ensure_ascii=False)

    logger.info("[probe] %s for persona %s saved", probe_id, persona_id)
    return result


@app.get("/probes/{probe_id}", response_model=ProbeResult)
async def get_probe(probe_id: str):
    """Fetch a probe result by ID — public, no auth, used by share page."""
    if not _PROBES_DIR.exists():
        raise HTTPException(status_code=404, detail=f"Probe '{probe_id}' not found")
    for probe_path in _PROBES_DIR.glob(f"*/{probe_id}.json"):
        try:
            with open(probe_path, encoding="utf-8") as f:
                data = json.load(f)
            return ProbeResult(**data)
        except Exception as exc:
            logger.warning("[get_probe] failed to load %s: %s", probe_path, exc)
            raise HTTPException(status_code=500, detail="Failed to load probe")
    raise HTTPException(status_code=404, detail=f"Probe '{probe_id}' not found")


@app.get("/generated/{persona_id}/probes")
async def list_probes_for_persona(persona_id: str):
    """List probe summaries for a persona (probe_id, product_name, purchase_intent score, created_at)."""
    probe_dir = _PROBES_DIR / persona_id
    if not probe_dir.exists():
        return []
    summaries = []
    for p in sorted(probe_dir.glob("pr-*.json"), reverse=True):
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            pi = data.get("purchase_intent") or {}
            summaries.append({
                "probe_id": data["probe_id"],
                "product_name": data.get("product_name", ""),
                "purchase_intent": pi.get("score", 0),
                "created_at": data.get("created_at", ""),
            })
        except Exception:
            pass
    return summaries


async def _auto_generate_portrait(persona_id: str, fal_key: str) -> None:
    """Background task: silently generate portrait after persona creation."""
    try:
        # Pass full persona so the prompt builder can pull derived_insights,
        # bio, household, etc. for richer setting/wardrobe/demeanour cues.
        persona = _GENERATED.get(persona_id) or {}
        prompt = _build_portrait_prompt_dict(persona)
        url = await _call_fal_portrait(prompt, fal_key)
        _GENERATED_PORTRAITS[persona_id] = url
        _save_portraits_to_disk()
        logger.info("[portrait:auto] %s done", persona_id)
    except Exception:
        logger.exception("[portrait:auto] failed for %s", persona_id)


# Per-persona asyncio locks so concurrent generate-portrait calls for the
# SAME persona share one fal.ai render instead of producing different faces.
# Without this, two parallel client requests (React Strict Mode double-fire,
# tab refresh during pending request, etc.) both miss the cache check, both
# hit fal.ai, and the page would flicker between two portraits — leading to
# the "portrait of persona changed by itself" report.
_PORTRAIT_LOCKS: dict[str, asyncio.Lock] = {}


@app.post("/generated/{persona_id}/portrait")
async def generate_portrait(persona_id: str, force: bool = False):
    """Generate (or return cached) portrait for a generated persona.

    Pass ?force=true to bypass the cache and regenerate with the current model.
    """
    if persona_id not in _GENERATED:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")

    # Fast path: already cached.
    if not force and persona_id in _GENERATED_PORTRAITS:
        return {"url": _GENERATED_PORTRAITS[persona_id], "persona_id": persona_id}

    # Single-flight: only one fal.ai call per persona at a time. Concurrent
    # callers wait for the lock; once acquired they re-check the cache (the
    # winner of the race will have populated it).
    lock = _PORTRAIT_LOCKS.setdefault(persona_id, asyncio.Lock())
    async with lock:
        if not force and persona_id in _GENERATED_PORTRAITS:
            return {"url": _GENERATED_PORTRAITS[persona_id], "persona_id": persona_id}

        fal_key = os.environ.get("FAL_KEY", "")
        if not fal_key:
            raise HTTPException(status_code=503, detail="FAL_KEY environment variable not set")

        # Pass full persona so the prompt builder can pull derived_insights,
        # bio, household, etc. for richer setting/wardrobe/demeanour cues.
        prompt = _build_portrait_prompt_dict(_GENERATED[persona_id])
        url = await _call_fal_portrait(prompt, fal_key)
        _GENERATED_PORTRAITS[persona_id] = url
        _save_portraits_to_disk()
        return {"url": url, "persona_id": persona_id, "prompt": prompt}


# ── Admin endpoints ───────────────────────────────────────────────────────
# Read-only oversight for the operator. Gated by ADMIN_EMAILS env var
# (comma-separated). All endpoints require a valid Auth.js JWT belonging to
# an email in that allowlist.

def _admin_emails() -> set[str]:
    raw = os.environ.get("ADMIN_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


async def get_admin_user(user: User = Depends(get_current_user)) -> User:  # type: ignore  # noqa: F821
    """FastAPI dep: 401 unless authenticated AND email is in ADMIN_EMAILS."""
    if (user.email or "").lower() not in _admin_emails():
        raise HTTPException(status_code=403, detail="Not an admin")
    return user


@app.get("/admin/stats")
async def admin_stats(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    """Top-level counts for the operator dashboard."""
    from sqlalchemy import func, select as sa_select
    users_total = (await db.execute(sa_select(func.count()).select_from(User))).scalar() or 0  # type: ignore  # noqa: F821
    events_total = (await db.execute(sa_select(func.count()).select_from(Event))).scalar() or 0  # type: ignore  # noqa: F821
    personas_total = (
        await db.execute(
            sa_select(func.count()).select_from(Event).where(Event.type == EventType.persona_generated)  # type: ignore  # noqa: F821
        )
    ).scalar() or 0
    probes_total = (
        await db.execute(
            sa_select(func.count()).select_from(Event).where(Event.type == EventType.probe_run)  # type: ignore  # noqa: F821
        )
    ).scalar() or 0
    chats_total = (
        await db.execute(
            sa_select(func.count()).select_from(Event).where(Event.type == EventType.chat_message)  # type: ignore  # noqa: F821
        )
    ).scalar() or 0
    return {
        "users_total": users_total,
        "events_total": events_total,
        "personas_total": personas_total,
        "probes_total": probes_total,
        "chats_total": chats_total,
        "personas_on_disk": len(_GENERATED),
    }


@app.get("/admin/users")
async def admin_users(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    """List all users with their per-type event counts."""
    from sqlalchemy import select as sa_select
    rows = (await db.execute(sa_select(User))).scalars().all()  # type: ignore  # noqa: F821
    users_out = []
    for u in rows:
        ev = (
            await db.execute(
                sa_select(Event).where(Event.user_id == u.id)  # type: ignore  # noqa: F821
            )
        ).scalars().all()
        personas = sum(1 for e in ev if e.type == EventType.persona_generated)  # type: ignore  # noqa: F821
        probes = sum(1 for e in ev if e.type == EventType.probe_run)  # type: ignore  # noqa: F821
        chats = sum(1 for e in ev if e.type == EventType.chat_message)  # type: ignore  # noqa: F821
        last_active = max((e.created_at for e in ev), default=None)
        users_out.append({
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "personas": personas,
            "probes": probes,
            "chats": chats,
            "last_active": last_active.isoformat() if last_active else None,
        })
    users_out.sort(key=lambda r: r["last_active"] or "", reverse=True)
    return users_out


@app.get("/admin/personas")
async def admin_personas(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
    limit: int = 100,
):
    """List recent personas joined with their creator's email."""
    from sqlalchemy import select as sa_select
    events = (
        await db.execute(
            sa_select(Event, User)  # type: ignore  # noqa: F821
            .join(User, Event.user_id == User.id)  # type: ignore  # noqa: F821
            .where(Event.type == EventType.persona_generated)  # type: ignore  # noqa: F821
            .order_by(Event.created_at.desc())  # type: ignore  # noqa: F821
            .limit(limit)
        )
    ).all()
    out = []
    for ev, usr in events:
        pid = ev.ref_id or ""
        p = _GENERATED.get(pid) or {}
        da = p.get("demographic_anchor") or {}
        out.append({
            "persona_id": pid,
            "name": da.get("name", "(missing)"),
            "age": da.get("age"),
            "city": da.get("city"),
            "country": da.get("country"),
            "creator_email": usr.email,
            "creator_name": usr.name,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
            "portrait_url": _GENERATED_PORTRAITS.get(pid),
        })
    return out


@app.get("/admin/probes")
async def admin_probes(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
    limit: int = 100,
):
    """List recent probes joined with creator email + verdict summary."""
    from sqlalchemy import select as sa_select
    events = (
        await db.execute(
            sa_select(Event, User)  # type: ignore  # noqa: F821
            .join(User, Event.user_id == User.id)  # type: ignore  # noqa: F821
            .where(Event.type == EventType.probe_run)  # type: ignore  # noqa: F821
            .order_by(Event.created_at.desc())  # type: ignore  # noqa: F821
            .limit(limit)
        )
    ).all()
    out = []
    for ev, usr in events:
        probe_id = ev.ref_id or ""
        # Probes are sharded under _PROBES_DIR/<persona_id>/<probe_id>.json
        # Find the file by glob.
        probe_data: dict = {}
        for path in _PROBES_DIR.rglob(f"{probe_id}.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    probe_data = json.load(f)
                break
            except Exception:
                pass
        pi = probe_data.get("purchase_intent") or {}
        out.append({
            "probe_id": probe_id,
            "product_name": probe_data.get("product_name", "(missing)"),
            "category": probe_data.get("category", ""),
            "purchase_intent": pi.get("score"),
            "top_objection": probe_data.get("top_objection", "")[:200],
            "persona_name": probe_data.get("persona_name", ""),
            "creator_email": usr.email,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        })
    return out


@app.get("/admin/events")
async def admin_events(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
    limit: int = 200,
):
    """Raw event firehose, most recent first."""
    from sqlalchemy import select as sa_select
    events = (
        await db.execute(
            sa_select(Event, User)  # type: ignore  # noqa: F821
            .join(User, Event.user_id == User.id)  # type: ignore  # noqa: F821
            .order_by(Event.created_at.desc())  # type: ignore  # noqa: F821
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": ev.id,
            "type": ev.type.value if hasattr(ev.type, "value") else str(ev.type),
            "user_email": usr.email,
            "ref_id": ev.ref_id,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }
        for ev, usr in events
    ]


@app.get("/admin/users/{user_id}")
async def admin_user_detail(
    user_id: str,
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    """Per-user detail: profile + full event timeline with enrichment.

    For each event, includes:
      - persona_generated: persona name/age/city + brief if known
      - probe_run: product name + verdict + top objection
      - chat_message: persona name + nothing else (chat content not stored)
    """
    from sqlalchemy import select as sa_select
    user_row = (
        await db.execute(sa_select(User).where(User.id == user_id))  # type: ignore  # noqa: F821
    ).scalar_one_or_none()
    if user_row is None:
        raise HTTPException(404, detail="User not found")

    events = (
        await db.execute(
            sa_select(Event)  # type: ignore  # noqa: F821
            .where(Event.user_id == user_id)  # type: ignore  # noqa: F821
            .order_by(Event.created_at.desc())  # type: ignore  # noqa: F821
            .limit(500)
        )
    ).scalars().all()

    enriched = []
    for ev in events:
        ev_type = ev.type.value if hasattr(ev.type, "value") else str(ev.type)
        item: dict = {
            "id": ev.id,
            "type": ev_type,
            "ref_id": ev.ref_id,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }
        ref = ev.ref_id or ""
        if ev_type == "persona_generated" and ref in _GENERATED:
            p = _GENERATED[ref]
            da = p.get("demographic_anchor") or {}
            item["persona"] = {
                "name": da.get("name"),
                "age": da.get("age"),
                "city": da.get("city"),
                "country": da.get("country"),
                "portrait_url": _GENERATED_PORTRAITS.get(ref),
            }
        elif ev_type == "probe_run":
            for path in _PROBES_DIR.rglob(f"{ref}.json"):
                try:
                    with open(path, encoding="utf-8") as f:
                        pd = json.load(f)
                    pi = pd.get("purchase_intent") or {}
                    item["probe"] = {
                        "product_name": pd.get("product_name"),
                        "category": pd.get("category"),
                        "purchase_intent": pi.get("score"),
                        "top_objection": (pd.get("top_objection") or "")[:200],
                        "persona_name": pd.get("persona_name"),
                    }
                    break
                except Exception:
                    pass
        elif ev_type == "chat_message" and ref in _GENERATED:
            p = _GENERATED[ref]
            da = p.get("demographic_anchor") or {}
            item["chat"] = {
                "persona_name": da.get("name"),
                "persona_id": ref,
            }
        enriched.append(item)

    return {
        "user": {
            "id": user_row.id,
            "email": user_row.email,
            "name": user_row.name,
            "banned": bool(getattr(user_row, "banned", False)),
            "banned_at": (
                user_row.banned_at.isoformat()
                if getattr(user_row, "banned_at", None) else None
            ),
            "banned_reason": getattr(user_row, "banned_reason", None),
            "flagged_count": int(getattr(user_row, "flagged_count", 0) or 0),
        },
        "events": enriched,
    }


# ── Rate limiting (per-IP + per-user) ─────────────────────────────────────
# In-memory token bucket. Buckets keyed by (route_class, identity).
# Identity = user.id if authed, else client IP.
# Resets on process restart — fine for our scale.

# ── Admin: ban / unban / flagged events ───────────────────────────────────

class BanRequest(BaseModel):
    reason: str = "violation of usage policy"


@app.post("/admin/users/{user_id}/ban")
async def admin_ban_user(
    user_id: str,
    payload: BanRequest,
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    """Mark a user as banned. They can authenticate but cannot use any
    gated endpoint (generate / probe / chat). Reversible via /unban."""
    from datetime import datetime as _dt, timezone as _tz
    from sqlalchemy import select as sa_select, update as sa_update
    target = (
        await db.execute(sa_select(User).where(User.id == user_id))  # type: ignore  # noqa: F821
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(404, detail="User not found")
    await db.execute(
        sa_update(User)
        .where(User.id == user_id)
        .values(banned=True, banned_at=_dt.now(_tz.utc), banned_reason=payload.reason[:200])
    )
    db.add(Event(user_id=user_id, type=EventType.user_banned, ref_id=f"manual:{payload.reason[:60]}"))
    await db.commit()
    logger.warning("[admin] banned user=%s reason=%s by=%s", target.email, payload.reason, _admin.email)
    return {"banned": True, "user_id": user_id, "reason": payload.reason}


@app.post("/admin/users/{user_id}/unban")
async def admin_unban_user(
    user_id: str,
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    """Lift a ban on a user. Resets flagged_count to 0."""
    from sqlalchemy import select as sa_select, update as sa_update
    target = (
        await db.execute(sa_select(User).where(User.id == user_id))  # type: ignore  # noqa: F821
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(404, detail="User not found")
    await db.execute(
        sa_update(User)
        .where(User.id == user_id)
        .values(banned=False, banned_at=None, banned_reason=None, flagged_count=0)
    )
    db.add(Event(user_id=user_id, type=EventType.user_unbanned, ref_id=f"by:{_admin.email}"[:200]))
    await db.commit()
    logger.info("[admin] unbanned user=%s by=%s", target.email, _admin.email)
    return {"banned": False, "user_id": user_id}


@app.get("/admin/flagged")
async def admin_flagged(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    """List all moderation_blocked events with the offending user attached."""
    from sqlalchemy import select as sa_select
    rows = (
        await db.execute(
            sa_select(Event, User)  # type: ignore
            .join(User, User.id == Event.user_id)  # type: ignore
            .where(Event.type == EventType.moderation_blocked)  # type: ignore
            .order_by(Event.created_at.desc())  # type: ignore
            .limit(500)
        )
    ).all()
    return [
        {
            "id": ev.id,
            "user_id": usr.id,
            "user_email": usr.email,
            "user_banned": bool(getattr(usr, "banned", False)),
            "user_flagged_count": int(getattr(usr, "flagged_count", 0) or 0),
            "ref_id": ev.ref_id,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }
        for ev, usr in rows
    ]


# ── Invite codes (private-launch gate) ───────────────────────────────────
# Shared codes (e.g. EARLYACCESS) — many people redeem the same code, we
# track usage count per code so distribution channels are visible.

class InviteCheckResponse(BaseModel):
    code: str
    valid: bool
    label: str | None = None
    used_count: int = 0
    max_uses: int | None = None
    reason: str | None = None


@app.get("/invites/{code}/check", response_model=InviteCheckResponse)
async def invites_check(
    code: str,
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    """Public endpoint — validates an invite code. No auth required.

    Used by the /invite/[code] landing page to decide whether to set the
    `invite_ok` cookie and forward the user to /sign-in.
    """
    from sqlalchemy import select as sa_select
    norm = (code or "").strip().upper()
    if not norm:
        return InviteCheckResponse(code=code, valid=False, reason="empty")
    row = (
        await db.execute(sa_select(InviteCode).where(InviteCode.code == norm))  # type: ignore
    ).scalar_one_or_none()
    if row is None:
        return InviteCheckResponse(code=norm, valid=False, reason="not_found")
    if not bool(getattr(row, "active", True)):
        return InviteCheckResponse(code=norm, valid=False, reason="inactive",
                                   label=row.label, used_count=row.used_count or 0,
                                   max_uses=row.max_uses)
    if row.max_uses is not None and (row.used_count or 0) >= row.max_uses:
        return InviteCheckResponse(code=norm, valid=False, reason="exhausted",
                                   label=row.label, used_count=row.used_count or 0,
                                   max_uses=row.max_uses)
    return InviteCheckResponse(
        code=norm, valid=True, label=row.label,
        used_count=row.used_count or 0, max_uses=row.max_uses,
    )


class InviteCreateRequest(BaseModel):
    label: str | None = None
    max_uses: int | None = None


@app.post("/admin/invites")
async def admin_create_invite(
    req: InviteCreateRequest,
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    """Admin: mint a fresh invite code with a random URL-safe value.

    Codes are no longer chosen by humans — they're auto-generated so
    they're unguessable and shareable as raw links. The `label` field
    is the admin-facing name of the distribution channel ("Twitter post
    Apr 27", "Sarah from Pepsi", etc.).
    """
    from sqlalchemy import select as sa_select
    from auth import mint_random_code  # noqa: PLC0415
    # Try a few times for a unique code (extreme entropy, so this is
    # belt-and-braces only).
    code = ""
    for _ in range(5):
        candidate = mint_random_code(10)
        existing = (
            await db.execute(sa_select(InviteCode).where(InviteCode.code == candidate))  # type: ignore
        ).scalar_one_or_none()
        if existing is None:
            code = candidate
            break
    if not code:
        raise HTTPException(500, detail="could not mint unique code")
    db.add(InviteCode(  # type: ignore
        code=code,
        label=req.label,
        max_uses=req.max_uses,
        used_count=0,
        active=True,
        created_by_email=_admin.email,
    ))
    await db.commit()
    logger.info("[admin] invite mint code=%s label=%s by=%s", code, req.label, _admin.email)
    return {"code": code, "ok": True}


class InviteEmailRequest(BaseModel):
    to_email: str
    label: str | None = None
    note: str | None = None


@app.post("/admin/invites/email")
async def admin_email_invite(
    req: InviteEmailRequest,
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    """Admin: mint a one-time code and email it directly to a person.

    Distinct from POST /admin/invites because (a) max_uses is forced to
    1, and (b) we record sent_to_email + sent_at so the admin sees
    "who I emailed, did they redeem?" in the invites table.
    """
    from sqlalchemy import select as sa_select
    from auth import mint_random_code  # noqa: PLC0415
    target = (req.to_email or "").strip().lower()
    if "@" not in target:
        raise HTTPException(400, detail="to_email must be a valid email")
    code = ""
    for _ in range(5):
        candidate = mint_random_code(10)
        existing = (
            await db.execute(sa_select(InviteCode).where(InviteCode.code == candidate))  # type: ignore
        ).scalar_one_or_none()
        if existing is None:
            code = candidate
            break
    if not code:
        raise HTTPException(500, detail="could not mint unique code")
    now = datetime.now(timezone.utc)
    db.add(InviteCode(  # type: ignore
        code=code,
        label=req.label or f"emailed:{target}",
        max_uses=1,
        used_count=0,
        active=True,
        created_by_email=_admin.email,
        sent_to_email=target,
        sent_at=now,
    ))
    await db.commit()
    # Fire the email best-effort. If Resend isn't configured the admin
    # still has the code in the table and can copy/paste it.
    invite_url = f"{_public_origin()}/invite/{code}"
    await _send_invite_email(target, invite_url, req.note or "")
    logger.info("[admin] invite emailed code=%s to=%s by=%s", code, target, _admin.email)
    return {"code": code, "url": invite_url, "ok": True}


# ── Pending-user endpoints (waitlist) ─────────────────────────────────────

class RedeemCodeRequest(BaseModel):
    code: str


@app.post("/redeem-code")
async def redeem_code(
    req: RedeemCodeRequest,
    user: User = Depends(get_current_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    """Pending user pastes an invite code on the waitlist screen.

    On success we activate the user, mint their personal reshare code,
    and record invited_by_user_id from the redeemed code's owner. The
    user can now do everything an active user can.
    """
    from sqlalchemy import select as sa_select, update as sa_update
    from auth import _create_personal_invite_code  # noqa: PLC0415
    norm = (req.code or "").strip().upper()
    if not norm:
        raise HTTPException(400, detail="code is required")
    if (getattr(user, "access_status", "active") or "active") == "active":
        return {"ok": True, "already_active": True}
    ic = (
        await db.execute(sa_select(InviteCode).where(InviteCode.code == norm))  # type: ignore
    ).scalar_one_or_none()
    if ic is None or not bool(getattr(ic, "active", True)):
        raise HTTPException(400, detail={"error": "invalid_code", "message": "That code isn't valid."})
    max_uses = getattr(ic, "max_uses", None)
    used = int(getattr(ic, "used_count", 0) or 0)
    if max_uses is not None and used >= max_uses:
        raise HTTPException(400, detail={"error": "exhausted", "message": "That code has been fully redeemed."})
    user.access_status = "active"
    user.approved_at = datetime.now(timezone.utc)
    user.invite_code_used = norm
    user.invited_by_user_id = getattr(ic, "created_by_user_id", None)
    if not getattr(user, "personal_invite_code", None):
        user.personal_invite_code = await _create_personal_invite_code(db, user)
    await db.execute(
        sa_update(InviteCode).where(InviteCode.code == norm)  # type: ignore
        .values(used_count=(InviteCode.used_count + 1))  # type: ignore
    )
    await db.commit()
    logger.info("[redeem] user=%s redeemed code=%s", user.email, norm)
    return {"ok": True, "personal_invite_code": user.personal_invite_code}


class AccessRequestPayload(BaseModel):
    reason: str | None = None


@app.post("/access-requests")
async def submit_access_request(
    req: AccessRequestPayload,
    user: User = Depends(get_current_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    """Pending user submits a "please let me in" form. Admin sees it
    in /admin/access-requests; user gets an auto-reply confirming."""
    from sqlalchemy import select as sa_select
    if (getattr(user, "access_status", "active") or "active") == "active":
        return {"ok": True, "already_active": True}
    reason = (req.reason or "").strip()[:2000]
    # Idempotent: if they have an open request already, just return it.
    existing = (
        await db.execute(
            sa_select(AccessRequest)  # type: ignore
            .where(AccessRequest.user_id == user.id)  # type: ignore
            .where(AccessRequest.status == "pending")  # type: ignore
        )
    ).scalar_one_or_none()
    if existing is not None:
        if reason and reason != (existing.reason or ""):
            existing.reason = reason
            await db.commit()
        return {"ok": True, "id": existing.id}
    ar = AccessRequest(user_id=user.id, reason=reason or None)  # type: ignore
    db.add(ar)
    await db.commit()
    # Fire the two emails best-effort.
    await _send_waitlist_user_email(user.email or "", user.name or "")
    await _send_admin_access_request_email(user, reason)
    logger.info("[access-request] from=%s", user.email)
    return {"ok": True, "id": ar.id}


@app.get("/access-requests/mine")
async def my_access_request(
    user: User = Depends(get_current_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    """Frontend reads this on the waitlist screen so it can show
    'we received your request on Apr 27' instead of the empty form."""
    from sqlalchemy import select as sa_select
    row = (
        await db.execute(
            sa_select(AccessRequest)  # type: ignore
            .where(AccessRequest.user_id == user.id)  # type: ignore
            .order_by(AccessRequest.created_at.desc())  # type: ignore
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        return {"exists": False}
    return {
        "exists": True,
        "status": row.status,
        "reason": row.reason,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


# ── Admin: approve pending users + view access requests ──────────────────

@app.post("/admin/users/{user_id}/approve")
async def admin_approve_user(
    user_id: str,
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    """Admin: flip a pending user to active without requiring a code.

    Use case: admin reviewed someone's access-request, decided to let
    them in. We mint their personal reshare code immediately and email
    them their welcome link.
    """
    from sqlalchemy import select as sa_select, update as sa_update
    from auth import _create_personal_invite_code  # noqa: PLC0415
    try:
        target = (await db.execute(sa_select(User).where(User.id == user_id))).scalar_one_or_none()  # type: ignore
        if target is None:
            raise HTTPException(404, detail="user not found")
        if (getattr(target, "access_status", "active") or "active") == "active":
            return {"ok": True, "already_active": True}
        target.access_status = "active"
        target.approved_at = datetime.now(timezone.utc)
        if not getattr(target, "personal_invite_code", None):
            try:
                target.personal_invite_code = await _create_personal_invite_code(db, target)
            except Exception as ce:  # noqa: BLE001
                # Non-fatal: code can be minted on next sign-in by auth.py.
                logger.warning("[admin] approve: invite-code mint failed for %s: %r", target.email, ce)
        # Resolve any open access-requests
        await db.execute(
            sa_update(AccessRequest)  # type: ignore
            .where(AccessRequest.user_id == target.id)  # type: ignore
            .where(AccessRequest.status == "pending")  # type: ignore
            .values(status="approved", resolved_at=datetime.now(timezone.utc), resolved_by_email=_admin.email)
        )
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception("[admin] approve failed for user_id=%s: %r", user_id, e)
        raise HTTPException(500, detail=f"approve_failed: {type(e).__name__}: {e}") from e

    # Email send is best-effort — the user is already approved in DB.
    email_sent = True
    try:
        await _send_approval_email(target.email or "", target.name or "")
    except Exception as ee:  # noqa: BLE001
        email_sent = False
        logger.warning("[admin] approve: email send failed for %s: %r", target.email, ee)
    logger.info("[admin] approved user=%s by=%s email_sent=%s", target.email, _admin.email, email_sent)
    return {"ok": True, "email_sent": email_sent}


@app.get("/admin/access-requests")
async def admin_list_access_requests(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    from sqlalchemy import select as sa_select
    rows = (
        await db.execute(
            sa_select(AccessRequest, User)  # type: ignore
            .join(User, User.id == AccessRequest.user_id)  # type: ignore
            .order_by(AccessRequest.created_at.desc())  # type: ignore
            .limit(500)
        )
    ).all()
    return [
        {
            "id": ar.id,
            "user_id": usr.id,
            "user_email": usr.email,
            "user_name": usr.name,
            "user_image": usr.image,
            "user_access_status": getattr(usr, "access_status", "active"),
            "reason": ar.reason,
            "status": ar.status,
            "created_at": ar.created_at.isoformat() if ar.created_at else None,
            "resolved_at": ar.resolved_at.isoformat() if ar.resolved_at else None,
            "resolved_by_email": ar.resolved_by_email,
        }
        for ar, usr in rows
    ]


@app.post("/admin/access-requests/{req_id}/dismiss")
async def admin_dismiss_access_request(
    req_id: str,
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(AccessRequest).where(AccessRequest.id == req_id)  # type: ignore
        .values(status="dismissed", resolved_at=datetime.now(timezone.utc), resolved_by_email=_admin.email)
    )
    await db.commit()
    return {"ok": True}


@app.get("/admin/referrals")
async def admin_referrals(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    """Referral tree: every active user with at least one downstream
    redemption, plus the count of people they've brought in."""
    from sqlalchemy import select as sa_select, func as sa_func
    inviters = (
        await db.execute(
            sa_select(
                User.invited_by_user_id,                     # type: ignore
                sa_func.count(User.id).label("count"),       # type: ignore
            )
            .where(User.invited_by_user_id.isnot(None))      # type: ignore
            .group_by(User.invited_by_user_id)               # type: ignore
            .order_by(sa_func.count(User.id).desc())         # type: ignore
        )
    ).all()
    out = []
    for inviter_id, n in inviters:
        u = (await db.execute(sa_select(User).where(User.id == inviter_id))).scalar_one_or_none()  # type: ignore
        if u is None:
            continue
        downstream = (
            await db.execute(
                sa_select(User)  # type: ignore
                .where(User.invited_by_user_id == inviter_id)  # type: ignore
                .order_by(User.id)  # type: ignore
            )
        ).scalars().all()
        out.append({
            "inviter_id": u.id,
            "inviter_email": u.email,
            "inviter_name": u.name,
            "personal_invite_code": getattr(u, "personal_invite_code", None),
            "downstream_count": int(n),
            "downstream": [
                {
                    "id": d.id,
                    "email": d.email,
                    "name": d.name,
                    "access_status": getattr(d, "access_status", "active"),
                }
                for d in downstream
            ],
        })
    return out


# ── Email helpers ────────────────────────────────────────────────────────

def _public_origin() -> str:
    """Public-facing origin for invite links in emails."""
    raw = os.environ.get("PUBLIC_WEB_ORIGIN", "").strip()
    if raw:
        return raw.rstrip("/")
    return "https://mind.simulatte.io"


async def _send_email_raw(to_email: str, subject: str, html: str) -> None:
    api_key = os.environ.get("AUTH_RESEND_KEY", "")
    if not api_key or not to_email:
        return
    from_email = os.environ.get("EMAIL_FROM", "noreply@mind.simulatte.io")
    try:
        import httpx as _httpx
        async with _httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"from": from_email, "to": [to_email], "subject": subject, "html": html},
            )
    except Exception:
        logger.exception("[email] send failed to=%s subject=%s", to_email, subject)


async def _send_invite_email(to_email: str, invite_url: str, note: str) -> None:
    note_html = ""
    if note.strip():
        # Escape minimally and wrap in a quote block
        import html as _html
        note_html = (
            f'<blockquote style="border-left:2px solid #A8FF3E;'
            f'padding:8px 16px;margin:16px 0;color:#9A9997;'
            f'font-style:italic">{_html.escape(note)}</blockquote>'
        )
    body = f"""<!doctype html><html><body style="font-family:-apple-system,Helvetica,Arial,sans-serif;
        background:#050505;color:#E9E6DF;padding:32px;line-height:1.6">
      <h1 style="font-size:28px;margin:0 0 16px">You're in.</h1>
      <p>You've been invited to The Mind — Simulatte's persona simulation engine
      for product teams. Click below to claim your access.</p>
      {note_html}
      <p style="margin:24px 0">
        <a href="{invite_url}" style="display:inline-block;background:#A8FF3E;
        color:#050505;padding:14px 24px;text-decoration:none;font-weight:bold;
        text-transform:uppercase;font-size:12px;letter-spacing:0.1em">Claim access →</a>
      </p>
      <p style="color:#9A9997;font-size:13px">Or paste this URL into your browser:<br>
      <code style="color:#A8FF3E">{invite_url}</code></p>
      <hr style="border:0;border-top:1px solid rgba(233,230,223,0.1);margin:32px 0">
      <p style="color:#9A9997;font-size:12px">Simulatte / The Mind / mind.simulatte.io</p>
    </body></html>"""
    await _send_email_raw(to_email, "You're invited to The Mind", body)


async def _send_waitlist_user_email(to_email: str, name: str) -> None:
    if not to_email:
        return
    first = (name or "").split(" ")[0] if name else ""
    greet = f"Hi {first}," if first else "Hi,"
    body = f"""<!doctype html><html><body style="font-family:-apple-system,Helvetica,Arial,sans-serif;
        background:#050505;color:#E9E6DF;padding:32px;line-height:1.6">
      <h1 style="font-size:28px;margin:0 0 16px">Thanks — you're on the waitlist.</h1>
      <p>{greet}</p>
      <p>We got your request to access The Mind. We're letting people in every
      week and we'll reply with your invite link soon.</p>
      <p>If you have a friend with an invite link, redeeming theirs gets you in
      immediately.</p>
      <p style="color:#9A9997;font-size:13px;margin-top:32px">— The Simulatte team</p>
    </body></html>"""
    await _send_email_raw(to_email, "You're on The Mind waitlist", body)


async def _send_admin_access_request_email(user: User, reason: str) -> None:
    admin_emails = [
        e.strip() for e in (os.environ.get("ADMIN_EMAILS", "") or "").split(",")
        if e.strip()
    ]
    if not admin_emails:
        return
    import html as _html
    admin_url = f"{_public_origin()}/admin/access-requests"
    reason_block = (
        f'<blockquote style="border-left:2px solid #A8FF3E;padding:8px 16px;'
        f'margin:16px 0;color:#9A9997">{_html.escape(reason)}</blockquote>'
        if reason else "<p><em>No reason provided.</em></p>"
    )
    body = f"""<!doctype html><html><body style="font-family:-apple-system,Helvetica,Arial,sans-serif;
        background:#050505;color:#E9E6DF;padding:32px;line-height:1.6">
      <h1 style="font-size:24px;margin:0 0 16px">New access request</h1>
      <p><strong>{_html.escape(user.name or '(no name)')}</strong>
      &lt;<a href="mailto:{_html.escape(user.email or '')}" style="color:#A8FF3E">
      {_html.escape(user.email or '')}</a>&gt;</p>
      {reason_block}
      <p style="margin:24px 0">
        <a href="{admin_url}" style="display:inline-block;background:#A8FF3E;
        color:#050505;padding:12px 20px;text-decoration:none;font-weight:bold;
        text-transform:uppercase;font-size:11px;letter-spacing:0.1em">
        Review in admin →</a>
      </p>
    </body></html>"""
    # Send to first admin (CC list could spam; one admin email is enough)
    await _send_email_raw(admin_emails[0], f"Access request from {user.email}", body)


async def _send_approval_email(to_email: str, name: str) -> None:
    if not to_email:
        return
    first = (name or "").split(" ")[0] if name else ""
    greet = f"Hi {first}," if first else "Hi,"
    home_url = _public_origin()
    body = f"""<!doctype html><html><body style="font-family:-apple-system,Helvetica,Arial,sans-serif;
        background:#050505;color:#E9E6DF;padding:32px;line-height:1.6">
      <h1 style="font-size:28px;margin:0 0 16px">You're in.</h1>
      <p>{greet}</p>
      <p>Your access to The Mind is active. Sign in and start building your
      first persona.</p>
      <p style="margin:24px 0">
        <a href="{home_url}" style="display:inline-block;background:#A8FF3E;
        color:#050505;padding:14px 24px;text-decoration:none;font-weight:bold;
        text-transform:uppercase;font-size:12px;letter-spacing:0.1em">
        Open The Mind →</a>
      </p>
      <p style="color:#9A9997;font-size:13px;margin-top:32px">— The Simulatte team</p>
    </body></html>"""
    await _send_email_raw(to_email, "Welcome to The Mind", body)


@app.get("/admin/invites")
async def admin_list_invites(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    """Admin: list all invite codes with usage counts + recent redeemers."""
    from sqlalchemy import select as sa_select, func as sa_func
    rows = (
        await db.execute(
            sa_select(InviteCode).order_by(InviteCode.created_at.desc())  # type: ignore
        )
    ).scalars().all()
    out = []
    for c in rows:
        # Count actual users who redeemed this code (more accurate than used_count
        # if the column ever drifts).
        actual = (
            await db.execute(
                sa_select(sa_func.count()).select_from(User)  # type: ignore
                .where(User.invite_code_used == c.code)  # type: ignore
            )
        ).scalar() or 0
        out.append({
            "code": c.code,
            "label": c.label,
            "max_uses": c.max_uses,
            "used_count": c.used_count or 0,
            "actual_redemptions": int(actual),
            "active": bool(c.active),
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "created_by_email": c.created_by_email,
            "created_by_user_id": getattr(c, "created_by_user_id", None),
            "sent_to_email": getattr(c, "sent_to_email", None),
            "sent_at": (c.sent_at.isoformat() if getattr(c, "sent_at", None) else None),
        })
    return out


@app.post("/admin/invites/{code}/deactivate")
async def admin_deactivate_invite(
    code: str,
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
):
    from sqlalchemy import update as sa_update
    norm = (code or "").strip().upper()
    await db.execute(
        sa_update(InviteCode).where(InviteCode.code == norm).values(active=False)  # type: ignore
    )
    await db.commit()
    return {"code": norm, "active": False}


# ── Admin: seed community wall ─────────────────────────────────────────
# One-shot bulk seeding. Runs the full generation pipeline for a fixed
# set of briefs as a background task so the HTTP request returns quickly
# and the actual generations happen on the server (with MIND_DATA_DIR
# pointing at the Railway volume). Idempotent — skips persona_ids that
# already exist in _GENERATED.

_SEED_BRIEFS: list[tuple[str, str]] = [
    ("Marcus Reyes, 32, Brooklyn",
     "Marcus Reyes, 32, lives in Crown Heights Brooklyn. Senior backend engineer "
     "at a Series-B fintech in the Flatiron, $185K base + RSUs. Dating someone "
     "from Bumble for 8 months. Spends $200/mo on a Peloton he uses twice a "
     "week. Reads The Verge daily, suspicious of crypto since FTX."),
    ("Sarah Chen, 28, San Francisco",
     "Sarah Chen, 28, lives in the Mission with two roommates. Product manager "
     "at an AI infra startup (Series A, ~$140K). Runs the SF marathon. "
     "Vegetarian since college. Trusts Wirecutter more than influencers."),
    ("Diego Martinez, 41, Austin",
     "Diego Martinez, 41, owns a small farm-to-table restaurant in East Austin. "
     "Married to a high-school teacher, two kids. $95K personal draw. "
     "Trusts other restaurant owners' word-of-mouth."),
    ("Jasmine Williams, 24, Atlanta",
     "Jasmine Williams, 24, dance educator and TikTok creator (220K followers). "
     "Lives with her mom in East Point Atlanta. Earns $3-6K/mo from brand deals. "
     "Trusts her three best friends' group chat over any creator."),
    ("Robert Kowalski, 58, Chicago",
     "Robert Kowalski, 58, retired union electrician (IBEW Local 134). "
     "Pension + social security ~$72K/yr. Drives a 2014 F-150. "
     "Distrusts most marketing. Won't touch subscriptions."),
    ("Emily Nakamura, 36, Seattle",
     "Emily Nakamura, 36, UX researcher at Microsoft, $165K + bonus. "
     "Vegan for 7 years. Trusts long-form reviews and academic papers. "
     "Tracks every purchase in a spreadsheet."),
    ("Tyler Brooks, 22, Nashville",
     "Tyler Brooks, 22, sophomore at Belmont University studying songwriting. "
     "Works 30 hrs/wk at a Music Row coffee shop. $14K/yr after expenses. "
     "Cash-poor, time-rich. Decides on gear after 10 YouTube reviews."),
    ("Maria Castillo, 45, Phoenix",
     "Maria Castillo, 45, ICU nurse at Banner Health. Single mom of two "
     "teenagers. $98K/yr but $1,400/mo on her ex's debt. Evangelical "
     "Christian. Trusts her sister and her pastor."),
    ("Aiden O'Brien, 29, Boston",
     "Aiden O'Brien, 29, biotech research associate at a Cambridge startup. "
     "MIT bioengineering BS, part-time MBA at Sloan. $115K base. "
     "Trusts peer-reviewed studies. Agonises 3 weeks before any non-essential "
     "purchase over $200."),
    ("Chloe Anderson, 38, Denver",
     "Chloe Anderson, 38, marketing director at an outdoor-gear DTC brand. "
     "Divorced 2 years ago, owns a rescue lab. Skis 30+ days a year. "
     "$185K + equity. Trusts athletes and gear-testers."),
    ("Sophie Dubois, 27, Paris",
     "Sophie Dubois, 27, buyer for a Parisian luxury department store. "
     "Sciences Po grad. Lives in the 11th arrondissement. €52K + bonus. "
     "Sceptical of crypto, NFTs. Trusts her grandmother's taste."),
    ("Liam Sorensen, 34, Copenhagen",
     "Liam Sorensen, 34, architect specialising in sustainable housing. "
     "DKK 480K/yr (~€64K). Lives in Vesterbro with his partner and toddler. "
     "Trusts the Danish design canon — anything pre-1980s Scandinavian."),
    ("Anna Kowalska, 31, Warsaw",
     "Anna Kowalska, 31, senior software developer at a Polish neobank. "
     "PLN 26K/mo (~€6K) gross. Lives alone in Praga district. Powerlifts 5x/wk. "
     "Trusts Reddit and her lifting coach. Saves aggressively."),
    ("Hannah Schmidt, 26, Berlin",
     "Hannah Schmidt, 26, freelance illustrator and visual artist. "
     "Iranian-German parents emigrated in the 90s. Lives in Neukölln. "
     "€28-40K/yr depending on commissions. Trusts her artist collective."),
    ("Oliver Whitfield, 52, London",
     "Oliver Whitfield, 52, ex-investment banker (Goldman, 18 yrs) now "
     "independent ESG consultant. £280K/yr. Divorced. Lives in Chelsea. "
     "Won't touch anything that smells of greenwashing."),
    ("Isabella Romano, 23, Milan",
     "Isabella Romano, 23, second-year design student at Politecnico Milano. "
     "Lives at home with parents. €600/mo from Instagram fashion micro-"
     "influencing. Studies industrial design, hates fast fashion. "
     "Trusts her best friend and her aunt who works at Marni."),
    ("Lukas Becker, 39, Munich",
     "Lukas Becker, 39, automotive engineer at BMW, EV transition team. "
     "€92K/yr. Married to a paediatrician, two kids. Bayern Munich season-"
     "ticket holder. Sceptical of Tesla. Trusts ADAC and Stiftung Warentest."),
    ("Freya Lindberg, 30, Stockholm",
     "Freya Lindberg, 30, senior product designer at Spotify HQ. "
     "SEK 58K/mo (~€5K). Runs a sourdough side-hustle. Vegetarian. "
     "Politically green-left. Trusts her ex-Klarna mentor."),
    ("Mateo Garcia, 47, Madrid",
     "Mateo Garcia, 47, chef-owner of a tapas bar in Lavapiés. €60K personal "
     "draw. Real Madrid season-ticket holder. Trusts other restaurant owners "
     "and his supplier of jamón ibérico (40 years)."),
    ("Catarina Almeida, 35, Lisbon",
     "Catarina Almeida, 35, remote ops manager for a Berlin-based fintech, "
     "earns €68K/yr in Lisbon. Returned from London 4 years ago. "
     "Surfs in Costa da Caparica every weekend. Trusts ex-Revolut colleagues."),
]


_SEED_LOCK = asyncio.Lock()
_SEED_STATUS: dict = {"running": False, "done": 0, "total": 0, "errors": []}


async def _seed_one(label: str, brief: str, admin_id: str, client, factory, fal_key: str, sem: asyncio.Semaphore):
    """Generate a single seed persona, with per-step timing and semaphore-bounded concurrency."""
    async with sem:
        import time as _t
        t0 = _t.time()
        try:
            logger.info("[seed] start %s", label)
            anchor, domain, _ = await _extract_from_brief(brief, None, client)
            t1 = _t.time()
            persona = await _generate_persona_direct(
                brief=brief, anchor=anchor, domain=domain, client=client,
            )
            t2 = _t.time()
            pid = persona["persona_id"]
            if pid not in _GENERATED:
                _GENERATED[pid] = persona
                _persist_generated_dict(persona)
                async with factory() as db:
                    db.add(Event(  # type: ignore
                        user_id=admin_id,
                        type=EventType.persona_generated,
                        ref_id=pid,
                    ))
                    await db.commit()
                if fal_key:
                    try:
                        # Pass full persona for richer character/background cues.
                        prompt = _build_portrait_prompt_dict(persona)
                        url = await _call_fal_portrait(prompt, fal_key)
                        _GENERATED_PORTRAITS[pid] = url
                        _save_portraits_to_disk()
                    except Exception:
                        logger.exception("[seed] portrait failed for %s", pid)
            t3 = _t.time()
            _SEED_STATUS["done"] += 1
            logger.info("[seed] %d/%d ✓ %s (extract=%.1fs gen=%.1fs portrait=%.1fs total=%.1fs)",
                        _SEED_STATUS["done"], len(_SEED_BRIEFS), label,
                        t1 - t0, t2 - t1, t3 - t2, t3 - t0)
        except Exception as exc:
            logger.exception("[seed] FAILED: %s after %.1fs", label, _t.time() - t0)
            _SEED_STATUS["errors"].append(f"{label}: {exc}")


async def _run_seed(admin_id: str):
    """Background task: generate all personas + portraits + events in parallel
    (bounded concurrency = 5 to avoid hammering Anthropic/fal rate limits)."""
    global _SEED_STATUS
    from db import get_session_factory  # noqa: PLC0415
    fal_key = os.environ.get("FAL_KEY", "")
    client = _client()
    factory = get_session_factory()
    _SEED_STATUS = {"running": True, "done": 0, "total": len(_SEED_BRIEFS), "errors": []}
    sem = asyncio.Semaphore(5)
    logger.info("[seed] starting parallel run of %d briefs (concurrency=5)", len(_SEED_BRIEFS))
    import time as _t
    t0 = _t.time()
    await asyncio.gather(*(
        _seed_one(label, brief, admin_id, client, factory, fal_key, sem)
        for label, brief in _SEED_BRIEFS
    ))
    _SEED_STATUS["running"] = False
    logger.info("[seed] complete in %.1fs: %d/%d done, %d errors",
                _t.time() - t0,
                _SEED_STATUS["done"], len(_SEED_BRIEFS), len(_SEED_STATUS["errors"]))


@app.post("/admin/seed-community")
async def admin_seed_community(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
):
    """Kick off bulk-seeding of 20 diverse US/Europe personas. Runs as a
    background task. Idempotent — skips persona_ids that already exist."""
    if _SEED_STATUS.get("running"):
        return {"running": True, "done": _SEED_STATUS["done"], "total": _SEED_STATUS["total"]}
    asyncio.create_task(_run_seed(_admin.id))
    return {"started": True, "total": len(_SEED_BRIEFS)}


@app.get("/admin/seed-community/status")
async def admin_seed_community_status(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
):
    return _SEED_STATUS


@app.delete("/admin/generated/{persona_id}")
async def admin_delete_generated(
    persona_id: str,
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
):
    """Remove a generated persona — JSON, in-memory entry, portrait URL.

    Useful for cleaning up duplicates from a retry after a transient
    error, or pulling a low-quality result off the community wall.
    """
    existed = persona_id in _GENERATED
    _GENERATED.pop(persona_id, None)
    _GENERATED_PORTRAITS.pop(persona_id, None)
    try:
        path = _GENERATED_DIR / f"{persona_id}.json"
        if path.exists():
            path.unlink()
    except Exception:
        logger.exception("[admin-delete] failed to unlink %s", persona_id)
    try:
        _save_portraits_to_disk()
    except Exception:
        logger.exception("[admin-delete] failed to persist portraits.json")
    return {"deleted": existed, "persona_id": persona_id}


@app.get("/admin/duplicates")
async def admin_duplicates(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
):
    """List generated personas grouped by name so the operator can spot
    accidental duplicates from retried generations."""
    from collections import defaultdict
    groups: dict[str, list[dict]] = defaultdict(list)
    for pid, p in _GENERATED.items():
        da = p.get("demographic_anchor") or {}
        name = (da.get("name") or "").strip().lower()
        if not name:
            continue
        groups[name].append({
            "persona_id": pid,
            "name": da.get("name"),
            "age": da.get("age"),
            "city": (da.get("location") or {}).get("city"),
            "created_at": p.get("created_at") or p.get("generated_at"),
            "portrait_url": _GENERATED_PORTRAITS.get(pid),
        })
    duplicates = {name: rows for name, rows in groups.items() if len(rows) > 1}
    return {"count": len(duplicates), "groups": duplicates}


# ── Portrait regeneration ──────────────────────────────────────────────────
# Existing portraits were drawn before the topical-prompt rebuild; this lets
# the operator re-roll them one-by-one or in bulk so they pick up wardrobe,
# demeanour, setting, and ethnicity cues from the new builder.

_REGEN_STATUS: dict = {"running": False, "done": 0, "total": 0, "errors": []}


@app.post("/admin/generated/{persona_id}/regenerate-portrait")
async def admin_regenerate_portrait(
    persona_id: str,
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
):
    """Re-run fal.ai for one persona and overwrite the existing URL."""
    if persona_id not in _GENERATED:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")
    fal_key = os.environ.get("FAL_KEY", "")
    if not fal_key:
        raise HTTPException(status_code=503, detail="FAL_KEY not configured")
    persona = _GENERATED[persona_id]
    prompt = _build_portrait_prompt_dict(persona)
    url = await _call_fal_portrait(prompt, fal_key)
    _GENERATED_PORTRAITS[persona_id] = url
    _save_portraits_to_disk()
    return {"persona_id": persona_id, "url": url}


async def _run_regen_all(fal_key: str):
    """Background task: regenerate every existing portrait, semaphore-bounded."""
    global _REGEN_STATUS
    pids = list(_GENERATED.keys())
    _REGEN_STATUS = {"running": True, "done": 0, "total": len(pids), "errors": []}
    sem = asyncio.Semaphore(5)

    async def one(pid: str):
        async with sem:
            try:
                prompt = _build_portrait_prompt_dict(_GENERATED[pid])
                url = await _call_fal_portrait(prompt, fal_key)
                _GENERATED_PORTRAITS[pid] = url
                _REGEN_STATUS["done"] += 1
                logger.info("[regen] %d/%d %s", _REGEN_STATUS["done"], len(pids), pid)
            except Exception as exc:
                logger.exception("[regen] %s failed", pid)
                _REGEN_STATUS["errors"].append(f"{pid}: {exc}")

    await asyncio.gather(*(one(pid) for pid in pids))
    _save_portraits_to_disk()
    _REGEN_STATUS["running"] = False
    logger.info("[regen] complete: %d/%d done, %d errors",
                _REGEN_STATUS["done"], len(pids), len(_REGEN_STATUS["errors"]))


@app.post("/admin/regenerate-all-portraits")
async def admin_regenerate_all_portraits(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
):
    """Kick off bulk regeneration of every generated persona's portrait.
    Idempotent — refuses to start if a regen is already running."""
    fal_key = os.environ.get("FAL_KEY", "")
    if not fal_key:
        raise HTTPException(status_code=503, detail="FAL_KEY not configured")
    if _REGEN_STATUS.get("running"):
        return {"running": True, "done": _REGEN_STATUS["done"], "total": _REGEN_STATUS["total"]}
    asyncio.create_task(_run_regen_all(fal_key))
    return {"started": True, "total": len(_GENERATED)}


@app.get("/admin/regenerate-all-portraits/status")
async def admin_regen_status(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
):
    return _REGEN_STATUS


# ── Admin: list every generated persona for the operator console ──────────

@app.get("/admin/generated")
async def admin_list_generated(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
):
    """Flat list of every generated persona — used by /admin/personas UI."""
    rows: list[dict] = []
    for pid, p in _GENERATED.items():
        da = p.get("demographic_anchor") or {}
        rows.append({
            "persona_id": pid,
            "name": da.get("name"),
            "age": da.get("age"),
            "city": (da.get("location") or {}).get("city"),
            "country": (da.get("location") or {}).get("country"),
            "occupation": (da.get("employment") or {}).get("occupation"),
            "portrait_url": _GENERATED_PORTRAITS.get(pid),
            "created_at": p.get("created_at") or p.get("generated_at"),
        })
    rows.sort(key=lambda r: (r.get("created_at") or ""), reverse=True)
    return {"count": len(rows), "personas": rows}


# ── Lightweight feedback / NPS endpoint ───────────────────────────────────

class FeedbackPayload(BaseModel):
    score: int  # 1-10
    comment: str | None = None
    surface: str | None = None  # "probe", "chat", "generate", "general"


@app.post("/feedback")
async def post_feedback(
    payload: FeedbackPayload,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Capture an NPS-style score (1-10) plus optional comment.

    Stored as an Event row with type=feedback and payload as ref_id JSON.
    No new table — keeps migration surface zero.
    """
    if not (1 <= payload.score <= 10):
        raise HTTPException(status_code=400, detail="score must be 1-10")
    try:
        body = json.dumps({
            "score": payload.score,
            "comment": (payload.comment or "")[:1000],
            "surface": payload.surface or "general",
        })
        db.add(Event(
            user_id=user.id,
            type=EventType.feedback,
            ref_id=body,
            created_at=datetime.now(timezone.utc),
        ))
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("[feedback] save failed")
        raise HTTPException(status_code=500, detail="failed to save feedback")
    return {"ok": True}


@app.get("/admin/feedback")
async def admin_feedback(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
):
    """Return recent feedback entries with the user's email for context."""
    from sqlalchemy import select as sa_select
    rows = (await db.execute(
        sa_select(Event, User)
        .join(User, Event.user_id == User.id)
        .where(Event.type == EventType.feedback)
        .order_by(Event.created_at.desc())
        .limit(limit)
    )).all()
    out: list[dict] = []
    for ev, u in rows:
        try:
            body = json.loads(ev.ref_id or "{}")
        except Exception:
            body = {}
        out.append({
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
            "email": u.email,
            "name": u.name,
            "score": body.get("score"),
            "comment": body.get("comment"),
            "surface": body.get("surface"),
        })
    if out:
        scores = [r["score"] for r in out if isinstance(r.get("score"), int)]
        promoters = sum(1 for s in scores if s >= 9)
        detractors = sum(1 for s in scores if s <= 6)
        nps = round(((promoters - detractors) / len(scores)) * 100) if scores else 0
        avg = round(sum(scores) / len(scores), 1) if scores else 0
        return {"count": len(out), "nps": nps, "avg": avg, "entries": out}
    return {"count": 0, "nps": 0, "avg": 0, "entries": []}


# ── Cost telemetry ────────────────────────────────────────────────────────
# Per-action cost estimates so the operator can watch unit economics.
# These are deliberate rough numbers — Anthropic prices vary per model
# and prompt size, fal.ai per image. Update when actual usage drifts.
_COST_CENTS_PER_ACTION = {
    "persona_generated": 18,  # Haiku extract + Sonnet generate + fal portrait
    "probe_run":          8,  # Sonnet × 3 short calls
    "chat_message":       3,  # Sonnet × 1 short call
}


@app.get("/admin/costs")
async def admin_costs(
    _admin: User = Depends(get_admin_user),  # type: ignore  # noqa: F821
    db: AsyncSession = Depends(get_db),  # type: ignore  # noqa: F821
    days: int = 30,
):
    """Estimated infrastructure spend over the last N days, by action.

    Counts events of each billable type and multiplies by a per-action
    cost estimate. Not exact — token-level billing varies — but close
    enough to watch unit economics and spot anomalies.
    """
    from sqlalchemy import func, select as sa_select
    cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)
    breakdown: list[dict] = []
    total_cents = 0
    for action_type, cents in _COST_CENTS_PER_ACTION.items():
        count = (await db.execute(
            sa_select(func.count(Event.id))
            .where(Event.type == EventType[action_type])
            .where(Event.created_at >= cutoff)
        )).scalar() or 0
        action_cents = count * cents
        total_cents += action_cents
        breakdown.append({
            "action": action_type,
            "count": count,
            "cents_per": cents,
            "total_cents": action_cents,
            "total_usd": round(action_cents / 100, 2),
        })
    return {
        "since": cutoff.isoformat(),
        "days": days,
        "total_cents": total_cents,
        "total_usd": round(total_cents / 100, 2),
        "breakdown": breakdown,
    }


# ── Rate limiting (per-IP / per-user sliding-window) ──────────────────────

import time as _rl_time
import threading as _rl_threading
from collections import defaultdict as _rl_defaultdict

_RL_LOCK = _rl_threading.Lock()
_RL_BUCKETS: dict[tuple[str, str], list[float]] = _rl_defaultdict(list)

_RL_LIMITS = {
    # route_class: (max_requests, window_seconds)
    "expensive": (10, 60 * 60),   # generate-persona / probe — 10/hr
    "chat": (60, 60 * 60),        # chat — 60/hr
    "default": (300, 60),         # everything else — 300/min
}


def _rate_limit_check(route_class: str, identity: str) -> None:
    """Sliding-window rate limiter. Raises 429 on excess."""
    max_req, window = _RL_LIMITS.get(route_class, _RL_LIMITS["default"])
    now = _rl_time.time()
    cutoff = now - window
    key = (route_class, identity)
    with _RL_LOCK:
        bucket = _RL_BUCKETS[key]
        # prune expired
        i = 0
        while i < len(bucket) and bucket[i] < cutoff:
            i += 1
        if i:
            del bucket[:i]
        if len(bucket) >= max_req:
            retry_after = int(bucket[0] + window - now) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit hit. Try again in {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    # Skip rate limiting for static / health / auth-dance / OG
    skip_prefixes = ("/healthz", "/api/auth/", "/admin/")
    if any(path.startswith(p) for p in skip_prefixes):
        return await call_next(request)

    # Identify caller (Bearer subject if present, else IP)
    identity = request.client.host if request.client else "unknown"
    is_admin_caller = False
    auth_header = request.headers.get("Authorization", "")
    bearer_token = auth_header[7:] if auth_header.startswith("Bearer ") else None
    if not bearer_token:
        # Fall back to Auth.js session cookie so browser-driven
        # admin requests (which use cookies, not Authorization) also
        # benefit from the bypass.
        for ck in ("authjs.session-token", "__Secure-authjs.session-token",
                   "next-auth.session-token", "__Secure-next-auth.session-token"):
            v = request.cookies.get(ck)
            if v:
                bearer_token = v
                break
    if bearer_token:
        try:
            import jwt as _rl_jwt
            secret = os.environ.get("NEXTAUTH_SECRET", "")
            if secret:
                payload = _rl_jwt.decode(
                    bearer_token,
                    secret,
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                )
                sub = payload.get("sub")
                if sub:
                    identity = f"user:{sub}"
                # Admin email bypass — operator never gets rate-limited
                # on their own infra. Mirrors the bypass already applied
                # to allowance / access_status checks elsewhere.
                email = (payload.get("email") or "").lower()
                admin_emails = {
                    e.strip().lower()
                    for e in (os.environ.get("ADMIN_EMAILS", "") or "").split(",")
                    if e.strip()
                }
                if email and email in admin_emails:
                    is_admin_caller = True
        except Exception:
            pass  # fall back to IP

    if is_admin_caller:
        return await call_next(request)

    # Classify route
    if path == "/generate-persona" or "/probe" in path:
        klass = "expensive"
    elif "/chat" in path:
        klass = "chat"
    else:
        klass = "default"

    try:
        _rate_limit_check(klass, identity)
    except HTTPException as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail},
            headers=e.headers or {},
        )
    return await call_next(request)


# ── Turnstile verification ────────────────────────────────────────────────
# Frontend posts a Turnstile token to /verify-turnstile; we verify with
# Cloudflare and return ok:true. The frontend gates "Continue with Google"
# behind a successful verification.

@app.post("/verify-turnstile")
async def verify_turnstile(payload: dict):
    """Verify a Cloudflare Turnstile token.

    Frontend calls this after the widget completes; on ok:true the sign-in
    button becomes enabled. If TURNSTILE_SECRET is unset, we treat it as a
    dev environment and return ok:true without checking.
    """
    secret = os.environ.get("TURNSTILE_SECRET", "")
    if not secret:
        return {"ok": True, "skipped": True}
    token = (payload or {}).get("token")
    if not token:
        return {"ok": False, "reason": "missing_token"}
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={"secret": secret, "response": token},
            )
            data = r.json()
            return {"ok": bool(data.get("success")), "raw": data}
    except Exception as exc:
        return {"ok": False, "reason": f"verify_failed: {exc}"}


# ── Session summary email (Phase 3b) ──────────────────────────────────────
# After a successful persona generation, the frontend POSTs here. We send
# the user a recap email via Resend with portrait + name + CTAs to probe / chat.
# No-op in dev (AUTH_RESEND_KEY unset). Idempotency: keyed by (user_id, persona_id);
# duplicate calls within process lifetime are silently dropped.

_SUMMARY_EMAIL_SENT: set[tuple[str, str]] = set()


def _summary_html(name: str, city: str | None, age: int | None, persona_id: str, portrait_url: str | None) -> str:
    sub = ", ".join(filter(None, [str(age) if age else None, city]))
    portrait_block = (
        f'<img src="{portrait_url}" width="120" height="120" style="border-radius:4px;display:block;margin:0 auto 24px;" alt="" />'
        if portrait_url else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8" />
<style>
  body {{ margin:0; padding:0; background:#0a0a0a; font-family:'Helvetica Neue',Arial,sans-serif; }}
  .wrap {{ max-width:480px; margin:40px auto; background:#0a0a0a; border:1px solid rgba(240,230,210,0.12); border-radius:4px; overflow:hidden; }}
  .header {{ padding:32px 40px 24px; border-bottom:1px solid rgba(240,230,210,0.08); }}
  .logo {{ font-size:18px; font-weight:800; letter-spacing:0.08em; text-transform:uppercase; color:#f0e6d2; }}
  .body {{ padding:32px 40px; color:#f0e6d2; }}
  .h1 {{ font-size:22px; font-weight:700; margin:0 0 12px; }}
  .sub {{ font-size:14px; color:rgba(240,230,210,0.6); margin:0 0 24px; line-height:1.6; }}
  .btn {{ display:inline-block; background:#A8FF3E; color:#0a0a0a; text-decoration:none; font-weight:700; font-size:14px; letter-spacing:0.06em; padding:12px 24px; border-radius:2px; margin-right:8px; }}
  .btn-ghost {{ display:inline-block; background:transparent; color:#f0e6d2; text-decoration:none; font-weight:600; font-size:14px; padding:12px 16px; border:1px solid rgba(240,230,210,0.2); border-radius:2px; }}
  .footer {{ padding:20px 40px; border-top:1px solid rgba(240,230,210,0.08); font-size:11px; color:rgba(240,230,210,0.3); line-height:1.6; }}
</style></head>
<body>
  <div class="wrap">
    <div class="header">
      <div class="logo">The Mind</div>
    </div>
    <div class="body">
      {portrait_block}
      <h1 class="h1">You created {name}.</h1>
      <p class="sub">{sub or 'A new synthetic person, ready to evaluate.'}</p>
      <p class="sub">Test how they react to a product, or have a conversation. They'll stay in character.</p>
      <a class="btn" href="https://mind.simulatte.io/persona/{persona_id}/probe">Run a probe</a>
      <a class="btn-ghost" href="https://mind.simulatte.io/persona/{persona_id}/chat">Chat with them</a>
    </div>
    <div class="footer">
      Simulatte / The Mind — sent because you generated a persona at mind.simulatte.io.
    </div>
  </div>
</body></html>"""


async def _send_summary_email(to_email: str, persona: dict, persona_id: str) -> None:
    api_key = os.environ.get("AUTH_RESEND_KEY", "")
    if not api_key or not to_email:
        return
    da = persona.get("demographic_anchor") or {}
    name = da.get("name") or "Persona"
    portrait = _GENERATED_PORTRAITS.get(persona_id)
    html = _summary_html(name, da.get("city"), da.get("age"), persona_id, portrait)
    from_email = os.environ.get("EMAIL_FROM", "noreply@mind.simulatte.io")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "from": from_email,
                    "to": [to_email],
                    "subject": f"You created {name} — The Mind",
                    "html": html,
                },
            )
    except Exception:
        logger.exception("[summary-email] failed for %s", to_email)


@app.post("/notify/persona-generated/{persona_id}")
async def notify_persona_generated(
    persona_id: str,
    user: User = Depends(get_current_user),  # type: ignore  # noqa: F821
):
    """Fire a session-summary email. Frontend calls fire-and-forget after success."""
    key = (user.id, persona_id)
    if key in _SUMMARY_EMAIL_SENT:
        return {"ok": True, "skipped": "already_sent"}
    persona = _GENERATED.get(persona_id)
    if not persona:
        return {"ok": False, "reason": "persona_not_found"}
    if not user.email:
        return {"ok": False, "reason": "no_email"}
    _SUMMARY_EMAIL_SENT.add(key)
    await _send_summary_email(user.email, persona, persona_id)
    return {"ok": True}
