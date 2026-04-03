# SPRINT 20 BRIEF — GOOSE
**Role:** Domain Merger
**Sprint:** 20 — MiroFish Domain Taxonomy Extraction
**Spec ref:** Master Spec §6 (Three-layer taxonomy, Filling Order), Constitution P8 (domain-agnostic core)
**Previous rating:** 20/20

---

## Context

Cursor extracts domain attributes. Codex ranks and selects them. Your job is to merge the selected domain attributes into the existing taxonomy structure so that `attribute_filler.py` can use the combined taxonomy without any changes to its interface.

**Critical constraint (P8):** The base taxonomy categories (`psychology`, `values`, `social`, `lifestyle`, `identity`, `decision_making`) must NEVER be mutated. Domain attributes go into a new `domain_specific` key only.

---

## File: `src/taxonomy/domain_merger.py`

```python
"""src/taxonomy/domain_merger.py

Merge ranked domain attributes into the base taxonomy structure.

The base taxonomy (Layer 1) is immutable. Domain attributes (Layer 2)
are added under a dedicated "domain_specific" key.

Output is the combined taxonomy dict that attribute_filler.py consumes.

Spec ref: Master Spec §6 — "Layer 2: Domain Extension (~30-80 attributes)"
Constitution P8 — "Domain-agnostic core. No product-specific attributes in base taxonomy."
"""
```

### Input / Output contract

**Input:**
- `base_taxonomy: dict` — the existing taxonomy from `src/taxonomy/base_taxonomy.py`
- `domain_attrs: list[DomainAttribute | RankedAttribute]` — the ranked list from Codex

**Output:**
- `dict` — a deep copy of `base_taxonomy` with a `domain_specific` key added:

```python
{
    "psychology": { ... },        # base — UNTOUCHED
    "values":     { ... },        # base — UNTOUCHED
    "social":     { ... },        # base — UNTOUCHED
    "lifestyle":  { ... },        # base — UNTOUCHED
    "identity":   { ... },        # base — UNTOUCHED
    "decision_making": { ... },   # base — UNTOUCHED
    "domain_specific": {          # NEW — domain Layer 2 attributes
        "pediatrician_trust": {
            "description": "...",
            "valid_range": "0.0-1.0",
            "example_values": ["...", "...", "..."],
            "signal_count": 47,
            "extraction_source": "corpus",
            "layer": 2,
        },
        # ...
    }
}
```

### Main function

```python
def merge_taxonomy(
    base: dict,
    domain_attrs: list,   # DomainAttribute or RankedAttribute — handle both
) -> dict:
    """
    Returns a new dict: deep copy of base + domain_specific key.

    Rules:
    - Never mutate base. Use copy.deepcopy(base) as starting point.
    - If base already has a "domain_specific" key (from a prior merge), REPLACE it entirely.
    - Each domain attribute becomes a key in "domain_specific", structured as shown above.
    - Add "layer": 2 to every domain attribute entry for traceability.
    - If domain_attrs is empty: return base copy with empty "domain_specific": {}.
    """
```

### Supporting function

```python
def get_domain_attribute_names(merged_taxonomy: dict) -> set[str]:
    """Return the set of attribute names in the domain_specific layer."""
    return set(merged_taxonomy.get("domain_specific", {}).keys())
```

### Conflict detection

```python
def detect_conflicts(base: dict, domain_attrs: list) -> list[str]:
    """
    Return list of domain attribute names that conflict with base taxonomy attributes.

    A conflict = same name appears in any base category AND in domain_attrs.
    This is informational only — the merger still proceeds (Codex's ranker should
    have already excluded exact duplicates, but this catches anything that slipped through).
    Conflicts are logged as warnings, not errors.
    """
```

---

## What to build

1. `detect_conflicts(base, domain_attrs) -> list[str]` — warning-only
2. `merge_taxonomy(base, domain_attrs) -> dict` — main function
3. `get_domain_attribute_names(merged_taxonomy) -> set[str]` — utility

---

## Constraints

- Use `copy.deepcopy(base)` — never mutate the input dict
- The `layer: 2` field is mandatory on every domain attribute entry (P10 — traceability)
- Log conflicts with `logging.warning(...)` — do not raise

---

## Outcome file

Write `sprints/outcome_goose.md`. Note any assumptions about DomainAttribute vs RankedAttribute handling, and confirm tests pass.
