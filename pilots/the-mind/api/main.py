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

import json
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

# ── repo root on sys.path — must be before any src.* imports ──────────────
_HERE = Path(__file__).parent                        # pilots/the-mind/api/
_EXEMPLAR_DIR = _HERE.parent / "exemplar_set_v1"    # pilots/the-mind/exemplar_set_v1/
_REPO_ROOT = _HERE.parent.parent.parent              # repo root
sys.path.insert(0, str(_REPO_ROOT))

import anthropic                                      # noqa: E402
from fastapi import FastAPI, HTTPException            # noqa: E402
from fastapi.middleware.cors import CORSMiddleware    # noqa: E402
from pydantic import BaseModel                        # noqa: E402

from src.cognition.decide import decide              # noqa: E402
from src.cognition.respond import respond            # noqa: E402
from src.schema.persona import PersonaRecord         # noqa: E402

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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


# ── app ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    personas = _load_all()
    logger.info("[the-mind] %d exemplar personas loaded", len(personas))
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
