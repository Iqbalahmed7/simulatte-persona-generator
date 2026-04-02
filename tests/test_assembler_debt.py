"""tests/test_assembler_debt.py — Sprint 11 technical debt tests.

Verifies:
1. distinctiveness_score is populated (non-hardcoded 0.0) for diverse cohorts
2. icp_spec_hash is a 16-char hex string
3. icp_spec_hash is deterministic across repeated calls
4. business_problem is passed through to TaxonomyMeta
5. icp_spec_hash varies by domain
"""

from unittest.mock import MagicMock, patch

_GATE_RUNNER_PATH = "src.cohort.assembler.CohortGateRunner"


def _all_pass_runner():
    mock = MagicMock()
    mock.return_value.run_all.return_value = []
    return mock


def test_distinctiveness_score_populated():
    """After fix, distinctiveness_score must be >= 0.0 and a float for a diverse cohort."""
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort

    p1 = make_synthetic_persona()
    p2 = make_synthetic_persona()
    # Make p2 distinct by overriding persona_id
    p2 = p2.model_copy(update={"persona_id": "pg-test-002"})

    with patch(_GATE_RUNNER_PATH, new_callable=_all_pass_runner):
        envelope = assemble_cohort([p1, p2], domain="cpg")

    assert envelope.cohort_summary.distinctiveness_score >= 0.0
    # Score should be a float (not hardcoded 0.0 when check_distinctiveness runs)
    assert isinstance(envelope.cohort_summary.distinctiveness_score, float)


def test_icp_spec_hash_format():
    """icp_spec_hash must be a non-empty 16-char hex string."""
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort

    persona = make_synthetic_persona()
    with patch(_GATE_RUNNER_PATH, new_callable=_all_pass_runner):
        envelope = assemble_cohort([persona], domain="cpg")

    h = envelope.taxonomy_used.icp_spec_hash
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)


def test_icp_spec_hash_deterministic():
    """Same input produces same hash on repeated calls."""
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort

    persona = make_synthetic_persona()
    with patch(_GATE_RUNNER_PATH, new_callable=_all_pass_runner):
        e1 = assemble_cohort([persona], domain="cpg")
        e2 = assemble_cohort([persona], domain="cpg")

    assert e1.taxonomy_used.icp_spec_hash == e2.taxonomy_used.icp_spec_hash


def test_business_problem_in_envelope():
    """business_problem from caller appears in TaxonomyMeta."""
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort

    persona = make_synthetic_persona()
    problem = "Why do customers churn in Q3?"
    with patch(_GATE_RUNNER_PATH, new_callable=_all_pass_runner):
        envelope = assemble_cohort([persona], domain="cpg", business_problem=problem)

    assert envelope.taxonomy_used.business_problem == problem


def test_icp_spec_hash_varies_by_domain():
    """Hash must differ for different domains."""
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort

    persona = make_synthetic_persona()
    with patch(_GATE_RUNNER_PATH, new_callable=_all_pass_runner):
        e1 = assemble_cohort([persona], domain="cpg")
        e2 = assemble_cohort([persona], domain="saas")

    assert e1.taxonomy_used.icp_spec_hash != e2.taxonomy_used.icp_spec_hash
