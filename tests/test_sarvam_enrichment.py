"""tests/test_sarvam_enrichment.py — Tests for SarvamEnricher.

Sprint 10 — Sarvam Indian Cultural Realism Layer.

Test 1 (integration): enricher returns a valid SarvamEnrichmentRecord for an India persona.
Tests 2-4 (structural): prompt builder, response parser with markdown, response parser invalid JSON.

Run structural tests (2-4) without --integration:
    python3 -m pytest tests/test_sarvam_enrichment.py -v

Run all tests with a live API key:
    python3 -m pytest tests/test_sarvam_enrichment.py -v --integration
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Test 1 — Integration: enricher returns SarvamEnrichmentRecord
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.integration
async def test_enricher_returns_record():
    """Integration: enricher returns a valid SarvamEnrichmentRecord for India persona."""
    import anthropic
    from src.sarvam.enrichment import SarvamEnricher
    from src.sarvam.config import SarvamConfig
    from src.sarvam.types import SarvamEnrichmentRecord
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from unittest.mock import MagicMock

    persona = make_synthetic_persona()

    # Override location to India (synthetic persona is already India/Mumbai,
    # but we build a MagicMock to satisfy the enricher's attribute access pattern)
    india_persona = MagicMock()
    india_persona.persona_id = persona.persona_id
    india_persona.narrative = persona.narrative
    india_persona.demographic_anchor = MagicMock()
    india_persona.demographic_anchor.name = "Priya Mehta"
    india_persona.demographic_anchor.age = 34
    india_persona.demographic_anchor.gender = "female"
    india_persona.demographic_anchor.location.country = "India"
    india_persona.demographic_anchor.location.city = "Mumbai"
    india_persona.demographic_anchor.location.region = "Maharashtra"
    india_persona.demographic_anchor.location.urban_tier = "metro"
    india_persona.demographic_anchor.household.structure = "nuclear"
    india_persona.demographic_anchor.household.size = 3
    india_persona.demographic_anchor.household.income_bracket = "middle"
    india_persona.demographic_anchor.education = "postgraduate"
    india_persona.demographic_anchor.employment = "full-time"
    india_persona.demographic_anchor.life_stage = "young professional"
    india_persona.life_stories = persona.life_stories
    india_persona.memory = persona.memory

    client = anthropic.AsyncAnthropic()
    enricher = SarvamEnricher(client)
    config = SarvamConfig.enabled()

    record = await enricher.enrich(india_persona, config)

    assert isinstance(record, SarvamEnrichmentRecord)
    assert record.enrichment_applied is True
    assert record.enriched_narrative is not None
    assert len(record.enriched_narrative.first_person) > 0
    assert len(record.enriched_narrative.third_person) > 0


# ---------------------------------------------------------------------------
# Test 2 — Structural: prompt builder produces non-empty prompt
# ---------------------------------------------------------------------------

def test_prompt_builder():
    """Structural: prompt builder returns non-empty string with key sections."""
    from src.sarvam.enrichment import SarvamEnricher
    from unittest.mock import MagicMock

    enricher = SarvamEnricher(llm_client=None)

    persona = MagicMock()
    persona.demographic_anchor.name = "Priya"
    persona.demographic_anchor.age = 34
    persona.demographic_anchor.gender = "female"
    persona.demographic_anchor.location.country = "India"
    persona.demographic_anchor.location.city = "Mumbai"
    persona.demographic_anchor.location.region = "Maharashtra"
    persona.demographic_anchor.location.urban_tier = "metro"
    persona.demographic_anchor.household.structure = "nuclear"
    persona.demographic_anchor.household.size = 3
    persona.demographic_anchor.household.income_bracket = "middle"
    persona.demographic_anchor.education = "postgraduate"
    persona.demographic_anchor.employment = "full-time"
    persona.demographic_anchor.life_stage = "young professional"
    persona.life_stories = []
    persona.narrative.first_person = "I am Priya..."
    persona.narrative.third_person = "Priya is a..."
    persona.memory.core.tendency_summary = "Tends to be price-sensitive."

    prompt = enricher._build_enrichment_prompt(persona, "narrative_and_examples", strict=True)

    assert len(prompt) > 100
    assert "India" in prompt or "india" in prompt.lower()
    assert "READ-ONLY" in prompt
    assert "JSON" in prompt


# ---------------------------------------------------------------------------
# Test 3 — Structural: parse response handles markdown code block
# ---------------------------------------------------------------------------

def test_parse_response_handles_markdown():
    """Structural: parser correctly strips ```json fences and returns parsed dict."""
    from src.sarvam.enrichment import SarvamEnricher

    enricher = SarvamEnricher(llm_client=None)

    response = """```json
{
    "enriched_first_person": "I shop at D-Mart...",
    "enriched_third_person": "Priya, a Mumbai professional...",
    "cultural_references_added": ["D-Mart"],
    "contextual_examples_replaced": []
}
```"""
    parsed = enricher._parse_enrichment_response(response)
    assert parsed["enriched_first_person"] == "I shop at D-Mart..."
    assert parsed["cultural_references_added"] == ["D-Mart"]


# ---------------------------------------------------------------------------
# Test 4 — Structural: parse response handles invalid JSON gracefully
# ---------------------------------------------------------------------------

def test_parse_response_invalid_json():
    """Structural: parser returns empty dict on invalid JSON input."""
    from src.sarvam.enrichment import SarvamEnricher

    enricher = SarvamEnricher(llm_client=None)
    result = enricher._parse_enrichment_response("this is not json at all")
    assert result == {}
