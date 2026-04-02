# Sprint 13 — G7/G8 Gate Threshold Scaling: Outcome

## Summary

Scaled G7 distinctiveness and G8 type-coverage thresholds by cohort size so that normal cohorts (N=5–9) no longer require `--skip-gates`.

---

## Files Modified

### 1. `src/cohort/distinctiveness.py`

- Added `_auto_threshold(n: int) -> float` helper that returns the correct threshold for cohort size n:
  - N <= 3: 0.10
  - N <= 5: 0.15
  - N <= 9: 0.25
  - N >= 10: 0.35
- Changed `check_distinctiveness()` signature: `threshold: float = 0.35` -> `threshold: float | None = None`
- When `threshold is None` (the default), the function calls `_auto_threshold(len(personas))` before proceeding.
- Updated docstring to describe the auto-scale table.

### 2. `src/cohort/type_coverage.py`

- Updated `_COVERAGE_RULES` dict:
  - `{3: 3, 5: 4, 10: 8}` -> `{3: 2, 5: 3, 10: 8}`
- Replaced `_required_types()` with explicit boundary logic:
  - N < 3: return 1
  - 3 <= N < 5: return 2
  - 5 <= N < 10: return 3
  - N >= 10: return 8
- Updated `check_type_coverage()` docstring to reflect new rules.

### 3. `src/schema/validators.py`

- `g7_distinctiveness()`: updated docstring from "> 0.35" to "threshold scales by cohort size (0.10-0.35)". No logic change — the call to `check_distinctiveness(personas)` now auto-scales.
- `g8_type_coverage()`: updated docstring and replaced the local `_COVERAGE_RULES` mirror (`{3: 3, 5: 4, 10: 8}` -> `{3: 2, 5: 3, 10: 8}`) and replaced the `if n >= 10 / else get(n)` block with the same 4-branch boundary logic as `_required_types()`.

### 4. `tests/test_cohort.py`

- `test_g8_fails_3_personas_2_types` -> renamed to `test_g8_fails_3_personas_1_type`: updated to assert failure when all 3 personas share the same type (1 distinct type < required 2).
- `test_g8_fails_5_personas_3_types` -> renamed to `test_g8_fails_5_personas_2_types`: updated to assert failure when only 2 distinct types present for N=5 (2 < required 3).

---

## Test Results

```
217 passed, 10 skipped in 1.15s
```

All 217 tests pass. No regressions.

---

## Threshold Confirmation

### G7 Auto-scale table

| Cohort size | Threshold |
|-------------|-----------|
| N <= 3      | 0.10      |
| N <= 5      | 0.15      |
| N <= 9      | 0.25      |
| N >= 10     | 0.35      |

### G8 Type coverage rules

| Cohort size | Required distinct types |
|-------------|------------------------|
| N < 3       | 1                      |
| 3 <= N < 5  | 2                      |
| 5 <= N < 10 | 3                      |
| N >= 10     | 8                      |

Both match the spec exactly.
