# SPRINT 11 BRIEF — OPENCODE
**Role:** HC3 Taxonomy Fix + Structural Smoke Tests
**Sprint:** 11 — Production Entry Point + Technical Debt Clearance
**Spec ref:** Master Spec §6 (Taxonomy Strategy), §10 (Constraint System — HC3)
**Previous rating:** 19/20 (mislabelled Sprint 9 outcome file as Sprint 10)

---

## Context

Two jobs this sprint:

1. **HC3 taxonomy fix**: `health_supplement_belief` has been missing from `base_taxonomy.py` since Sprint 1. The HC3 hard constraint checker already handles it correctly (it silently no-ops when the attribute is absent). Adding the attribute activates the check automatically.

2. **Structural smoke tests**: Write a test file that validates the complete pipeline can be imported and structurally invoked end-to-end without any LLM calls. This confirms all modules are correctly wired together.

---

## Fix 1: Add `health_supplement_belief` to `src/taxonomy/base_taxonomy.py`

The attribute belongs in the `"health"` category (adjacent to `health_consciousness` and `health_anxiety`).

Find the `health` category block in `base_taxonomy.py`. It currently contains:
- `health_anxiety` (continuous, psychology category)
- `health_consciousness` (continuous, lifestyle category)

Add to the **psychology** category (where `health_anxiety` lives) — this is critical because `src/generation/constraint_checker.py` reads `health_supplement_belief` from the `"psychology"` category via `_get_attr_value(persona, "psychology", "health_supplement_belief")`.

```python
_continuous(
    "health_supplement_belief",
    "psychology",
    "Belief in the efficacy of dietary supplements, vitamins, and nutraceuticals. "
    "High values indicate strong supplement advocacy; low values indicate skepticism.",
    0.45,
),
```

The `_continuous` helper signature is: `_continuous(name, category, description, default_value)`.

Place it immediately after `health_anxiety` in the psychology block.

---

## Fix 2: Write `tests/test_smoke.py`

Structural smoke tests — no LLM calls. These confirm every key module imports correctly and basic structural invariants hold.

### Test 1: Core schema imports without error

```python
def test_schema_imports():
    """All core schema types importable."""
    from src.schema.persona import (
        PersonaRecord, Attribute, BehaviouralTendencies,
        CoreMemory, WorkingMemory, Narrative,
        DerivedInsights, LifeStory, Reflection, Observation,
    )
    from src.schema.cohort import CohortEnvelope, CohortSummary, TaxonomyMeta
    assert PersonaRecord is not None
    assert CohortEnvelope is not None
```

### Test 2: Taxonomy loads and has health_supplement_belief

```python
def test_taxonomy_has_health_supplement_belief():
    """HC3 fix: health_supplement_belief must now be in the base taxonomy."""
    from src.taxonomy.base_taxonomy import BASE_TAXONOMY
    all_attr_names = [attr.name for attr in BASE_TAXONOMY]
    assert "health_supplement_belief" in all_attr_names, (
        "HC3 fix not applied: health_supplement_belief missing from base taxonomy"
    )
```

### Test 3: health_supplement_belief is in lifestyle category

```python
def test_health_supplement_belief_category():
    from src.taxonomy.base_taxonomy import BASE_TAXONOMY
    attr = next((a for a in BASE_TAXONOMY if a.name == "health_supplement_belief"), None)
    assert attr is not None
    assert attr.category == "psychology"  # constraint_checker reads from psychology
    assert attr.type == "continuous"
    assert 0.0 <= attr.default_value <= 1.0
```

### Test 4: HC3 constraint checker now activates (no longer silently skipped)

```python
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
        label="Health Anxiety", source="proxy",
    )
    attrs["psychology"] = psych

    # Set health_supplement_belief > 0.80 in psychology (where constraint_checker reads it)
    psych["health_supplement_belief"] = Attribute(
        value=0.90, type="continuous",
        label="Health Supplement Belief", source="proxy",
    )
    attrs["psychology"] = psych

    tampered = persona.model_copy(update={"attributes": attrs})
    checker = ConstraintChecker()
    violations = checker.check_hard_constraints(tampered)

    # HC3 should now fire (not silently skip)
    hc3_violations = [v for v in violations if "supplement" in v.lower() or "HC3" in v]
    assert len(hc3_violations) > 0, (
        "HC3 did not fire — check that health_supplement_belief is in taxonomy "
        "and constraint_checker.py handles this combination"
    )
```

### Test 5: All src modules importable without error

```python
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
```

### Test 6: Sarvam pipeline returns skip record for non-India (smoke)

```python
import pytest

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
```

### Test 7: HC3 checker works with absent attribute (graceful no-op)

```python
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
    if "lifestyle" in attrs:
        lifestyle = dict(attrs["lifestyle"])
        lifestyle.pop("health_supplement_belief", None)
        attrs["lifestyle"] = lifestyle
    stripped_persona = persona.model_copy(update={"attributes": attrs})

    checker = ConstraintChecker()
    # Should not raise
    violations = checker.check_hard_constraints(stripped_persona)
    assert isinstance(violations, list)
```

---

## Constraints

- No LLM calls.
- Test 4 (HC3 activation test) may need to inspect `ConstraintChecker.check_hard_constraints()` signature — if it doesn't exist under that name, look at the constraint checker's public method (use `dir(checker)` or read the file).
- If HC3 fires a different violation message than expected, adjust the `hc3_violations` filter in Test 4 to match actual message text.
- 7 tests, all pass without `--integration`.
- Full suite must remain 155+ passed.

---

## Outcome File

Write `sprints/outcome_opencode.md` with:
1. Lines changed in base_taxonomy.py
2. HC3 activation confirmed
3. Smoke test results (7/7)
4. Full suite result
5. Known gaps
