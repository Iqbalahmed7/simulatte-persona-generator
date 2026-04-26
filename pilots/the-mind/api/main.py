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
from fastapi import FastAPI, HTTPException            # noqa: E402
from fastapi.middleware.cors import CORSMiddleware    # noqa: E402
from fastapi.responses import StreamingResponse       # noqa: E402
from pydantic import BaseModel                        # noqa: E402

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

_GENERATED: dict[str, dict] = {}
_GENERATED_DIR = _HERE.parent / "generated_personas"

_EXEMPLAR_PORTRAITS: dict[str, str] = {}   # slug → fal.io URL (exemplar personas)
_GENERATED_PORTRAITS: dict[str, str] = {}  # persona_id → fal.io URL (generated personas)


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
        data = json.loads(msg.content[0].text)
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
    allow_origins=["*"],  # Tighten to mind.simulatte.io in production
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
        "Hyper-realistic photograph, not a painting, not illustrated, no filters, no text, no watermark."
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
        "Hyper-realistic photograph, not a painting, not illustrated, no filters, no text, no watermark."
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
    "industry": "<industry sector>",
    "seniority": "<junior|mid|senior|lead|executive|owner>"
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

    return {
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


async def _call_fal_portrait(prompt: str, fal_key: str) -> str:
    """Call fal.io flux-realism and return the image URL."""
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                "https://fal.run/fal-ai/flux-realism",
                headers={"Authorization": f"Key {fal_key}", "Content-Type": "application/json"},
                json={
                    "prompt": prompt,
                    "image_size": "portrait_4_3",
                    "num_inference_steps": 28,
                    "guidance_scale": 3.5,
                    "num_images": 1,
                    "enable_safety_checker": True,
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
async def generate_exemplar_portrait(slug: str):
    """Generate a portrait for an exemplar persona via fal.io flux-realism."""
    try:
        persona = _load_one(slug)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if slug in _EXEMPLAR_PORTRAITS:
        return {"url": _EXEMPLAR_PORTRAITS[slug], "persona_id": persona.persona_id}

    fal_key = os.environ.get("FAL_KEY", "")
    if not fal_key:
        raise HTTPException(status_code=503, detail="FAL_KEY environment variable not set")

    prompt = _build_portrait_prompt(persona.demographic_anchor)
    url = await _call_fal_portrait(prompt, fal_key)
    _EXEMPLAR_PORTRAITS[slug] = url
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


@app.post("/generate-persona")
async def generate_persona_stream(request: ICPRequest):
    """Stream persona generation via SSE.

    Events:
        {"type": "status",  "message": "..."}
        {"type": "result",  "persona_id": "...", "name": "..."}
        {"type": "error",   "message": "..."}
    """
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
    return data


async def _auto_generate_portrait(persona_id: str, fal_key: str) -> None:
    """Background task: silently generate portrait after persona creation."""
    try:
        da = (_GENERATED.get(persona_id) or {}).get("demographic_anchor") or {}
        prompt = _build_portrait_prompt_dict(da)
        url = await _call_fal_portrait(prompt, fal_key)
        _GENERATED_PORTRAITS[persona_id] = url
        logger.info("[portrait:auto] %s done", persona_id)
    except Exception:
        logger.exception("[portrait:auto] failed for %s", persona_id)


@app.post("/generated/{persona_id}/portrait")
async def generate_portrait(persona_id: str):
    """Generate (or return cached) portrait for a generated persona."""
    if persona_id not in _GENERATED:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")

    # Return cached URL if already generated
    if persona_id in _GENERATED_PORTRAITS:
        return {"url": _GENERATED_PORTRAITS[persona_id], "persona_id": persona_id}

    fal_key = os.environ.get("FAL_KEY", "")
    if not fal_key:
        raise HTTPException(status_code=503, detail="FAL_KEY environment variable not set")

    da = _GENERATED[persona_id].get("demographic_anchor") or {}
    prompt = _build_portrait_prompt_dict(da)
    url = await _call_fal_portrait(prompt, fal_key)
    _GENERATED_PORTRAITS[persona_id] = url
    return {"url": url, "persona_id": persona_id, "prompt": prompt}
