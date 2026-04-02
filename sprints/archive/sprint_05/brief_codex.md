# SPRINT 5 BRIEF — CODEX
**Role:** Persona Type Coverage
**Sprint:** 5 — Cohort Assembly + Experiment Modularity
**Spec check:** Master Spec §11 (Persona Type System, Cohort Composition Rules)
**Previous rating:** 18/20

---

## Your Job This Sprint

One file: `type_coverage.py`. You own the 8-type classification system and cohort type-coverage enforcement gate (G8).

---

## File: `src/cohort/type_coverage.py`

### The 8 Persona Types (from §11)

```
1. The Pragmatist      — Low brand loyalty, high price sensitivity
2. The Loyalist        — High consistency, habitual decision style
3. The Aspirant        — Gap between self-concept and behaviour (aspiration_vs_constraint tension)
4. The Anxious Optimizer — High analytical style, low risk appetite
5. The Social Validator — Trust anchor: peer, social decision style
6. The Value Rebel     — Counter-cultural values, high independence
7. The Reluctant User  — Low satisfaction, moderate-high churn risk
8. The Power User      — High feature orientation, high consistency
```

### Interface

```python
from enum import Enum
from src.schema.persona import PersonaRecord, DerivedInsights, BehaviouralTendencies

class PersonaType(str, Enum):
    PRAGMATIST = "The Pragmatist"
    LOYALIST = "The Loyalist"
    ASPIRANT = "The Aspirant"
    ANXIOUS_OPTIMIZER = "The Anxious Optimizer"
    SOCIAL_VALIDATOR = "The Social Validator"
    VALUE_REBEL = "The Value Rebel"
    RELUCTANT_USER = "The Reluctant User"
    POWER_USER = "The Power User"

def classify_persona_type(persona: PersonaRecord) -> PersonaType:
    """
    Classify a persona into one of the 8 types using attribute signals.
    Rule-based. No LLM calls. Returns the single best-match type.
    """
    ...

def check_type_coverage(
    personas: list[PersonaRecord],
) -> tuple[bool, list[PersonaType], list[PersonaType]]:
    """
    Check cohort composition rules (G8):
    - 3 personas: >= 3 distinct types
    - 5 personas: >= 4 distinct types
    - 10 personas: all 8 types
    - 10+ personas: all 8 types

    Returns:
        (passed: bool, present_types: list, missing_types: list)
    """
    ...
```

### Classification Rules

Implement `classify_persona_type` using a scoring system. For each type, compute a score from 0–1 based on the attributes below. The type with the highest score wins.

**Pragmatist** — score from:
- `price_sensitivity.band` in ("high", "extreme") → +0.4
- `switching_propensity.band` in ("high", "extreme") → +0.3
- `brand_loyalty` attribute < 0.35 → +0.3

**Loyalist** — score from:
- `behavioural_tendencies.switching_propensity.band` in ("low", "very_low") → +0.4
- `derived_insights.decision_style` == "habitual" → +0.4
- `brand_loyalty` attribute > 0.75 → +0.2

**Aspirant** — score from:
- `tension_seed` attribute == "aspiration_vs_constraint" → +0.5
- `primary_value_driver` attribute in ("status", "brand") → +0.3
- `economic_constraint_level` attribute > 0.6 → +0.2

**Anxious Optimizer** — score from:
- `derived_insights.decision_style` == "analytical" → +0.4
- `risk_tolerance` attribute < 0.3 → +0.3
- `analysis_paralysis` attribute (if present) > 0.6 → +0.3

**Social Validator** — score from:
- `derived_insights.trust_anchor` == "peer" → +0.5
- `derived_insights.decision_style` == "social" → +0.3
- `social_proof_bias` attribute > 0.65 → +0.2

**Value Rebel** — score from:
- `tension_seed` attribute == "independence_vs_validation" → +0.3
- `social_orientation` attribute < 0.3 → +0.3
- `brand_loyalty` attribute < 0.25 → +0.2
- `primary_value_driver` attribute not in ("brand", "status") → +0.2

**Reluctant User** — score from:
- `switching_propensity.band` in ("high", "extreme") → +0.3
- `brand_loyalty` attribute < 0.4 → +0.2
- `tension_seed` attribute == "loyalty_vs_curiosity" → +0.3
- `risk_tolerance` attribute < 0.4 → +0.2

**Power User** — score from:
- `derived_insights.decision_style` == "analytical" → +0.2
- `brand_loyalty` attribute > 0.80 → +0.4
- `switching_propensity.band` in ("very_low", "low") → +0.4

### Attribute Access Pattern

```python
def _get_attr_value(persona: PersonaRecord, attr_name: str, default=None):
    """Safe attribute access across all categories."""
    for category in persona.attributes.values():
        if attr_name in category:
            return category[attr_name].value
    return default
```

Use this for all attribute reads. Attributes may be in any category dict.

### Cohort Size Rules

```python
_COVERAGE_RULES = {
    3: 3,   # >= 3 distinct types
    5: 4,   # >= 4 distinct types
    10: 8,  # all 8 types
}

def _required_types(n: int) -> int:
    if n >= 10:
        return 8
    return _COVERAGE_RULES.get(n, min(n, 8))
```

---

## Constraints

- No LLM calls. All classification is rule-based.
- A persona must always be classified as exactly one type (the highest-scoring one). Break ties by the enum order (first one wins).
- If no score is > 0 for any type (very sparse persona), default to `PersonaType.PRAGMATIST`.
- `check_type_coverage` must handle any cohort size N (not just 3, 5, 10).

---

## Outcome File

When done, write `sprints/outcome_codex.md` with:
1. Files created (line counts)
2. Classification rules — show the scoring table for all 8 types
3. `check_type_coverage` — show what it returns for N=3, 5, 10
4. Known gaps (e.g. attribute absence handling, score tie-breaking)
