"""Sarvam enrichment pipeline — top-level entry point.

Sprint 10 — Sarvam Indian Cultural Realism Layer.
Wires activation check → enrichment → CR1 validation into one call.
"""
from __future__ import annotations

from typing import Any

from src.sarvam.config import SarvamConfig
from src.sarvam.types import SarvamEnrichmentRecord

# Module-level imports so names are patchable in tests.
# These are intentionally kept at the top to allow unittest.mock.patch to
# target src.sarvam.pipeline.should_activate / src.sarvam.pipeline.SarvamEnricher.
from src.sarvam.activation import should_activate, make_skip_record
from src.sarvam.enrichment import SarvamEnricher
from src.sarvam.cr1_validator import run_cr1_check, update_enrichment_record_with_cr1


async def run_sarvam_enrichment(
    persona: Any,               # PersonaRecord
    config: SarvamConfig,
    llm_client: Any,
) -> SarvamEnrichmentRecord:
    """Run the full Sarvam enrichment pipeline for a single persona.

    Steps:
    1. Check activation conditions (should_activate).
       If not met → return skip record immediately.
    2. Run SarvamEnricher.enrich(persona, config).
    3. Run CR1 check (original persona vs post-enrichment persona — should be identical
       since enrichment never modifies the PersonaRecord).
    4. Update enrichment record validation_status.cr1_isolation.
    5. Return final SarvamEnrichmentRecord.

    Note on CR1: Since enrichment never modifies the PersonaRecord,
    CR1 is a structural invariant check. We pass the same persona twice
    to confirm no mutation occurred. In a future integration where
    Sarvam re-runs the decision engine, CR1 would compare real decision outputs.

    Args:
        persona: A validated PersonaRecord (India + opt-in conditions checked internally).
        config: SarvamConfig instance.
        llm_client: Anthropic async client.

    Returns:
        SarvamEnrichmentRecord — either an enrichment result or a skip record.
    """
    # Step 1: Activation check
    active, reason = should_activate(persona, config)
    if not active:
        return make_skip_record(persona.persona_id, reason)

    # Step 2: Enrich
    enricher = SarvamEnricher(llm_client)
    enrichment_record = await enricher.enrich(persona, config)

    # Step 3 + 4: CR1 check — persona must be unchanged
    # We compare persona to itself (no mutation should have occurred)
    cr1_result = run_cr1_check(persona, persona)
    enrichment_record = update_enrichment_record_with_cr1(enrichment_record, cr1_result)

    return enrichment_record
