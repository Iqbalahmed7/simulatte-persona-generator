"""tests/test_icp_spec_grounded.py — Sprint 9

Tests for ICPSpec.domain_data field and GENERATOR_VERSION bump.
"""


def test_icp_spec_accepts_domain_data():
    from src.generation.identity_constructor import ICPSpec
    spec = ICPSpec(
        domain="cpg",
        mode="grounded",
        domain_data=["I bought this because it was affordable.", "Switched brands due to price."],
    )
    assert spec.domain_data is not None
    assert len(spec.domain_data) == 2
    assert spec.mode == "grounded"


def test_icp_spec_domain_data_defaults_to_none():
    from src.generation.identity_constructor import ICPSpec
    spec = ICPSpec(domain="saas", mode="quick")
    assert spec.domain_data is None


def test_icp_spec_backward_compatible():
    """Existing callers with no domain_data field still work."""
    from src.generation.identity_constructor import ICPSpec
    spec = ICPSpec(domain="cpg", mode="simulation-ready", persona_index=3)
    assert spec.persona_id_prefix == "default"
    assert spec.persona_index == 3
    assert spec.domain_data is None


def test_icp_spec_domain_data_empty_list():
    from src.generation.identity_constructor import ICPSpec
    spec = ICPSpec(domain="cpg", mode="grounded", domain_data=[])
    assert spec.domain_data == []


def test_generator_version_updated():
    from src.generation import identity_constructor
    assert identity_constructor.GENERATOR_VERSION == "2.1.0"
