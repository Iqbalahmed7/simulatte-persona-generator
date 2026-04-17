"""Sarvam enrichment output types.

Sprint 10 — Sarvam Indian Cultural Realism Layer.
All types are Pydantic models (extra='forbid').
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CRStatus = Literal["pass", "fail", "not_run"]


class EnrichedNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_person: str
    """Sarvam-enriched first-person narrative."""

    third_person: str
    """Sarvam-enriched third-person narrative."""


class ContextualReplacement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original: str
    """The original Western-default or generic reference."""

    replacement: str
    """The India-specific replacement (traceable to an attribute)."""

    attribute_source: str
    """The persona field this replacement derives from, e.g. 'location.city' or 'values.brand_loyalty'."""


class ValidationStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cr1_isolation: CRStatus = "not_run"
    """CR1: Persona record not modified by enrichment. Automated."""

    cr2_stereotype_audit: CRStatus = "not_run"
    """CR2: Anti-stereotypicality audit on enriched narratives. Automated."""

    cr3_cultural_realism: CRStatus = "not_run"
    """CR3: Region/religion/urban-tier consistency. Automated."""

    cr4_persona_fidelity: CRStatus = "not_run"
    """CR4: Enriched narrative preserves key persona facts. Automated."""

    def all_passed(self) -> bool:
        """True only if every CR check explicitly passed (not_run counts as fail)."""
        return all(
            s == "pass"
            for s in (
                self.cr1_isolation,
                self.cr2_stereotype_audit,
                self.cr3_cultural_realism,
                self.cr4_persona_fidelity,
            )
        )


class SarvamEnrichmentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enrichment_applied: bool
    """True if enrichment ran. False if activation conditions were not met."""

    enrichment_provider: Literal["sarvam", "none"] = "none"
    """Provider identifier. 'sarvam' when applied, 'none' when not applied."""

    enrichment_scope: str = ""
    """Scope string describing which surfaces were enriched."""

    persona_id: str
    """ID of the persona this enrichment record belongs to."""

    enriched_narrative: EnrichedNarrative | None = None
    """Enriched narratives. None if enrichment_applied is False."""

    cultural_references_added: list[str] = Field(default_factory=list)
    """List of India-specific cultural references added (traceable to attributes)."""

    contextual_examples_replaced: list[ContextualReplacement] = Field(default_factory=list)
    """List of contextual replacements made (Western -> India-specific)."""

    validation_status: ValidationStatus = Field(default_factory=ValidationStatus)
    """CR test status. All 'not_run' until explicitly evaluated."""

    cr_diagnostics: dict[str, list[str]] = Field(default_factory=dict)
    """Per-CR violation messages. Keyed by 'cr1' | 'cr2' | 'cr3' | 'cr4'.
    Populated only for checks that ran and produced violations/warnings."""

    skip_reason: str | None = None
    """Reason enrichment was skipped (if enrichment_applied is False)."""
