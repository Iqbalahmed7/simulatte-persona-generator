"""
PersonaGenerationBrief — the single input contract for the orchestration layer.

Any caller (Claude agent, Python script, REST client, another pipeline) passes
one of these objects to invoke_persona_generator().  Every field has a sensible
default so a minimal call only needs client, domain, and business_problem.

Usage::

    from src.orchestrator.brief import PersonaGenerationBrief, RunIntent

    brief = PersonaGenerationBrief(
        client="LittleJoys",
        domain="cpg",
        business_problem="Why do Mumbai parents switch nutrition brands for under-5s?",
        count=50,
        run_intent=RunIntent.DELIVER,
        sarvam_enabled=True,
        anchor_overrides={"location": "Mumbai", "life_stage": "parent"},
    )
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


class RunIntent(str, Enum):
    """Declares the *purpose* of this run.  Drives tier recommendation and
    default quality gate strictness.

    EXPLORE   → exploratory research, hypothesis generation.  SIGNAL tier.
    CALIBRATE → prompt / taxonomy tuning runs.  SIGNAL tier.
    DELIVER   → final client-facing output.  DEEP tier.
    VOLUME    → large-scale distribution modelling.  VOLUME tier.
    """
    EXPLORE   = "explore"
    CALIBRATE = "calibrate"
    DELIVER   = "deliver"
    VOLUME    = "volume"


class SimulationScenario(BaseModel):
    """Optional stimulus sequence to run immediately after generation."""
    stimuli: list[str] = Field(default_factory=list)
    decision_scenario: str | None = None
    rounds: int = Field(default=1, ge=1, le=10)


class PersonaGenerationBrief(BaseModel):
    """Complete specification for a persona generation + optional simulation run.

    Minimal required fields:  client, domain, business_problem
    Everything else has sensible defaults.
    """

    # ── Identity ──────────────────────────────────────────────────────────
    client: str = Field(..., description="Organisation / brand name (e.g. 'LittleJoys')")
    domain: str = Field(..., description="Domain key: 'cpg', 'saas', 'ecommerce', etc.")
    business_problem: str = Field(
        ...,
        description="The research question this cohort will answer.",
    )

    # ── Scale ─────────────────────────────────────────────────────────────
    count: int = Field(default=10, ge=1, le=500, description="Number of personas to generate.")

    # ── Intent & Tier ─────────────────────────────────────────────────────
    run_intent: RunIntent = Field(
        default=RunIntent.EXPLORE,
        description="Purpose of the run — drives tier recommendation.",
    )
    tier_override: str | None = Field(
        default=None,
        description="Force a specific tier ('deep'/'signal'/'volume').  Skips advisor.",
        pattern="^(deep|signal|volume)$",
    )

    # ── Generation options ────────────────────────────────────────────────
    mode: str = Field(
        default="deep",
        description="Persona build depth: 'quick' | 'deep' | 'simulation-ready' | 'grounded'",
        pattern="^(quick|deep|simulation-ready|grounded)$",
    )
    anchor_overrides: dict[str, Any] = Field(
        default_factory=dict,
        description="Forced demographic values, e.g. {'location': 'Mumbai', 'life_stage': 'parent'}",
    )
    persona_id_prefix: str = Field(default="pg", description="Prefix for persona_id strings.")
    sarvam_enabled: bool = Field(
        default=False,
        description="Enable Sarvam cultural enrichment (India-specific personas).",
    )

    # ── Grounding corpus ──────────────────────────────────────────────────
    corpus_path: str | Path | None = Field(
        default=None,
        description="Path to JSON file with raw text documents for signal tagging + grounding.",
    )
    domain_data: list[str] | None = Field(
        default=None,
        description="Raw text strings (reviews, posts) passed directly instead of corpus_path.",
    )

    # ── Optional simulation ───────────────────────────────────────────────
    simulation: SimulationScenario | None = Field(
        default=None,
        description="If provided, runs a simulation immediately after generation.",
    )

    # ── Quality & gates ───────────────────────────────────────────────────
    skip_gates: bool = Field(
        default=False,
        description="Skip cohort-level validation gates (G6–G11). Use only for dev/debug.",
    )
    max_quarantine_pct: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="If more than this fraction of personas fail G12, abort the run.",
    )
    max_retries_per_persona: int = Field(
        default=2,
        ge=0,
        le=5,
        description="How many times to regenerate a persona that fails quality gates.",
    )

    # ── Output & persistence ──────────────────────────────────────────────
    output_dir: str | Path | None = Field(
        default=None,
        description="Directory to write cohort JSON + pipeline doc.  Defaults to COHORT_STORE_DIR.",
    )
    auto_confirm: bool = Field(
        default=False,
        description="Skip the cost-estimate confirmation prompt and proceed automatically.",
    )
    emit_pipeline_doc: bool = Field(
        default=True,
        description="Auto-generate a Simulatte pipeline documentation note after generation.",
    )

    # ── Registry ─────────────────────────────────────────────────────────
    registry_path: str | Path | None = Field(
        default=None,
        description="Path to persona registry JSON for reuse / drift detection.",
    )

    @model_validator(mode="after")
    def _resolve_corpus(self) -> "PersonaGenerationBrief":
        """If corpus_path is given, load domain_data from it (list of strings)."""
        if self.corpus_path is not None and self.domain_data is None:
            import json
            p = Path(self.corpus_path)
            if p.exists():
                raw = json.loads(p.read_text())
                if isinstance(raw, list):
                    self.domain_data = [str(x) for x in raw]
                elif isinstance(raw, dict) and "documents" in raw:
                    self.domain_data = [str(x) for x in raw["documents"]]
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
