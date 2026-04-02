"""tests/test_assembler_grounding.py — Sprint 9 grounding integration tests.

Tests that assemble_cohort() correctly wires the grounding pipeline when
domain_data is provided, and preserves existing behaviour when it is not.

Gate validation is mocked to all-pass so these tests focus solely on the
grounding integration logic, not cohort diversity requirements.
"""
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Fixture: build a mock CohortGateRunner that always passes all gates
# ---------------------------------------------------------------------------

def _make_passing_gate_runner():
    """Return a MagicMock whose run_all() returns all-passing ValidationResults."""
    from src.schema.validators import ValidationResult

    mock_runner_instance = MagicMock()
    mock_runner_instance.run_all.return_value = [
        ValidationResult(passed=True, gate="G6"),
        ValidationResult(passed=True, gate="G7"),
        ValidationResult(passed=True, gate="G8"),
        ValidationResult(passed=True, gate="G9"),
        ValidationResult(passed=True, gate="G11"),
    ]
    mock_runner_cls = MagicMock(return_value=mock_runner_instance)
    return mock_runner_cls


# ---------------------------------------------------------------------------
# Test 1: assemble_cohort without domain_data unchanged
# ---------------------------------------------------------------------------

def test_assembler_without_domain_data():
    """No domain_data → existing behaviour unchanged. mode from persona."""
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    original_mode = persona.mode

    with patch("src.cohort.assembler.CohortGateRunner", _make_passing_gate_runner()):
        envelope = assemble_cohort([persona], domain="cpg")

    assert envelope.grounding_summary.domain_data_signals_extracted == 0
    assert envelope.grounding_summary.clusters_derived == 0
    assert envelope.taxonomy_used.domain_data_used is False
    assert envelope.mode == original_mode


# ---------------------------------------------------------------------------
# Test 2: assemble_cohort with domain_data → grounded
# ---------------------------------------------------------------------------

def test_assembler_with_domain_data_sets_grounded():
    """With domain_data: signals_extracted > 0, clusters > 0, domain_data_used True."""
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    domain_data = [
        "I switched brands because the price was too high.",
        "A trusted doctor recommended this product to me.",
        "Bought it after seeing a discount — worth it.",
        "My friend told me to try this and I switched.",
        "Too expensive — I rejected it completely.",
    ]

    with patch("src.cohort.assembler.CohortGateRunner", _make_passing_gate_runner()):
        envelope = assemble_cohort([persona], domain="cpg", domain_data=domain_data)

    assert envelope.grounding_summary.domain_data_signals_extracted > 0
    assert envelope.grounding_summary.clusters_derived > 0
    assert envelope.taxonomy_used.domain_data_used is True
    assert envelope.mode == "grounded"


# ---------------------------------------------------------------------------
# Test 3: GroundingSummary distribution sums to 1.0
# ---------------------------------------------------------------------------

def test_grounding_summary_distribution_sums_to_one():
    """tendency_source_distribution must sum to exactly 1.0."""
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    domain_data = [
        "Switched because of high price — avoided it.",
        "My expert doctor recommended switching to this brand.",
        "Bought on recommendation from a trusted peer.",
    ] * 5  # 15 texts

    with patch("src.cohort.assembler.CohortGateRunner", _make_passing_gate_runner()):
        envelope = assemble_cohort(
            [make_synthetic_persona()], domain="cpg", domain_data=domain_data
        )
    dist = envelope.grounding_summary.tendency_source_distribution
    total = sum(dist.values())
    assert abs(total - 1.0) < 1e-6, f"Distribution sums to {total}, not 1.0"
    # Must have all three keys
    assert set(dist.keys()) == {"grounded", "proxy", "estimated"}


# ---------------------------------------------------------------------------
# Test 4: Persona tendency source upgraded after grounding
# ---------------------------------------------------------------------------

def test_persona_tendency_source_upgraded():
    """At least one tendency should have source='grounded' after grounding."""
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    domain_data = [
        "I always switch when the price goes up — it's too expensive.",
        "A friend recommended this and I trusted them.",
        "Rejected it outright — cost too high.",
        "Expert review convinced me to buy.",
        "Switched to a cheaper brand after the price doubled.",
    ] * 4  # 20 texts

    with patch("src.cohort.assembler.CohortGateRunner", _make_passing_gate_runner()):
        envelope = assemble_cohort(
            [make_synthetic_persona()], domain="cpg", domain_data=domain_data
        )
    persona = envelope.personas[0]
    bt = persona.behavioural_tendencies
    sources = {
        bt.price_sensitivity.source,
        bt.trust_orientation.source,
        bt.switching_propensity.source,
    }
    assert "grounded" in sources, f"Expected grounded source. Got: {sources}"


# ---------------------------------------------------------------------------
# Test 5: assemble_cohort still raises on gate failure (unchanged behaviour)
# ---------------------------------------------------------------------------

def test_assembler_raises_on_empty_personas():
    """assemble_cohort([]) must still raise ValueError."""
    from src.cohort.assembler import assemble_cohort
    with pytest.raises(ValueError):
        assemble_cohort([], domain="cpg")
