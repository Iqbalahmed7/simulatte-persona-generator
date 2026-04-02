# SPRINT 1 BRIEF — ANTIGRAVITY
**Role:** Validator + Quality Enforcer
**Sprint:** 1 — Foundation: Schema + Taxonomy
**Spec check:** Master Spec §10 (Constraint System), §11 (Distinctiveness), §12 (Validity Protocol G1–G3), §14A S5 (5:3:2 stratification settled)
**Previous rating:** n/a (Sprint 1)

---

## Your Job This Sprint

You build the three quality enforcement components: the schema validator, the cosine-distance stratification engine, and the hard/soft constraint checker. These are the gates that prevent garbage personas from leaving the generation pipeline.

Three files. They depend on schema (Cursor) and taxonomy (Codex).

---

## Files

```
src/
  schema/
    validators.py           ← G1, G2, G3 automated validation gates
  generation/
    stratification.py       ← 5:3:2 cosine-distance stratification
    constraint_checker.py   ← Hard + soft constraint validation
```

---

## File 1: `src/schema/validators.py`

### What It Does

Implements the automated structural validation gates G1, G2, G3 from the Validity Protocol. These run on every generated persona before it is accepted.

### Interface

```python
from src.schema.persona import PersonaRecord
from src.taxonomy.base_taxonomy import AttributeDefinition

class ValidationResult:
    passed: bool
    gate: str
    failures: list[str]  # human-readable failure descriptions
    warnings: list[str]  # soft issues that don't fail the gate

class PersonaValidator:
    """
    Runs structural validation gates G1, G2, G3 on a persona record.
    """

    def validate_all(self, persona: PersonaRecord) -> list[ValidationResult]:
        """Run all gates. Returns results for G1, G2, G3."""
        ...

    def g1_schema_validity(self, persona: PersonaRecord) -> ValidationResult:
        """
        G1: Every sample persona parses without Pydantic error.
        Check:
        - PersonaRecord is a valid Pydantic model (already true if it's a PersonaRecord)
        - key_tensions has ≥ 1 item
        - life_stories has 2–3 items
        - key_values has 3–5 items
        - source_observation_ids on every Reflection has ≥ 2 items
        - All TrustWeights floats are 0.0–1.0
        - All Attribute sources are from the valid set
        - persona_id matches format pg-[prefix]-[NNN]
        """
        ...

    def g2_hard_constraints(self, persona: PersonaRecord) -> ValidationResult:
        """
        G2: Hard constraint checker correctly rejects all impossible combinations.
        See HARD_CONSTRAINTS table below.
        Returns ValidationResult with all violations listed.
        """
        ...

    def g3_tendency_attribute_consistency(
        self,
        persona: PersonaRecord,
        taxonomy: list[AttributeDefinition],
    ) -> ValidationResult:
        """
        G3: Tendency-attribute consistency checker flags all 8 rule violations.
        See TENDENCY_ATTRIBUTE_RULES below.
        """
        ...
```

### Hard Constraints (G2) — Implement All 6

These are logically impossible combinations. Any persona violating one fails G2.

| # | Constraint | Description |
|---|-----------|-------------|
| HC1 | `age < 22 AND life_stage == "established"` | Cannot be established under 22 |
| HC2 | `household.dual_income == True AND household.structure == "single-parent"` | Single parent can't be dual-income |
| HC3 | `derived_insights.risk_appetite == "high" AND attributes.psychology.status_quo_bias > 0.8` | High risk appetite + extreme status quo bias impossible |
| HC4 | `derived_insights.trust_anchor == "self" AND attributes.psychology.authority_bias > 0.85` | Self-trust anchor + extreme authority bias contradicts |
| HC5 | `attributes.values.brand_loyalty > 0.9 AND attributes.values.indie_brand_openness > 0.85` | Cannot be extremely loyal AND extremely open to unknowns |
| HC6 | `derived_insights.decision_style == "analytical" AND attributes.psychology.information_need < 0.1` | Analytical style requires non-trivial information need |

### Tendency-Attribute Rules (G3) — Implement All 8

These check that the derived tendency bands are consistent with the underlying attribute values.

| # | Rule |
|---|------|
| TR1 | If `price_sensitivity.band == "extreme"` → `attributes.values.deal_seeking_intensity > 0.7` |
| TR2 | If `price_sensitivity.band == "low"` → `attributes.values.budget_consciousness < 0.4` |
| TR3 | If `trust_orientation.dominant == "peer"` → `attributes.social.social_proof_bias > 0.6` |
| TR4 | If `trust_orientation.dominant == "authority"` → `attributes.psychology.authority_bias > 0.6` |
| TR5 | If `switching_propensity.band == "high"` → `attributes.values.brand_loyalty < 0.5` |
| TR6 | If `switching_propensity.band == "low"` → `attributes.values.brand_loyalty > 0.5` |
| TR7 | If `derived_insights.risk_appetite == "low"` → `attributes.psychology.risk_tolerance < 0.35` |
| TR8 | If `derived_insights.risk_appetite == "high"` → `attributes.psychology.risk_tolerance > 0.65` |

Note: `attributes.category.name` refers to `persona.attributes[category][name].value`.

### Attribute Access Helper

```python
def _get_attr_value(
    self,
    persona: PersonaRecord,
    category: str,
    name: str,
) -> float | str | None:
    """
    Safe accessor for persona.attributes[category][name].value.
    Returns None if the attribute is missing (don't raise — log as warning).
    """
    ...
```

---

## File 2: `src/generation/stratification.py`

### What It Does

Implements 5:3:2 stratification for cohort assembly. Given a list of persona candidates, selects a cohort that distributes 50% near cluster center / 30% mid-range / 20% far, using cosine distance on the 8 anchor attributes.

### Background

Without stratification, LLM-generated personas cluster near the mean. 5:3:2 counteracts this by deliberately including outlier personas. The 8 anchor attributes are the basis for distance computation because they define the core identity space.

### Interface

```python
import numpy as np
from src.schema.persona import PersonaRecord
from src.taxonomy.base_taxonomy import ANCHOR_ATTRIBUTES

class StratificationResult:
    cohort: list[PersonaRecord]
    near_center: list[PersonaRecord]   # 50% — closest to centroid
    mid_range: list[PersonaRecord]     # 30% — moderate distance
    far_outliers: list[PersonaRecord]  # 20% — highest distance
    centroid: np.ndarray
    distances: dict[str, float]        # persona_id → cosine distance from centroid

class CohortStratifier:
    """
    Selects and stratifies a cohort from a pool of candidate personas.
    """

    def stratify(
        self,
        candidates: list[PersonaRecord],
        target_size: int,
    ) -> StratificationResult:
        """
        From candidates, select target_size personas using 5:3:2 stratification.

        Requirements:
        - target_size must be ≥ 3 (otherwise 5:3:2 is undefined)
        - Minimum candidates pool must be ≥ target_size * 2 (caller's responsibility)
        - Distribution: round(0.5 * target_size) near / round(0.3 * target_size) mid / remainder far
        - Within ±1 tolerance on each band (to handle rounding with small N)

        Returns StratificationResult with selected cohort and per-band breakdown.
        """
        ...

    def _extract_anchor_vector(self, persona: PersonaRecord) -> np.ndarray:
        """
        Extract the 8 anchor attribute values as a float vector.
        For categorical anchors, encode as index in the options list (0-indexed, normalised to 0.0–1.0).
        For continuous anchors, use value directly.
        Returns a vector of length 8.
        """
        ...

    def _cosine_distance(self, a: np.ndarray, b: np.ndarray) -> float:
        """Cosine distance (1 - cosine similarity). Returns 0.0–2.0."""
        ...

    def _compute_centroid(self, vectors: list[np.ndarray]) -> np.ndarray:
        """Mean of all vectors."""
        ...
```

### Categorical Anchor Encoding

The 8 anchors include categorical attributes (`personality_type`, `trust_orientation_primary`, etc.). Encode these as:

```python
option_index = options.index(value)  # position in options list
encoded = option_index / (len(options) - 1)  # normalise to 0.0–1.0
```

If the value is not found in options, encode as 0.5 (neutral — log a warning).

### Acceptance Criteria

A cohort of 10 must produce 5/3/2 distribution within ±1 tolerance:
- 5 near-center (acceptable: 4–6)
- 3 mid-range (acceptable: 2–4)
- 2 far outliers (acceptable: 1–3)

---

## File 3: `src/generation/constraint_checker.py`

### What It Does

Provides a clean interface for running the hard constraint checks and correlation soft checks during and after persona generation. This is the runtime enforcement layer — it wraps the validators and can be called by the attribute filler mid-fill.

### Interface

```python
from src.schema.persona import PersonaRecord, Attribute
from src.taxonomy.base_taxonomy import KNOWN_CORRELATIONS

class ConstraintViolation:
    constraint_id: str      # e.g., "HC1", "CORR_1"
    constraint_type: str    # "hard" or "soft"
    description: str
    attr_a: str | None
    attr_b: str | None
    severity: str           # "blocking" (hard) | "tension" (soft)

class ConstraintChecker:

    def check_hard_constraints(
        self,
        persona: PersonaRecord,
    ) -> list[ConstraintViolation]:
        """
        Runs all 6 hard constraint checks (HC1–HC6).
        Returns list of violations — empty list means clean.
        Hard violations are blocking: the persona should not be accepted.
        """
        ...

    def check_correlation_consistency(
        self,
        attributes: dict[str, dict[str, Attribute]],
    ) -> list[ConstraintViolation]:
        """
        Checks KNOWN_CORRELATIONS from base taxonomy.
        For each (attr_a, attr_b, direction) pair:
        - If both attributes are present
        - And the direction is violated (both available as continuous values)
        - Flag as a soft constraint tension

        Threshold: positive pair violated if |a - b| > 0.5 and direction mismatch.
        Negative pair violated if (a + b > 1.5) — both are high when they should oppose.

        Returns list of soft violations. These are not blocking — they are logged as tensions.
        """
        ...

    def check_all(
        self,
        persona: PersonaRecord,
    ) -> tuple[list[ConstraintViolation], list[ConstraintViolation]]:
        """
        Returns (hard_violations, soft_violations).
        Convenience method that runs both checks.
        """
        ...
```

### Correlation Direction Logic

```python
# From KNOWN_CORRELATIONS:
# ("budget_consciousness", "deal_seeking_intensity", "positive")
# → Both should be high together or low together
# Violation: one is > 0.7 while the other is < 0.3

# ("brand_loyalty", "indie_brand_openness", "negative")
# → If one is high, the other should be low
# Violation: both > 0.65 simultaneously
```

Use a threshold of 0.65 for "high" and 0.35 for "low" in soft correlation checks.

### Note on Separation from Validators

`constraint_checker.py` is a runtime component (called during and after generation). `validators.py` is a post-hoc gate (called on a complete PersonaRecord). They share logic for HC1–HC6 but serve different callers:

- Attribute filler (Goose) calls `ConstraintChecker.check_correlation_consistency()` mid-fill.
- The generation pipeline calls `PersonaValidator.validate_all()` on the completed persona.

Do not merge these — keep the interfaces separate.

---

## Integration Contract

- **Imports from Cursor:** `from src.schema.persona import PersonaRecord, Attribute, ...`
- **Imports from Codex:** `from src.taxonomy.base_taxonomy import ANCHOR_ATTRIBUTES, KNOWN_CORRELATIONS`
- **Called by generation pipeline:** `PersonaValidator.validate_all(persona)` as gate before cohort assembly
- **Called by Goose mid-fill:** `ConstraintChecker.check_correlation_consistency(attributes)`

---

## Dependencies

- `numpy` for cosine distance computation in stratification
- No LLM calls in any of these files — purely deterministic

---

## Outcome File

When done, write `sprints/outcome_antigravity.md` with:
1. Files created (with line counts)
2. All 6 hard constraints implemented — confirm each HC# with a test case description
3. All 8 tendency-attribute rules implemented — confirm each TR# with a test case description
4. Stratification: result on a synthetic 20-persona pool targeting N=10 (report 5:3:2 breakdown)
5. Correlation soft check: which of KNOWN_CORRELATIONS were hardest to encode and why
6. Known gaps or edge cases not handled
