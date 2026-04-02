"""Sarvam activation — checks whether enrichment should run for a persona.

Sprint 10 — Sarvam Indian Cultural Realism Layer.
"""
from __future__ import annotations

from typing import Any, Tuple

from src.sarvam.config import SarvamConfig
from src.sarvam.types import SarvamEnrichmentRecord, ValidationStatus


def should_activate(persona: Any, config: SarvamConfig) -> Tuple[bool, str]:
    """Return (active, reason) for whether Sarvam enrichment should run.

    Args:
        persona: PersonaRecord — must have demographic_anchor.location.country.
        config: SarvamConfig instance.

    Returns:
        (True, "met") if all activation conditions are satisfied.
        (False, <reason>) otherwise.
    """
    if not config.sarvam_enrichment:
        return False, "disabled: sarvam_enrichment is False in config"

    try:
        country = persona.demographic_anchor.location.country
    except AttributeError:
        return False, "skipped: could not read persona.demographic_anchor.location.country"

    if country != "India":
        return False, f"skipped: persona country is not India (got: {country!r})"

    return True, "met"


def make_skip_record(persona_id: str, reason: str) -> SarvamEnrichmentRecord:
    """Create a skip SarvamEnrichmentRecord when activation conditions are not met."""
    return SarvamEnrichmentRecord(
        persona_id=persona_id,
        enrichment_applied=False,
        enrichment_provider="none",
        enrichment_scope="",
        skip_reason=reason,
        validation_status=ValidationStatus(),
    )
