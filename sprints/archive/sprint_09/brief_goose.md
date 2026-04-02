# SPRINT 9 BRIEF — GOOSE
**Role:** Grounding Integration Tests
**Sprint:** 9 — Wire Grounding into Generation Flow
**Spec ref:** Master Spec §7 (Grounded Mode Pipeline end-to-end)
**Previous rating:** 19/20

---

## Context

Sprint 9 wires the grounding pipeline into `assemble_cohort()`. Your job is to write the integration test suite that validates the full grounded cohort assembly flow — from raw texts all the way to a correct, schema-valid `CohortEnvelope`.

**One new file:** `tests/test_grounding_integration.py`

---

## File: `tests/test_grounding_integration.py`

### Test 1: Full grounded pipeline — CohortEnvelope shape

```python
def test_full_grounded_cohort_envelope_shape():
    """
    End-to-end: assemble_cohort with domain_data produces a schema-valid
    CohortEnvelope with all grounding fields correctly populated.
    """
    from src.cohort.assembler import assemble_cohort
    from src.schema.cohort import CohortEnvelope
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    domain_data = [
        "I switched brands because the price went up dramatically.",
        "My doctor specifically recommended this supplement.",
        "Bought it after reading trusted expert reviews.",
        "Too expensive — rejected and switched to the cheaper alternative.",
        "A friend's recommendation made me try this brand.",
        "The price was too high — I avoided it completely.",
        "Switched from my old brand when quality improved.",
        "Expert certification gave me confidence to buy.",
    ]
    personas = [make_synthetic_persona() for _ in range(2)]
    envelope = assemble_cohort(personas, domain="cpg", domain_data=domain_data)

    # Schema validity — Pydantic would have raised on construction if invalid
    assert isinstance(envelope, CohortEnvelope)
    assert envelope.mode == "grounded"
    assert envelope.domain == "cpg"
    assert len(envelope.personas) == 2
```

### Test 2: GroundingSummary fields all populated

```python
def test_grounded_cohort_grounding_summary_populated():
    """
    GroundingSummary in grounded mode must have:
    - signals_extracted > 0
    - clusters_derived >= 1
    - tendency_source_distribution sums to 1.0
    - distribution keys = {"grounded", "proxy", "estimated"}
    """
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    domain_data = [
        "Rejected this product — far too expensive for what it offers.",
        "My friend switched and convinced me to try it.",
        "Expert-certified — I bought it with confidence.",
        "Switched brands after price doubled — couldn't afford it.",
        "Doctor recommended this supplement for my condition.",
    ] * 3  # 15 texts

    envelope = assemble_cohort([make_synthetic_persona()], domain="cpg", domain_data=domain_data)
    gs = envelope.grounding_summary

    assert gs.domain_data_signals_extracted > 0
    assert gs.clusters_derived >= 1
    total = sum(gs.tendency_source_distribution.values())
    assert abs(total - 1.0) < 1e-6
    assert set(gs.tendency_source_distribution.keys()) == {"grounded", "proxy", "estimated"}
```

### Test 3: TaxonomyMeta.domain_data_used set correctly

```python
def test_taxonomy_meta_domain_data_used():
    """
    domain_data_used should be True when domain_data provided, False otherwise.
    """
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    domain_data = ["I bought this after a price comparison.", "Expert review convinced me."]

    # With domain_data
    envelope_grounded = assemble_cohort([persona], domain="cpg", domain_data=domain_data)
    assert envelope_grounded.taxonomy_used.domain_data_used is True

    # Without domain_data
    envelope_proxy = assemble_cohort([make_synthetic_persona()], domain="cpg")
    assert envelope_proxy.taxonomy_used.domain_data_used is False
```

### Test 4: Grounded source proportion is > 0 after grounding

```python
def test_grounded_source_proportion_positive():
    """
    After running with domain_data, the 'grounded' proportion in
    tendency_source_distribution should be > 0.
    """
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    domain_data = [
        f"Product {i} — too expensive, switched to a cheaper alternative." for i in range(10)
    ] + [
        f"Expert review {i} convinced me to buy this product." for i in range(10)
    ]

    envelope = assemble_cohort([make_synthetic_persona()], domain="cpg", domain_data=domain_data)
    grounded_frac = envelope.grounding_summary.tendency_source_distribution["grounded"]
    assert grounded_frac > 0.0, f"Expected grounded > 0, got {grounded_frac}"
```

### Test 5: Proxy cohort (no domain_data) → signals_extracted = 0, clusters_derived = 0

```python
def test_proxy_cohort_zeros_in_grounding_summary():
    """
    Without domain_data, grounding summary has:
    - domain_data_signals_extracted == 0
    - clusters_derived == 0
    - grounded proportion == 0.0
    """
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    envelope = assemble_cohort([make_synthetic_persona()], domain="cpg")
    gs = envelope.grounding_summary

    assert gs.domain_data_signals_extracted == 0
    assert gs.clusters_derived == 0
    assert gs.tendency_source_distribution["grounded"] == 0.0
```

### Test 6: Multi-persona grounded cohort — all personas updated

```python
def test_multi_persona_grounded_cohort():
    """
    With 3 personas and domain_data, all 3 should be in the envelope
    with at least one grounded tendency each.
    """
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    personas = [make_synthetic_persona() for _ in range(3)]
    domain_data = [
        "Switched brands after the price doubled.",
        "My trusted friend recommended this product.",
        "Expert-certified organic — bought with confidence.",
        "Rejected because it was too expensive.",
        "Doctor's recommendation — switched immediately.",
    ] * 4  # 20 texts

    envelope = assemble_cohort(personas, domain="cpg", domain_data=domain_data)

    assert len(envelope.personas) == 3
    for persona in envelope.personas:
        bt = persona.behavioural_tendencies
        sources = {bt.price_sensitivity.source, bt.trust_orientation.source, bt.switching_propensity.source}
        assert "grounded" in sources, f"Persona {persona.persona_id} has no grounded tendency"
```

### Test 7: Warning accessible via pipeline (below 200 signals)

```python
def test_grounded_cohort_below_200_still_builds():
    """
    Even with < 200 texts (below the grounding threshold), the cohort
    assembles successfully. The pipeline emits a warning internally,
    but assemble_cohort does not raise.
    """
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    small_domain_data = [
        "Bought this — price was right.",
        "Switched due to price increase.",
        "Expert recommended it.",
    ]  # Only 3 texts — below 200 threshold

    # Must not raise
    envelope = assemble_cohort([make_synthetic_persona()], domain="cpg", domain_data=small_domain_data)
    assert envelope.mode == "grounded"
    assert envelope.grounding_summary.domain_data_signals_extracted > 0
```

### Test 8: ICPSpec.domain_data field accessible

```python
def test_icp_spec_domain_data_field():
    """
    ICPSpec (Sprint 9 Cursor) should now have a domain_data field.
    """
    from src.generation.identity_constructor import ICPSpec
    spec = ICPSpec(
        domain="cpg",
        mode="grounded",
        domain_data=["Too expensive — rejected.", "Friend recommended it."],
    )
    assert hasattr(spec, "domain_data")
    assert spec.domain_data is not None
    assert len(spec.domain_data) == 2
```

---

## Constraints

- No LLM calls.
- All 8 tests pass without `--integration`.
- Tests import from `src.cohort.assembler` and `tests.fixtures.synthetic_persona`.
- Do not mock the grounding pipeline — call the real pipeline end-to-end.
- Tests must be robust to small dataset variance (clustering with few signals may produce 1 cluster — that's ok).

---

## Outcome File

When done, write `sprints/outcome_goose.md` with:
1. File created (line count)
2. Test results (8/8)
3. Any edge cases observed during testing
4. Full suite result
5. Known gaps
