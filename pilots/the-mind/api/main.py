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
    from db import User, get_db                            # noqa: E402
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    personas = _load_all()
    logger.info("[the-mind] %d exemplar personas loaded", len(personas))
    _load_generated_from_disk()
    logger.info("[the-mind] %d generated personas loaded from disk", len(_GENERATED))
    yield


app = FastAPI(
    title="The Mind API",
    description="Persona simulation API for mind.simulatte.io — exemplar_set_v1_2026_04",
    version="1.0.0",
    lifespan=lifespan,
)

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
    """Build a rich, realistic portrait prompt from demographic anchor data (Pydantic model)."""
    gender_word = "woman" if da.gender == "female" else "man" if da.gender == "male" else "person"
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

    return (
        f"Candid photorealistic portrait of a {da.age}-year-old {gender_word} from {city}, {country}{context}. "
        "Shot on Sony A7 III, 85mm f/1.8 lens, natural window light, shallow depth of field. "
        "Authentic skin texture, realistic pores, natural hair, genuine relaxed expression. "
        "Upper body framing, slightly off-axis gaze, neutral indoor environment. "
        "Hyper-realistic photograph, not a painting, not illustrated, no filters, no text, no watermark. "
        "photo-realistic DSLR portrait, 85mm f/1.4 lens, natural skin texture with visible pores and subtle imperfections, "
        "candid expression with soft natural lighting, environmental context appropriate to their occupation and location, "
        "color-accurate, neutral grading, not stylized, not AI-rendered, looks like a real person photographed on a Tuesday afternoon"
    )


def _build_portrait_prompt_dict(da: dict) -> str:
    """Build a portrait prompt from a plain-dict demographic anchor (web-generated personas)."""
    gender = da.get("gender", "")
    gender_word = "woman" if gender == "female" else "man" if gender == "male" else "person"
    location = da.get("location") or {}
    city = location.get("city", "")
    country = location.get("country", "")
    employment = da.get("employment") or {}
    occupation = employment.get("occupation", "") or ""
    life_stage = (da.get("life_stage") or "").replace("_", " ")
    age = da.get("age", 30)

    context_parts = []
    if occupation:
        context_parts.append(occupation)
    if life_stage:
        context_parts.append(life_stage)
    context = f", {', '.join(context_parts)}" if context_parts else ""

    return (
        f"Candid photorealistic portrait of a {age}-year-old {gender_word} from {city}, {country}{context}. "
        "Shot on Sony A7 III, 85mm f/1.8 lens, natural window light, shallow depth of field. "
        "Authentic skin texture, realistic pores, natural hair, genuine relaxed expression. "
        "Upper body framing, slightly off-axis gaze, neutral indoor environment. "
        "Hyper-realistic photograph, not a painting, not illustrated, no filters, no text, no watermark. "
        "photo-realistic DSLR portrait, 85mm f/1.4 lens, natural skin texture with visible pores and subtle imperfections, "
        "candid expression with soft natural lighting, environmental context appropriate to their occupation and location, "
        "color-accurate, neutral grading, not stylized, not AI-rendered, looks like a real person photographed on a Tuesday afternoon"
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

    await check_and_increment_allowance(user, "probe", db)

    persona = _load_persona_for_probe(persona_id)
    da = persona.get("demographic_anchor") or {}
    name = da.get("name") or "Persona"
    portrait_url = _GENERATED_PORTRAITS.get(persona_id)

    product_brief = {
        "product_name": request.product_name,
        "category": request.category,
        "description": request.description,
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
        da = (_GENERATED.get(persona_id) or {}).get("demographic_anchor") or {}
        prompt = _build_portrait_prompt_dict(da)
        url = await _call_fal_portrait(prompt, fal_key)
        _GENERATED_PORTRAITS[persona_id] = url
        _save_portraits_to_disk()
        logger.info("[portrait:auto] %s done", persona_id)
    except Exception:
        logger.exception("[portrait:auto] failed for %s", persona_id)


@app.post("/generated/{persona_id}/portrait")
async def generate_portrait(persona_id: str, force: bool = False):
    """Generate (or return cached) portrait for a generated persona.

    Pass ?force=true to bypass the cache and regenerate with the current model.
    """
    if persona_id not in _GENERATED:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")

    # Return cached URL if already generated
    if not force and persona_id in _GENERATED_PORTRAITS:
        return {"url": _GENERATED_PORTRAITS[persona_id], "persona_id": persona_id}

    fal_key = os.environ.get("FAL_KEY", "")
    if not fal_key:
        raise HTTPException(status_code=503, detail="FAL_KEY environment variable not set")

    da = _GENERATED[persona_id].get("demographic_anchor") or {}
    prompt = _build_portrait_prompt_dict(da)
    url = await _call_fal_portrait(prompt, fal_key)
    _GENERATED_PORTRAITS[persona_id] = url
    _save_portraits_to_disk()
    return {"url": url, "persona_id": persona_id, "prompt": prompt}
