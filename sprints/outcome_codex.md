# Sprint 22 — Outcome: Codex

**Date:** 2026-04-03
**Deliverable:** `src/calibration/benchmark_anchor.py`
**Engineer:** Codex

---

## What Was Built

`src/calibration/benchmark_anchor.py` — deterministic benchmark anchoring module.

### Classes and functions delivered

**`BenchmarkReport` (dataclass)**
- Fields: `conversion_divergence`, `wtp_divergence`, `c3_passed`, `c3_warning`, `recommendations`
- `summary()` method returns a multi-line string with divergence, C3 gate result, and recommendations

**`compare_to_benchmarks(cohort_summary, benchmarks, simulated_conversion=None) -> BenchmarkReport`**
- Accepts `CohortSummary` instances or plain dicts
- When `simulated_conversion` is None: estimates from `decision_style_distribution` as sum of "emotional" + "habitual" shares; falls back to 0.5 if neither key is present
- Computes `conversion_divergence = abs(sim - bench) / bench`
- C3 gate: `c3_passed = 0.5 <= ratio <= 2.0`
- C3 warning: `c3_warning = conversion_divergence > 0.20`
- WTP divergence: if `"wtp_median"` in benchmarks, uses `consistency_scores.mean / 74` as proxy multiplier
- Builds four recommendation strings covering: >30% divergence, below 0.5x benchmark, above 2x benchmark, >20% warning

**`check_c3(simulated_conversion, benchmark_conversion) -> GateResult`**
- Returns a `GateResult` (imported from `src.validation.simulation_gates`) for gate "C3"
- `passed = 0.5 <= ratio <= 2.0`
- `warning = divergence > 0.20`
- `action_required = "Review stimulus design and tendency calibration"` when not passed, else None

---

## Import Check

```
python3 -c "from src.calibration.benchmark_anchor import BenchmarkReport, compare_to_benchmarks, check_c3; print('Import OK')"
Import OK
```

---

## Test Result

```
545 passed, 15 skipped in 5.50s
```

No regressions. All pre-existing tests continue to pass.

---

## Spec Alignment

- C2: module is the mechanism by which benchmark anchoring is applied for the first time
- C3: `check_c3()` implements the 0.5x–2x hard gate; `c3_warning` flag implements the >20% soft warning
- Deterministic: zero LLM calls
- `__init__.py` pre-existed in `src/calibration/`; module added alongside it
