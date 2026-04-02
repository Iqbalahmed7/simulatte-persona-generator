"""Tests for the SaaS domain — taxonomy, pool validation, and spec file (Sprint 13)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Valid schema Literal values sourced from src/schema/persona.py
# ---------------------------------------------------------------------------
_VALID_HOUSEHOLD_STRUCTURES = {"nuclear", "joint", "single-parent", "couple-no-kids", "other"}
_VALID_INCOME_BRACKETS = {"lower-middle", "middle", "upper-middle", "high", "affluent"}
_VALID_URBAN_TIERS = {"metro", "tier2", "tier3", "rural"}
_VALID_GENDERS = {"female", "male", "non-binary"}
_VALID_LIFE_STAGES = {
    "early-career", "mid-career", "late-career",
    "early-family", "student", "retired",
}
_VALID_EDUCATIONS = {"high-school", "undergraduate", "postgraduate", "doctoral"}
_VALID_EMPLOYMENTS = {
    "full-time", "part-time", "self-employed", "homemaker", "student", "retired"
}


def test_saas_taxonomy_loads():
    """load_taxonomy('saas') returns a non-empty list of AttributeDefinitions."""
    from src.taxonomy.domain_templates.template_loader import load_taxonomy

    taxonomy = load_taxonomy("saas")
    assert isinstance(taxonomy, list)
    assert len(taxonomy) > 0, "Expected at least 1 attribute in the SaaS taxonomy"


def test_saas_domain_attrs_load():
    """get_domain_attributes('saas') returns a non-empty list."""
    from src.taxonomy.domain_templates.template_loader import get_domain_attributes

    domain_attrs = get_domain_attributes("saas")
    assert isinstance(domain_attrs, list)
    assert len(domain_attrs) > 0, "Expected at least 1 domain-specific attribute for SaaS"


def test_saas_pool_structure_valid():
    """All Household.structure values in _SAAS_POOL are valid schema Literals."""
    from src.generation.demographic_sampler import _SAAS_POOL

    # pool tuple layout:
    # (name, age, gender, country, region, city, urban_tier,
    #  structure, size, income_bracket, dual_income,
    #  life_stage, education, employment)
    for entry in _SAAS_POOL:
        (name, age, gender, country, region, city, urban_tier,
         structure, size, income_bracket, dual_income,
         life_stage, education, employment) = entry

        assert structure in _VALID_HOUSEHOLD_STRUCTURES, (
            f"'{name}': invalid Household.structure '{structure}'. "
            f"Valid values: {sorted(_VALID_HOUSEHOLD_STRUCTURES)}"
        )
        assert 18 <= age <= 65, (
            f"'{name}': age {age} is outside expected range 18-65"
        )
        assert urban_tier in _VALID_URBAN_TIERS, (
            f"'{name}': invalid urban_tier '{urban_tier}'. "
            f"Valid values: {sorted(_VALID_URBAN_TIERS)}"
        )
        assert income_bracket in _VALID_INCOME_BRACKETS, (
            f"'{name}': invalid income_bracket '{income_bracket}'. "
            f"Valid values: {sorted(_VALID_INCOME_BRACKETS)}"
        )


def test_saas_sample_anchor():
    """sample_demographic_anchor('saas', 0) returns a valid DemographicAnchor instance."""
    from src.generation.demographic_sampler import sample_demographic_anchor
    from src.schema.persona import DemographicAnchor

    anchor = sample_demographic_anchor("saas", 0)
    assert isinstance(anchor, DemographicAnchor)
    assert anchor.name
    assert 18 <= anchor.age <= 65
    assert anchor.gender in _VALID_GENDERS
    assert anchor.location.urban_tier in _VALID_URBAN_TIERS
    assert anchor.household.structure in _VALID_HOUSEHOLD_STRUCTURES


def test_saas_spec_json_exists():
    """examples/spec_saas.json exists and is valid JSON with expected keys."""
    repo_root = Path(__file__).parent.parent
    spec_path = repo_root / "examples" / "spec_saas.json"

    assert spec_path.exists(), f"spec_saas.json not found at {spec_path}"

    with spec_path.open() as fh:
        data = json.load(fh)

    assert "persona_id_prefix" in data, "Missing key: persona_id_prefix"
    assert data["persona_id_prefix"] == "saas"
    assert "anchor_overrides" in data
    assert "domain_data" in data
