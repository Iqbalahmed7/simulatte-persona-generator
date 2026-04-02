# SPRINT 8 OUTCOME — ANTIGRAVITY

**Role:** Grounding Gate Tests
**Sprint:** 8 — Grounding Pipeline
**Status:** Test file complete. All 8 tests fail due to missing dependencies from other engineers.
**Date:** 2026-04-02

---

## 1. File Created

| File | Lines |
|------|-------|
| `tests/test_grounding_gates.py` | 227 |

---

## 2. Test Results

All 8 tests were collected cleanly and attempted to run. All 8 fail with the same root cause: `ModuleNotFoundError: No module named 'src.grounding.feature_constructor'`.

```
tests/test_grounding_gates.py::test_grounding_result_shape              FAILED
tests/test_grounding_gates.py::test_grounding_summary_construction      FAILED
tests/test_grounding_gates.py::test_warning_below_threshold             FAILED
tests/test_grounding_gates.py::test_no_warning_above_threshold          FAILED
tests/test_grounding_gates.py::test_g11_tendency_sources_valid          FAILED
tests/test_grounding_gates.py::test_archetype_count_within_bounds       FAILED
tests/test_grounding_gates.py::test_pipeline_preserves_persona_id       FAILED
tests/test_grounding_gates.py::test_archetype_centroid_9_dims           FAILED

8 failed in 0.30s
```

The failure is uniform: `pipeline.py` (OpenCode) exists and imports correctly, but it lazily imports `src.grounding.feature_constructor` (Goose) at call time, which is not yet delivered. This blocks all pipeline execution.

### Per-test failure classification

| # | Test | Expected Outcome | Blocking Dependency |
|---|------|-----------------|-------------------|
| 1 | `test_grounding_result_shape` | Pass | `feature_constructor`, `cluster_deriver`, `tendency_assigner` (Goose/Codex) |
| 2 | `test_grounding_summary_construction` | Pass | Same + `types.py` full types (OpenCode) |
| 3 | `test_warning_below_threshold` | Pass | `feature_constructor`, `cluster_deriver`, `tendency_assigner` |
| 4 | `test_no_warning_above_threshold` | Pass | Same |
| 5 | `test_g11_tendency_sources_valid` | Pass | Same |
| 6 | `test_archetype_count_within_bounds` | Pass | Same |
| 7 | `test_pipeline_preserves_persona_id` | Pass | Same |
| 8 | `test_archetype_centroid_9_dims` | Pass | Same |

---

## 3. G11 Validation Approach

Test 5 (`test_g11_tendency_sources_valid`) validates spec rule G11 (Tendency Source Gate).

**Sources checked:** Three fields on `persona.behavioural_tendencies`:
- `bt.price_sensitivity.source`
- `bt.trust_orientation.source`
- `bt.switching_propensity.source`

**Valid literal set:** `{"grounded", "proxy", "estimated"}` — matching `TendencySource` in `src/schema/persona.py`.

Each persona in `result.personas` is iterated. For each, all three sources are asserted to be members of the valid set, with a descriptive failure message if not. The test uses 15 input texts (3 texts x 5 repeats) spanning trust citations, price signals, and friend recommendations to exercise the full tendency assignment logic.

---

## 4. GroundingSummary Construction — Fraction Computation (Test 2)

After running the pipeline, the test reads the `source` field from all three tendency bands on the updated persona:

```python
sources = [
    bt.price_sensitivity.source,      # "grounded" | "proxy" | "estimated"
    bt.trust_orientation.source,
    bt.switching_propensity.source,
]
```

Fractions are computed as simple proportions over the fixed list of 3 tendencies:

- `grounded_frac = sources.count("grounded") / 3`
- `proxy_frac    = sources.count("proxy") / 3`
- `estimated_frac = 1.0 - grounded_frac - proxy_frac`

The `estimated_frac` is derived as the remainder rather than counted directly, ensuring the three fractions sum to exactly 1.0 regardless of floating-point accumulation. The resulting `GroundingSummary` is constructed with Pydantic, which validates: keys are exactly `{"grounded", "proxy", "estimated"}`, all values are in [0.0, 1.0], and the sum is 1.0 +/- 1e-6. If the Pydantic constructor does not raise, the test passes.

---

## 5. Known Gaps

### Missing modules (other engineers)

The following modules are not yet delivered and are required for all 8 tests to pass:

| Module | Engineer | Stage |
|--------|----------|-------|
| `src/grounding/feature_constructor.py` | Goose | Stage 2 — feature construction |
| `src/grounding/cluster_deriver.py` | Codex | Stage 3 — K-means clustering |
| `src/grounding/tendency_assigner.py` | Goose | Stage 4 — tendency assignment |
| `src/grounding/types.py` (full version) | OpenCode | Shared types contract |

The current `types.py` is a stub containing only `Signal` and `SignalType`. The full version must export `BehaviouralFeatures`, `BehaviouralArchetype`, and `GroundingResult` for `pipeline.py` to import cleanly at module load time.

### Test 4 signal-count guarantee

Test 4 uses 200 texts each containing the word "costs" (matched via the `cost` substring in `PRICE_KEYWORDS`). The `signal_extractor` guarantees at least 1 signal per non-empty text, so 200 texts produce >= 200 signals. This is reliable.

### No integration flag required

All 8 tests are designed to run without `--integration`. They call `run_grounding_pipeline` directly and rely entirely on keyword-based, LLM-free pipeline stages. Once the missing modules are delivered, all 8 should pass unconditionally in any CI environment.
