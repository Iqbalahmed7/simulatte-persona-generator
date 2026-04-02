"""tests/test_sarvam_cr1.py — CR1 Isolation Validator tests.

Sprint 10 — Sarvam Indian Cultural Realism Layer.
6 tests verifying that run_cr1_check() correctly detects (or confirms absence of)
PersonaRecord modifications after enrichment.

No LLM calls. No --integration flag required.
"""
from __future__ import annotations


def test_cr1_identical_personas():
    """Identical persona passed as both args → CR1 passes with no violations."""
    from src.sarvam.cr1_validator import run_cr1_check
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    result = run_cr1_check(persona, persona)
    assert result.passed is True
    assert result.violations == []
    assert "PASS" in result.summary


def test_cr1_model_copy_no_changes():
    """model_copy() with no updates produces an identical dict → CR1 passes."""
    from src.sarvam.cr1_validator import run_cr1_check
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    copy = persona.model_copy()
    result = run_cr1_check(persona, copy)
    assert result.passed is True


def test_cr1_detects_attribute_change():
    """Simulates Sarvam illegally modifying a persona attribute."""
    from src.sarvam.cr1_validator import run_cr1_check
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.schema.persona import Attribute

    persona = make_synthetic_persona()
    # Illegally modify one attribute
    modified_attrs = dict(persona.attributes)
    if "psychology" in modified_attrs:
        modified_category = dict(modified_attrs["psychology"])
        first_key = next(iter(modified_category))
        orig_attr = modified_category[first_key]
        if orig_attr.type == "continuous":
            tampered = Attribute(
                value=min(1.0, float(orig_attr.value) + 0.1),
                type="continuous",
                label=orig_attr.label,
                source=orig_attr.source,
            )
            modified_category[first_key] = tampered
            modified_attrs["psychology"] = modified_category
            tampered_persona = persona.model_copy(update={"attributes": modified_attrs})
            result = run_cr1_check(persona, tampered_persona)
            assert result.passed is False
            assert len(result.violations) >= 1


def test_cr1_detects_tendency_change():
    """CR1 must catch tendency source changes (e.g., proxy → grounded illegally)."""
    from src.sarvam.cr1_validator import run_cr1_check
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.schema.persona import PriceSensitivityBand

    persona = make_synthetic_persona()
    orig_band = persona.behavioural_tendencies.price_sensitivity.band
    tampered_price_sensitivity = PriceSensitivityBand(
        band=orig_band,
        description="illegally changed description by Sarvam",
        source="grounded",  # was "proxy"
    )
    tampered_tendencies = persona.behavioural_tendencies.model_copy(
        update={"price_sensitivity": tampered_price_sensitivity}
    )
    tampered_persona = persona.model_copy(
        update={"behavioural_tendencies": tampered_tendencies}
    )
    result = run_cr1_check(persona, tampered_persona)
    assert result.passed is False


def test_update_enrichment_record_with_cr1():
    """update_enrichment_record_with_cr1 stamps cr1_isolation and does not mutate original."""
    from src.sarvam.cr1_validator import update_enrichment_record_with_cr1, CR1Result
    from src.sarvam.types import SarvamEnrichmentRecord, ValidationStatus

    record = SarvamEnrichmentRecord(
        enrichment_applied=True,
        enrichment_provider="sarvam",
        persona_id="test-001",
        validation_status=ValidationStatus(),
    )
    cr1_result = CR1Result(passed=True, violations=[], summary="CR1 PASS")
    updated = update_enrichment_record_with_cr1(record, cr1_result)

    assert updated.validation_status.cr1_isolation == "pass"
    # Original record must not be mutated
    assert record.validation_status.cr1_isolation == "not_run"


def test_cr1_summary_on_failure():
    """A changed top-level field triggers FAIL with 'FAIL' in summary."""
    from src.sarvam.cr1_validator import run_cr1_check
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    # mode change SHOULD be caught
    tampered = persona.model_copy(update={"mode": "quick"})  # was "simulation-ready"
    result = run_cr1_check(persona, tampered)
    assert result.passed is False
    assert "FAIL" in result.summary
