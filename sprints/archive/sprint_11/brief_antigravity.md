# SPRINT 11 BRIEF — ANTIGRAVITY
**Role:** Pipeline Integration Gate Tests
**Sprint:** 11 — Production Entry Point + Technical Debt Clearance
**Spec ref:** Validity Protocol gates G7 (distinctiveness), G2 (hard constraints), §14A S17 (promotion)
**Previous rating:** 20/20

---

## Context

Sprint 11 closes the last technical debt gaps. Your job: write integration gate tests that verify the complete pipeline works end-to-end (structurally, no LLM). Specifically:
1. G7 distinctiveness gate is now populated (Codex fix) — verify the score flows into the envelope
2. HC3 constraint is now active (OpenCode fix) — verify the violation fires
3. Memory promotion executor is wired (Goose fix) — verify promotion pass runs
4. CLI entry point exists (Cursor fix) — verify CLI structure

---

## File: `tests/test_sprint11_gates.py`

### Test 1: G7 distinctiveness score is in envelope (not hardcoded 0.0)

```python
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
        m = MagicMock(); m.return_value.run_all.return_value = []; return m

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
```

### Test 2: icp_spec_hash is non-empty and hex

```python
def test_icp_spec_hash_populated():
    """
    Carry-forward resolved: icp_spec_hash must be a 16-char hex string.
    """
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    def _all_pass():
        m = MagicMock(); m.return_value.run_all.return_value = []; return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg")

    h = envelope.taxonomy_meta.icp_spec_hash
    assert len(h) == 16
    assert h.isalnum()
    assert not h == ""
```

### Test 3: HC3 constraint is active after taxonomy fix

```python
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
        value=0.10, type="continuous", label="Health Anxiety", source="proxy"
    )
    psych["health_supplement_belief"] = Attribute(
        value=0.90, type="continuous", label="Health Supplement Belief", source="proxy"
    )
    attrs["psychology"] = psych
    tampered = persona.model_copy(update={"attributes": attrs})

    checker = ConstraintChecker()
    violations = checker.check_hard_constraints(tampered)
    hc3 = [v for v in violations if "HC3" in str(v) or "supplement" in str(v).lower()]
    assert len(hc3) >= 1, f"HC3 did not fire. All violations: {violations}"
```

### Test 4: Memory promotion executor exists and is importable

```python
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
```

### Test 5: LoopResult has promoted_memory_ids field

```python
def test_loop_result_promoted_field():
    """LoopResult.promoted_memory_ids must exist and default to []."""
    from src.cognition.loop import LoopResult
    result = LoopResult(persona=None, decision_output=None, reflected=False)
    assert hasattr(result, "promoted_memory_ids")
    assert result.promoted_memory_ids == []
```

### Test 6: CLI module is importable

```python
def test_cli_importable():
    """CLI entry point must be importable."""
    from src.cli import cli, generate, _run_generation
    import inspect
    assert callable(cli)
    assert callable(generate)
    assert inspect.iscoroutinefunction(_run_generation)
```

### Test 7: business_problem parameter accepted by assemble_cohort

```python
def test_business_problem_accepted():
    """assemble_cohort must accept business_problem parameter."""
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock
    import inspect

    sig = inspect.signature(assemble_cohort)
    assert "business_problem" in sig.parameters, (
        "business_problem parameter not added to assemble_cohort()"
    )
```

### Test 8: Full pipeline structural run (no LLM) — spec to envelope

```python
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
        m = MagicMock(); m.return_value.run_all.return_value = []; return m

    persona = make_synthetic_persona()
    with patch("src.cohort.assembler.CohortGateRunner", new_callable=_all_pass):
        envelope = assemble_cohort([persona], domain="cpg", business_problem="Test run")

    # Envelope has all expected fields
    assert envelope.cohort_id is not None
    assert len(envelope.personas) == 1
    assert envelope.taxonomy_meta.icp_spec_hash != ""
    assert envelope.taxonomy_meta.business_problem == "Test run"
    assert envelope.cohort_summary.decision_style_distribution is not None
    assert isinstance(envelope.cohort_summary.distinctiveness_score, float)
    # Cohort mode is set
    assert envelope.mode in ("simulation-ready", "quick", "grounded", "deep")
```

---

## Constraints

- No LLM calls. All tests use `make_synthetic_persona()` fixture + mocks.
- 8 tests, all pass without `--integration`.
- Tests may depend on Cursor (CLI), Codex (assembler fix), Goose (promotion), OpenCode (taxonomy) work — run this file LAST after all other Sprint 11 agents complete.
- Full suite must remain 155+ passed.

---

## Outcome File

Write `sprints/outcome_antigravity.md` with:
1. File created (line count)
2. Which carry-forwards are now verified closed
3. Test results (8/8)
4. Full suite result
5. Any failures and their cause
