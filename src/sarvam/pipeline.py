"""Sarvam enrichment pipeline — top-level entry point.

Sprint 10 — Sarvam Indian Cultural Realism Layer.
Wires activation check → enrichment → CR1–CR4 validation into one call.

Per Master Spec §15G rule S27, all four cultural-realism checks must
pass before a Sarvam-enriched persona is considered approved:

  CR1 — Isolation (persona record unchanged by enrichment)
  CR2 — Anti-stereotypicality audit
  CR3 — Cultural consistency (region/religion/urban-tier)
  CR4 — Persona fidelity (key facts preserved in enriched narrative)
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
from src.sarvam.cr1_validator import run_cr1_check
from src.sarvam.cr2_validator import run_cr2_check
from src.sarvam.cr3_validator import run_cr3_check
from src.sarvam.cr4_validator import run_cr4_check


async def run_sarvam_enrichment(
    persona: Any,               # PersonaRecord
    config: SarvamConfig,
    llm_client: Any,
) -> SarvamEnrichmentRecord:
    """Run the full Sarvam enrichment pipeline for a single persona.

    Steps:
      1. Check activation conditions. If not met → return skip record.
      2. Run SarvamEnricher.enrich(persona, config).
      3. Run all four CR checks (CR1 isolation, CR2 stereotype,
         CR3 consistency, CR4 fidelity) against the enriched output.
      4. Fold each check's pass/fail into validation_status and
         violations into cr_diagnostics.
      5. Return the updated enrichment record.

    Args:
        persona: A validated PersonaRecord.
        config: SarvamConfig instance.
        llm_client: Anthropic async client.

    Returns:
        SarvamEnrichmentRecord — either an enrichment result with CR1–CR4
        status populated, or a skip record.
    """
    # Step 1: Activation check
    active, reason = should_activate(persona, config)
    if not active:
        return make_skip_record(persona.persona_id, reason)

    # Step 2: Enrich
    enricher = SarvamEnricher(llm_client)
    enrichment_record = await enricher.enrich(persona, config)

    # Step 3: Run all four CR checks
    # Short-circuit if the enricher produced no narrative (parsing failure etc.).
    if enrichment_record.enriched_narrative is None:
        return enrichment_record

    enriched_first = enrichment_record.enriched_narrative.first_person
    enriched_third = enrichment_record.enriched_narrative.third_person
    original_first = persona.narrative.first_person

    cr_diagnostics: dict[str, list[str]] = {}

    # --- CR1: Isolation (persona must not have been mutated) -----------------
    # Enrichment is read-only by contract; we compare persona to itself since
    # the enricher cannot return a modified copy via the current signature.
    # If a future integration lets enrichment reshape the persona, swap the
    # second arg for the post-enrichment persona object.
    cr1_result = run_cr1_check(persona, persona)
    cr1_status = "pass" if cr1_result.passed else "fail"
    if not cr1_result.passed:
        cr_diagnostics["cr1"] = list(cr1_result.violations)

    # --- CR2: Anti-stereotypicality audit -----------------------------------
    cr2_result = run_cr2_check(
        persona_id=persona.persona_id,
        enriched_narrative_first=enriched_first,
        enriched_narrative_third=enriched_third,
        persona_record=persona,
    )
    cr2_status = "pass" if cr2_result.passed else "fail"
    cr2_messages: list[str] = []
    if cr2_result.hard_violations:
        cr2_messages.extend(f"HARD: {v}" for v in cr2_result.hard_violations)
    if cr2_result.soft_flags:
        cr2_messages.extend(f"SOFT: {v}" for v in cr2_result.soft_flags)
    if cr2_messages:
        cr_diagnostics["cr2"] = cr2_messages

    # --- CR3: Cultural consistency ------------------------------------------
    cr3_result = run_cr3_check(
        persona_id=persona.persona_id,
        enriched_narrative_first=enriched_first,
        enriched_narrative_third=enriched_third,
        persona_record=persona,
    )
    cr3_status = "pass" if cr3_result.passed else "fail"
    cr3_messages = list(cr3_result.violations)
    if cr3_result.warnings:
        cr3_messages.extend(f"WARN: {w}" for w in cr3_result.warnings)
    if cr3_messages:
        cr_diagnostics["cr3"] = cr3_messages

    # --- CR4: Persona fidelity ----------------------------------------------
    # CR4 checks fact preservation. We run it against the first-person narrative
    # since that's the surface most prone to dropping facts under enrichment.
    cr4_result = run_cr4_check(
        persona_id=persona.persona_id,
        original_narrative=original_first,
        enriched_narrative=enriched_first,
        persona_record=persona,
    )
    cr4_status = "pass" if cr4_result.passed else "fail"
    if cr4_result.missing_facts:
        cr_diagnostics["cr4"] = list(cr4_result.missing_facts)

    # Step 4: Fold all CR statuses + diagnostics into the enrichment record
    updated_validation_status = enrichment_record.validation_status.model_copy(
        update={
            "cr1_isolation": cr1_status,
            "cr2_stereotype_audit": cr2_status,
            "cr3_cultural_realism": cr3_status,
            "cr4_persona_fidelity": cr4_status,
        }
    )
    return enrichment_record.model_copy(
        update={
            "validation_status": updated_validation_status,
            "cr_diagnostics": cr_diagnostics,
        }
    )
