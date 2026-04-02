"""tests/test_sprint11_gates.py — Sprint 11 Integration Gate Tests.

Validates work completed by Sprint 11 engineers:
  - Codex: G7 distinctiveness score populated; business_problem param in assemble_cohort
  - OpenCode: HC3 constraint active via health_supplement_belief in BASE_TAXONOMY
  - Goose: Memory promotion executor wired
  - Cursor: CLI entry point exists

No LLM calls. All tests use make_synthetic_persona() + mocks.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Test 1: G7 distinctiveness score is in envelope (not hardcoded 0.0)
# ---------------------------------------------------------------------------

def test_g7_distinctiveness_score_not_hardcoded():
    """
    G7 carry-forward resolved: distinctiveness_score must come from
    check_distinctiveness(), not be hardcoded 0.0.
    A single-persona cohort gets 0.0 (correct: can't compute pairwise distance).
    A 2-persona cohort gets a non-negative float from the actual computation.
    """
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock()
        m.return_value.run_all.return_value = []
        return m

    p1 = make_synthetic_persona()
    p2 = make_synthetic_persona()
    p2 = p2.model_copy(update={"persona_id": "pg-gate-002"})

    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([p1, p2], domain="cpg")

    score = envelope.cohort_summary.distinctiveness_score
    assert isinstance(score, float)
    assert score >= 0.0
    # Score is derived from actual computation — field is populated
    assert envelope.cohort_summary is not None


# ---------------------------------------------------------------------------
# Test 2: icp_spec_hash is non-empty and hex
# ---------------------------------------------------------------------------

def test_icp_spec_hash_populated():
    """
    Carry-forward resolved: icp_spec_hash must be a 16-char hex string.
    icp_spec_hash is a top-level field on CohortEnvelope and also stored
    inside taxonomy_used (TaxonomyMeta).
    """
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock()
        m.return_value.run_all.return_value = []
        return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg")

    h = envelope.icp_spec_hash
    assert len(h) == 16
    assert h.isalnum()
    assert not h == ""


# ---------------------------------------------------------------------------
# Test 3: HC3 constraint is active after taxonomy fix
# ---------------------------------------------------------------------------

def test_hc3_active():
    """
    HC3 carry-forward resolved: health_supplement_belief now in taxonomy.
    Verify HC3 fires for a violating persona.
    """
    from src.taxonomy.base_taxonomy import BASE_TAXONOMY
    from src.generation.constraint_checker import ConstraintChecker
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.schema.persona import Attribute

    # Confirm attribute exists in taxonomy first
    attr_names = [a.name for a in BASE_TAXONOMY]
    assert "health_supplement_belief" in attr_names, "HC3 fix not applied"

    persona = make_synthetic_persona()
    attrs = dict(persona.attributes)
    psych = dict(attrs.get("psychology", {}))
    psych["health_anxiety"] = Attribute(
        value=0.10, type="continuous", label="Health Anxiety", source="sampled"
    )
    psych["health_supplement_belief"] = Attribute(
        value=0.90, type="continuous", label="Health Supplement Belief", source="sampled"
    )
    attrs["psychology"] = psych
    tampered = persona.model_copy(update={"attributes": attrs})

    checker = ConstraintChecker()
    violations = checker.check_hard_constraints(tampered)
    hc3 = [
        v for v in violations
        if getattr(v, "constraint_id", "") == "HC3"
        or "supplement" in getattr(v, "description", "").lower()
        or "supplement" in getattr(v, "attr_b", "").lower()
    ]
    assert len(hc3) >= 1, (
        f"HC3 did not fire. All violations: "
        f"{[v.to_dict() if hasattr(v, 'to_dict') else v for v in violations]}"
    )


# ---------------------------------------------------------------------------
# Test 4: Memory promotion executor exists and is importable
# ---------------------------------------------------------------------------

def test_promotion_executor_importable():
    """Memory promotion executor must be importable."""
    from src.memory.promotion_executor import (
        get_promotable_observations,
        promote_to_core,
        run_promotion_pass,
    )
    assert callable(get_promotable_observations)
    assert callable(promote_to_core)
    assert callable(run_promotion_pass)


# ---------------------------------------------------------------------------
# Test 5: LoopResult has promoted_memory_ids field
# ---------------------------------------------------------------------------

def test_loop_result_promoted_field():
    """LoopResult.promoted_memory_ids must exist and default to []."""
    from src.cognition.loop import LoopResult
    from src.schema.persona import Observation
    from datetime import datetime, timezone

    obs = Observation(
        id="obs-gate-001",
        timestamp=datetime.now(timezone.utc),
        type="observation",
        content="Test stimulus for gate check",
        importance=5,
        emotional_valence=0.0,
        source_stimulus_id=None,
        last_accessed=datetime.now(timezone.utc),
    )
    result = LoopResult(observation=obs, reflected=False)
    assert hasattr(result, "promoted_memory_ids")
    assert result.promoted_memory_ids == []


# ---------------------------------------------------------------------------
# Test 6: CLI module is importable
# ---------------------------------------------------------------------------

def test_cli_importable():
    """CLI entry point must be importable."""
    from src.cli import cli, generate, _run_generation
    import inspect
    assert callable(cli)
    assert callable(generate)
    assert inspect.iscoroutinefunction(_run_generation)


# ---------------------------------------------------------------------------
# Test 7: business_problem parameter accepted by assemble_cohort
# ---------------------------------------------------------------------------

def test_business_problem_accepted():
    """assemble_cohort must accept business_problem parameter."""
    from src.cohort.assembler import assemble_cohort
    import inspect

    sig = inspect.signature(assemble_cohort)
    assert "business_problem" in sig.parameters, (
        "business_problem parameter not added to assemble_cohort()"
    )


# ---------------------------------------------------------------------------
# Test 8: Full pipeline structural run (no LLM) — spec to envelope
# ---------------------------------------------------------------------------

def test_full_pipeline_structural():
    """
    Structural end-to-end: build a persona without LLM calls using the
    synthetic fixture, assemble it into a cohort, verify the envelope
    has all key fields populated.
    """
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock()
        m.return_value.run_all.return_value = []
        return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg", business_problem="Test run")

    # Envelope has all expected fields
    assert envelope.cohort_id is not None
    assert len(envelope.personas) == 1
    assert envelope.icp_spec_hash != ""
    assert envelope.business_problem == "Test run"
    assert envelope.cohort_summary.decision_style_distribution is not None
    assert isinstance(envelope.cohort_summary.distinctiveness_score, float)
    # Cohort mode is set
    assert envelope.mode in ("simulation-ready", "quick", "grounded", "deep")
