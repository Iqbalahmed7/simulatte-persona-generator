"""Sarvam enrichment configuration.

Sprint 10 — Sarvam Indian Cultural Realism Layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


SarvamEnrichmentScope = Literal[
    "narrative_only",
    "narrative_and_examples",
    "full",
]
"""
narrative_only            — enriches first_person + third_person narratives only.
narrative_and_examples    — enriches narratives + replaces contextual examples.
full                      — all permitted surfaces (narratives + examples + dialogue tone).
"""


@dataclass
class SarvamConfig:
    """Configuration for a Sarvam enrichment run.

    sarvam_enrichment: bool
        Master switch. Must be True for enrichment to run.
        Default: False — opt-in required.

    scope: SarvamEnrichmentScope
        Which surfaces to enrich.
        Default: "narrative_and_examples"

    model: str
        LLM model identifier for enrichment calls.
        Default: "claude-haiku-4-5-20251001" (low cost, fast).
        Set to a Sarvam API model identifier when Sarvam API key is available.

    max_narrative_words: int
        Maximum word count for enriched narratives (enforced by enricher).
        Default: 200

    anti_stereotypicality_strict: bool
        If True, enricher prompt includes strict anti-stereotypicality instructions
        and explicitly lists prohibited defaults.
        Default: True
    """
    sarvam_enrichment: bool = False
    scope: SarvamEnrichmentScope = "narrative_and_examples"
    model: str = "claude-haiku-4-5-20251001"
    max_narrative_words: int = 200
    anti_stereotypicality_strict: bool = True

    @classmethod
    def enabled(cls, scope: SarvamEnrichmentScope = "narrative_and_examples") -> "SarvamConfig":
        """Convenience constructor for an enabled config with default settings."""
        return cls(sarvam_enrichment=True, scope=scope)

    @classmethod
    def disabled(cls) -> "SarvamConfig":
        """Convenience constructor for a disabled config (default state)."""
        return cls(sarvam_enrichment=False)

    @classmethod
    def for_sarvam_api(cls, scope: SarvamEnrichmentScope = "narrative_and_examples") -> "SarvamConfig":
        """Config preset for Sarvam API (not Claude Haiku)."""
        return cls(sarvam_enrichment=True, scope=scope, model="sarvam-m")
