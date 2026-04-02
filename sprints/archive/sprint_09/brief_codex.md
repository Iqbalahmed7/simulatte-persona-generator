# SPRINT 9 BRIEF — CODEX
**Role:** Wire grounding pipeline into assemble_cohort()
**Sprint:** 9 — Wire Grounding into Generation Flow
**Spec ref:** Master Spec §7 (Grounding Pipeline → CohortEnvelope), §14 S15
**Previous rating:** 20/20

---

## Context

Sprint 8 built the grounding pipeline. Sprint 9 wires it into `assemble_cohort()`. When `domain_data` is provided, the cohort assembler should run the grounding pipeline and:
1. Update personas with grounded tendencies
2. Populate `GroundingSummary` with real signal/cluster counts
3. Set `TaxonomyMeta.domain_data_used = True`
4. Set the cohort `mode = "grounded"`

**One file to modify:** `src/cohort/assembler.py`

---

## Change: Add `domain_data` parameter to `assemble_cohort()`

### Current signature (line ~146):
```python
def assemble_cohort(
    personas: list[PersonaRecord],
    domain: str,
    cohort_id: str | None = None,
) -> CohortEnvelope:
```

### New signature:
```python
def assemble_cohort(
    personas: list[PersonaRecord],
    domain: str,
    cohort_id: str | None = None,
    domain_data: list[str] | None = None,
) -> CohortEnvelope:
    """
    Assemble N personas into a validated CohortEnvelope.

    If domain_data is provided (list of raw text strings — reviews, posts),
    runs the grounding pipeline to upgrade persona tendency sources from
    'proxy' to 'grounded' before building the envelope. The GroundingSummary
    will reflect actual signal and cluster counts.

    Raises ValueError listing failed gates if any gate fails.
    cohort_id defaults to f"cohort-{uuid4().hex[:8]}"
    """
```

### Integration point — insert AFTER gate validation, BEFORE computing summary:

```python
# Step 2.5 (NEW): Grounding pipeline — runs after gate validation,
# before summary + envelope construction.
grounding_signals_extracted: int = 0
grounding_clusters_derived: int = 0
domain_data_used: bool = False
grounded_mode: str = personas[0].mode  # default: keep original mode

if domain_data:
    from src.grounding.pipeline import run_grounding_pipeline
    grounding_result = run_grounding_pipeline(domain_data, personas)
    personas = grounding_result.personas          # updated with grounded tendencies
    grounding_signals_extracted = grounding_result.signals_extracted
    grounding_clusters_derived = grounding_result.clusters_derived
    domain_data_used = True
    grounded_mode = "grounded"
```

### Update `GroundingSummary` construction (replaces current hardcoded-zeros version):

Current code (around line 199–218) computes tendency_sources and builds GroundingSummary with `domain_data_signals_extracted=0, clusters_derived=0`. Replace with:

```python
# Recompute tendency sources from (potentially updated) personas
tendency_sources: list[str] = []
for p in personas:
    bt = p.behavioural_tendencies
    for field_name in ("price_sensitivity", "switching_propensity", "trust_orientation"):
        obj = getattr(bt, field_name, None)
        if obj is not None and hasattr(obj, "source") and obj.source is not None:
            tendency_sources.append(obj.source)

total_sources = len(tendency_sources) if tendency_sources else 1
source_counts = Counter(tendency_sources)
grounding_summary = GroundingSummary(
    tendency_source_distribution={
        "grounded": round(source_counts.get("grounded", 0) / total_sources, 6),
        "proxy": round(source_counts.get("proxy", 0) / total_sources, 6),
        "estimated": round(source_counts.get("estimated", 0) / total_sources, 6),
    },
    domain_data_signals_extracted=grounding_signals_extracted,
    clusters_derived=grounding_clusters_derived,
)
```

### Update `TaxonomyMeta` construction to use `domain_data_used`:

```python
taxonomy_used = TaxonomyMeta(
    base_attributes=total_attrs,
    domain_extension_attributes=0,
    total_attributes=total_attrs,
    domain_data_used=domain_data_used,   # was hardcoded False
)
```

### Update `mode` to use `grounded_mode`:

```python
# Derive mode — "grounded" if domain_data was provided, else first persona's mode
mode = grounded_mode   # was: mode = personas[0].mode
```

---

## Important: GroundingSummary distribution must sum to 1.0

The `GroundingSummary` validator requires `sum(tendency_source_distribution.values()) == 1.0`.

With rounding, the sum may be off by 1e-6. The current code uses `round(..., 6)`. This is already in the file. Keep this approach but add a correction pass:

```python
dist = {
    "grounded": round(source_counts.get("grounded", 0) / total_sources, 6),
    "proxy": round(source_counts.get("proxy", 0) / total_sources, 6),
    "estimated": round(source_counts.get("estimated", 0) / total_sources, 6),
}
# Correct rounding drift — add/subtract residual to/from largest bucket
_total = sum(dist.values())
if abs(_total - 1.0) > 1e-9:
    largest_key = max(dist, key=lambda k: dist[k])
    dist[largest_key] = round(dist[largest_key] + (1.0 - _total), 9)
grounding_summary = GroundingSummary(
    tendency_source_distribution=dist,
    domain_data_signals_extracted=grounding_signals_extracted,
    clusters_derived=grounding_clusters_derived,
)
```

---

## Tests: `tests/test_assembler_grounding.py`

### Test 1: assemble_cohort without domain_data unchanged

```python
def test_assembler_without_domain_data():
    """No domain_data → existing behaviour unchanged. mode from persona."""
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    original_mode = persona.mode
    envelope = assemble_cohort([persona], domain="cpg")

    assert envelope.grounding_summary.domain_data_signals_extracted == 0
    assert envelope.grounding_summary.clusters_derived == 0
    assert envelope.taxonomy_used.domain_data_used is False
    assert envelope.mode == original_mode
```

### Test 2: assemble_cohort with domain_data → grounded

```python
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
    envelope = assemble_cohort([persona], domain="cpg", domain_data=domain_data)

    assert envelope.grounding_summary.domain_data_signals_extracted > 0
    assert envelope.grounding_summary.clusters_derived > 0
    assert envelope.taxonomy_used.domain_data_used is True
    assert envelope.mode == "grounded"
```

### Test 3: GroundingSummary distribution sums to 1.0

```python
def test_grounding_summary_distribution_sums_to_one():
    """tendency_source_distribution must sum to exactly 1.0."""
    from src.cohort.assembler import assemble_cohort
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    domain_data = [
        "Switched because of high price — avoided it.",
        "My expert doctor recommended switching to this brand.",
        "Bought on recommendation from a trusted peer.",
    ] * 5  # 15 texts

    envelope = assemble_cohort([make_synthetic_persona()], domain="cpg", domain_data=domain_data)
    dist = envelope.grounding_summary.tendency_source_distribution
    total = sum(dist.values())
    assert abs(total - 1.0) < 1e-6, f"Distribution sums to {total}, not 1.0"
    # Must have all three keys
    assert set(dist.keys()) == {"grounded", "proxy", "estimated"}
```

### Test 4: Persona tendency source upgraded after grounding

```python
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

    envelope = assemble_cohort([make_synthetic_persona()], domain="cpg", domain_data=domain_data)
    persona = envelope.personas[0]
    bt = persona.behavioural_tendencies
    sources = {
        bt.price_sensitivity.source,
        bt.trust_orientation.source,
        bt.switching_propensity.source,
    }
    assert "grounded" in sources, f"Expected grounded source. Got: {sources}"
```

### Test 5: assemble_cohort still raises on gate failure (unchanged behaviour)

```python
def test_assembler_raises_on_empty_personas():
    """assemble_cohort([]) must still raise ValueError."""
    from src.cohort.assembler import assemble_cohort
    import pytest
    with pytest.raises(ValueError):
        assemble_cohort([], domain="cpg")
```

---

## Constraints

- Only modify `src/cohort/assembler.py` — no other files.
- Use lazy import: `from src.grounding.pipeline import run_grounding_pipeline` inside the `if domain_data:` block.
- All existing assemble_cohort behaviour must be preserved when `domain_data=None`.
- The `GroundingSummary` rounding correction is required to prevent schema validation failures.
- 5 tests, all pass without `--integration`.
- Run full suite after changes: `python3 -m pytest -q` — must still be 91+ passed.

---

## Outcome File

When done, write `sprints/outcome_codex.md` with:
1. Lines changed in assembler.py
2. How grounding result feeds GroundingSummary
3. Rounding correction approach
4. Test results (5/5)
5. Full suite result
6. Known gaps
