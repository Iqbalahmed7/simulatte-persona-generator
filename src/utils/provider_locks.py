"""provider_locks.py — quality-aware provider routing config.

Pins quality-sensitive stages (decide, synthesis) to Anthropic so multi-LLM
fallback never silently degrades persona quality. Flexible stages (perceive,
signal_tag, summarise) can swap to OpenAI / Sarvam / Haiku for cost savings.

Read this file FIRST when adding a new LLM caller — register the stage here
before adding it.
"""
from __future__ import annotations
from typing import Literal, TypedDict

Provider = Literal["anthropic", "openai", "sarvam"]
Sensitivity = Literal["high", "medium", "low"]


class StageRule(TypedDict, total=False):
    """Routing rule for a single pipeline stage."""
    sensitivity: Sensitivity
    locked_provider: Provider | None       # None = flexible
    locked_models: list[str]               # only honoured when locked_provider set
    calibrated_for: list[Provider]         # providers that passed parity gate
    prefer_cheap: bool                     # use cheapest tier in calibrated_for
    note: str                              # why this rule


# ── Stage taxonomy ─────────────────────────────────────────────────────────
#
# HIGH sensitivity:  swap = cohort drift. Always lock to anthropic, retry on
#                    failure, never silently failover. Re-calibrate before
#                    permitting any new provider here.
#
# MEDIUM sensitivity: style differs but probe quality survives. Permit failover
#                    among providers that passed the parity gate.
#
# LOW sensitivity:   extraction / tagging / parsing. Use cheapest provider.
#                    Failover anywhere.
#
PROVIDER_LOCKS: dict[str, StageRule] = {
    # ── HIGH — Anthropic only ─────────────────────────────────────────────
    "decide": {
        "sensitivity": "high",
        "locked_provider": "anthropic",
        "locked_models": ["claude-sonnet-4-5"],
        "note": "Calibrated against real-world distributions. Swap = drift.",
    },
    "synthesis": {
        "sensitivity": "high",
        "locked_provider": "anthropic",
        "locked_models": ["claude-sonnet-4-5"],
        "note": "Twin profile + persona core construction. Provider choice "
                "shapes the decision_filter framing — never swap without "
                "passing parity gate.",
    },
    "respond": {
        "sensitivity": "high",
        "locked_provider": "anthropic",
        "note": "In-character probe replies. Voice consistency matters.",
    },

    # ── MEDIUM — Failover allowed among calibrated providers ─────────────
    "reflect": {
        "sensitivity": "medium",
        "locked_provider": None,
        "calibrated_for": ["anthropic"],  # add "openai" after parity gate passes
        "note": "Self-reflection on probe outcomes. Update calibrated_for "
                "once OpenAI passes parity.",
    },
    "perceive": {
        "sensitivity": "medium",
        "locked_provider": None,
        "calibrated_for": ["anthropic"],
        "note": "Stimulus interpretation. Watch for framing drift on swap.",
    },
    "frame_score": {
        "sensitivity": "medium",
        "locked_provider": None,
        "calibrated_for": ["anthropic"],
        "note": "Operator outreach scoring. Anthropic-only until parity gate "
                "validates GPT-4o gives equivalent reply_probability bucketing.",
    },

    # ── LOW — Failover anywhere, prefer cheap ─────────────────────────────
    "signal_tag": {
        "sensitivity": "low",
        "locked_provider": None,
        "calibrated_for": ["anthropic", "openai"],
        "prefer_cheap": True,
        "note": "Tag onboarding signals. Mostly extraction.",
    },
    "domain_extract": {
        "sensitivity": "low",
        "locked_provider": None,
        "calibrated_for": ["anthropic", "openai"],
        "prefer_cheap": True,
        "note": "Pull domain entities from text.",
    },
    "summarise": {
        "sensitivity": "low",
        "locked_provider": None,
        "calibrated_for": ["anthropic", "openai"],
        "prefer_cheap": True,
        "note": "Working/episodic memory summarisation.",
    },
    "enrich_extract": {
        "sensitivity": "low",
        "locked_provider": None,
        "calibrated_for": ["anthropic", "openai"],
        "prefer_cheap": True,
        "note": "URL/PDF/transcript text cleaning.",
    },
}


# ── Capability gates ───────────────────────────────────────────────────────
# Some tasks pin to a provider not for quality but because only that provider
# offers the capability natively.

CAPABILITY_LOCKS: dict[str, Provider] = {
    "web_search": "anthropic",     # Anthropic web_search_20250305 native tool
    "image_gen":  "openai",         # DALL-E (we currently use fal.ai instead)
}


def get_stage_rule(stage: str) -> StageRule:
    """Return the rule for a stage. Defaults to medium-sensitivity Anthropic-only.

    Unknown stages default to safe (Anthropic-locked) — fail closed, not open.
    """
    if stage not in PROVIDER_LOCKS:
        return {
            "sensitivity": "medium",
            "locked_provider": "anthropic",
            "note": f"Unknown stage '{stage}' — defaulting to Anthropic. "
                    f"Register in provider_locks.py before adding new callers.",
        }
    return PROVIDER_LOCKS[stage]
