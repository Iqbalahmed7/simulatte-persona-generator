# SPRINT 10 BRIEF — CURSOR
**Role:** Sarvam Config + Types + Activation Gate
**Sprint:** 10 — Sarvam Indian Cultural Realism Layer
**Spec ref:** Master Spec §15, SIMULATTE_SARVAM_TEST_PROTOCOL.md
**Previous rating:** 20/20

---

## Context

Sprint 10 builds the Sarvam Indian Cultural Realism Layer. Sarvam is an expression-only enrichment layer that adds culturally authentic Indian texture to persona narratives. It NEVER modifies persona identity, attributes, tendencies, or decisions.

Your job: the foundational types, config, and activation logic. No LLM calls.

---

## File 1: `src/sarvam/__init__.py`

```python
"""Sarvam — Indian Cultural Realism Layer.

Sprint 10. Expression-only enrichment for India-market personas.
Activation requires: persona.location.country == "India"
AND client_config.sarvam_enrichment == True.

Never invoked during simulation or cognitive loop.
"""
```

---

## File 2: `src/sarvam/config.py`

```python
"""Sarvam enrichment configuration.

Sprint 10 — Sarvam Indian Cultural Realism Layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


SarvamEnrichmentScope = Literal[
    "narrative_only",
    "narrative_and_examples",
    "full",
]
"""
narrative_only            — enriches first_person + third_person narratives only.
narrative_and_examples    — enriches narratives + replaces contextual examples.
full                      — all permitted surfaces (narratives + examples + dialogue tone).
"""


@dataclass
class SarvamConfig:
    """Configuration for a Sarvam enrichment run.

    sarvam_enrichment: bool
        Master switch. Must be True for enrichment to run.
        Default: False — opt-in required.

    scope: SarvamEnrichmentScope
        Which surfaces to enrich.
        Default: "narrative_and_examples"

    model: str
        LLM model identifier for enrichment calls.
        Default: "claude-haiku-4-5-20251001" (low cost, fast).
        Set to a Sarvam API model identifier when Sarvam API key is available.

    max_narrative_words: int
        Maximum word count for enriched narratives (enforced by enricher).
        Default: 200

    anti_stereotypicality_strict: bool
        If True, enricher prompt includes strict anti-stereotypicality instructions
        and explicitly lists prohibited defaults.
        Default: True
    """
    sarvam_enrichment: bool = False
    scope: SarvamEnrichmentScope = "narrative_and_examples"
    model: str = "claude-haiku-4-5-20251001"
    max_narrative_words: int = 200
    anti_stereotypicality_strict: bool = True

    @classmethod
    def enabled(cls, scope: SarvamEnrichmentScope = "narrative_and_examples") -> "SarvamConfig":
        """Convenience constructor for an enabled config with default settings."""
        return cls(sarvam_enrichment=True, scope=scope)

    @classmethod
    def disabled(cls) -> "SarvamConfig":
        """Convenience constructor for a disabled config (default state)."""
        return cls(sarvam_enrichment=False)
```

---

## File 3: `src/sarvam/types.py`

Pydantic models for the enrichment output record (serializable, schema-enforced).

```python
"""Sarvam enrichment output types.

Sprint 10 — Sarvam Indian Cultural Realism Layer.
All types are Pydantic models (extra='forbid').
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CRStatus = Literal["pass", "fail", "not_run"]


class EnrichedNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_person: str
    """Sarvam-enriched first-person narrative."""

    third_person: str
    """Sarvam-enriched third-person narrative."""


class ContextualReplacement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original: str
    """The original Western-default or generic reference."""

    replacement: str
    """The India-specific replacement (traceable to an attribute)."""

    attribute_source: str
    """The persona field this replacement derives from, e.g. 'location.city' or 'values.brand_loyalty'."""


class ValidationStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cr1_isolation: CRStatus = "not_run"
    """CR1: Persona record not modified by enrichment. Automated."""

    cr2_stereotype_audit: CRStatus = "not_run"
    """CR2: Cultural details derive from attributes. Manual/semi-automated."""

    cr3_cultural_realism: CRStatus = "not_run"
    """CR3: Human evaluator rating ≥ 4.0/5.0. Human-evaluated."""

    cr4_persona_fidelity: CRStatus = "not_run"
    """CR4: Enriched output is the same person. Human-evaluated."""


class SarvamEnrichmentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enrichment_applied: bool
    """True if enrichment ran. False if activation conditions were not met."""

    enrichment_provider: Literal["sarvam", "none"] = "none"
    """Provider identifier. 'sarvam' when applied, 'none' when not applied."""

    enrichment_scope: str = ""
    """Scope string describing which surfaces were enriched."""

    persona_id: str
    """ID of the persona this enrichment record belongs to."""

    enriched_narrative: EnrichedNarrative | None = None
    """Enriched narratives. None if enrichment_applied is False."""

    cultural_references_added: list[str] = Field(default_factory=list)
    """List of India-specific cultural references added (traceable to attributes)."""

    contextual_examples_replaced: list[ContextualReplacement] = Field(default_factory=list)
    """List of contextual replacements made (Western → India-specific)."""

    validation_status: ValidationStatus = Field(default_factory=ValidationStatus)
    """CR test status. All 'not_run' until explicitly evaluated."""

    skip_reason: str | None = None
    """Reason enrichment was skipped (if enrichment_applied is False)."""
```

---

## File 4: `src/sarvam/activation.py`

```python
"""Sarvam activation gate.

Sprint 10 — Sarvam Indian Cultural Realism Layer.
Determines whether Sarvam enrichment should run for a given persona + config.
"""
from __future__ import annotations

from src.sarvam.config import SarvamConfig


def should_activate(persona: object, config: SarvamConfig) -> tuple[bool, str]:
    """Determine whether Sarvam enrichment should activate.

    Activation conditions (ALL must hold):
    1. config.sarvam_enrichment == True
    2. persona.location.country == "India"

    Args:
        persona: A PersonaRecord (typed as object to avoid circular imports).
        config: SarvamConfig instance.

    Returns:
        Tuple of (should_activate: bool, reason: str).
        reason explains why activation was granted or denied.
    """
    ...
```

### Implementation:

```python
def should_activate(persona, config):
    if not config.sarvam_enrichment:
        return False, "sarvam_enrichment is disabled in config (opt-in required)"

    country = None
    try:
        country = persona.demographic_anchor.location.country
    except AttributeError:
        return False, "persona.demographic_anchor.location.country not accessible"

    if not country:
        return False, "persona location country is not set"

    if country.lower() != "india":
        return False, f"persona country is '{country}', not 'India' — Sarvam is India-only"

    return True, "activation conditions met: India + opt-in"
```

Also add:

```python
def make_skip_record(persona_id: str, reason: str) -> "SarvamEnrichmentRecord":
    """Build a SarvamEnrichmentRecord for a skipped enrichment (activation not met)."""
    from src.sarvam.types import SarvamEnrichmentRecord
    return SarvamEnrichmentRecord(
        enrichment_applied=False,
        enrichment_provider="none",
        persona_id=persona_id,
        skip_reason=reason,
    )
```

---

## File 5: `tests/test_sarvam_activation.py`

### Test 1: India + enabled → activates

```python
def test_activation_india_enabled():
    from src.sarvam.activation import should_activate
    from src.sarvam.config import SarvamConfig

    class MockPersona:
        class demographic_anchor:
            class location:
                country = "India"

    active, reason = should_activate(MockPersona(), SarvamConfig.enabled())
    assert active is True
    assert "met" in reason.lower()
```

### Test 2: India + disabled → no activation

```python
def test_activation_india_disabled():
    from src.sarvam.activation import should_activate
    from src.sarvam.config import SarvamConfig

    class MockPersona:
        class demographic_anchor:
            class location:
                country = "India"

    active, reason = should_activate(MockPersona(), SarvamConfig.disabled())
    assert active is False
    assert "disabled" in reason.lower()
```

### Test 3: Non-India + enabled → no activation

```python
def test_activation_non_india():
    from src.sarvam.activation import should_activate
    from src.sarvam.config import SarvamConfig

    class MockPersona:
        class demographic_anchor:
            class location:
                country = "USA"

    active, reason = should_activate(MockPersona(), SarvamConfig.enabled())
    assert active is False
    assert "india-only" in reason.lower() or "india" in reason.lower()
```

### Test 4: Missing country → no activation

```python
def test_activation_missing_country():
    from src.sarvam.activation import should_activate
    from src.sarvam.config import SarvamConfig

    class MockPersona:
        class demographic_anchor:
            class location:
                country = None

    active, reason = should_activate(MockPersona(), SarvamConfig.enabled())
    assert active is False
```

### Test 5: SarvamConfig defaults

```python
def test_sarvam_config_defaults():
    from src.sarvam.config import SarvamConfig
    config = SarvamConfig()
    assert config.sarvam_enrichment is False
    assert config.scope == "narrative_and_examples"
    assert config.anti_stereotypicality_strict is True
```

### Test 6: SarvamConfig.enabled() convenience constructor

```python
def test_sarvam_config_enabled_constructor():
    from src.sarvam.config import SarvamConfig
    config = SarvamConfig.enabled()
    assert config.sarvam_enrichment is True
    assert config.scope == "narrative_and_examples"
```

### Test 7: SarvamEnrichmentRecord schema — enrichment_applied False

```python
def test_enrichment_record_not_applied():
    from src.sarvam.types import SarvamEnrichmentRecord
    record = SarvamEnrichmentRecord(
        enrichment_applied=False,
        enrichment_provider="none",
        persona_id="test-001",
        skip_reason="not India",
    )
    assert record.enrichment_applied is False
    assert record.enriched_narrative is None
    assert record.skip_reason == "not India"
```

### Test 8: SarvamEnrichmentRecord schema — enrichment_applied True

```python
def test_enrichment_record_applied():
    from src.sarvam.types import SarvamEnrichmentRecord, EnrichedNarrative, ValidationStatus
    record = SarvamEnrichmentRecord(
        enrichment_applied=True,
        enrichment_provider="sarvam",
        enrichment_scope="narrative_and_examples",
        persona_id="test-001",
        enriched_narrative=EnrichedNarrative(
            first_person="I shop at Meesho for value...",
            third_person="Priya, a Mumbai professional...",
        ),
        cultural_references_added=["Meesho", "chai tapri"],
        validation_status=ValidationStatus(cr1_isolation="pass"),
    )
    assert record.enrichment_applied is True
    assert record.enriched_narrative is not None
    assert len(record.cultural_references_added) == 2
    assert record.validation_status.cr1_isolation == "pass"
```

### Test 9: make_skip_record utility

```python
def test_make_skip_record():
    from src.sarvam.activation import make_skip_record
    record = make_skip_record("pg-cpg-001", "not India")
    assert record.enrichment_applied is False
    assert record.persona_id == "pg-cpg-001"
    assert record.skip_reason == "not India"
```

### Test 10: ValidationStatus defaults all "not_run"

```python
def test_validation_status_defaults():
    from src.sarvam.types import ValidationStatus
    vs = ValidationStatus()
    assert vs.cr1_isolation == "not_run"
    assert vs.cr2_stereotype_audit == "not_run"
    assert vs.cr3_cultural_realism == "not_run"
    assert vs.cr4_persona_fidelity == "not_run"
```

---

## Constraints

- No LLM calls anywhere in this set of files.
- `should_activate` uses only `getattr`/attribute access — no type imports from `src.schema.persona`.
- All Pydantic models use `extra="forbid"`.
- 10 tests, all pass without `--integration`.
- Run full suite after changes: must remain 123 passed.

---

## Outcome File

When done, write `sprints/outcome_cursor.md` with:
1. Files created (line counts)
2. Activation logic — all conditions
3. Test results (10/10)
4. Full suite result
5. Known gaps
