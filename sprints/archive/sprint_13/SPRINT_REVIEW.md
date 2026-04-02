# Sprint 13 Review — Performance + Gate Calibration + Simulation CLI

**Sprint:** 13
**Theme:** Make the system fast, self-sufficient, and fully CLI-accessible
**Status:** COMPLETE ✅
**Date:** 2026-04-02
**Test Suite:** 233 passed, 10 skipped (up from 217)

---

## Deliverables

### Cursor — G7/G8 Threshold Scaling
- `src/cohort/distinctiveness.py` — `_auto_threshold(n)` helper; `check_distinctiveness()` accepts `threshold: float | None = None`; auto-scales: N≤3→0.10, N≤5→0.15, N≤9→0.25, N≥10→0.35
- `src/cohort/type_coverage.py` — `_COVERAGE_RULES` updated to {3:2, 5:3, 10:8}; `_required_types()` explicit boundary logic
- `src/schema/validators.py` — g7/g8 docstrings and local rules mirror updated
- `tests/test_cohort.py` — 2 tests updated to match new failure boundaries
- **Result:** `--skip-gates` no longer needed for normal N=5 CPG cohorts

### Codex — Parallel Persona Generation
- `src/cli.py` — `_run_generation()` refactored with nested `_build_one(i)` coroutine + `asyncio.gather()`
- All personas now build concurrently; progress reported as each completes
- **Result:** ~4× speedup (5 personas ~3 min vs ~12 min)

### Goose — `simulate` CLI Command
- `src/cli.py` — `simulate` command + `_run_simulation()` async helper added
- `examples/scenario_cpg.json` — example scenario file (3 stimuli + decision_scenario)
- Uses correct `DecisionOutput` field names (`.decision`, `.reasoning_trace`) from live code
- **Result:** `python -m src.cli simulate --cohort cohort.json --scenario scenario.json` works

### OpenCode — SaaS Domain Validation
- `examples/spec_saas.json` — SaaS ICP spec stub created
- `tests/test_saas_domain.py` — 5 validation tests
- No fixes required: SaaS already fully wired, pool valid, DOMAIN_REGISTRY correct
- Discovery: `UrbanTier` has no `"tier1"` — valid values are `metro`, `tier2`, `tier3`, `rural`
- SaaS taxonomy: 191 attributes (151 base + 40 SaaS-specific)

### Antigravity — Sprint 13 Gate Tests
- `tests/test_sprint13_gates.py` — 11 tests (G7 scaling ×5, G8 scaling ×3, parallel gen ×2, simulate ×1)
- All 11 passed immediately
- Full suite 228 passed at time of run (233 after OpenCode added 5 more)

---

## Engineer Ratings

| Engineer | Task | Quality | Notes |
|----------|------|---------|-------|
| Cursor | G7/G8 scaling | 10/10 | Clean implementation, updated test fixtures correctly |
| Codex | Parallel generation | 9/10 | Clean nested closure, correct asyncio.gather usage |
| Goose | Simulate command | 9/10 | Caught DecisionOutput field name discrepancy from brief |
| OpenCode | SaaS validation | 9/10 | Thorough schema check, found tier1 not a valid UrbanTier |
| Antigravity | Gate tests | 10/10 | All 11 passed immediately, good coverage across all deliverables |

---

## Live CLI — All Commands

```bash
# Generate (now parallel, ~3 min for 5 personas; no --skip-gates needed)
python -m src.cli generate --spec spec.json --count 5 --domain cpg --mode quick --output cohort.json

# Load, report, survey (unchanged)
python -m src.cli load cohort.json
python -m src.cli report cohort.json
python -m src.cli survey --cohort cohort.json --questions examples/questions_cpg.json

# NEW: Simulate
python -m src.cli simulate --cohort cohort.json --scenario examples/scenario_cpg.json --rounds 3 --output sim_results.json
```

---

## Pending for Sprint 14 (suggestions)
- Live end-to-end test of `simulate` command against real API
- Live end-to-end test of `--domain saas` generation
- Calibration state persistence (currently always empty in envelope)
- Memory promotion surfaced in simulation output
