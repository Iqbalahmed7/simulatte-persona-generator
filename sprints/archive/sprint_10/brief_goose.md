# SPRINT 10 BRIEF — GOOSE
**Role:** CR1 Validator + CR1 Tests
**Sprint:** 10 — Sarvam Indian Cultural Realism Layer
**Spec ref:** SIMULATTE_SARVAM_TEST_PROTOCOL.md — CR1 Isolation Test
**Previous rating:** 20/20

---

## Context

Sprint 10 builds the Sarvam layer. Your job: the CR1 isolation validator. CR1 verifies that Sarvam enrichment did NOT modify the `PersonaRecord` — zero tolerance for attribute/tendency/memory changes.

CR1 is automated (code-level diff of persona fields).

---

## File: `src/sarvam/cr1_validator.py`

```python
"""CR1 Isolation Validator for Sarvam enrichment.

Sprint 10 — Sarvam Indian Cultural Realism Layer.
CR1: Verifies that Sarvam enrichment did not modify the PersonaRecord.

Zero tolerance for:
- Attribute value changes
- BehaviouralTendencies changes
- CoreMemory changes
- WorkingMemory changes

From SIMULATTE_SARVAM_TEST_PROTOCOL.md:
"The PersonaRecord must be identical before and after enrichment."
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CR1Result:
    """Result of a CR1 isolation check."""
    passed: bool
    violations: list[str]
    """List of field paths that differ between original and post-enrichment persona."""
    summary: str
    """Human-readable summary of the CR1 result."""


def run_cr1_check(
    original_persona: object,
    post_enrichment_persona: object,
) -> CR1Result:
    """Run the CR1 isolation check.

    Compares original_persona against post_enrichment_persona field by field.
    Both should be identical since Sarvam enrichment must not modify the PersonaRecord.

    Fields checked (zero-tolerance):
    - attributes (all category/name/value combinations)
    - behavioural_tendencies (price_sensitivity, trust_orientation, switching_propensity, objection_profile)
    - memory.core (all fields)
    - memory.working.observations (count and content)
    - derived_insights (decision_style, trust_anchor, risk_appetite, key_tensions)
    - demographic_anchor (all demographic fields)

    Args:
        original_persona: The PersonaRecord before enrichment.
        post_enrichment_persona: The PersonaRecord after enrichment (should be identical).

    Returns:
        CR1Result with passed=True if no differences found.
    """
    ...
```

### Implementation approach — use `.model_dump()` for comparison:

Since PersonaRecord is a Pydantic model, use `model_dump()` to get a comparable dict, then do a recursive field comparison. Mark violations as `"field.path: original_value → post_value"`.

```python
def run_cr1_check(original_persona, post_enrichment_persona):
    violations = []

    # Get comparable dicts — Pydantic model_dump() handles nested models
    try:
        original_dict = original_persona.model_dump()
        post_dict = post_enrichment_persona.model_dump()
    except AttributeError:
        # Fallback for non-Pydantic objects — compare repr
        if repr(original_persona) != repr(post_enrichment_persona):
            violations.append("persona: repr differs (not a Pydantic model)")
        if violations:
            return CR1Result(passed=False, violations=violations,
                             summary=f"CR1 FAIL: {len(violations)} violation(s)")
        return CR1Result(passed=True, violations=[], summary="CR1 PASS")

    _compare_dicts(original_dict, post_dict, path="", violations=violations)

    if violations:
        summary = f"CR1 FAIL: {len(violations)} violation(s) — " + "; ".join(violations[:3])
        if len(violations) > 3:
            summary += f" (+ {len(violations) - 3} more)"
        return CR1Result(passed=False, violations=violations, summary=summary)

    return CR1Result(passed=True, violations=[], summary="CR1 PASS: persona record unchanged")


def _compare_dicts(
    original: dict,
    post: dict,
    path: str,
    violations: list[str],
) -> None:
    """Recursively compare two dicts, recording path-level violations."""
    all_keys = set(original.keys()) | set(post.keys())
    for key in all_keys:
        current_path = f"{path}.{key}" if path else key

        if key not in original:
            violations.append(f"{current_path}: missing in original")
            continue
        if key not in post:
            violations.append(f"{current_path}: missing in post-enrichment")
            continue

        orig_val = original[key]
        post_val = post[key]

        if isinstance(orig_val, dict) and isinstance(post_val, dict):
            _compare_dicts(orig_val, post_val, current_path, violations)
        elif isinstance(orig_val, list) and isinstance(post_val, list):
            _compare_lists(orig_val, post_val, current_path, violations)
        elif orig_val != post_val:
            violations.append(f"{current_path}: {orig_val!r} → {post_val!r}")


def _compare_lists(
    original: list,
    post: list,
    path: str,
    violations: list[str],
) -> None:
    """Compare two lists element-by-element."""
    if len(original) != len(post):
        violations.append(f"{path}: length {len(original)} → {len(post)}")
        return
    for i, (orig_item, post_item) in enumerate(zip(original, post)):
        item_path = f"{path}[{i}]"
        if isinstance(orig_item, dict) and isinstance(post_item, dict):
            _compare_dicts(orig_item, post_item, item_path, violations)
        elif orig_item != post_item:
            violations.append(f"{item_path}: {orig_item!r} → {post_item!r}")
```

Also add this convenience function:

```python
def update_enrichment_record_with_cr1(
    enrichment_record: object,
    cr1_result: CR1Result,
) -> object:
    """Update a SarvamEnrichmentRecord's validation_status.cr1_isolation field.

    Returns the record updated via model_copy(). Does not mutate.
    """
    cr1_status = "pass" if cr1_result.passed else "fail"
    updated_status = enrichment_record.validation_status.model_copy(
        update={"cr1_isolation": cr1_status}
    )
    return enrichment_record.model_copy(
        update={"validation_status": updated_status}
    )
```

---

## File: `tests/test_sarvam_cr1.py`

### Test 1: Identical personas → CR1 pass

```python
def test_cr1_identical_personas():
    from src.sarvam.cr1_validator import run_cr1_check
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    result = run_cr1_check(persona, persona)
    assert result.passed is True
    assert result.violations == []
    assert "PASS" in result.summary
```

### Test 2: model_copy with no changes → CR1 pass

```python
def test_cr1_model_copy_no_changes():
    from src.sarvam.cr1_validator import run_cr1_check
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    copy = persona.model_copy()
    result = run_cr1_check(persona, copy)
    assert result.passed is True
```

### Test 3: Changed attribute value → CR1 fail

```python
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
```

### Test 4: Changed tendency source → CR1 fail

```python
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
```

### Test 5: update_enrichment_record_with_cr1

```python
def test_update_enrichment_record_with_cr1():
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
```

### Test 6: CR1 result summary on failure

```python
def test_cr1_summary_on_failure():
    from src.sarvam.cr1_validator import run_cr1_check
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.schema.persona import Narrative

    persona = make_synthetic_persona()
    # Narrative change should NOT be caught by CR1 (narrative is expression, not identity)
    # But mode change SHOULD be caught
    tampered = persona.model_copy(update={"mode": "quick"})  # was "simulation-ready"
    result = run_cr1_check(persona, tampered)
    assert result.passed is False
    assert "FAIL" in result.summary
```

---

## Constraints

- No LLM calls. Pure field comparison.
- `run_cr1_check` must use `model_dump()` — not `==` comparison on the full PersonaRecord (too broad; we want field-level diff).
- Tests 3 and 4 may skip silently if the persona fixture doesn't have the expected attribute category — use `if "psychology" in modified_attrs:` guard.
- 6 tests, all pass without `--integration`.
- Run full suite: must remain 123+ passed.

---

## Outcome File

When done, write `sprints/outcome_goose.md` with:
1. File created (line count)
2. Comparison approach — how model_dump() diff works
3. Test results (6/6)
4. Full suite result
5. Known gaps
