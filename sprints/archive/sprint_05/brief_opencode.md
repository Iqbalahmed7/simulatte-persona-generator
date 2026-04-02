# SPRINT 5 BRIEF — OPENCODE
**Role:** Cohort Diversity + Distinctiveness
**Sprint:** 5 — Cohort Assembly + Experiment Modularity
**Spec check:** Master Spec §11 (Diversity Metrics, Distinctiveness Metric)
**Previous rating:** 18/20

---

## Your Job This Sprint

Two files. You own the diversity distribution checks (G6) and cosine-distance distinctiveness enforcement (G7).

---

## File 1: `src/cohort/diversity_checker.py`

### What It Does

Checks that a cohort's demographic distribution satisfies G6 rules.

### Interface

```python
from src.schema.persona import PersonaRecord
from dataclasses import dataclass

@dataclass
class DiversityResult:
    passed: bool
    failures: list[str]
    warnings: list[str]
    city_distribution: dict[str, float]      # city → fraction
    age_distribution: dict[str, float]       # bracket → fraction
    income_distribution: dict[str, float]    # bracket → fraction

def check_diversity(personas: list[PersonaRecord]) -> DiversityResult:
    """
    G6 — Population Distribution checks:
    1. No city > 20% of cohort
    2. No age bracket > 40% of cohort
    3. Income spans >= 3 distinct brackets

    Also check from §11 Diversity Metrics table:
    4. No decision_style > 50% of cohort (warning, not failure)
    5. Trust anchor: >= 3 distinct anchors represented (warning, not failure)

    Rules 1-3 are failures. Rules 4-5 are warnings.
    """
    ...
```

### Age Brackets

```python
def _age_bracket(age: int) -> str:
    if age < 25: return "18-24"
    if age < 35: return "25-34"
    if age < 45: return "35-44"
    if age < 55: return "45-54"
    if age < 65: return "55-64"
    return "65+"
```

### Distribution Computation

```python
def _distribution(values: list[str]) -> dict[str, float]:
    """Compute fraction each unique value takes of total."""
    n = len(values)
    counts: dict[str, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return {k: c / n for k, c in counts.items()}
```

---

## File 2: `src/cohort/distinctiveness.py`

### What It Does

Computes mean pairwise cosine distance on the 8 anchor attributes across all persona pairs. Enforces G7 threshold > 0.35. Identifies the most similar pair for resampling if below threshold.

### Interface

```python
import math
from src.schema.persona import PersonaRecord

# The 8 anchor attributes (from §6 ANCHOR_ATTRS)
_ANCHOR_ATTRS = [
    "personality_type",       # categorical — encode as index
    "risk_tolerance",         # continuous 0-1
    "trust_orientation_primary",  # categorical
    "economic_constraint_level",  # continuous 0-1
    "life_stage_priority",    # categorical
    "primary_value_driver",   # categorical
    "social_orientation",     # continuous 0-1
    "tension_seed",           # categorical
]

@dataclass
class DistinctivenessResult:
    passed: bool
    mean_pairwise_distance: float
    threshold: float
    most_similar_pair: tuple[str, str] | None   # (persona_id_a, persona_id_b)
    failures: list[str]
    resample_attempts: int = 0

def check_distinctiveness(
    personas: list[PersonaRecord],
    threshold: float = 0.35,
) -> DistinctivenessResult:
    """
    G7 — Cohort Distinctiveness:
    Compute mean pairwise cosine distance on 8 anchor attributes.
    Threshold: > 0.35

    If below threshold:
    - Identify the most similar pair (lowest cosine distance)
    - Include their persona_ids in most_similar_pair for the assembler to resample

    Does NOT perform resampling — returns the result for the assembler to act on.
    """
    ...
```

### Vectorisation of Anchor Attributes

For categorical attributes, encode as integer index in a predefined vocab:

```python
_CATEGORICAL_VOCABS: dict[str, list[str]] = {
    "personality_type": ["analytical", "social", "habitual", "spontaneous"],
    "trust_orientation_primary": ["self", "peer", "expert", "brand", "authority", "community"],
    "life_stage_priority": ["career", "family", "personal_growth", "legacy", "survival"],
    "primary_value_driver": ["price", "quality", "brand", "convenience", "relationships", "status"],
    "tension_seed": [
        "aspiration_vs_constraint", "independence_vs_validation",
        "quality_vs_budget", "loyalty_vs_curiosity", "control_vs_delegation",
    ],
}

def _encode_anchor_vector(persona: PersonaRecord) -> list[float]:
    """
    Return an 8-element float vector for cosine distance computation.
    - Continuous attrs: use raw value (already 0-1)
    - Categorical attrs: encode as index/len(vocab) → normalised 0-1
    - Missing attr: default to 0.5
    """
    ...
```

### Cosine Distance

```python
def _cosine_distance(a: list[float], b: list[float]) -> float:
    """
    Returns 1 - cosine_similarity.
    Range: [0, 1]. Higher = more different.
    Guard against zero vectors (return 0.0 distance — identical).
    """
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return 1.0 - (dot / (mag_a * mag_b))
```

### Mean Pairwise Distance

```python
def _mean_pairwise_distance(vectors: list[list[float]]) -> float:
    """All pairs (i, j) where i < j. Return mean cosine distance."""
    n = len(vectors)
    if n < 2:
        return 0.0
    distances = []
    for i in range(n):
        for j in range(i + 1, n):
            distances.append(_cosine_distance(vectors[i], vectors[j]))
    return sum(distances) / len(distances)
```

---

## Outcome File

When done, write `sprints/outcome_opencode.md` with:
1. Files created (line counts)
2. G6 — show which rules are failures vs warnings
3. G7 — show the anchor vector encoding for one worked example
4. Known gaps (e.g. categorical vocab completeness, missing attribute handling)
