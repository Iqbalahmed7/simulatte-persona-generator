# SPRINT 9 BRIEF — CURSOR
**Role:** ICPSpec domain_data field + IdentityConstructor grounded mode
**Sprint:** 9 — Wire Grounding into Generation Flow
**Spec ref:** Master Spec §7 (Grounding activates from ICP Spec Section 5)
**Previous rating:** 20/20

---

## Context

Sprint 8 built the grounding pipeline as a standalone module. Sprint 9 wires it into the main generation flow. Your job is to extend `ICPSpec` in `identity_constructor.py` with a `domain_data` field so callers can pass raw review/post texts alongside their ICP spec.

**One file to modify:** `src/generation/identity_constructor.py`

---

## Change 1: Add `domain_data` to `ICPSpec`

Current `ICPSpec` (lines ~111–132):
```python
@dataclass
class ICPSpec:
    domain: str
    mode: str
    anchor_overrides: dict[str, Any] = field(default_factory=dict)
    persona_id_prefix: str = "default"
    persona_index: int = 1
```

New `ICPSpec` — add one field with a default of `None`:
```python
@dataclass
class ICPSpec:
    domain: str
    mode: str
    anchor_overrides: dict[str, Any] = field(default_factory=dict)
    persona_id_prefix: str = "default"
    persona_index: int = 1
    domain_data: list[str] | None = None
    """Raw text strings (reviews, posts) for grounding. When provided and
    mode='grounded', assemble_cohort() will run the grounding pipeline to
    upgrade tendency sources from 'proxy' to 'grounded'."""
```

---

## Change 2: Validate mode="grounded" requires domain_data at cohort level (not build level)

The `build()` method does NOT run grounding itself — grounding is a cohort-level operation (clustering needs all personas). However, add a note in the docstring of `build()` to document this:

Add this line to the `build()` docstring after "Returns a validated PersonaRecord.":
```
If icp_spec.mode == "grounded", the returned persona will have mode="grounded"
but tendency sources will still be "proxy" until assemble_cohort() is called
with domain_data — which upgrades tendencies via the grounding pipeline.
```

No other changes to `build()` logic.

---

## Change 3: GENERATOR_VERSION bump

Update the version constant:
```python
GENERATOR_VERSION = "2.1.0"   # was "2.0.0"
```

---

## Tests: `tests/test_icp_spec_grounded.py`

### Test 1: ICPSpec accepts domain_data

```python
def test_icp_spec_accepts_domain_data():
    from src.generation.identity_constructor import ICPSpec
    spec = ICPSpec(
        domain="cpg",
        mode="grounded",
        domain_data=["I bought this because it was affordable.", "Switched brands due to price."],
    )
    assert spec.domain_data is not None
    assert len(spec.domain_data) == 2
    assert spec.mode == "grounded"
```

### Test 2: domain_data defaults to None

```python
def test_icp_spec_domain_data_defaults_to_none():
    from src.generation.identity_constructor import ICPSpec
    spec = ICPSpec(domain="saas", mode="quick")
    assert spec.domain_data is None
```

### Test 3: ICPSpec backward compatible (no domain_data = no change)

```python
def test_icp_spec_backward_compatible():
    """Existing callers with no domain_data field still work."""
    from src.generation.identity_constructor import ICPSpec
    spec = ICPSpec(domain="cpg", mode="simulation-ready", persona_index=3)
    assert spec.persona_id_prefix == "default"
    assert spec.persona_index == 3
    assert spec.domain_data is None
```

### Test 4: domain_data can be an empty list

```python
def test_icp_spec_domain_data_empty_list():
    from src.generation.identity_constructor import ICPSpec
    spec = ICPSpec(domain="cpg", mode="grounded", domain_data=[])
    assert spec.domain_data == []
```

### Test 5: GENERATOR_VERSION updated

```python
def test_generator_version_updated():
    from src.generation import identity_constructor
    assert identity_constructor.GENERATOR_VERSION == "2.1.0"
```

---

## Constraints

- Only modify `src/generation/identity_constructor.py` — no other files.
- Do not change any logic in `build()` beyond the docstring addition.
- `domain_data` must be the LAST field in `ICPSpec` (field ordering matters for dataclass defaults).
- 5 tests, all pass without `--integration`.
- Run full suite after your changes: `python3 -m pytest -q` — must still be 91 passed.

---

## Outcome File

When done, write `sprints/outcome_cursor.md` with:
1. Lines changed in identity_constructor.py
2. Test results (5/5)
3. Full suite result (must remain 91 passed)
4. Known gaps
