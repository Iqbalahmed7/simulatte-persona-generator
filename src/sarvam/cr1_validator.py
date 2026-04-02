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

from dataclasses import dataclass, field


@dataclass
class CR1Result:
    """Result of a CR1 isolation check."""
    passed: bool
    violations: list
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
    violations: list,
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
            violations.append(f"{current_path}: {orig_val!r} \u2192 {post_val!r}")


def _compare_lists(
    original: list,
    post: list,
    path: str,
    violations: list,
) -> None:
    """Compare two lists element-by-element."""
    if len(original) != len(post):
        violations.append(f"{path}: length {len(original)} \u2192 {len(post)}")
        return
    for i, (orig_item, post_item) in enumerate(zip(original, post)):
        item_path = f"{path}[{i}]"
        if isinstance(orig_item, dict) and isinstance(post_item, dict):
            _compare_dicts(orig_item, post_item, item_path, violations)
        elif orig_item != post_item:
            violations.append(f"{item_path}: {orig_item!r} \u2192 {post_item!r}")


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
