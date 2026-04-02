# SPRINT 5 BRIEF — ANTIGRAVITY
**Role:** Cohort Quality Gate Runner
**Sprint:** 5 — Cohort Assembly + Experiment Modularity
**Spec check:** Validity Protocol G6, G7, G8, G9, G11
**Previous rating:** 19/20

---

## Your Job This Sprint

One file: `CohortGateRunner` added to `src/schema/validators.py`. Implements G6, G7, G8, G9, G11 as a cohort-level gate runner that Cursor's `assemble_cohort()` calls.

Also write `tests/test_cohort.py` — synthetic cohort tests for all five gates.

---

## File 1: Add `CohortGateRunner` to `src/schema/validators.py`

### Interface

```python
from src.schema.persona import PersonaRecord
from src.cohort.diversity_checker import check_diversity
from src.cohort.distinctiveness import check_distinctiveness
from src.cohort.type_coverage import check_type_coverage

class CohortGateRunner:
    """Runs all cohort-level validation gates."""

    def run_all(
        self,
        personas: list[PersonaRecord],
    ) -> list[ValidationResult]:
        """
        Runs G6, G7, G8, G9, G11 in order.
        Returns list of ValidationResult (one per gate).
        """
        return [
            self.g6_distribution(personas),
            self.g7_distinctiveness(personas),
            self.g8_type_coverage(personas),
            self.g9_tension_completeness(personas),
            self.g11_tendency_source(personas),
        ]

    def g6_distribution(self, personas: list[PersonaRecord]) -> ValidationResult:
        """G6: No city >20%, no age bracket >40%, income spans >=3 brackets."""
        ...

    def g7_distinctiveness(self, personas: list[PersonaRecord]) -> ValidationResult:
        """G7: Mean pairwise cosine distance on 8 core attributes > 0.35."""
        ...

    def g8_type_coverage(self, personas: list[PersonaRecord]) -> ValidationResult:
        """G8: Type coverage per cohort size rules."""
        ...

    def g9_tension_completeness(self, personas: list[PersonaRecord]) -> ValidationResult:
        """G9: Every persona has >= 1 explicit tension in derived_insights.key_tensions."""
        ...

    def g11_tendency_source(self, personas: list[PersonaRecord]) -> ValidationResult:
        """G11: Every tendency field has source != None."""
        ...
```

### Gate Implementations

**G6** — delegate to `check_diversity(personas)`. Map failures to `ValidationResult(gate="G6", passed=result.passed, failures=result.failures, warnings=result.warnings)`.

**G7** — delegate to `check_distinctiveness(personas)`. If `result.passed` is False, failures = [f"Mean pairwise cosine distance {result.mean_pairwise_distance:.3f} is below threshold {result.threshold}. Most similar pair: {result.most_similar_pair}"].

**G8** — delegate to `check_type_coverage(personas)`. If not passed, failures = [f"Required {required} distinct types, found {len(present)}. Missing: {missing}"].

**G9** — iterate personas. For each: check `len(persona.derived_insights.key_tensions) >= 1`. Collect persona_ids that fail. Failures = [f"Persona {pid}: no tensions in derived_insights.key_tensions"].

**G11** — iterate personas. For each: check `persona.behavioural_tendencies` — all tendency sub-fields that have a `source` field must have `source` not None. Collect failures by persona_id and field name.

### Guard G11 against missing source field

Not all tendency sub-objects have a `source` field. Check only those that do:
```python
for field_name in ["price_sensitivity", "switching_propensity", "trust_orientation"]:
    obj = getattr(persona.behavioural_tendencies, field_name, None)
    if obj is not None and hasattr(obj, "source") and obj.source is None:
        failures.append(f"Persona {persona.persona_id}: {field_name}.source is None")
```

---

## File 2: `tests/test_cohort.py`

Write tests for all five gates using synthetic personas. Use `make_synthetic_persona()` from `tests/fixtures/synthetic_persona.py` as your base, then modify attributes for specific test cases.

### Required Tests

```python
class TestG6Distribution:
    def test_g6_passes_diverse_cohort(self): ...       # 5 personas, 5 cities, varied ages
    def test_g6_fails_city_concentration(self): ...    # 3/5 personas same city → >20% if city has 3/5 = 60%
    def test_g6_fails_age_concentration(self): ...     # 4/5 personas same age bracket → 80% > 40%
    def test_g6_fails_insufficient_income_brackets(self): ...  # all same income bracket

class TestG7Distinctiveness:
    def test_g7_passes_diverse_cohort(self): ...       # varied anchor attributes → distance > 0.35
    def test_g7_fails_identical_cohort(self): ...      # all same persona → distance 0.0 < 0.35
    def test_g7_identifies_most_similar_pair(self): ... # returns the right pair IDs

class TestG8TypeCoverage:
    def test_g8_passes_3_personas_3_types(self): ...
    def test_g8_fails_3_personas_2_types(self): ...
    def test_g8_passes_5_personas_4_types(self): ...
    def test_g8_fails_5_personas_3_types(self): ...

class TestG9TensionCompleteness:
    def test_g9_passes_all_have_tensions(self): ...
    def test_g9_fails_persona_with_no_tensions(self): ...  # override key_tensions=[]

class TestG11TendencySource:
    def test_g11_passes_all_sources_set(self): ...    # source="proxy" on all
    def test_g11_fails_null_source(self): ...         # override source=None on one tendency

class TestResetWorkingMemory:
    def test_reset_clears_working_fields(self): ...
    def test_reset_preserves_core_memory(self): ...
    def test_reset_is_idempotent(self): ...
```

Import `reset_working_memory` from `src.experiment.modality` for the reset tests.

---

## Integration Contract

- `CohortGateRunner` is imported by Cursor's `assemble_cohort`: `from src.schema.validators import CohortGateRunner`
- Import guards: wrap `check_diversity`, `check_distinctiveness`, `check_type_coverage` in try/except ImportError at the top of validators.py (parallel sprint build safety)
- `ValidationResult` already exists in `validators.py` — reuse it

---

## Outcome File

When done, write `sprints/outcome_antigravity.md` with:
1. Files modified/created
2. G9 and G11 — exact check logic (they're new gates, not delegated)
3. Test results table (pass/fail/skip counts)
4. Known gaps
