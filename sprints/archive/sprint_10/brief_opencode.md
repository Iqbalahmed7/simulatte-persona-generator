# SPRINT 10 BRIEF — OPENCODE
**Role:** Sarvam Structural Tests + End-to-End Flow
**Sprint:** 10 — Sarvam Indian Cultural Realism Layer
**Spec ref:** Master Spec §15, activation pre-check, end-to-end shape
**Previous rating:** 20/20

---

## Context

Sprint 10 builds Sarvam. Your job: write structural (non-LLM) tests for the full Sarvam flow, and write a `run_sarvam_enrichment()` top-level function that wires activation + enrichment + CR1 together.

---

## File: `src/sarvam/pipeline.py`

The top-level Sarvam entry point that callers use.

```python
"""Sarvam enrichment pipeline — top-level entry point.

Sprint 10 — Sarvam Indian Cultural Realism Layer.
Wires activation check → enrichment → CR1 validation into one call.
"""
from __future__ import annotations

from typing import Any

from src.sarvam.config import SarvamConfig
from src.sarvam.types import SarvamEnrichmentRecord


async def run_sarvam_enrichment(
    persona: Any,               # PersonaRecord
    config: SarvamConfig,
    llm_client: Any,
) -> SarvamEnrichmentRecord:
    """Run the full Sarvam enrichment pipeline for a single persona.

    Steps:
    1. Check activation conditions (should_activate).
       If not met → return skip record immediately.
    2. Run SarvamEnricher.enrich(persona, config).
    3. Run CR1 check (original persona vs post-enrichment persona — should be identical
       since enrichment never modifies the PersonaRecord).
    4. Update enrichment record validation_status.cr1_isolation.
    5. Return final SarvamEnrichmentRecord.

    Note on CR1: Since enrichment never modifies the PersonaRecord,
    CR1 is a structural invariant check. We pass the same persona twice
    to confirm no mutation occurred. In a future integration where
    Sarvam re-runs the decision engine, CR1 would compare real decision outputs.

    Args:
        persona: A validated PersonaRecord (India + opt-in conditions checked internally).
        config: SarvamConfig instance.
        llm_client: Anthropic async client.

    Returns:
        SarvamEnrichmentRecord — either an enrichment result or a skip record.
    """
    ...
```

### Implementation:

```python
async def run_sarvam_enrichment(persona, config, llm_client):
    from src.sarvam.activation import should_activate, make_skip_record
    from src.sarvam.enrichment import SarvamEnricher
    from src.sarvam.cr1_validator import run_cr1_check, update_enrichment_record_with_cr1

    # Step 1: Activation check
    active, reason = should_activate(persona, config)
    if not active:
        return make_skip_record(persona.persona_id, reason)

    # Step 2: Enrich
    enricher = SarvamEnricher(llm_client)
    enrichment_record = await enricher.enrich(persona, config)

    # Step 3 + 4: CR1 check — persona must be unchanged
    # We compare persona to itself (no mutation should have occurred)
    cr1_result = run_cr1_check(persona, persona)
    enrichment_record = update_enrichment_record_with_cr1(enrichment_record, cr1_result)

    return enrichment_record
```

---

## File: `tests/test_sarvam_structural.py`

All structural tests — no LLM calls, use mocked enricher.

### Test 1: run_sarvam_enrichment skips non-India persona

```python
@pytest.mark.asyncio
async def test_pipeline_skips_non_india():
    from src.sarvam.pipeline import run_sarvam_enrichment
    from src.sarvam.config import SarvamConfig
    from unittest.mock import MagicMock

    persona = MagicMock()
    persona.persona_id = "test-001"
    persona.demographic_anchor.location.country = "USA"

    record = await run_sarvam_enrichment(persona, SarvamConfig.enabled(), llm_client=None)
    assert record.enrichment_applied is False
    assert record.skip_reason is not None
    assert "india" in record.skip_reason.lower()
```

### Test 2: run_sarvam_enrichment skips when disabled

```python
@pytest.mark.asyncio
async def test_pipeline_skips_when_disabled():
    from src.sarvam.pipeline import run_sarvam_enrichment
    from src.sarvam.config import SarvamConfig
    from unittest.mock import MagicMock

    persona = MagicMock()
    persona.persona_id = "test-002"
    persona.demographic_anchor.location.country = "India"

    record = await run_sarvam_enrichment(persona, SarvamConfig.disabled(), llm_client=None)
    assert record.enrichment_applied is False
    assert "disabled" in record.skip_reason.lower()
```

### Test 3: run_sarvam_enrichment with mocked enricher → CR1 pass

```python
@pytest.mark.asyncio
async def test_pipeline_cr1_passes_with_mock():
    """With a mocked enricher, CR1 should pass (persona not mutated)."""
    from src.sarvam.pipeline import run_sarvam_enrichment
    from src.sarvam.config import SarvamConfig
    from src.sarvam.types import SarvamEnrichmentRecord, EnrichedNarrative, ValidationStatus
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from unittest.mock import patch, AsyncMock

    persona = make_synthetic_persona()

    mock_record = SarvamEnrichmentRecord(
        enrichment_applied=True,
        enrichment_provider="sarvam",
        enrichment_scope="narrative_and_examples",
        persona_id=persona.persona_id,
        enriched_narrative=EnrichedNarrative(
            first_person="I shop at D-Mart...",
            third_person="Priya, a Mumbai professional...",
        ),
        validation_status=ValidationStatus(),
    )

    with patch("src.sarvam.pipeline.should_activate", return_value=(True, "met")):
        with patch("src.sarvam.pipeline.SarvamEnricher") as MockEnricher:
            MockEnricher.return_value.enrich = AsyncMock(return_value=mock_record)
            record = await run_sarvam_enrichment(
                persona, SarvamConfig.enabled(), llm_client=None
            )

    assert record.enrichment_applied is True
    assert record.validation_status.cr1_isolation == "pass"
```

### Test 4: Pipeline returns correct persona_id

```python
@pytest.mark.asyncio
async def test_pipeline_skip_record_has_persona_id():
    from src.sarvam.pipeline import run_sarvam_enrichment
    from src.sarvam.config import SarvamConfig
    from unittest.mock import MagicMock

    persona = MagicMock()
    persona.persona_id = "pg-cpg-007"
    persona.demographic_anchor.location.country = "UK"

    record = await run_sarvam_enrichment(persona, SarvamConfig.enabled(), llm_client=None)
    assert record.persona_id == "pg-cpg-007"
```

### Test 5: SarvamEnrichmentRecord is JSON-serialisable

```python
def test_enrichment_record_json_serialisable():
    """SarvamEnrichmentRecord must be JSON-serialisable via model_dump()."""
    from src.sarvam.types import SarvamEnrichmentRecord, EnrichedNarrative, ValidationStatus
    import json

    record = SarvamEnrichmentRecord(
        enrichment_applied=True,
        enrichment_provider="sarvam",
        enrichment_scope="narrative_only",
        persona_id="test-001",
        enriched_narrative=EnrichedNarrative(
            first_person="I shop at D-Mart...",
            third_person="Priya, a Mumbai professional...",
        ),
        cultural_references_added=["D-Mart", "Chai tapri"],
        validation_status=ValidationStatus(cr1_isolation="pass"),
    )
    dumped = record.model_dump()
    json_str = json.dumps(dumped)
    assert len(json_str) > 0
    loaded = json.loads(json_str)
    assert loaded["enrichment_applied"] is True
    assert loaded["persona_id"] == "test-001"
```

---

## Constraints

- No LLM calls. Use `unittest.mock.patch` for enricher in Test 3.
- All 5 tests pass without `--integration`.
- `pipeline.py` must use lazy imports (inside the function) to avoid circular imports.
- Full suite: must remain 123+ passed.

---

## Outcome File

When done, write `sprints/outcome_opencode.md` with:
1. Files created (line counts)
2. Pipeline wiring — activation → enrichment → CR1
3. Test results (5/5)
4. Full suite result
5. Known gaps
