"""tests/test_registry_integration.py — Sprint 31 · Antigravity test suite

Covers:
  - src/registry/registry_lookup.py   (classify_scenario, plan_reuse,
                                        DOMAIN_TAXONOMY_CLASSES, ReuseCandidate, ReusePlan)
  - src/registry/drift_detector.py    (DriftResult, detect_drift, filter_drifted)
  - src/registry/registry_assembler.py (RegistryAssemblyResult, assemble_from_registry)
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from src.registry.persona_registry import PersonaRegistry, RegistryEntry
from src.registry.registry_lookup import (
    DOMAIN_TAXONOMY_CLASSES,
    ReuseCandidate,
    ReusePlan,
    classify_scenario,
    plan_reuse,
)
from src.registry.drift_detector import DriftResult, detect_drift, filter_drifted
from src.registry.registry_assembler import RegistryAssemblyResult, assemble_from_registry
from src.schema.persona import PersonaRecord

# ---------------------------------------------------------------------------
# make_minimal_persona helper
# ---------------------------------------------------------------------------

from src.schema.persona import (
    Attribute,
    BehaviouralTendencies,
    CopingMechanism,
    CoreMemory,
    DemographicAnchor,
    DerivedInsights,
    Household,
    ImmutableConstraints,
    LifeDefiningEvent,
    LifeStory,
    Location,
    Memory,
    Narrative,
    Objection,
    PriceSensitivityBand,
    RelationshipMap,
    SimulationState,
    TendencyBand,
    TrustOrientation,
    TrustWeights,
    WorkingMemory,
)


def make_minimal_persona(
    persona_id="pg-test-001",
    domain="cpg",
    age=30,
    gender="female",
    city_tier="metro",
) -> PersonaRecord:
    return PersonaRecord(
        persona_id=persona_id,
        generated_at=datetime.now(timezone.utc),
        generator_version="test-1.0",
        domain=domain,
        mode="quick",
        demographic_anchor=DemographicAnchor(
            name="Test Persona",
            age=age,
            gender=gender,
            location=Location(
                country="India",
                region="Maharashtra",
                city="Mumbai",
                urban_tier=city_tier,
            ),
            household=Household(
                structure="nuclear",
                size=4,
                income_bracket="middle",
                dual_income=True,
            ),
            life_stage="young adult",
            education="undergraduate",
            employment="full-time",
        ),
        life_stories=[
            LifeStory(
                title="Career",
                when="2020",
                event="Got first job",
                lasting_impact="Became independent",
            ),
            LifeStory(
                title="Family",
                when="2015",
                event="Moved to city",
                lasting_impact="Urban mindset",
            ),
        ],
        attributes={
            "base": {
                "openness": Attribute(
                    value=0.7,
                    type="continuous",
                    label="Openness",
                    source="sampled",
                )
            }
        },
        derived_insights=DerivedInsights(
            decision_style="analytical",
            decision_style_score=0.7,
            trust_anchor="authority",
            risk_appetite="medium",
            primary_value_orientation="quality",
            coping_mechanism=CopingMechanism(
                type="research_deep_dive", description="Researches"
            ),
            consistency_score=80,
            consistency_band="high",
            key_tensions=["price vs quality"],
        ),
        behavioural_tendencies=BehaviouralTendencies(
            price_sensitivity=PriceSensitivityBand(
                band="medium", description="moderate", source="grounded"
            ),
            trust_orientation=TrustOrientation(
                weights=TrustWeights(
                    expert=0.5,
                    peer=0.2,
                    brand=0.1,
                    ad=0.05,
                    community=0.1,
                    influencer=0.05,
                ),
                dominant="expert",
                description="trusts experts",
                source="grounded",
            ),
            switching_propensity=TendencyBand(
                band="low", description="loyal", source="grounded"
            ),
            objection_profile=[
                Objection(
                    objection_type="price_vs_value",
                    likelihood="medium",
                    severity="friction",
                )
            ],
            reasoning_prompt="Think analytically.",
        ),
        narrative=Narrative(
            first_person="I am...", third_person="She is...", display_name="Test"
        ),
        decision_bullets=["Considers quality first"],
        memory=Memory(
            core=CoreMemory(
                identity_statement="A careful decision-maker",
                key_values=["quality", "trust", "value"],
                life_defining_events=[
                    LifeDefiningEvent(
                        age_when=25,
                        event="Career start",
                        lasting_impact="Ambition",
                    )
                ],
                relationship_map=RelationshipMap(
                    primary_decision_partner="spouse",
                    key_influencers=["doctor"],
                    trust_network=["family"],
                ),
                immutable_constraints=ImmutableConstraints(
                    budget_ceiling=None,
                    non_negotiables=["quality"],
                    absolute_avoidances=["counterfeit"],
                ),
                tendency_summary="Analytical and careful",
            ),
            working=WorkingMemory(
                observations=[],
                reflections=[],
                plans=[],
                brand_memories={},
                simulation_state=SimulationState(
                    current_turn=0,
                    importance_accumulator=0.0,
                    reflection_count=0,
                    awareness_set={},
                    consideration_set=[],
                    last_decision=None,
                ),
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def empty_registry(tmp_path):
    return PersonaRegistry(registry_path=tmp_path / "registry")


@pytest.fixture()
def populated_registry(tmp_path):
    """Registry containing 3 personas across different domains and demographics."""
    reg = PersonaRegistry(registry_path=tmp_path / "registry")
    reg.add(make_minimal_persona("pg-001", domain="cpg", age=28, gender="female", city_tier="metro"))
    reg.add(make_minimal_persona("pg-002", domain="cpg", age=35, gender="male", city_tier="tier2"))
    reg.add(make_minimal_persona("pg-003", domain="fintech", age=30, gender="female", city_tier="metro"))
    return reg


def _make_entry(persona_id="e-001", age=28, gender="female", city_tier="metro",
                domain="cpg", registered_at="2024-04-03T00:00:00+00:00"):
    """Build a SimpleNamespace that satisfies the drift_detector's duck-typed RegistryEntry."""
    return SimpleNamespace(
        persona_id=persona_id,
        age=age,
        gender=gender,
        city_tier=city_tier,
        domain=domain,
        registered_at=registered_at,
    )


# ===========================================================================
# Section 1: registry_lookup — classify_scenario
# ===========================================================================

class TestClassifyScenario:

    def test_exact_same_domain(self):
        assert classify_scenario("cpg", "cpg") == "same_domain"

    def test_same_domain_case_insensitive(self):
        assert classify_scenario("CPG", "cpg") == "same_domain"

    def test_same_domain_mixed_case(self):
        assert classify_scenario("Fintech", "fintech") == "same_domain"

    def test_adjacent_cpg_child_nutrition(self):
        assert classify_scenario("cpg", "child-nutrition") == "adjacent_domain"

    def test_adjacent_child_nutrition_cpg(self):
        assert classify_scenario("child-nutrition", "cpg") == "adjacent_domain"

    def test_adjacent_cpg_health_food(self):
        assert classify_scenario("health-food", "cpg") == "adjacent_domain"

    def test_adjacent_fintech_banking(self):
        assert classify_scenario("fintech", "banking") == "adjacent_domain"

    def test_adjacent_banking_insurance(self):
        assert classify_scenario("banking", "insurance") == "adjacent_domain"

    def test_adjacent_healthcare_wellness(self):
        assert classify_scenario("healthcare", "wellness") == "adjacent_domain"

    def test_adjacent_ecommerce_retail(self):
        assert classify_scenario("ecommerce", "retail") == "adjacent_domain"

    def test_adjacent_education_edtech(self):
        assert classify_scenario("education", "edtech") == "adjacent_domain"

    def test_adjacent_saas_b2b_saas(self):
        assert classify_scenario("saas", "b2b-saas") == "adjacent_domain"

    def test_different_domain_cpg_fintech(self):
        assert classify_scenario("cpg", "fintech") == "different_domain"

    def test_different_domain_healthcare_ecommerce(self):
        assert classify_scenario("healthcare", "ecommerce") == "different_domain"

    def test_different_domain_education_banking(self):
        assert classify_scenario("education", "banking") == "different_domain"

    def test_unknown_existing_domain(self):
        assert classify_scenario("some-unknown-vertical", "cpg") == "different_domain"

    def test_unknown_new_domain(self):
        assert classify_scenario("cpg", "some-unknown-vertical") == "different_domain"

    def test_both_unknown_domains(self):
        assert classify_scenario("unknown-a", "unknown-b") == "different_domain"

    def test_domain_taxonomy_classes_cpg_group(self):
        """Spot-check DOMAIN_TAXONOMY_CLASSES groups as a sanity check."""
        assert DOMAIN_TAXONOMY_CLASSES["cpg"] == DOMAIN_TAXONOMY_CLASSES["child-nutrition"]

    def test_domain_taxonomy_classes_financial_group(self):
        assert DOMAIN_TAXONOMY_CLASSES["fintech"] == DOMAIN_TAXONOMY_CLASSES["banking"]


# ===========================================================================
# Section 2: registry_lookup — plan_reuse
# ===========================================================================

class TestPlanReuse:

    def test_empty_registry_all_gap(self, empty_registry):
        plan = plan_reuse(empty_registry, 25, 35, "cpg", target_count=5)
        assert plan.gap_count == 5
        assert plan.candidates == []
        assert plan.target_count == 5

    def test_empty_registry_registry_match_count_zero(self, empty_registry):
        plan = plan_reuse(empty_registry, 25, 35, "cpg", target_count=3)
        assert plan.registry_match_count == 0

    def test_with_matching_personas_candidates_populated(self, populated_registry):
        # pg-001 (cpg, age 28, female, metro) and pg-002 (cpg, age 35, male, tier2)
        # both fall in 25–40 range
        plan = plan_reuse(populated_registry, 25, 40, "cpg", target_count=10)
        assert len(plan.candidates) > 0

    def test_gap_computed_correctly(self, populated_registry):
        plan = plan_reuse(populated_registry, 25, 40, "cpg", target_count=10)
        assert plan.gap_count == plan.target_count - len(plan.candidates)

    def test_candidates_capped_at_target_count(self, populated_registry):
        # Registry has 3 personas; request only 2
        plan = plan_reuse(populated_registry, 20, 40, "cpg", target_count=2)
        assert len(plan.candidates) <= 2

    def test_gap_zero_when_enough_matches(self, populated_registry):
        # All 3 personas fit the 20–40 range; request only 2
        plan = plan_reuse(populated_registry, 20, 40, "cpg", target_count=2)
        assert plan.gap_count == 0

    def test_age_filter_excludes_out_of_range(self, populated_registry):
        # pg-002 is age 35; only request 25–29
        plan = plan_reuse(populated_registry, 25, 29, "cpg", target_count=10)
        for c in plan.candidates:
            assert 25 <= c.age <= 29

    def test_gender_filter_applied(self, populated_registry):
        plan = plan_reuse(populated_registry, 20, 40, "cpg", target_count=10, icp_gender="male")
        for c in plan.candidates:
            assert c.gender == "male"

    def test_gender_filter_female(self, populated_registry):
        plan = plan_reuse(populated_registry, 20, 40, "cpg", target_count=10, icp_gender="female")
        for c in plan.candidates:
            assert c.gender == "female"

    def test_candidate_scenario_same_domain(self, populated_registry):
        plan = plan_reuse(populated_registry, 25, 30, "cpg", target_count=10)
        cpg_candidates = [c for c in plan.candidates if c.existing_domain == "cpg"]
        for c in cpg_candidates:
            assert c.scenario == "same_domain"

    def test_candidate_scenario_different_domain(self, populated_registry):
        # pg-003 is fintech; querying for cpg → different_domain
        plan = plan_reuse(populated_registry, 25, 35, "cpg", target_count=10)
        fintech_candidates = [c for c in plan.candidates if c.existing_domain == "fintech"]
        for c in fintech_candidates:
            assert c.scenario == "different_domain"

    def test_reuse_candidate_fields_accessible(self, populated_registry):
        plan = plan_reuse(populated_registry, 20, 40, "cpg", target_count=10)
        assert len(plan.candidates) > 0
        c = plan.candidates[0]
        assert hasattr(c, "persona_id")
        assert hasattr(c, "age")
        assert hasattr(c, "gender")
        assert hasattr(c, "city_tier")
        assert hasattr(c, "existing_domain")
        assert hasattr(c, "scenario")

    def test_reuse_plan_is_dataclass(self, empty_registry):
        plan = plan_reuse(empty_registry, 20, 40, "cpg", target_count=1)
        assert isinstance(plan, ReusePlan)


# ===========================================================================
# Section 3: drift_detector — detect_drift
# ===========================================================================

class TestDetectDrift:

    def test_current_age_computed_correctly_two_years(self):
        # Registered 2024-04-03, age 28. On 2026-04-03 should be 30.
        entry = _make_entry(age=28, registered_at="2024-04-03T00:00:00+00:00")
        result = detect_drift(entry, 25, 40, current_date=date(2026, 4, 3))
        assert result.current_age == 30

    def test_years_elapsed_is_float(self):
        entry = _make_entry(age=28, registered_at="2024-04-03T00:00:00+00:00")
        result = detect_drift(entry, 25, 40, current_date=date(2026, 4, 3))
        assert isinstance(result.years_elapsed, float)

    def test_years_elapsed_approximately_two(self):
        entry = _make_entry(age=28, registered_at="2024-04-03T00:00:00+00:00")
        result = detect_drift(entry, 25, 40, current_date=date(2026, 4, 3))
        assert 1.9 < result.years_elapsed < 2.1

    def test_no_drift_within_band(self):
        entry = _make_entry(age=28, registered_at="2024-04-03T00:00:00+00:00")
        result = detect_drift(entry, 25, 40, current_date=date(2026, 4, 3))
        assert result.is_drifted is False

    def test_drifted_when_current_age_exceeds_max(self):
        # Registered 5 years ago at 28 → current_age ≈ 33; ICP max is 30
        entry = _make_entry(age=28, registered_at="2019-04-03T00:00:00+00:00")
        result = detect_drift(entry, 25, 30, current_date=date(2026, 4, 3))
        assert result.is_drifted is True
        assert result.current_age > 30

    def test_drifted_when_current_age_below_min(self):
        # Registered 6 years ago at age 16 → current_age ≈ 22; ICP min is 25
        entry = _make_entry(age=16, registered_at="2020-04-03T00:00:00+00:00")
        result = detect_drift(entry, 25, 40, current_date=date(2026, 4, 3))
        assert result.is_drifted is True
        assert result.current_age < 25

    def test_drift_result_fields_accessible(self):
        entry = _make_entry(persona_id="test-persona", age=28,
                            registered_at="2024-04-03T00:00:00+00:00")
        result = detect_drift(entry, 25, 40, current_date=date(2026, 4, 3))
        assert result.persona_id == "test-persona"
        assert result.age_at_registration == 28
        assert isinstance(result.current_age, int)
        assert isinstance(result.is_drifted, bool)

    def test_drift_result_is_dataclass(self):
        entry = _make_entry(age=28, registered_at="2024-04-03T00:00:00+00:00")
        result = detect_drift(entry, 25, 40, current_date=date(2026, 4, 3))
        assert isinstance(result, DriftResult)

    def test_icp_bounds_stored_on_result(self):
        entry = _make_entry(age=28, registered_at="2024-04-03T00:00:00+00:00")
        result = detect_drift(entry, 22, 45, current_date=date(2026, 4, 3))
        assert result.icp_age_min == 22
        assert result.icp_age_max == 45

    def test_at_exact_upper_boundary_not_drifted(self):
        # Registered exactly 2 years ago at 28 → current_age exactly 30; max is 30
        entry = _make_entry(age=28, registered_at="2024-04-03T00:00:00+00:00")
        result = detect_drift(entry, 25, 30, current_date=date(2026, 4, 3))
        assert result.is_drifted is False

    def test_just_over_upper_boundary_drifted(self):
        # Registered 3 years ago at 28 → current_age 31; max is 30
        entry = _make_entry(age=28, registered_at="2023-04-03T00:00:00+00:00")
        result = detect_drift(entry, 25, 30, current_date=date(2026, 4, 3))
        assert result.is_drifted is True

    def test_recent_registration_no_age_change(self):
        # Registered same day — full years elapsed is 0, current_age == age
        today = date(2026, 4, 3)
        entry = _make_entry(age=32, registered_at="2026-04-03T00:00:00+00:00")
        result = detect_drift(entry, 25, 40, current_date=today)
        assert result.current_age == 32


# ===========================================================================
# Section 4: drift_detector — filter_drifted
# ===========================================================================

class TestFilterDrifted:

    def test_all_valid_drifted_list_empty(self):
        entries = [
            _make_entry("e-001", age=28, registered_at="2025-01-01T00:00:00+00:00"),
            _make_entry("e-002", age=30, registered_at="2025-06-01T00:00:00+00:00"),
        ]
        valid, drifted = filter_drifted(entries, 25, 40, current_date=date(2026, 4, 3))
        assert len(drifted) == 0
        assert len(valid) == 2

    def test_all_drifted_valid_list_empty(self):
        # Both registered 10 years ago at age 50 → current_age ≈ 60; max ICP is 40
        entries = [
            _make_entry("e-001", age=50, registered_at="2016-01-01T00:00:00+00:00"),
            _make_entry("e-002", age=50, registered_at="2016-06-01T00:00:00+00:00"),
        ]
        valid, drifted = filter_drifted(entries, 25, 40, current_date=date(2026, 4, 3))
        assert len(valid) == 0
        assert len(drifted) == 2

    def test_mixed_correct_split(self):
        # e-001: age 28, registered 2025-01-01 → current_age ~29, within 25-40 → valid
        # e-002: age 50, registered 2016-01-01 → current_age ~60, above 40 → drifted
        entries = [
            _make_entry("e-001", age=28, registered_at="2025-01-01T00:00:00+00:00"),
            _make_entry("e-002", age=50, registered_at="2016-01-01T00:00:00+00:00"),
        ]
        valid, drifted = filter_drifted(entries, 25, 40, current_date=date(2026, 4, 3))
        assert len(valid) == 1
        assert len(drifted) == 1
        assert valid[0].persona_id == "e-001"
        assert drifted[0].persona_id == "e-002"

    def test_empty_list_both_empty(self):
        valid, drifted = filter_drifted([], 25, 40, current_date=date(2026, 4, 3))
        assert valid == []
        assert drifted == []


# ===========================================================================
# Section 5: registry_assembler — assemble_from_registry
# ===========================================================================

class TestAssembleFromRegistry:

    def test_empty_registry_gap_equals_target(self, empty_registry):
        result = assemble_from_registry(
            empty_registry, 25, 40, "cpg", target_count=5,
            current_date=date(2026, 4, 3),
        )
        assert result.gap_count == 5
        assert result.target_count == 5

    def test_empty_registry_no_reused_personas(self, empty_registry):
        result = assemble_from_registry(
            empty_registry, 25, 40, "cpg", target_count=3,
            current_date=date(2026, 4, 3),
        )
        assert result.reused_personas == []

    def test_result_is_correct_type(self, empty_registry):
        result = assemble_from_registry(
            empty_registry, 25, 40, "cpg", target_count=2,
            current_date=date(2026, 4, 3),
        )
        assert isinstance(result, RegistryAssemblyResult)

    def test_same_domain_persona_counted(self, tmp_path):
        reg = PersonaRegistry(registry_path=tmp_path / "registry")
        reg.add(make_minimal_persona("pg-same", domain="cpg", age=30, gender="female", city_tier="metro"))
        result = assemble_from_registry(
            reg, 25, 40, "cpg", target_count=5,
            current_date=date(2026, 4, 3),
        )
        assert result.same_domain_count == 1
        assert result.gap_count == 4

    def test_same_domain_persona_not_regrounded(self, tmp_path):
        reg = PersonaRegistry(registry_path=tmp_path / "registry")
        reg.add(make_minimal_persona("pg-same", domain="cpg", age=30, gender="female", city_tier="metro"))
        result = assemble_from_registry(
            reg, 25, 40, "cpg", target_count=5,
            current_date=date(2026, 4, 3),
        )
        persona = result.reused_personas[0]
        assert persona.behavioural_tendencies.price_sensitivity.source == "grounded"
        assert persona.behavioural_tendencies.trust_orientation.source == "grounded"
        assert persona.behavioural_tendencies.switching_propensity.source == "grounded"

    def test_different_domain_persona_regrounded(self, tmp_path):
        reg = PersonaRegistry(registry_path=tmp_path / "registry")
        reg.add(make_minimal_persona("pg-diff", domain="fintech", age=30, gender="female", city_tier="metro"))
        result = assemble_from_registry(
            reg, 25, 40, "cpg", target_count=5,
            current_date=date(2026, 4, 3),
        )
        assert result.regrounded_count == 1
        persona = result.reused_personas[0]
        assert persona.behavioural_tendencies.price_sensitivity.source == "estimated"
        assert persona.behavioural_tendencies.trust_orientation.source == "estimated"
        assert persona.behavioural_tendencies.switching_propensity.source == "estimated"

    def test_different_domain_persona_domain_updated(self, tmp_path):
        reg = PersonaRegistry(registry_path=tmp_path / "registry")
        reg.add(make_minimal_persona("pg-diff", domain="fintech", age=30, gender="female", city_tier="metro"))
        result = assemble_from_registry(
            reg, 25, 40, "cpg", target_count=5,
            current_date=date(2026, 4, 3),
        )
        persona = result.reused_personas[0]
        assert persona.domain == "cpg"

    def test_reused_personas_are_persona_record_objects(self, tmp_path):
        reg = PersonaRegistry(registry_path=tmp_path / "registry")
        reg.add(make_minimal_persona("pg-001", domain="cpg", age=30, gender="female", city_tier="metro"))
        result = assemble_from_registry(
            reg, 25, 40, "cpg", target_count=5,
            current_date=date(2026, 4, 3),
        )
        for p in result.reused_personas:
            assert isinstance(p, PersonaRecord)

    def test_drift_filtered_count_reported(self, tmp_path):
        reg = PersonaRegistry(registry_path=tmp_path / "registry")
        # Register a persona whose index age falls within the ICP band (age=35),
        # then rewind registered_at so that the computed current age drifts above max.
        # Age 35 registered 10 years ago → current_age ≈ 45, which exceeds max=40.
        p = make_minimal_persona("pg-drift", domain="cpg", age=35, city_tier="metro")
        reg.add(p)
        import json
        index_path = tmp_path / "registry" / "index" / "registry_index.json"
        data = json.loads(index_path.read_text())
        # Keep age=35 (passes find filter for 25–40) but set old registered_at
        data[0]["registered_at"] = "2016-01-01T00:00:00+00:00"
        index_path.write_text(json.dumps(data))

        result = assemble_from_registry(
            reg, 25, 40, "cpg", target_count=5,
            current_date=date(2026, 4, 3),
        )
        assert result.drift_filtered_count >= 1

    def test_registry_match_count_gte_valid_entries(self, tmp_path):
        reg = PersonaRegistry(registry_path=tmp_path / "registry")
        reg.add(make_minimal_persona("pg-001", domain="cpg", age=30))
        reg.add(make_minimal_persona("pg-002", domain="cpg", age=32))
        result = assemble_from_registry(
            reg, 25, 40, "cpg", target_count=10,
            current_date=date(2026, 4, 3),
        )
        assert result.registry_match_count >= len(result.reused_personas)

    def test_gap_count_never_negative(self, tmp_path):
        reg = PersonaRegistry(registry_path=tmp_path / "registry")
        for i in range(5):
            reg.add(make_minimal_persona(f"pg-{i:03d}", domain="cpg", age=28 + i))
        result = assemble_from_registry(
            reg, 25, 40, "cpg", target_count=3,
            current_date=date(2026, 4, 3),
        )
        assert result.gap_count >= 0

    def test_target_count_preserved_on_result(self, empty_registry):
        result = assemble_from_registry(
            empty_registry, 25, 40, "cpg", target_count=7,
            current_date=date(2026, 4, 3),
        )
        assert result.target_count == 7
