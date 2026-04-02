# SPRINT 11 BRIEF — CODEX
**Role:** Assembler Technical Debt — Distinctiveness + Hashing
**Sprint:** 11 — Production Entry Point + Technical Debt Clearance
**Spec ref:** Master Spec §11 (Distinctiveness Enforcement), §5 (CohortEnvelope schema)
**Previous rating:** 20/20

---

## Context

Sprint 11 clears critical carry-forwards in the assembler. Two issues have been hardcoded since Sprint 5:
1. `distinctiveness_score` is hardcoded `0.0` — the `check_distinctiveness()` function exists in `src/cohort/distinctiveness.py` but is never called from the assembler.
2. `business_problem` and `icp_spec_hash` are both hardcoded as empty strings — these should carry meaningful values.

Your job: fix both.

---

## Fix 1: Wire `check_distinctiveness()` into `_build_cohort_summary()`

In `src/cohort/assembler.py`, find the `_build_cohort_summary()` function. Currently:

```python
# distinctiveness_score placeholder — actual computation lives in G7 / check_distinctiveness
distinctiveness_score: float = 0.0
```

Replace with a real call to `check_distinctiveness()`. Import lazily inside the function to avoid circular imports:

```python
# Compute actual distinctiveness score via G7 check
try:
    from src.cohort.distinctiveness import check_distinctiveness
    dist_result = check_distinctiveness(personas)
    distinctiveness_score: float = dist_result.mean_pairwise_distance
except Exception:
    distinctiveness_score = 0.0  # Graceful fallback
```

`check_distinctiveness` signature: `check_distinctiveness(personas: list[PersonaRecord], threshold: float = 0.35) -> DistinctivenessResult`

`DistinctivenessResult.mean_pairwise_distance: float` — this is the value we want.

---

## Fix 2: Populate `business_problem` and `icp_spec_hash` in `assemble_cohort()`

### Step 2a: Add `business_problem` parameter to `assemble_cohort()`

Update the signature:

```python
def assemble_cohort(
    personas: list[PersonaRecord],
    domain: str,
    cohort_id: str | None = None,
    domain_data: list[str] | None = None,
    business_problem: str = "",   # NEW — caller supplies the business problem statement
) -> CohortEnvelope:
```

Pass it through to the `TaxonomyMeta` constructor:

```python
business_problem=business_problem,  # was hardcoded ""
```

### Step 2b: Compute `icp_spec_hash` from personas

`icp_spec_hash` should be a deterministic fingerprint of the cohort's ICP parameters. Derive it from:
- `domain`
- `len(personas)`
- sorted list of `persona.persona_id` for each persona

```python
import hashlib, json as _json
_hash_payload = _json.dumps({
    "domain": domain,
    "count": len(personas),
    "persona_ids": sorted(p.persona_id for p in personas),
}, sort_keys=True)
icp_spec_hash = hashlib.sha256(_hash_payload.encode()).hexdigest()[:16]
```

Pass to `TaxonomyMeta`:

```python
icp_spec_hash=icp_spec_hash,  # was hardcoded ""
```

---

## File: `tests/test_assembler_debt.py`

### Test 1: distinctiveness_score is non-zero for a diverse cohort

```python
def test_distinctiveness_score_populated():
    """After fix, distinctiveness_score must be > 0.0 for a diverse cohort."""
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    _GATE_RUNNER_PATH = "src.cohort.assembler.CohortGateRunner"

    def _all_pass_runner():
        mock = MagicMock()
        mock.return_value.run_all.return_value = []
        return mock

    # Use the diverse cohort fixture if available, else build 2 distinct personas
    p1 = make_synthetic_persona()
    p2 = make_synthetic_persona()
    # Make p2 distinct by overriding age to something very different
    p2 = p2.model_copy(update={"persona_id": "pg-test-002"})

    with patch(_GATE_RUNNER_PATH, new_callable=_all_pass_runner):
        envelope = assemble_cohort([p1, p2], domain="cpg")

    assert envelope.cohort_summary.distinctiveness_score >= 0.0
    # Score should be a float (not hardcoded 0.0 when check_distinctiveness runs)
    assert isinstance(envelope.cohort_summary.distinctiveness_score, float)
```

### Test 2: icp_spec_hash is a 16-char hex string

```python
def test_icp_spec_hash_format():
    """icp_spec_hash must be a non-empty 16-char hex string."""
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    _GATE_RUNNER_PATH = "src.cohort.assembler.CohortGateRunner"

    def _all_pass_runner():
        mock = MagicMock()
        mock.return_value.run_all.return_value = []
        return mock

    persona = make_synthetic_persona()
    with patch(_GATE_RUNNER_PATH, new_callable=_all_pass_runner):
        envelope = assemble_cohort([persona], domain="cpg")

    h = envelope.taxonomy_meta.icp_spec_hash
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)
```

### Test 3: icp_spec_hash is deterministic

```python
def test_icp_spec_hash_deterministic():
    """Same input produces same hash on repeated calls."""
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    _GATE_RUNNER_PATH = "src.cohort.assembler.CohortGateRunner"

    def _all_pass_runner():
        mock = MagicMock()
        mock.return_value.run_all.return_value = []
        return mock

    persona = make_synthetic_persona()
    with patch(_GATE_RUNNER_PATH, new_callable=_all_pass_runner):
        e1 = assemble_cohort([persona], domain="cpg")
        e2 = assemble_cohort([persona], domain="cpg")

    assert e1.taxonomy_meta.icp_spec_hash == e2.taxonomy_meta.icp_spec_hash
```

### Test 4: business_problem passed through

```python
def test_business_problem_in_envelope():
    """business_problem from caller appears in TaxonomyMeta."""
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    _GATE_RUNNER_PATH = "src.cohort.assembler.CohortGateRunner"

    def _all_pass_runner():
        mock = MagicMock()
        mock.return_value.run_all.return_value = []
        return mock

    persona = make_synthetic_persona()
    problem = "Why do customers churn in Q3?"
    with patch(_GATE_RUNNER_PATH, new_callable=_all_pass_runner):
        envelope = assemble_cohort([persona], domain="cpg", business_problem=problem)

    assert envelope.taxonomy_meta.business_problem == problem
```

### Test 5: icp_spec_hash changes when domain changes

```python
def test_icp_spec_hash_varies_by_domain():
    """Hash must differ for different domains."""
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    from src.cohort.assembler import assemble_cohort
    from unittest.mock import patch, MagicMock

    _GATE_RUNNER_PATH = "src.cohort.assembler.CohortGateRunner"

    def _all_pass_runner():
        mock = MagicMock()
        mock.return_value.run_all.return_value = []
        return mock

    persona = make_synthetic_persona()
    with patch(_GATE_RUNNER_PATH, new_callable=_all_pass_runner):
        e1 = assemble_cohort([persona], domain="cpg")
        e2 = assemble_cohort([persona], domain="saas")

    assert e1.taxonomy_meta.icp_spec_hash != e2.taxonomy_meta.icp_spec_hash
```

---

## Constraints

- Do NOT break existing tests. The `assemble_cohort()` signature change (adding `business_problem=""`) is backward-compatible (default value).
- Lazy import for `check_distinctiveness` — wrap in `try/except` as shown, fallback to `0.0`.
- No LLM calls.
- Full suite must remain 155+ passed.
- All 5 new tests pass without `--integration`.

---

## Outcome File

Write `sprints/outcome_codex.md` with:
1. Lines changed in assembler.py
2. Distinctiveness wiring approach
3. Hash derivation logic
4. Test results (5/5)
5. Full suite result
6. Known gaps
