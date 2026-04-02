# SPRINT 9 BRIEF — ANTIGRAVITY
**Role:** Grounded Cohort Gate Tests
**Sprint:** 9 — Wire Grounding into Generation Flow
**Spec ref:** Master Spec §7 (Grounded Mode), G11 (tendency source gate)
**Previous rating:** 20/20

---

## Context

Sprint 9 wires grounding into `assemble_cohort()`. Your job is to write gate-level tests that verify the grounded `CohortEnvelope` satisfies all schema and spec constraints — including G11 (all tendency sources valid), GroundingSummary schema validation, and mode="grounded" consistency.

**One new file:** `tests/test_grounded_cohort_gates.py`

---

## File: `tests/test_grounded_cohort_gates.py`

### Test 1: G11 — all tendency sources valid after grounding

```python
def test_g11_all_tendency_sources_valid_after_grounding():
    """
    G11: After assemble_cohort with domain_data, every persona tendency
    source must be one of: grounded, proxy, estimated.
    """
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    domain_data = [
        "Switched brands due to high price — too expensive.",
        "Doctor recommended — I bought it.",
        "Friend told me to try — switched immediately.",
        "Rejected because of cost.",
        "Expert review convinced me.",
    ] * 3  # 15 texts

    valid_sources = {"grounded", "proxy", "estimated"}
    envelope = assemble_cohort([make_synthetic_persona()], domain="cpg", domain_data=domain_data)

    for persona in envelope.personas:
        bt = persona.behavioural_tendencies
        assert bt.price_sensitivity.source in valid_sources
        assert bt.trust_orientation.source in valid_sources
        assert bt.switching_propensity.source in valid_sources
```

### Test 2: GroundingSummary schema passes Pydantic validation

```python
def test_grounding_summary_pydantic_valid():
    """
    GroundingSummary from a grounded cohort must satisfy Pydantic schema:
    - distribution keys = {"grounded", "proxy", "estimated"}
    - values sum to 1.0 (within 1e-6)
    - domain_data_signals_extracted >= 0
    - clusters_derived >= 0
    """
    from src.cohort.assembler import assemble_cohort
    from src.schema.cohort import GroundingSummary
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    domain_data = [
        f"Too expensive — I avoided it, item {i}." for i in range(10)
    ]
    envelope = assemble_cohort([make_synthetic_persona()], domain="cpg", domain_data=domain_data)
    gs = envelope.grounding_summary

    # Re-validate through Pydantic (would raise if invalid)
    revalidated = GroundingSummary(
        tendency_source_distribution=gs.tendency_source_distribution,
        domain_data_signals_extracted=gs.domain_data_signals_extracted,
        clusters_derived=gs.clusters_derived,
    )
    assert revalidated.domain_data_signals_extracted >= 0
    assert revalidated.clusters_derived >= 0
    total = sum(revalidated.tendency_source_distribution.values())
    assert abs(total - 1.0) < 1e-6
```

### Test 3: Mode="grounded" consistent across envelope and personas

```python
def test_grounded_mode_consistent():
    """
    When domain_data is provided:
    - envelope.mode == "grounded"
    - All personas in envelope have mode == "grounded"
    """
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    domain_data = [
        "Switched to a cheaper brand — price was too high.",
        "Expert review gave me confidence.",
        "My friend recommended this product.",
    ] * 5

    personas = [make_synthetic_persona() for _ in range(2)]
    envelope = assemble_cohort(personas, domain="cpg", domain_data=domain_data)

    assert envelope.mode == "grounded"
    for persona in envelope.personas:
        assert persona.mode == "grounded", (
            f"Persona {persona.persona_id} mode is '{persona.mode}', expected 'grounded'"
        )
```

### Test 4: TaxonomyMeta.domain_data_used = True in grounded mode

```python
def test_taxonomy_meta_domain_data_used_grounded():
    """taxonomy_used.domain_data_used must be True for a grounded cohort."""
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    domain_data = ["Bought it on recommendation — price was right."] * 5

    envelope = assemble_cohort([make_synthetic_persona()], domain="cpg", domain_data=domain_data)
    assert envelope.taxonomy_used.domain_data_used is True
```

### Test 5: CohortEnvelope cohort_id is preserved (not mutated by grounding)

```python
def test_cohort_id_preserved_after_grounding():
    """cohort_id passed to assemble_cohort must be unchanged in the envelope."""
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    domain_data = ["Switched brands — price too high.", "Expert recommendation."] * 5
    custom_id = "test-cohort-grounded-001"

    envelope = assemble_cohort(
        [make_synthetic_persona()],
        domain="cpg",
        cohort_id=custom_id,
        domain_data=domain_data,
    )
    assert envelope.cohort_id == custom_id
```

### Test 6: GroundingSummary validator — distribution with wrong keys raises

```python
def test_grounding_summary_rejects_wrong_keys():
    """
    GroundingSummary schema rejects distributions with missing or extra keys.
    """
    from src.schema.cohort import GroundingSummary
    import pytest

    with pytest.raises(Exception):
        GroundingSummary(
            tendency_source_distribution={
                "grounded": 0.5,
                "proxy": 0.5,
                # missing "estimated" key
            },
            domain_data_signals_extracted=10,
            clusters_derived=2,
        )
```

### Test 7: Proxy cohort mode unchanged (no regression)

```python
def test_proxy_cohort_mode_unchanged():
    """
    Without domain_data, the cohort mode should reflect the personas' original mode.
    No regression from Sprint 9 changes.
    """
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    original_mode = persona.mode  # "simulation-ready" from fixture

    envelope = assemble_cohort([persona], domain="cpg")  # no domain_data
    assert envelope.mode == original_mode
    assert envelope.taxonomy_used.domain_data_used is False
    assert envelope.grounding_summary.domain_data_signals_extracted == 0
```

### Test 8: grounding_context utility importable

```python
def test_grounding_context_importable():
    """
    GroundingContext and compute_tendency_source_distribution
    should be importable from src.grounding.grounding_context.
    """
    from src.grounding.grounding_context import (
        GroundingContext,
        compute_tendency_source_distribution,
        build_grounding_summary_from_result,
    )
    assert callable(compute_tendency_source_distribution)
    assert callable(build_grounding_summary_from_result)
    ctx = GroundingContext(domain_data=["text 1"])
    assert ctx.has_data is True
```

---

## Constraints

- No LLM calls.
- 8 tests, all pass without `--integration`.
- Test 3 (mode consistency) checks BOTH envelope AND individual personas — if personas aren't mode="grounded" after grounding, this is a real spec drift.
- Test 6 uses `pytest.raises(Exception)` broadly — `GroundingSummary` raises `ValueError` via Pydantic, which is an `Exception` subclass.

---

## Outcome File

When done, write `sprints/outcome_antigravity.md` with:
1. File created (line count)
2. Test results (8/8)
3. G11 coverage — which fields checked
4. Mode consistency check — what was verified
5. Full suite result
6. Known gaps
