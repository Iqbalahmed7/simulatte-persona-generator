"""Tests for the Health & Wellness domain template (Sprint 12)."""
from __future__ import annotations


def test_hw_template_loads():
    """Health & Wellness domain attributes load without error."""
    from src.taxonomy.domain_templates.health_wellness import HEALTH_WELLNESS_DOMAIN_ATTRIBUTES
    assert HEALTH_WELLNESS_DOMAIN_ATTRIBUTES is not None
    assert len(HEALTH_WELLNESS_DOMAIN_ATTRIBUTES) > 0


def test_hw_template_attribute_count():
    """Template has at least 25 attributes."""
    from src.taxonomy.domain_templates.health_wellness import HEALTH_WELLNESS_DOMAIN_ATTRIBUTES
    count = len(HEALTH_WELLNESS_DOMAIN_ATTRIBUTES)
    assert count >= 25, f"Expected >=25 attributes, got {count}"


def test_hw_template_valid_defaults():
    """All attributes are continuous with population_prior in [0, 1]."""
    from src.taxonomy.domain_templates.health_wellness import HEALTH_WELLNESS_DOMAIN_ATTRIBUTES
    for attr in HEALTH_WELLNESS_DOMAIN_ATTRIBUTES:
        assert attr.attr_type == "continuous"
        # population_prior may have been converted to a dict by _domain_attr_definitions
        pp = attr.population_prior
        if isinstance(pp, dict):
            value = pp["value"]
        else:
            value = float(pp)
        assert 0.0 <= value <= 1.0, (
            f"{attr.name}: population_prior {value} out of [0, 1]"
        )


def test_hw_template_categories():
    """All four domain-specific categories are present."""
    from src.taxonomy.domain_templates.health_wellness import HEALTH_WELLNESS_DOMAIN_ATTRIBUTES
    categories = {attr.category for attr in HEALTH_WELLNESS_DOMAIN_ATTRIBUTES}
    assert "health_attitudes" in categories
    assert "health_behaviours" in categories
    assert "health_consumption" in categories
    assert "health_information" in categories


def test_template_loader_finds_hw():
    """health_wellness must be discoverable via DOMAIN_REGISTRY and load_taxonomy."""
    from src.taxonomy.domain_templates.template_loader import (
        DOMAIN_REGISTRY,
        get_domain_attributes,
        load_taxonomy,
    )
    assert "health_wellness" in DOMAIN_REGISTRY

    domain_attrs = get_domain_attributes("health_wellness")
    assert len(domain_attrs) >= 25

    merged = load_taxonomy("health_wellness")
    assert len(merged) > len(domain_attrs)


def test_hw_no_name_clashes_with_base_taxonomy():
    """No attribute name in the H&W template clashes with the base taxonomy."""
    from src.taxonomy.domain_templates.health_wellness import HEALTH_WELLNESS_DOMAIN_ATTRIBUTES
    from src.taxonomy.base_taxonomy import BASE_TAXONOMY

    base_names = {a.name for a in BASE_TAXONOMY}
    hw_names = {a.name for a in HEALTH_WELLNESS_DOMAIN_ATTRIBUTES}
    clashes = base_names & hw_names
    assert clashes == set(), f"Name clashes with base taxonomy: {clashes}"
