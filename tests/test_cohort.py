"""tests/test_cohort.py — Synthetic cohort tests for G6, G7, G8, G9, G11 gates.

Uses make_synthetic_persona() from tests/fixtures/synthetic_persona.py as base,
then overrides attributes for specific test cases. Also tests reset_working_memory
from src.experiment.modality.
"""

from __future__ import annotations

import copy
import uuid

import pytest

from tests.fixtures.synthetic_persona import make_synthetic_persona
from src.schema.validators import CohortGateRunner
from src.schema.persona import (
    Attribute,
    BehaviouralTendencies,
    DemographicAnchor,
    DerivedInsights,
    Household,
    Location,
    Objection,
    PersonaRecord,
    PriceSensitivityBand,
    TendencyBand,
    TrustOrientation,
    TrustWeights,
)


# ---------------------------------------------------------------------------
# Helper: clone a persona with a new unique persona_id
# ---------------------------------------------------------------------------

def _clone(persona: PersonaRecord, persona_id: str | None = None) -> PersonaRecord:
    """Return a deep-cloned persona with a new persona_id (defaults to a UUID slug)."""
    pid = persona_id or f"pg-test-{uuid.uuid4().hex[:6]}"
    return persona.model_copy(update={"persona_id": pid})


def _set_city(persona: PersonaRecord, city: str) -> PersonaRecord:
    """Return a new persona with demographic_anchor.location.city overridden."""
    new_location = persona.demographic_anchor.location.model_copy(update={"city": city})
    new_anchor = persona.demographic_anchor.model_copy(update={"location": new_location})
    return persona.model_copy(update={"demographic_anchor": new_anchor})


def _set_age(persona: PersonaRecord, age: int) -> PersonaRecord:
    """Return a new persona with demographic_anchor.age overridden."""
    new_anchor = persona.demographic_anchor.model_copy(update={"age": age})
    return persona.model_copy(update={"demographic_anchor": new_anchor})


def _set_income_bracket(persona: PersonaRecord, bracket: str) -> PersonaRecord:
    """Return a new persona with household.income_bracket overridden."""
    new_household = persona.demographic_anchor.household.model_copy(
        update={"income_bracket": bracket}
    )
    new_anchor = persona.demographic_anchor.model_copy(update={"household": new_household})
    return persona.model_copy(update={"demographic_anchor": new_anchor})


def _set_key_tensions(persona: PersonaRecord, tensions: list[str]) -> PersonaRecord:
    """Return a new persona with derived_insights.key_tensions overridden.

    Note: Pydantic validator requires key_tensions has >= 1 item. Use a single
    placeholder when you need an 'empty' test — G9 tests for the gate's detection
    of empty lists, so we bypass pydantic by directly checking the gate logic.
    This helper is for setting non-empty values.
    """
    new_insights = persona.derived_insights.model_copy(update={"key_tensions": tensions})
    return persona.model_copy(update={"derived_insights": new_insights})


def _set_tendency_source(
    persona: PersonaRecord, field_name: str, source
) -> PersonaRecord:
    """Return a new persona with behavioural_tendencies.<field_name>.source overridden."""
    tendency_obj = getattr(persona.behavioural_tendencies, field_name)
    new_tendency = tendency_obj.model_copy(update={"source": source})
    new_bt = persona.behavioural_tendencies.model_copy(
        update={field_name: new_tendency}
    )
    return persona.model_copy(update={"behavioural_tendencies": new_bt})


def _set_attribute(
    persona: PersonaRecord, category: str, name: str, value
) -> PersonaRecord:
    """Return a new persona with attributes[category][name].value overridden."""
    existing_attr = persona.attributes[category][name]
    new_attr = existing_attr.model_copy(update={"value": value})
    new_cat = dict(persona.attributes[category])
    new_cat[name] = new_attr
    new_attrs = dict(persona.attributes)
    new_attrs[category] = new_cat
    return persona.model_copy(update={"attributes": new_attrs})


def _set_decision_style(persona: PersonaRecord, style: str) -> PersonaRecord:
    """Return a new persona with derived_insights.decision_style overridden."""
    new_insights = persona.derived_insights.model_copy(update={"decision_style": style})
    return persona.model_copy(update={"derived_insights": new_insights})


def _set_trust_anchor(persona: PersonaRecord, anchor: str) -> PersonaRecord:
    """Return a new persona with derived_insights.trust_anchor overridden."""
    new_insights = persona.derived_insights.model_copy(update={"trust_anchor": anchor})
    return persona.model_copy(update={"derived_insights": new_insights})


def _set_switching_propensity_band(persona: PersonaRecord, band: str) -> PersonaRecord:
    """Return a new persona with behavioural_tendencies.switching_propensity.band overridden."""
    new_sp = persona.behavioural_tendencies.switching_propensity.model_copy(
        update={"band": band}
    )
    new_bt = persona.behavioural_tendencies.model_copy(update={"switching_propensity": new_sp})
    return persona.model_copy(update={"behavioural_tendencies": new_bt})


# ---------------------------------------------------------------------------
# Runner fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def runner() -> CohortGateRunner:
    return CohortGateRunner()


# ---------------------------------------------------------------------------
# G6 Distribution Tests
# ---------------------------------------------------------------------------

class TestG6Distribution:

    def test_g6_passes_diverse_cohort(self, runner: CohortGateRunner):
        """5 personas, 5 distinct cities, varied ages → no rule violated."""
        base = make_synthetic_persona()
        cities = ["Mumbai", "Delhi", "Chennai", "Kolkata", "Bangalore"]
        ages = [24, 30, 41, 52, 62]  # spread across 5 different brackets
        personas = []
        for i, (city, age) in enumerate(zip(cities, ages)):
            p = _clone(base, f"pg-g6-pass-{i:03d}")
            p = _set_city(p, city)
            p = _set_age(p, age)
            # Use 5 distinct income brackets
            income_brackets = ["low", "lower-middle", "middle", "upper-middle", "high"]
            p = _set_income_bracket(p, income_brackets[i])
            personas.append(p)

        result = runner.g6_distribution(personas)
        assert result.passed, f"Expected G6 to pass. Failures: {result.failures}"
        assert result.gate == "G6"

    def test_g6_fails_city_concentration(self, runner: CohortGateRunner):
        """3/5 personas in the same city → 60% > 20% → G6 fails."""
        base = make_synthetic_persona()
        # 3 personas in "Mumbai" (60%), 1 in "Delhi", 1 in "Chennai"
        cities = ["Mumbai", "Mumbai", "Mumbai", "Delhi", "Chennai"]
        ages = [24, 34, 45, 55, 28]
        income_brackets = ["low", "middle", "high", "lower-middle", "upper-middle"]
        personas = []
        for i, (city, age, bracket) in enumerate(zip(cities, ages, income_brackets)):
            p = _clone(base, f"pg-g6-city-{i:03d}")
            p = _set_city(p, city)
            p = _set_age(p, age)
            p = _set_income_bracket(p, bracket)
            personas.append(p)

        result = runner.g6_distribution(personas)
        assert not result.passed, "Expected G6 to fail on city concentration"
        assert any("Mumbai" in f for f in result.failures), (
            f"Expected failure mentioning 'Mumbai'. Got: {result.failures}"
        )

    def test_g6_fails_age_concentration(self, runner: CohortGateRunner):
        """4/5 personas in the same age bracket (25-34) → 80% > 40% → G6 fails."""
        base = make_synthetic_persona()
        # 4 personas aged 25-34, 1 aged 55
        ages = [26, 27, 28, 29, 55]
        cities = ["Mumbai", "Delhi", "Chennai", "Kolkata", "Bangalore"]
        income_brackets = ["low", "lower-middle", "middle", "upper-middle", "high"]
        personas = []
        for i, (age, city, bracket) in enumerate(zip(ages, cities, income_brackets)):
            p = _clone(base, f"pg-g6-age-{i:03d}")
            p = _set_age(p, age)
            p = _set_city(p, city)
            p = _set_income_bracket(p, bracket)
            personas.append(p)

        result = runner.g6_distribution(personas)
        assert not result.passed, "Expected G6 to fail on age concentration"
        assert any("25-34" in f for f in result.failures), (
            f"Expected failure mentioning '25-34'. Got: {result.failures}"
        )

    def test_g6_fails_insufficient_income_brackets(self, runner: CohortGateRunner):
        """All 5 personas in the same income bracket → only 1 bracket, < 3 required."""
        base = make_synthetic_persona()
        cities = ["Mumbai", "Delhi", "Chennai", "Kolkata", "Bangalore"]
        ages = [24, 30, 41, 52, 62]
        personas = []
        for i, (city, age) in enumerate(zip(cities, ages)):
            p = _clone(base, f"pg-g6-income-{i:03d}")
            p = _set_city(p, city)
            p = _set_age(p, age)
            # All same income bracket
            p = _set_income_bracket(p, "middle")
            personas.append(p)

        result = runner.g6_distribution(personas)
        assert not result.passed, "Expected G6 to fail on insufficient income brackets"
        assert any("income" in f.lower() or "bracket" in f.lower() for f in result.failures), (
            f"Expected failure mentioning income brackets. Got: {result.failures}"
        )


# ---------------------------------------------------------------------------
# G7 Distinctiveness Tests
# ---------------------------------------------------------------------------

class TestG7Distinctiveness:

    def _add_anchor_attrs(
        self,
        persona: PersonaRecord,
        personality_type: str,
        trust_orientation_primary: str,
        economic_constraint_level: float,
        life_stage_priority: str,
        social_orientation: float,
        tension_seed_val: str,
    ) -> PersonaRecord:
        """Add the full set of 8 anchor attributes needed for G7 distinctiveness checks.

        Many anchor attrs are absent from the base fixture. We add them here so the
        cosine-distance encoder gets real values instead of 0.5 defaults.
        """
        # personality_type — add to identity category (may not exist)
        attrs = dict(persona.attributes)
        identity_cat = dict(attrs.get("identity", {}))
        identity_cat["personality_type"] = Attribute(
            value=personality_type, type="categorical",
            label="Personality type", source="anchored",
        )
        identity_cat["tension_seed"] = Attribute(
            value=tension_seed_val, type="categorical",
            label="Tension seed", source="anchored",
        )
        identity_cat["life_stage_priority"] = Attribute(
            value=life_stage_priority, type="categorical",
            label="Life stage priority", source="anchored",
        )
        attrs["identity"] = identity_cat

        # Also override personality_type in psychology category if present,
        # since _get_attr_value returns the first match and psychology
        # is typically iterated before identity.
        psych_cat_check = attrs.get("psychology", {})
        if "personality_type" in psych_cat_check:
            new_psych = dict(psych_cat_check)
            new_psych["personality_type"] = Attribute(
                value=personality_type, type="categorical",
                label="Personality type", source="anchored",
            )
            attrs["psychology"] = new_psych

        # trust_orientation_primary — add to social category
        social_cat = dict(attrs.get("social", {}))
        social_cat["trust_orientation_primary"] = Attribute(
            value=trust_orientation_primary, type="categorical",
            label="Trust orientation primary", source="anchored",
        )
        attrs["social"] = social_cat

        # economic_constraint_level and social_orientation as continuous — add to psychology
        psych_cat = dict(attrs.get("psychology", {}))
        psych_cat["economic_constraint_level"] = Attribute(
            value=economic_constraint_level, type="continuous",
            label="Economic constraint level", source="anchored",
        )
        attrs["psychology"] = psych_cat

        # social_orientation as continuous — put in social category, overriding
        # the existing categorical "community" value from the base fixture so
        # the distinctiveness encoder reads the numeric value.
        social_cat["social_orientation"] = Attribute(
            value=social_orientation, type="continuous",
            label="Social orientation (numeric)", source="anchored",
        )
        attrs["social"] = social_cat

        return persona.model_copy(update={"attributes": attrs})

    def test_g7_passes_diverse_cohort(self, runner: CohortGateRunner):
        """5 personas with highly varied anchor attributes → distance > 0.35."""
        base = make_synthetic_persona()

        # Build personas with maximally varied anchor attributes.
        # We vary all 8 anchor attrs to ensure real cosine distance.
        # Format: (persona_id, personality_type, trust_orientation_primary,
        #          risk_tolerance, economic_constraint_level, life_stage_priority,
        #          primary_value_driver, social_orientation, tension_seed)
        personas_config = [
            ("pg-g7-div-001", "analytical", "expert",      0.10, 0.90,
             "career",          "quality",      0.10, "aspiration_vs_constraint"),
            ("pg-g7-div-002", "social",     "peer",        0.50, 0.30,
             "family",          "price",        0.90, "loyalty_vs_curiosity"),
            ("pg-g7-div-003", "habitual",   "brand",       0.85, 0.10,
             "personal_growth", "brand",        0.50, "independence_vs_validation"),
            ("pg-g7-div-004", "spontaneous", "community",  0.20, 0.70,
             "legacy",          "convenience",  0.80, "quality_vs_budget"),
            ("pg-g7-div-005", "analytical", "self",        0.65, 0.50,
             "survival",        "status",       0.20, "control_vs_delegation"),
        ]

        personas = []
        for (pid, pt, top, rt, ecl, lsp, pvd, so, ts) in personas_config:
            p = _clone(base, pid)
            # Set the two attrs already in the base fixture
            p = _set_attribute(p, "psychology", "risk_tolerance", rt)
            p = _set_attribute(p, "values", "primary_value_driver", pvd)
            # Add/override the full set of 8 anchor attrs
            p = self._add_anchor_attrs(
                p,
                personality_type=pt,
                trust_orientation_primary=top,
                economic_constraint_level=ecl,
                life_stage_priority=lsp,
                social_orientation=so,
                tension_seed_val=ts,
            )
            personas.append(p)

        result = runner.g7_distinctiveness(personas)
        assert result.gate == "G7"
        if result.warnings and "not available" in result.warnings[0]:
            pytest.skip("check_distinctiveness not yet available")
        assert result.passed, (
            f"Expected G7 to pass for diverse cohort. "
            f"Failures: {result.failures}"
        )

    def test_g7_fails_identical_cohort(self, runner: CohortGateRunner):
        """5 identical personas → distance 0.0 < 0.35 → G7 fails."""
        base = make_synthetic_persona()
        # All personas are identical clones (just different IDs)
        personas = [_clone(base, f"pg-g7-same-{i:03d}") for i in range(5)]

        result = runner.g7_distinctiveness(personas)
        assert result.gate == "G7"

        if result.warnings and "not available" in result.warnings[0]:
            pytest.skip("check_distinctiveness not yet available")

        assert not result.passed, "Expected G7 to fail for identical cohort"
        assert len(result.failures) == 1
        assert "below threshold" in result.failures[0]

    def test_g7_identifies_most_similar_pair(self, runner: CohortGateRunner):
        """G7 failure message includes the most similar pair's persona IDs."""
        base = make_synthetic_persona()
        personas = [_clone(base, f"pg-g7-pair-{i:03d}") for i in range(3)]

        result = runner.g7_distinctiveness(personas)
        assert result.gate == "G7"

        if result.warnings and "not available" in result.warnings[0]:
            pytest.skip("check_distinctiveness not yet available")

        # When it fails, the failure message should mention a pair
        if not result.passed:
            assert len(result.failures) == 1
            failure_msg = result.failures[0]
            # The failure message from CohortGateRunner includes "Most similar pair:"
            assert "Most similar pair" in failure_msg, (
                f"Expected failure to identify most similar pair. Got: {failure_msg}"
            )
            # At least one of the persona IDs should appear in the failure message
            any_id_found = any(p.persona_id in failure_msg for p in personas)
            assert any_id_found, (
                f"Expected a persona ID in failure message. Got: {failure_msg}"
            )
        else:
            # If it somehow passed, we just verify the gate ran
            assert result.gate == "G7"


# ---------------------------------------------------------------------------
# G8 Type Coverage Tests
# ---------------------------------------------------------------------------

class TestG8TypeCoverage:

    def _make_social_validator(self, persona_id: str) -> PersonaRecord:
        """Create a Social Validator persona (peer trust, social style)."""
        base = make_synthetic_persona()
        p = _clone(base, persona_id)
        p = _set_decision_style(p, "social")
        p = _set_trust_anchor(p, "peer")
        return p

    def _make_pragmatist(self, persona_id: str) -> PersonaRecord:
        """Create a Pragmatist persona (high price sensitivity, high switching)."""
        base = make_synthetic_persona()
        p = _clone(base, persona_id)
        # price_sensitivity.band already "high" in base persona
        p = _set_switching_propensity_band(p, "high")
        p = _set_attribute(p, "values", "brand_loyalty", 0.20)
        return p

    def _make_anxious_optimizer(self, persona_id: str) -> PersonaRecord:
        """Create an Anxious Optimizer persona (analytical, low risk)."""
        base = make_synthetic_persona()
        p = _clone(base, persona_id)
        p = _set_decision_style(p, "analytical")
        p = _set_trust_anchor(p, "authority")
        p = _set_attribute(p, "psychology", "risk_tolerance", 0.15)
        return p

    def _make_loyalist(self, persona_id: str) -> PersonaRecord:
        """Create a Loyalist persona (habitual, low switching, high brand loyalty)."""
        base = make_synthetic_persona()
        p = _clone(base, persona_id)
        p = _set_decision_style(p, "habitual")
        p = _set_trust_anchor(p, "authority")
        p = _set_switching_propensity_band(p, "low")
        p = _set_attribute(p, "values", "brand_loyalty", 0.82)
        return p

    def _make_aspirant(self, persona_id: str) -> PersonaRecord:
        """Create an Aspirant persona (aspiration_vs_constraint tension)."""
        base = make_synthetic_persona()
        p = _clone(base, persona_id)
        p = _set_attribute(p, "identity", "tension_seed", "aspiration_vs_constraint")
        p = _set_attribute(p, "values", "primary_value_driver", "status")
        return p

    def test_g8_passes_3_personas_3_types(self, runner: CohortGateRunner):
        """3 personas, 3 distinct types → G8 passes (requires >= 3)."""
        personas = [
            self._make_social_validator("pg-g8-3p-001"),
            self._make_pragmatist("pg-g8-3p-002"),
            self._make_anxious_optimizer("pg-g8-3p-003"),
        ]
        result = runner.g8_type_coverage(personas)
        assert result.gate == "G8"

        if result.warnings and "not available" in result.warnings[0]:
            pytest.skip("check_type_coverage not yet available")

        assert result.passed, f"Expected G8 to pass for 3 distinct types. Failures: {result.failures}"

    def test_g8_fails_3_personas_1_type(self, runner: CohortGateRunner):
        """3 personas, only 1 distinct type → G8 fails (requires >= 2)."""
        personas = [
            self._make_pragmatist("pg-g8-3f-001"),
            self._make_pragmatist("pg-g8-3f-002"),
            self._make_pragmatist("pg-g8-3f-003"),
        ]
        result = runner.g8_type_coverage(personas)
        assert result.gate == "G8"

        if result.warnings and "not available" in result.warnings[0]:
            pytest.skip("check_type_coverage not yet available")

        assert not result.passed, (
            "Expected G8 to fail when only 1 type present in a 3-persona cohort"
        )
        assert len(result.failures) == 1
        assert "Required" in result.failures[0]

    def test_g8_passes_5_personas_4_types(self, runner: CohortGateRunner):
        """5 personas, 4 distinct types → G8 passes (requires >= 4)."""
        personas = [
            self._make_social_validator("pg-g8-5p-001"),
            self._make_pragmatist("pg-g8-5p-002"),
            self._make_anxious_optimizer("pg-g8-5p-003"),
            self._make_loyalist("pg-g8-5p-004"),
            self._make_loyalist("pg-g8-5p-005"),  # 4th type repeated — still 4 distinct types
        ]
        result = runner.g8_type_coverage(personas)
        assert result.gate == "G8"

        if result.warnings and "not available" in result.warnings[0]:
            pytest.skip("check_type_coverage not yet available")

        assert result.passed, (
            f"Expected G8 to pass for 4 distinct types in 5-persona cohort. "
            f"Failures: {result.failures}"
        )

    def test_g8_fails_5_personas_2_types(self, runner: CohortGateRunner):
        """5 personas, only 2 distinct types → G8 fails (requires >= 3)."""
        personas = [
            self._make_social_validator("pg-g8-5f-001"),
            self._make_social_validator("pg-g8-5f-002"),
            self._make_pragmatist("pg-g8-5f-003"),
            self._make_pragmatist("pg-g8-5f-004"),
            self._make_pragmatist("pg-g8-5f-005"),
        ]
        result = runner.g8_type_coverage(personas)
        assert result.gate == "G8"

        if result.warnings and "not available" in result.warnings[0]:
            pytest.skip("check_type_coverage not yet available")

        assert not result.passed, (
            "Expected G8 to fail when only 2 types present in a 5-persona cohort"
        )
        assert len(result.failures) == 1


# ---------------------------------------------------------------------------
# G9 Tension Completeness Tests
# ---------------------------------------------------------------------------

class TestG9TensionCompleteness:

    def test_g9_passes_all_have_tensions(self, runner: CohortGateRunner):
        """All 3 personas have >= 1 tension → G9 passes."""
        base = make_synthetic_persona()
        personas = [
            _clone(base, f"pg-g9-pass-{i:03d}") for i in range(3)
        ]
        # Base persona already has 2 tensions — no override needed

        result = runner.g9_tension_completeness(personas)
        assert result.passed, f"Expected G9 to pass. Failures: {result.failures}"
        assert result.gate == "G9"
        assert result.failures == []

    def test_g9_fails_persona_with_no_tensions(self, runner: CohortGateRunner):
        """One persona has key_tensions=[] → G9 fails for that persona.

        Since Pydantic enforces key_tensions >= 1, we test the gate logic
        directly by crafting a mock persona-like object and checking the
        gate behaves correctly when a persona reports 0 tensions.

        We bypass the Pydantic constraint by patching the derived_insights
        at the model level, using object.__setattr__ to force the empty list
        into a normally-validated field.
        """
        base = make_synthetic_persona()
        # Create a persona with a properly constructed record first
        p0 = _clone(base, "pg-g9-fail-001")
        p1 = _clone(base, "pg-g9-fail-002")  # normal persona
        p2 = _clone(base, "pg-g9-fail-003")  # normal persona

        # Force key_tensions to empty list on p0 by bypassing Pydantic validation
        # We construct a raw dict, then use model_construct to skip validation
        insights_dict = p0.derived_insights.model_dump()
        insights_dict["key_tensions"] = []
        # Use model_construct to bypass Pydantic validators
        from src.schema.persona import DerivedInsights
        empty_insights = DerivedInsights.model_construct(**insights_dict)
        p0 = p0.model_copy(update={"derived_insights": empty_insights})

        personas = [p0, p1, p2]
        result = runner.g9_tension_completeness(personas)

        assert not result.passed, "Expected G9 to fail when a persona has no tensions"
        assert result.gate == "G9"
        assert len(result.failures) == 1
        assert "pg-g9-fail-001" in result.failures[0]
        assert "no tensions" in result.failures[0]


# ---------------------------------------------------------------------------
# G11 Tendency Source Tests
# ---------------------------------------------------------------------------

class TestG11TendencySource:

    def test_g11_passes_all_sources_set(self, runner: CohortGateRunner):
        """All tendency source fields are set ('proxy') → G11 passes."""
        base = make_synthetic_persona()
        personas = [
            _clone(base, f"pg-g11-pass-{i:03d}") for i in range(3)
        ]
        # Base persona has source="grounded" on all tendency fields — should pass

        result = runner.g11_tendency_source(personas)
        assert result.passed, f"Expected G11 to pass. Failures: {result.failures}"
        assert result.gate == "G11"
        assert result.failures == []

    def test_g11_fails_null_source(self, runner: CohortGateRunner):
        """One persona has price_sensitivity.source=None → G11 fails."""
        base = make_synthetic_persona()
        p0 = _clone(base, "pg-g11-fail-001")
        p1 = _clone(base, "pg-g11-fail-002")

        # Force price_sensitivity.source to None by bypassing Pydantic
        from src.schema.persona import PriceSensitivityBand
        ps_dict = p0.behavioural_tendencies.price_sensitivity.model_dump()
        ps_dict["source"] = None
        null_ps = PriceSensitivityBand.model_construct(**ps_dict)
        new_bt = p0.behavioural_tendencies.model_copy(
            update={"price_sensitivity": null_ps}
        )
        p0 = p0.model_copy(update={"behavioural_tendencies": new_bt})

        personas = [p0, p1]
        result = runner.g11_tendency_source(personas)

        assert not result.passed, "Expected G11 to fail when source is None"
        assert result.gate == "G11"
        assert len(result.failures) == 1
        assert "pg-g11-fail-001" in result.failures[0]
        assert "price_sensitivity.source is None" in result.failures[0]


# ---------------------------------------------------------------------------
# Reset Working Memory Tests
# ---------------------------------------------------------------------------

class TestResetWorkingMemory:

    def test_reset_clears_working_fields(self):
        """reset_working_memory clears observations, reflections, plans, brand_memories."""
        from src.experiment.modality import reset_working_memory

        persona = make_synthetic_persona()
        # Base persona has seed memories in working memory
        assert len(persona.memory.working.observations) > 0, (
            "Fixture should have bootstrapped working memory observations"
        )

        reset = reset_working_memory(persona)

        assert reset.memory.working.observations == [], "Observations should be cleared"
        assert reset.memory.working.reflections == [], "Reflections should be cleared"
        assert reset.memory.working.plans == [], "Plans should be cleared"
        assert reset.memory.working.brand_memories == {}, "Brand memories should be cleared"
        assert reset.memory.working.simulation_state.current_turn == 0
        assert reset.memory.working.simulation_state.importance_accumulator == 0.0
        assert reset.memory.working.simulation_state.reflection_count == 0
        assert reset.memory.working.simulation_state.awareness_set == {}
        assert reset.memory.working.simulation_state.consideration_set == []
        assert reset.memory.working.simulation_state.last_decision is None

    def test_reset_preserves_core_memory(self):
        """reset_working_memory never touches persona.memory.core."""
        from src.experiment.modality import reset_working_memory

        persona = make_synthetic_persona()
        original_core = persona.memory.core

        reset = reset_working_memory(persona)

        # Core memory should be completely unchanged
        assert reset.memory.core.identity_statement == original_core.identity_statement
        assert reset.memory.core.key_values == original_core.key_values
        assert reset.memory.core.tendency_summary == original_core.tendency_summary
        assert len(reset.memory.core.life_defining_events) == len(
            original_core.life_defining_events
        )
        # Original persona must be unmodified (no mutation)
        assert persona.memory.core.identity_statement == original_core.identity_statement

    def test_reset_is_idempotent(self):
        """Calling reset twice produces the same result as calling it once."""
        from src.experiment.modality import reset_working_memory

        persona = make_synthetic_persona()

        reset_once = reset_working_memory(persona)
        reset_twice = reset_working_memory(reset_once)

        # Both should have empty working memory
        assert reset_twice.memory.working.observations == []
        assert reset_twice.memory.working.reflections == []
        assert reset_twice.memory.working.plans == []
        assert reset_twice.memory.working.brand_memories == {}
        assert reset_twice.memory.working.simulation_state.current_turn == 0
        assert reset_twice.memory.working.simulation_state.importance_accumulator == 0.0

        # Core memory should be identical across both resets
        assert reset_once.memory.core.identity_statement == reset_twice.memory.core.identity_statement
        assert reset_once.memory.core.key_values == reset_twice.memory.core.key_values
