"""tests/test_persona_registry.py — Sprint 30 · Antigravity test suite

Covers:
  - src/registry/persona_registry.py  (RegistryEntry, PersonaRegistry)
  - src/registry/registry_index.py    (age_band, build_demographics_index,
                                        query_index, domain_history, personas_by_domain)
  - src/registry/persona_regrounder.py (reground_for_domain, _downgrade_sources)
  - src/registry/cohort_manifest.py   (CohortManifest, save_manifest, load_manifest,
                                        make_manifest)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.registry.persona_registry import PersonaRegistry, RegistryEntry
from src.registry.registry_index import (
    age_band,
    build_demographics_index,
    domain_history,
    personas_by_domain,
    query_index,
)
from src.registry.persona_regrounder import _downgrade_sources, reground_for_domain
from src.registry.cohort_manifest import (
    CohortManifest,
    load_manifest,
    make_manifest,
    save_manifest,
)
from src.schema.persona import (
    Attribute,
    BehaviouralTendencies,
    CoreMemory,
    CopingMechanism,
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
    PersonaRecord,
    PriceSensitivityBand,
    RelationshipMap,
    SimulationState,
    TendencyBand,
    TrustOrientation,
    TrustWeights,
    WorkingMemory,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def make_minimal_persona(
    persona_id: str = "pg-test-001",
    domain: str = "cpg",
    age: int = 30,
    gender: str = "female",
    city_tier: str = "metro",
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
                ),
            }
        },
        derived_insights=DerivedInsights(
            decision_style="analytical",
            decision_style_score=0.7,
            trust_anchor="authority",
            risk_appetite="medium",
            primary_value_orientation="quality",
            coping_mechanism=CopingMechanism(
                type="research_deep_dive",
                description="Researches thoroughly",
            ),
            consistency_score=80,
            consistency_band="high",
            key_tensions=["price vs quality"],
        ),
        behavioural_tendencies=BehaviouralTendencies(
            price_sensitivity=PriceSensitivityBand(
                band="medium",
                description="moderate",
                source="grounded",
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
                band="low",
                description="loyal",
                source="grounded",
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
            first_person="I am...",
            third_person="She is...",
            display_name="Test",
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


def make_entry(
    persona_id: str = "pg-test-001",
    age: int = 30,
    gender: str = "female",
    city_tier: str = "metro",
    domain: str = "cpg",
    registered_at: str = "2026-01-01T00:00:00+00:00",
) -> RegistryEntry:
    return RegistryEntry(
        persona_id=persona_id,
        age=age,
        gender=gender,
        city_tier=city_tier,
        domain=domain,
        registered_at=registered_at,
    )


# ===========================================================================
# RegistryEntry
# ===========================================================================

def test_registry_entry_fields_accessible():
    entry = make_entry()
    assert entry.persona_id == "pg-test-001"
    assert entry.age == 30
    assert entry.gender == "female"
    assert entry.city_tier == "metro"
    assert entry.domain == "cpg"
    assert entry.registered_at == "2026-01-01T00:00:00+00:00"


def test_registry_entry_default_version():
    entry = make_entry()
    assert entry.version == "1.0"


def test_registry_entry_custom_version():
    entry = RegistryEntry(
        persona_id="pg-v2",
        age=25,
        gender="male",
        city_tier="tier2",
        domain="fmcg",
        registered_at="2026-01-02T00:00:00+00:00",
        version="2.5",
    )
    assert entry.version == "2.5"


# ===========================================================================
# PersonaRegistry — empty-state behaviour
# ===========================================================================

def test_list_all_empty_registry(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    assert registry.list_all() == []


def test_get_empty_registry_returns_none(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    assert registry.get("pg-nonexistent") is None


def test_find_empty_registry_returns_empty_list(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    assert registry.find() == []


# ===========================================================================
# PersonaRegistry — add()
# ===========================================================================

def test_add_returns_registry_entry(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    persona = make_minimal_persona()
    entry = registry.add(persona)
    assert isinstance(entry, RegistryEntry)


def test_add_entry_has_correct_persona_id(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    persona = make_minimal_persona(persona_id="pg-abc-001")
    entry = registry.add(persona)
    assert entry.persona_id == "pg-abc-001"


def test_add_entry_has_correct_age(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    persona = make_minimal_persona(age=42)
    entry = registry.add(persona)
    assert entry.age == 42


def test_add_entry_has_correct_gender(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    persona = make_minimal_persona(gender="male")
    entry = registry.add(persona)
    assert entry.gender == "male"


def test_add_entry_has_correct_city_tier(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    persona = make_minimal_persona(city_tier="tier2")
    entry = registry.add(persona)
    assert entry.city_tier == "tier2"


def test_add_entry_has_correct_domain(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    persona = make_minimal_persona(domain="fintech")
    entry = registry.add(persona)
    assert entry.domain == "fintech"


def test_add_increments_list_all(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    registry.add(make_minimal_persona())
    assert len(registry.list_all()) == 1


def test_add_multiple_increments_list_all(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    registry.add(make_minimal_persona(persona_id="pg-001"))
    registry.add(make_minimal_persona(persona_id="pg-002"))
    registry.add(make_minimal_persona(persona_id="pg-003"))
    assert len(registry.list_all()) == 3


def test_get_after_add_returns_persona_record(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    persona = make_minimal_persona(persona_id="pg-get-001")
    registry.add(persona)
    result = registry.get("pg-get-001")
    assert result is not None
    assert result.persona_id == "pg-get-001"


def test_add_idempotent_single_entry(tmp_path):
    """Adding the same persona_id twice should leave exactly 1 entry in index."""
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    persona = make_minimal_persona(persona_id="pg-idem-001")
    registry.add(persona)
    registry.add(persona)
    assert len(registry.list_all()) == 1


# ===========================================================================
# PersonaRegistry — find() filters
# ===========================================================================

def test_find_no_filters_returns_all(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    registry.add(make_minimal_persona(persona_id="pg-f1", age=28))
    registry.add(make_minimal_persona(persona_id="pg-f2", age=45))
    assert len(registry.find()) == 2


def test_find_age_min_filter(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    registry.add(make_minimal_persona(persona_id="pg-young", age=22))
    registry.add(make_minimal_persona(persona_id="pg-mid", age=35))
    registry.add(make_minimal_persona(persona_id="pg-old", age=55))
    results = registry.find(age_min=30)
    ids = [e.persona_id for e in results]
    assert "pg-mid" in ids
    assert "pg-old" in ids
    assert "pg-young" not in ids


def test_find_age_max_filter(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    registry.add(make_minimal_persona(persona_id="pg-young", age=22))
    registry.add(make_minimal_persona(persona_id="pg-mid", age=35))
    results = registry.find(age_max=30)
    ids = [e.persona_id for e in results]
    assert "pg-young" in ids
    assert "pg-mid" not in ids


def test_find_gender_filter(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    registry.add(make_minimal_persona(persona_id="pg-f", gender="female"))
    registry.add(make_minimal_persona(persona_id="pg-m", gender="male"))
    results = registry.find(gender="male")
    assert len(results) == 1
    assert results[0].persona_id == "pg-m"


def test_find_city_tier_filter(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    registry.add(make_minimal_persona(persona_id="pg-metro", city_tier="metro"))
    registry.add(make_minimal_persona(persona_id="pg-t2", city_tier="tier2"))
    results = registry.find(city_tier="tier2")
    assert len(results) == 1
    assert results[0].persona_id == "pg-t2"


def test_find_domain_filter(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    registry.add(make_minimal_persona(persona_id="pg-cpg", domain="cpg"))
    registry.add(make_minimal_persona(persona_id="pg-fin", domain="fintech"))
    results = registry.find(domain="fintech")
    assert len(results) == 1
    assert results[0].persona_id == "pg-fin"


# ===========================================================================
# PersonaRegistry — sync_from_json()
# ===========================================================================

def test_sync_from_json_adds_personas(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    personas = [
        make_minimal_persona(persona_id="pg-sync-001"),
        make_minimal_persona(persona_id="pg-sync-002"),
    ]
    json_file = tmp_path / "cohort.json"
    json_file.write_text(
        json.dumps([json.loads(p.model_dump_json()) for p in personas])
    )
    entries = registry.sync_from_json(json_file)
    assert len(entries) == 2


def test_sync_from_json_returns_registry_entries(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    persona = make_minimal_persona(persona_id="pg-sync-003")
    json_file = tmp_path / "cohort2.json"
    json_file.write_text(
        json.dumps([json.loads(persona.model_dump_json())])
    )
    entries = registry.sync_from_json(json_file)
    assert all(isinstance(e, RegistryEntry) for e in entries)


def test_sync_from_json_personas_retrievable(tmp_path):
    registry = PersonaRegistry(registry_path=tmp_path / "reg")
    persona = make_minimal_persona(persona_id="pg-sync-004")
    json_file = tmp_path / "cohort3.json"
    json_file.write_text(
        json.dumps([json.loads(persona.model_dump_json())])
    )
    registry.sync_from_json(json_file)
    result = registry.get("pg-sync-004")
    assert result is not None
    assert result.persona_id == "pg-sync-004"


# ===========================================================================
# registry_index — age_band()
# ===========================================================================

def test_age_band_under_25():
    assert age_band(24) == "<25"


def test_age_band_zero():
    assert age_band(0) == "<25"


def test_age_band_exactly_25():
    assert age_band(25) == "25-34"


def test_age_band_34():
    assert age_band(34) == "25-34"


def test_age_band_35():
    assert age_band(35) == "35-44"


def test_age_band_44():
    assert age_band(44) == "35-44"


def test_age_band_45():
    assert age_band(45) == "45-54"


def test_age_band_54():
    assert age_band(54) == "45-54"


def test_age_band_55():
    assert age_band(55) == "55+"


def test_age_band_80():
    assert age_band(80) == "55+"


# ===========================================================================
# registry_index — build_demographics_index()
# ===========================================================================

def test_build_demographics_index_correct_key():
    entries = [make_entry(age=30, city_tier="metro", gender="female")]
    index = build_demographics_index(entries)
    assert "25-34|metro|female" in index


def test_build_demographics_index_key_contains_persona_id():
    entries = [make_entry(persona_id="pg-key-001", age=30, city_tier="metro", gender="female")]
    index = build_demographics_index(entries)
    assert "pg-key-001" in index["25-34|metro|female"]


def test_build_demographics_index_multiple_entries_same_key():
    entries = [
        make_entry(persona_id="pg-a", age=30, city_tier="metro", gender="female"),
        make_entry(persona_id="pg-b", age=32, city_tier="metro", gender="female"),
    ]
    index = build_demographics_index(entries)
    bucket = index["25-34|metro|female"]
    assert "pg-a" in bucket
    assert "pg-b" in bucket


def test_build_demographics_index_different_keys():
    entries = [
        make_entry(persona_id="pg-m", age=30, city_tier="metro", gender="male"),
        make_entry(persona_id="pg-f", age=30, city_tier="metro", gender="female"),
    ]
    index = build_demographics_index(entries)
    assert "25-34|metro|male" in index
    assert "25-34|metro|female" in index


# ===========================================================================
# registry_index — query_index()
# ===========================================================================

def test_query_index_no_filters_returns_all():
    entries = [make_entry(persona_id="pg-q1"), make_entry(persona_id="pg-q2")]
    results = query_index(entries)
    assert len(results) == 2


def test_query_index_age_range_filter():
    entries = [
        make_entry(persona_id="pg-young", age=20),
        make_entry(persona_id="pg-mid",   age=35),
        make_entry(persona_id="pg-old",   age=60),
    ]
    results = query_index(entries, age_min=25, age_max=50)
    ids = [e.persona_id for e in results]
    assert "pg-mid" in ids
    assert "pg-young" not in ids
    assert "pg-old" not in ids


def test_query_index_gender_case_insensitive():
    entries = [
        make_entry(persona_id="pg-f", gender="Female"),
        make_entry(persona_id="pg-m", gender="male"),
    ]
    results = query_index(entries, gender="female")
    assert len(results) == 1
    assert results[0].persona_id == "pg-f"


def test_query_index_city_tier_case_insensitive():
    entries = [
        make_entry(persona_id="pg-metro", city_tier="Metro"),
        make_entry(persona_id="pg-t2",    city_tier="tier2"),
    ]
    results = query_index(entries, city_tier="metro")
    assert len(results) == 1
    assert results[0].persona_id == "pg-metro"


def test_query_index_domain_case_insensitive():
    entries = [
        make_entry(persona_id="pg-cpg", domain="CPG"),
        make_entry(persona_id="pg-fin", domain="fintech"),
    ]
    results = query_index(entries, domain="cpg")
    assert len(results) == 1
    assert results[0].persona_id == "pg-cpg"


def test_query_index_combined_filters():
    entries = [
        make_entry(persona_id="pg-match",   age=30, gender="female", city_tier="metro", domain="cpg"),
        make_entry(persona_id="pg-no-age",  age=50, gender="female", city_tier="metro", domain="cpg"),
        make_entry(persona_id="pg-no-dom",  age=30, gender="female", city_tier="metro", domain="fintech"),
    ]
    results = query_index(entries, age_max=40, gender="female", domain="cpg")
    assert len(results) == 1
    assert results[0].persona_id == "pg-match"


# ===========================================================================
# registry_index — domain_history()
# ===========================================================================

def test_domain_history_single_entry():
    entries = [make_entry(persona_id="pg-dh", domain="cpg", registered_at="2026-01-01T00:00:00+00:00")]
    history = domain_history(entries)
    assert "pg-dh" in history
    assert history["pg-dh"] == ["cpg"]


def test_domain_history_chronological_order():
    entries = [
        make_entry(persona_id="pg-x", domain="fmcg",    registered_at="2026-03-01T00:00:00+00:00"),
        make_entry(persona_id="pg-x", domain="fintech",  registered_at="2026-01-01T00:00:00+00:00"),
    ]
    history = domain_history(entries)
    # fintech (Jan) should come before fmcg (Mar)
    assert history["pg-x"][0] == "fintech"
    assert history["pg-x"][1] == "fmcg"


def test_domain_history_deduplicates_same_domain():
    entries = [
        make_entry(persona_id="pg-dup", domain="cpg", registered_at="2026-01-01T00:00:00+00:00"),
        make_entry(persona_id="pg-dup", domain="cpg", registered_at="2026-02-01T00:00:00+00:00"),
    ]
    history = domain_history(entries)
    assert history["pg-dup"] == ["cpg"]


# ===========================================================================
# registry_index — personas_by_domain()
# ===========================================================================

def test_personas_by_domain_match():
    entries = [
        make_entry(persona_id="pg-cpg-1", domain="cpg"),
        make_entry(persona_id="pg-fin-1", domain="fintech"),
    ]
    results = personas_by_domain(entries, "cpg")
    assert len(results) == 1
    assert results[0].persona_id == "pg-cpg-1"


def test_personas_by_domain_case_insensitive():
    entries = [
        make_entry(persona_id="pg-upper", domain="CPG"),
        make_entry(persona_id="pg-lower", domain="cpg"),
    ]
    results = personas_by_domain(entries, "cpg")
    assert len(results) == 2


def test_personas_by_domain_no_match():
    entries = [make_entry(persona_id="pg-fin", domain="fintech")]
    results = personas_by_domain(entries, "cpg")
    assert results == []


# ===========================================================================
# persona_regrounder — reground_for_domain()
# ===========================================================================

def test_reground_changes_domain():
    persona = make_minimal_persona(domain="cpg")
    regrounded = reground_for_domain(persona, "fintech")
    assert regrounded.domain == "fintech"


def test_reground_price_sensitivity_source_estimated():
    persona = make_minimal_persona()
    regrounded = reground_for_domain(persona, "fintech")
    assert regrounded.behavioural_tendencies.price_sensitivity.source == "estimated"


def test_reground_trust_orientation_source_estimated():
    persona = make_minimal_persona()
    regrounded = reground_for_domain(persona, "fintech")
    assert regrounded.behavioural_tendencies.trust_orientation.source == "estimated"


def test_reground_switching_propensity_source_estimated():
    persona = make_minimal_persona()
    regrounded = reground_for_domain(persona, "fintech")
    assert regrounded.behavioural_tendencies.switching_propensity.source == "estimated"


def test_reground_does_not_mutate_original():
    persona = make_minimal_persona(domain="cpg")
    reground_for_domain(persona, "fintech")
    assert persona.domain == "cpg"


def test_reground_original_price_sensitivity_source_unchanged():
    persona = make_minimal_persona()
    original_source = persona.behavioural_tendencies.price_sensitivity.source
    reground_for_domain(persona, "fintech")
    assert persona.behavioural_tendencies.price_sensitivity.source == original_source


def test_reground_persona_id_preserved():
    persona = make_minimal_persona(persona_id="pg-preserve-001")
    regrounded = reground_for_domain(persona, "fintech")
    assert regrounded.persona_id == "pg-preserve-001"


def test_reground_core_memory_preserved():
    persona = make_minimal_persona()
    original_identity = persona.memory.core.identity_statement
    regrounded = reground_for_domain(persona, "fintech")
    assert regrounded.memory.core.identity_statement == original_identity


def test_reground_returns_new_object():
    persona = make_minimal_persona()
    regrounded = reground_for_domain(persona, "fintech")
    assert regrounded is not persona


def test_reground_demographic_anchor_preserved():
    persona = make_minimal_persona(age=35, gender="male")
    regrounded = reground_for_domain(persona, "saas")
    assert regrounded.demographic_anchor.age == 35
    assert regrounded.demographic_anchor.gender == "male"


# ===========================================================================
# cohort_manifest — CohortManifest
# ===========================================================================

def test_cohort_manifest_fields():
    manifest = CohortManifest(
        cohort_id="lj-cohort-v3",
        domain="child-nutrition",
        icp_spec_hash="abc123",
        persona_ids=["pg-001", "pg-002"],
        snapshot_date="2026-04-03",
        registry_version="simulatte-v1.2",
    )
    assert manifest.cohort_id == "lj-cohort-v3"
    assert manifest.domain == "child-nutrition"
    assert manifest.icp_spec_hash == "abc123"
    assert manifest.persona_ids == ["pg-001", "pg-002"]
    assert manifest.snapshot_date == "2026-04-03"
    assert manifest.registry_version == "simulatte-v1.2"


def test_cohort_manifest_notes_default_empty():
    manifest = CohortManifest(
        cohort_id="c1",
        domain="cpg",
        icp_spec_hash="",
        persona_ids=[],
        snapshot_date="2026-04-03",
        registry_version="simulatte-v1.0",
    )
    assert manifest.notes == ""


# ===========================================================================
# cohort_manifest — make_manifest()
# ===========================================================================

def test_make_manifest_returns_cohort_manifest():
    manifest = make_manifest("lj-v1", "cpg", ["pg-001"])
    assert isinstance(manifest, CohortManifest)


def test_make_manifest_correct_cohort_id():
    manifest = make_manifest("test-cohort", "cpg", ["pg-001"])
    assert manifest.cohort_id == "test-cohort"


def test_make_manifest_correct_domain():
    manifest = make_manifest("test-cohort", "fintech", ["pg-001"])
    assert manifest.domain == "fintech"


def test_make_manifest_correct_persona_ids():
    ids = ["pg-001", "pg-002", "pg-003"]
    manifest = make_manifest("c", "cpg", ids)
    assert manifest.persona_ids == ids


def test_make_manifest_snapshot_date_today():
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    manifest = make_manifest("c", "cpg", [])
    assert manifest.snapshot_date == today


def test_make_manifest_snapshot_date_format():
    manifest = make_manifest("c", "cpg", [])
    parts = manifest.snapshot_date.split("-")
    assert len(parts) == 3
    assert len(parts[0]) == 4  # YYYY
    assert len(parts[1]) == 2  # MM
    assert len(parts[2]) == 2  # DD


def test_make_manifest_notes_default_empty():
    manifest = make_manifest("c", "cpg", [])
    assert manifest.notes == ""


def test_make_manifest_notes_custom():
    manifest = make_manifest("c", "cpg", [], notes="sprint 30 cohort")
    assert manifest.notes == "sprint 30 cohort"


# ===========================================================================
# cohort_manifest — save_manifest() + load_manifest() round-trip
# ===========================================================================

def test_save_and_load_manifest_round_trip(tmp_path):
    manifest = make_manifest(
        cohort_id="rt-cohort",
        domain="saas",
        persona_ids=["pg-rt-001", "pg-rt-002"],
        icp_spec_hash="deadbeef",
        registry_version="simulatte-v2.0",
        notes="round-trip test",
    )
    path = tmp_path / "manifests" / "rt_cohort.json"
    save_manifest(manifest, path)
    loaded = load_manifest(path)
    assert loaded.cohort_id == manifest.cohort_id
    assert loaded.domain == manifest.domain
    assert loaded.icp_spec_hash == manifest.icp_spec_hash
    assert loaded.registry_version == manifest.registry_version
    assert loaded.notes == manifest.notes
    assert loaded.snapshot_date == manifest.snapshot_date


def test_save_manifest_creates_parent_dirs(tmp_path):
    manifest = make_manifest("c", "cpg", [])
    nested = tmp_path / "deep" / "nested" / "dir" / "manifest.json"
    save_manifest(manifest, nested)
    assert nested.exists()


def test_loaded_manifest_persona_ids_match(tmp_path):
    ids = ["pg-a", "pg-b", "pg-c"]
    manifest = make_manifest("id-test", "cpg", ids)
    path = tmp_path / "id_test.json"
    save_manifest(manifest, path)
    loaded = load_manifest(path)
    assert loaded.persona_ids == ids


def test_save_manifest_writes_valid_json(tmp_path):
    manifest = make_manifest("json-test", "cpg", ["pg-001"])
    path = tmp_path / "json_test.json"
    save_manifest(manifest, path)
    raw = json.loads(path.read_text())
    assert raw["cohort_id"] == "json-test"
    assert isinstance(raw["persona_ids"], list)
