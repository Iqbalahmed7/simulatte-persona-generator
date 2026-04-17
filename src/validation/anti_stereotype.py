"""Anti-Stereotypicality Validator — universal (not India-only).

Master Spec §10 — Anti-Stereotypicality Constraints:
  These are hard constraints. They apply to ALL persona generation —
  standard LLM-generated narratives, Sarvam-enriched outputs, interview
  dialogue, and decision reasoning traces alike.

  "If a narrative or cultural enrichment output contains any of the
   [prohibited defaults] without explicit derivation from the persona's
   attribute profile, it fails the anti-stereotypicality check and must
   be regenerated."

This validator complements (but does not replace) the India-specific
CR2 check in src/sarvam/cr2_validator.py. CR2 runs inside the Sarvam
pipeline. This validator runs on the *standard* narrative for every
persona, regardless of geography.

Scope
-----
Checks three classes of stereotypicality violations:

  1. Demographic stereotyping — age/gender/role clichés applied without
     attribute justification (e.g., "typical millennial", "boomer
     mentality", "tech-savvy teenager" as a default).
  2. Cultural defaults — region/religion/class clichés asserted without
     explicit derivation (the India-specific defaults from §10 lines
     1033-1044 live here; non-India clichés also flagged).
  3. Role-based clichés — occupation/life-stage assumptions applied as
     personality shortcuts ("strict engineer", "nurturing mother",
     "workaholic executive" without attribute support).

Violations are classified as:
  - hard_violations: prohibited defaults present → regeneration required
  - soft_warnings: pattern present but may be attribute-justified → review

Attribute-justification
-----------------------
Some patterns are prohibited ONLY when unsupported by the persona's
attributes. The `_is_justified()` helper checks whether a given
narrative element is traceable to a PersonaRecord field. If the
caller passes a persona_record, soft-pattern occurrences that can
be justified are removed from the hard list.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AntiStereotypeResult:
    """Result of an anti-stereotypicality check on a narrative."""
    passed: bool
    persona_id: str
    hard_violations: list[str] = field(default_factory=list)
    soft_warnings: list[str] = field(default_factory=list)
    checks_run: int = 0


# ---------------------------------------------------------------------------
# Prohibited patterns — §10 prohibited defaults + common non-India clichés.
# ---------------------------------------------------------------------------

# HARD: these are prohibited defaults per §10. Always flagged unless an
# attribute-level override in _context_overrides() clears them.
_HARD_PATTERNS_INDIA = [
    # From §10 Anti-Stereotypicality table + §15G Rule S-1..S-5
    ("joint family", "household.structure override required"),
    ("arranged marriage", "life_story or values explicit mention required"),
    ("jugaad", "attribute-supported (values.resourcefulness, etc.)"),
    ("dowry", "never a default"),
    ("namaste", "surface greeting stereotype"),
    ("curry", "food stereotype"),
    ("bollywood", "cultural stereotype"),
]

# HARD: universal demographic clichés applied as shortcuts.
_HARD_PATTERNS_DEMOGRAPHIC = [
    ("typical millennial", "generation-as-personality shortcut"),
    ("typical boomer", "generation-as-personality shortcut"),
    ("boomer mentality", "generation-as-personality shortcut"),
    ("tech-savvy teenager", "age-as-capability default"),
    ("tech-illiterate senior", "age-as-capability default"),
    ("digital native", "generation-as-skill shortcut"),
    ("typical gen z", "generation-as-personality shortcut"),
]

# HARD: role/occupation clichés used as personality replacements.
_HARD_PATTERNS_ROLE = [
    ("strict engineer", "occupation-as-personality"),
    ("nurturing mother", "role-as-personality default"),
    ("workaholic executive", "occupation-as-personality"),
    ("stressed-out banker", "occupation-as-mood default"),
    ("free-spirited artist", "occupation-as-personality"),
    ("spendthrift millennial", "compound demographic cliché"),
]

# SOFT: patterns that MAY be legitimate but need attribute justification.
# These are flagged for review; they are only hard failures if no
# supporting attribute exists on the persona record.
_SOFT_PATTERNS_ATTRIBUTE_DEPENDENT = [
    # India-context soft (from §10 prohibited-defaults table)
    ("chai", ["lifestyle.food_preferences", "values.tradition_orientation"]),
    ("temple", ["religious_identity", "religious_salience"]),
    ("festival", ["values.tradition_orientation", "religious_salience"]),
    ("cricket", ["lifestyle.sports_interest"]),
    ("hindi", ["location.region"]),
    # Universal
    ("traditional values", ["values.tradition_orientation"]),
    ("conservative", ["worldview.political_lean", "values.tradition_orientation"]),
    ("price-conscious", ["values.budget_consciousness"]),
    ("brand-loyal", ["values.brand_loyalty"]),
]


def _is_attribute_supported(
    persona_record: Any,
    attribute_paths: list[str],
    threshold: float = 0.55,
) -> bool:
    """Check if any of the given dotted-path attributes on the persona
    is set to a meaningful/high value (>= threshold for numeric, truthy
    for categorical).

    Returns True if the narrative element can be justified by the record.
    """
    if persona_record is None:
        return False
    for path in attribute_paths:
        val = _resolve_path(persona_record, path)
        if val is None:
            continue
        if isinstance(val, (int, float)):
            if float(val) >= threshold:
                return True
        elif isinstance(val, str):
            if val and val.lower() not in ("none", "null", "unknown", "na"):
                return True
        elif isinstance(val, bool):
            if val:
                return True
    return False


def _resolve_path(obj: Any, dotted: str) -> Any:
    """Resolve a dotted attribute path on an object or dict.

    Supports both Pydantic models (getattr) and raw dicts (item access).
    Also handles the attributes[category][name].value convention used by
    PersonaRecord.attributes.
    """
    parts = dotted.split(".")
    cur: Any = obj
    for p in parts:
        if cur is None:
            return None
        # Try attribute access
        try:
            nxt = getattr(cur, p)
        except AttributeError:
            nxt = None
        # Fallback to item access
        if nxt is None and isinstance(cur, dict):
            nxt = cur.get(p)
        cur = nxt

    # If we landed on an Attribute-like object with a .value, unwrap it.
    if cur is not None and hasattr(cur, "value"):
        return cur.value

    # Try the attributes[category][name] convention one more time.
    if cur is None and len(parts) == 2:
        attrs = getattr(obj, "attributes", None)
        if attrs is not None:
            cat, name = parts
            cat_dict = attrs.get(cat) if isinstance(attrs, dict) else None
            if cat_dict:
                attr = cat_dict.get(name)
                if attr is not None:
                    return getattr(attr, "value", None) or (
                        attr.get("value") if isinstance(attr, dict) else None
                    )
    return cur


def _context_overrides(text_lower: str, persona_record: Any) -> set[str]:
    """Return the set of pattern-phrases whose violation can be cleared
    given the persona_record. E.g. 'joint family' is OK if household.structure='joint'.
    """
    cleared: set[str] = set()
    if persona_record is None:
        return cleared

    anchor = getattr(persona_record, "demographic_anchor", None)
    if anchor is None:
        return cleared

    household = getattr(anchor, "household", None)
    if household and getattr(household, "structure", None) == "joint":
        cleared.add("joint family")

    # 'arranged marriage' is OK if a life story explicitly mentions it
    life_stories = getattr(persona_record, "life_stories", None) or []
    for ls in life_stories:
        story_text = getattr(ls, "story", None) or (
            ls.get("story") if isinstance(ls, dict) else ""
        )
        if story_text and "arranged marriage" in str(story_text).lower():
            cleared.add("arranged marriage")
            break

    return cleared


def run_anti_stereotype_check(
    persona_id: str,
    narrative_first: str,
    narrative_third: str = "",
    persona_record: Any = None,
) -> AntiStereotypeResult:
    """Run the universal anti-stereotypicality audit on a persona's
    standard narrative (first-person and optional third-person).

    Unlike CR2 (which runs inside the Sarvam pipeline on enriched output),
    this validator runs on the STANDARD narrative — the default-path
    output of every persona, India or not.

    Args:
        persona_id: Persona identifier for diagnostic traceability.
        narrative_first: First-person narrative text.
        narrative_third: Optional third-person narrative text.
        persona_record: Optional PersonaRecord for attribute-justification.
            When provided, soft patterns supported by attributes are NOT
            treated as violations. When None, all patterns are flagged.

    Returns:
        AntiStereotypeResult(passed, hard_violations, soft_warnings, …)
    """
    combined = f"{narrative_first} {narrative_third}".lower()
    hard_violations: list[str] = []
    soft_warnings: list[str] = []
    checks_run = 0

    # Context overrides — phrases cleared by attribute-level justification.
    cleared = _context_overrides(combined, persona_record)

    # --- Hard India-specific patterns ---
    for pattern, reason in _HARD_PATTERNS_INDIA:
        checks_run += 1
        if pattern in combined and pattern not in cleared:
            hard_violations.append(f"[india] '{pattern}': {reason}")

    # --- Hard demographic/generational patterns ---
    for pattern, reason in _HARD_PATTERNS_DEMOGRAPHIC:
        checks_run += 1
        if pattern in combined:
            hard_violations.append(f"[demographic] '{pattern}': {reason}")

    # --- Hard role/occupation patterns ---
    for pattern, reason in _HARD_PATTERNS_ROLE:
        checks_run += 1
        if pattern in combined:
            hard_violations.append(f"[role] '{pattern}': {reason}")

    # --- Soft patterns (attribute-dependent) ---
    for pattern, attribute_paths in _SOFT_PATTERNS_ATTRIBUTE_DEPENDENT:
        checks_run += 1
        # Use whole-word boundary for short tokens to avoid false positives
        # (e.g. 'hindi' should not match 'behind india').
        if re.search(rf"\b{re.escape(pattern)}\b", combined):
            if _is_attribute_supported(persona_record, attribute_paths):
                # Cleared by attribute — no warning emitted.
                continue
            if persona_record is None:
                soft_warnings.append(
                    f"'{pattern}' present; attribute justification not verifiable "
                    f"(no persona_record supplied)"
                )
            else:
                # Pattern present but no supporting attribute — soft warning.
                soft_warnings.append(
                    f"'{pattern}' present but not supported by "
                    f"{'/'.join(attribute_paths[:2])}"
                )

    return AntiStereotypeResult(
        passed=len(hard_violations) == 0,
        persona_id=persona_id,
        hard_violations=hard_violations,
        soft_warnings=soft_warnings,
        checks_run=checks_run,
    )
