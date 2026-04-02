"""tests/test_smoke.py — Structural smoke tests for Sprint 11.

No LLM calls. Validates that all key modules import correctly and
basic structural invariants hold end-to-end.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Test 1: Core schema imports without error
# ---------------------------------------------------------------------------

def test_schema_imports():
    """All core schema types importable."""
    from src.schema.persona import (
        PersonaRecord, Attribute, BehaviouralTendencies,
        CoreMemory, WorkingMemory, Narrative,
        DerivedInsights, LifeStory,
    )
    from src.schema.cohort import CohortEnvelope, CohortSummary, TaxonomyMeta
    assert PersonaRecord is not None
    assert CohortEnvelope is not None


# ---------------------------------------------------------------------------
# Test 2: Taxonomy loads and has health_supplement_belief
# ---------------------------------------------------------------------------

def test_taxonomy_has_health_supplement_belief():
    """HC3 fix: health_supplement_belief must now be in the base taxonomy."""
    from src.taxonomy.base_taxonomy import BASE_TAXONOMY
    all_attr_names = [attr.name for attr in BASE_TAXONOMY]
    assert "health_supplement_belief" in all_attr_names, (
        "HC3 fix not applied: health_supplement_belief missing from base taxonomy"
    )


# ---------------------------------------------------------------------------
# Test 3: health_supplement_belief is in psychology category
# ---------------------------------------------------------------------------

def test_health_supplement_belief_category():
    from src.taxonomy.base_taxonomy import BASE_TAXONOMY
    attr = next((a for a in BASE_TAXONOMY if a.name == "health_supplement_belief"), None)
    assert attr is not None
    assert attr.category == "psychology"  # constraint_checker reads from psychology
    assert attr.attr_type == "continuous"
    assert 0.0 <= attr.population_prior <= 1.0


# ---------------------------------------------------------------------------
# Test 4: HC3 constraint checker now activates (no longer silently skipped)
# ---------------------------------------------------------------------------

def test_hc3_activates_after_fix():
    """
    HC3: health_anxiety < 0.2 AND health_supplement_belief > 0.80 is contradictory.
    After the fix, this combination must be flagged (not silently skipped).
    """
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.schema.persona import Attribute
    from src.generation.constraint_checker import ConstraintChecker

    persona = make_synthetic_persona()

    # Inject a violating combination into the persona's attributes
    attrs = dict(persona.attributes)

    # Set health_anxiety < 0.2 in psychology
    psych = dict(attrs.get("psychology", {}))
    psych["health_anxiety"] = Attribute(
        value=0.10, type="continuous",
        label="Health Anxiety", source="sampled",
    )
    attrs["psychology"] = psych

    # Set health_supplement_belief > 0.80 in psychology (where constraint_checker reads it)
    psych["health_supplement_belief"] = Attribute(
        value=0.90, type="continuous",
        label="Health Supplement Belief", source="sampled",
    )
    attrs["psychology"] = psych

    tampered = persona.model_copy(update={"attributes": attrs})
    checker = ConstraintChecker()
    violations = checker.check_hard_constraints(tampered)

    # HC3 should now fire (not silently skip)
    hc3_violations = [
        v for v in violations
        if "HC3" in (v.constraint_id if hasattr(v, "constraint_id") else str(v))
    ]
    assert len(hc3_violations) > 0, (
        "HC3 did not fire — check that health_supplement_belief is in taxonomy "
        "and constraint_checker.py handles this combination"
    )


# ---------------------------------------------------------------------------
# Test 5: All src modules importable without error
# ---------------------------------------------------------------------------

def test_all_src_modules_importable():
    """Every src module must import without raising."""
    import importlib
    modules = [
        "src.schema.persona",
        "src.schema.cohort",
        "src.taxonomy.base_taxonomy",
        "src.generation.identity_constructor",
        "src.generation.attribute_filler",
        "src.generation.constraint_checker",
        "src.generation.tendency_estimator",
        "src.cohort.assembler",
        "src.cohort.distinctiveness",
        "src.cohort.diversity_checker",
        "src.memory.core_memory",
        "src.memory.working_memory",
        "src.memory.retrieval",
        "src.cognition.loop",
        "src.modalities.survey",
        "src.modalities.simulation",
        "src.grounding.pipeline",
        "src.sarvam.activation",
        "src.sarvam.config",
        "src.sarvam.types",
        "src.sarvam.pipeline",
        "src.sarvam.cr1_validator",
    ]
    for mod in modules:
        imported = importlib.import_module(mod)
        assert imported is not None, f"Failed to import {mod}"


# ---------------------------------------------------------------------------
# Test 6: Sarvam pipeline returns skip record for non-India (smoke)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sarvam_smoke_non_india():
    """Sarvam pipeline smoke test — non-India persona is skipped correctly."""
    from src.sarvam.pipeline import run_sarvam_enrichment
    from src.sarvam.config import SarvamConfig
    from unittest.mock import MagicMock

    persona = MagicMock()
    persona.persona_id = "smoke-001"
    persona.demographic_anchor.location.country = "USA"

    record = await run_sarvam_enrichment(persona, SarvamConfig.enabled(), llm_client=None)
    assert record.enrichment_applied is False


# ---------------------------------------------------------------------------
# Test 7: HC3 checker works with absent attribute (graceful no-op)
# ---------------------------------------------------------------------------

def test_hc3_absent_attribute_no_op():
    """
    If health_supplement_belief is present in taxonomy but absent from a specific
    persona's attributes dict, HC3 check should not raise — it should be a no-op.
    This tests the graceful fallback path in ConstraintChecker.
    """
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.generation.constraint_checker import ConstraintChecker

    persona = make_synthetic_persona()
    # Remove health_supplement_belief from the persona if present
    attrs = dict(persona.attributes)
    if "psychology" in attrs:
        psychology = dict(attrs["psychology"])
        psychology.pop("health_supplement_belief", None)
        attrs["psychology"] = psychology
    if "lifestyle" in attrs:
        lifestyle = dict(attrs["lifestyle"])
        lifestyle.pop("health_supplement_belief", None)
        attrs["lifestyle"] = lifestyle
    stripped_persona = persona.model_copy(update={"attributes": attrs})

    checker = ConstraintChecker()
    # Should not raise
    violations = checker.check_hard_constraints(stripped_persona)
    assert isinstance(violations, list)
