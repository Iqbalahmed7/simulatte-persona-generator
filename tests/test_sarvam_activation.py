"""Tests for Sarvam activation gate, config, and types.

Sprint 10 — Sarvam Indian Cultural Realism Layer.
10 tests, no LLM calls, no --integration flag required.
"""
from __future__ import annotations


def test_activation_india_enabled():
    from src.sarvam.activation import should_activate
    from src.sarvam.config import SarvamConfig

    class MockPersona:
        class demographic_anchor:
            class location:
                country = "India"

    active, reason = should_activate(MockPersona(), SarvamConfig.enabled())
    assert active is True
    assert "met" in reason.lower()


def test_activation_india_disabled():
    from src.sarvam.activation import should_activate
    from src.sarvam.config import SarvamConfig

    class MockPersona:
        class demographic_anchor:
            class location:
                country = "India"

    active, reason = should_activate(MockPersona(), SarvamConfig.disabled())
    assert active is False
    assert "disabled" in reason.lower()


def test_activation_non_india():
    from src.sarvam.activation import should_activate
    from src.sarvam.config import SarvamConfig

    class MockPersona:
        class demographic_anchor:
            class location:
                country = "USA"

    active, reason = should_activate(MockPersona(), SarvamConfig.enabled())
    assert active is False
    assert "india-only" in reason.lower() or "india" in reason.lower()


def test_activation_missing_country():
    from src.sarvam.activation import should_activate
    from src.sarvam.config import SarvamConfig

    class MockPersona:
        class demographic_anchor:
            class location:
                country = None

    active, reason = should_activate(MockPersona(), SarvamConfig.enabled())
    assert active is False


def test_sarvam_config_defaults():
    from src.sarvam.config import SarvamConfig
    config = SarvamConfig()
    assert config.sarvam_enrichment is False
    assert config.scope == "narrative_and_examples"
    assert config.anti_stereotypicality_strict is True


def test_sarvam_config_enabled_constructor():
    from src.sarvam.config import SarvamConfig
    config = SarvamConfig.enabled()
    assert config.sarvam_enrichment is True
    assert config.scope == "narrative_and_examples"


def test_enrichment_record_not_applied():
    from src.sarvam.types import SarvamEnrichmentRecord
    record = SarvamEnrichmentRecord(
        enrichment_applied=False,
        enrichment_provider="none",
        persona_id="test-001",
        skip_reason="not India",
    )
    assert record.enrichment_applied is False
    assert record.enriched_narrative is None
    assert record.skip_reason == "not India"


def test_enrichment_record_applied():
    from src.sarvam.types import SarvamEnrichmentRecord, EnrichedNarrative, ValidationStatus
    record = SarvamEnrichmentRecord(
        enrichment_applied=True,
        enrichment_provider="sarvam",
        enrichment_scope="narrative_and_examples",
        persona_id="test-001",
        enriched_narrative=EnrichedNarrative(
            first_person="I shop at Meesho for value...",
            third_person="Priya, a Mumbai professional...",
        ),
        cultural_references_added=["Meesho", "chai tapri"],
        validation_status=ValidationStatus(cr1_isolation="pass"),
    )
    assert record.enrichment_applied is True
    assert record.enriched_narrative is not None
    assert len(record.cultural_references_added) == 2
    assert record.validation_status.cr1_isolation == "pass"


def test_make_skip_record():
    from src.sarvam.activation import make_skip_record
    record = make_skip_record("pg-cpg-001", "not India")
    assert record.enrichment_applied is False
    assert record.persona_id == "pg-cpg-001"
    assert record.skip_reason == "not India"


def test_validation_status_defaults():
    from src.sarvam.types import ValidationStatus
    vs = ValidationStatus()
    assert vs.cr1_isolation == "not_run"
    assert vs.cr2_stereotype_audit == "not_run"
    assert vs.cr3_cultural_realism == "not_run"
    assert vs.cr4_persona_fidelity == "not_run"
