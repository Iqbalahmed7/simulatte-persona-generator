"""tests/test_sarvam_routing.py — LLM router wiring tests.

Sprint 16 — Sarvam LLM Router integration.

Tests:
    1. test_enricher_uses_complete_when_base_llm_client
       — BaseLLMClient passed to SarvamEnricher; verify .complete() is called.

    2. test_enricher_uses_messages_create_for_legacy_anthropic_client
       — Legacy mock (has .messages.create but NOT .complete) passed to SarvamEnricher;
         verify .messages.create() is called.

    3. test_sarvam_config_model_defaults_to_haiku
       — SarvamConfig() default model is "claude-haiku-4-5-20251001".

    4. test_sarvam_config_for_sarvam_api_uses_sarvam_m
       — SarvamConfig.for_sarvam_api().model == "sarvam-m".

Run:
    python3 -m pytest tests/test_sarvam_routing.py -v --tb=short
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Test 1 — BaseLLMClient path: .complete() is called
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enricher_uses_complete_when_base_llm_client():
    """SarvamEnricher calls llm.complete() when passed a BaseLLMClient instance."""
    from src.sarvam.enrichment import SarvamEnricher
    from src.sarvam.config import SarvamConfig

    # Build a mock that has .complete (mimics BaseLLMClient)
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(
        return_value=(
            '{"enriched_first_person": "I am Priya.", '
            '"enriched_third_person": "Priya is a professional.", '
            '"cultural_references_added": [], '
            '"contextual_examples_replaced": []}'
        )
    )

    enricher = SarvamEnricher(llm_client=mock_llm)

    # Build a minimal mock persona
    persona = MagicMock()
    persona.persona_id = "pg-test-001"
    persona.demographic_anchor.name = "Priya Mehta"
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
    persona.narrative.third_person = "Priya is a professional..."
    persona.memory.core.tendency_summary = "Tends to be price-sensitive."

    config = SarvamConfig.enabled()
    await enricher.enrich(persona, config)

    # .complete() must have been called; .messages.create must NOT
    mock_llm.complete.assert_called_once()
    assert not hasattr(mock_llm, 'messages') or not mock_llm.messages.create.called


# ---------------------------------------------------------------------------
# Test 2 — Legacy Anthropic client path: .messages.create() is called
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enricher_uses_messages_create_for_legacy_anthropic_client():
    """SarvamEnricher calls llm.messages.create() for a legacy Anthropic-style client."""
    from src.sarvam.enrichment import SarvamEnricher
    from src.sarvam.config import SarvamConfig

    # Build a mock that has ONLY .messages.create (no .complete)
    legacy_response = MagicMock()
    legacy_response.content = [MagicMock()]
    legacy_response.content[0].text = (
        '{"enriched_first_person": "I am Priya.", '
        '"enriched_third_person": "Priya is a professional.", '
        '"cultural_references_added": [], '
        '"contextual_examples_replaced": []}'
    )

    mock_llm = MagicMock(spec=[])  # spec=[] means no attributes by default
    mock_messages = MagicMock()
    mock_messages.create = AsyncMock(return_value=legacy_response)
    mock_llm.messages = mock_messages
    # Explicitly verify no .complete attribute
    assert not hasattr(mock_llm, 'complete')

    enricher = SarvamEnricher(llm_client=mock_llm)

    persona = MagicMock()
    persona.persona_id = "pg-test-002"
    persona.demographic_anchor.name = "Rahul Kumar"
    persona.demographic_anchor.age = 28
    persona.demographic_anchor.gender = "male"
    persona.demographic_anchor.location.country = "India"
    persona.demographic_anchor.location.city = "Delhi"
    persona.demographic_anchor.location.region = "Delhi"
    persona.demographic_anchor.location.urban_tier = "metro"
    persona.demographic_anchor.household.structure = "nuclear"
    persona.demographic_anchor.household.size = 2
    persona.demographic_anchor.household.income_bracket = "upper-middle"
    persona.demographic_anchor.education = "graduate"
    persona.demographic_anchor.employment = "full-time"
    persona.demographic_anchor.life_stage = "early career"
    persona.life_stories = []
    persona.narrative.first_person = "I am Rahul..."
    persona.narrative.third_person = "Rahul is a developer..."
    persona.memory.core.tendency_summary = "Tends to research extensively before buying."

    config = SarvamConfig.enabled()
    await enricher.enrich(persona, config)

    # .messages.create() must have been called
    mock_llm.messages.create.assert_called_once()


# ---------------------------------------------------------------------------
# Test 3 — SarvamConfig default model is Claude Haiku
# ---------------------------------------------------------------------------

def test_sarvam_config_model_defaults_to_haiku():
    """SarvamConfig() default model is 'claude-haiku-4-5-20251001'."""
    from src.sarvam.config import SarvamConfig

    config = SarvamConfig()
    assert config.model == "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Test 4 — SarvamConfig.for_sarvam_api() uses sarvam-m
# ---------------------------------------------------------------------------

def test_sarvam_config_for_sarvam_api_uses_sarvam_m():
    """SarvamConfig.for_sarvam_api().model == 'sarvam-m'."""
    from src.sarvam.config import SarvamConfig

    config = SarvamConfig.for_sarvam_api()
    assert config.model == "sarvam-m"
    assert config.sarvam_enrichment is True
