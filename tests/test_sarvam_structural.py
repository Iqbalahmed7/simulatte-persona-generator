"""tests/test_sarvam_structural.py — Structural tests for the Sarvam pipeline.

Sprint 10 — Sarvam Indian Cultural Realism Layer.
No LLM calls. All enricher calls are mocked.
Tests verify pipeline wiring, skip logic, CR1 pass, and JSON serialisability.
"""
from __future__ import annotations

import json

import pytest


# ---------------------------------------------------------------------------
# Test 1: run_sarvam_enrichment skips non-India persona
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_skips_non_india():
    from src.sarvam.pipeline import run_sarvam_enrichment
    from src.sarvam.config import SarvamConfig
    from unittest.mock import MagicMock

    persona = MagicMock()
    persona.persona_id = "test-001"
    persona.demographic_anchor.location.country = "USA"

    record = await run_sarvam_enrichment(persona, SarvamConfig.enabled(), llm_client=None)
    assert record.enrichment_applied is False
    assert record.skip_reason is not None
    assert "india" in record.skip_reason.lower()


# ---------------------------------------------------------------------------
# Test 2: run_sarvam_enrichment skips when disabled
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_skips_when_disabled():
    from src.sarvam.pipeline import run_sarvam_enrichment
    from src.sarvam.config import SarvamConfig
    from unittest.mock import MagicMock

    persona = MagicMock()
    persona.persona_id = "test-002"
    persona.demographic_anchor.location.country = "India"

    record = await run_sarvam_enrichment(persona, SarvamConfig.disabled(), llm_client=None)
    assert record.enrichment_applied is False
    assert "disabled" in record.skip_reason.lower()


# ---------------------------------------------------------------------------
# Test 3: run_sarvam_enrichment with mocked enricher → CR1 pass
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_cr1_passes_with_mock():
    """With a mocked enricher, CR1 should pass (persona not mutated)."""
    from src.sarvam.pipeline import run_sarvam_enrichment
    from src.sarvam.config import SarvamConfig
    from src.sarvam.types import SarvamEnrichmentRecord, EnrichedNarrative, ValidationStatus
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from unittest.mock import patch, AsyncMock

    persona = make_synthetic_persona()

    mock_record = SarvamEnrichmentRecord(
        enrichment_applied=True,
        enrichment_provider="sarvam",
        enrichment_scope="narrative_and_examples",
        persona_id=persona.persona_id,
        enriched_narrative=EnrichedNarrative(
            first_person="I shop at D-Mart...",
            third_person="Priya, a Mumbai professional...",
        ),
        validation_status=ValidationStatus(),
    )

    with patch("src.sarvam.pipeline.should_activate", return_value=(True, "met")):
        with patch("src.sarvam.pipeline.SarvamEnricher") as MockEnricher:
            MockEnricher.return_value.enrich = AsyncMock(return_value=mock_record)
            record = await run_sarvam_enrichment(
                persona, SarvamConfig.enabled(), llm_client=None
            )

    assert record.enrichment_applied is True
    assert record.validation_status.cr1_isolation == "pass"


# ---------------------------------------------------------------------------
# Test 4: Pipeline returns correct persona_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_skip_record_has_persona_id():
    from src.sarvam.pipeline import run_sarvam_enrichment
    from src.sarvam.config import SarvamConfig
    from unittest.mock import MagicMock

    persona = MagicMock()
    persona.persona_id = "pg-cpg-007"
    persona.demographic_anchor.location.country = "UK"

    record = await run_sarvam_enrichment(persona, SarvamConfig.enabled(), llm_client=None)
    assert record.persona_id == "pg-cpg-007"


# ---------------------------------------------------------------------------
# Test 5: SarvamEnrichmentRecord is JSON-serialisable
# ---------------------------------------------------------------------------

def test_enrichment_record_json_serialisable():
    """SarvamEnrichmentRecord must be JSON-serialisable via model_dump()."""
    from src.sarvam.types import SarvamEnrichmentRecord, EnrichedNarrative, ValidationStatus

    record = SarvamEnrichmentRecord(
        enrichment_applied=True,
        enrichment_provider="sarvam",
        enrichment_scope="narrative_only",
        persona_id="test-001",
        enriched_narrative=EnrichedNarrative(
            first_person="I shop at D-Mart...",
            third_person="Priya, a Mumbai professional...",
        ),
        cultural_references_added=["D-Mart", "Chai tapri"],
        validation_status=ValidationStatus(cr1_isolation="pass"),
    )
    dumped = record.model_dump()
    json_str = json.dumps(dumped)
    assert len(json_str) > 0
    loaded = json.loads(json_str)
    assert loaded["enrichment_applied"] is True
    assert loaded["persona_id"] == "test-001"
