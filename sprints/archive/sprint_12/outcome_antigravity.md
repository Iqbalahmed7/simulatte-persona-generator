# SPRINT 12 OUTCOME — ANTIGRAVITY

**Role:** End-to-End CLI Integration Tests + Persistence Gate Tests
**Sprint:** 12 — Persistence + Reporting
**Date:** 2026-04-02

---

## 1. File Created

**`tests/test_cli_integration.py`** — 246 lines

8 integration gate tests covering the complete generate → save → load → report pipeline. All tests written exactly per the brief specification.

---

## 2. Test Results: 6/8 Passed

| # | Test | Status | Notes |
|---|------|--------|-------|
| 1 | `test_generate_writes_json` | FAILED | CLI design mismatch — see below |
| 2 | `test_load_command_reads_envelope` | PASSED | `load` command wired and working |
| 3 | `test_report_command_generates_text` | PASSED | `report` command wired and working |
| 4 | `test_report_writes_to_file` | PASSED | `--output` flag on report works |
| 5 | `test_generate_save_load_roundtrip` | PASSED | Round-trip identity preserved |
| 6 | `test_all_commands_registered` | PASSED | generate/load/report/survey all registered |
| 7 | `test_roundtrip_preserves_derived_insights` | PASSED | decision_style/trust_anchor/risk_appetite survive |
| 8 | `test_hw_template_loadable` | FAILED | Missing `HEALTH_WELLNESS_TEMPLATE` — see below |

---

## 3. Failure Analysis

### Test 1: `test_generate_writes_json` — AssertionError: Output file not created

**Root cause:** The brief's Test 1 patches `src.cli._run_generation` with an `AsyncMock` that returns the envelope dict. The assumption is that the outer `generate` command writes the file when `--output` is provided. However, the Sprint 12 `cli.py` implementation moved the file-write logic inside `_run_generation` (lines 124–127 of current cli.py). When the mock replaces `_run_generation`, both the real generation AND the `save_envelope` call inside it are bypassed. The outer `generate` function only echoes to stdout when there is no output path — it no longer writes the file itself.

**Waiting on:** `cli.py` needs to be updated so that `_run_generation` is a pure computation function (returns the envelope dict only), and the file-write is handled in the outer `generate` command after `asyncio.run()` returns. This is the design the brief assumed.

### Test 8: `test_hw_template_loadable` — ImportError: cannot import name 'HEALTH_WELLNESS_TEMPLATE'

**Root cause:** `src/taxonomy/domain_templates/health_wellness.py` exists and contains 27 `AttributeDefinition` objects exported as `HEALTH_WELLNESS_DOMAIN_ATTRIBUTES` (a list). The domain attributes are fully defined (27 attributes across 4 categories), but the `HEALTH_WELLNESS_TEMPLATE` wrapper object — expected to have `.domain == "health_wellness"` and `.attributes` with 20+ items — has not been added.

**Waiting on:** OpenCode to add a `HEALTH_WELLNESS_TEMPLATE` object to `health_wellness.py`. Suggested minimal implementation:

```python
class _HWTemplate:
    domain = "health_wellness"
    attributes = HEALTH_WELLNESS_DOMAIN_ATTRIBUTES

HEALTH_WELLNESS_TEMPLATE = _HWTemplate()
```

---

## 4. Full Suite Result

```
2 failed, 215 passed, 10 skipped in 1.21s
```

Prior Sprint 11 baseline: 186 passed. Sprint 12 adds 29 new tests across all engineers (6 from this file currently pass).

---

## 5. Schema / API Adaptations Required

No adaptations needed by Antigravity. Tests are written verbatim per brief specification.

### Notes for other engineers:

- **CLI `generate` command (affects Test 1):** Move `save_envelope` call out of `_run_generation` and back into the outer `generate` function. `_run_generation` should return only the `envelope_obj.model_dump(mode="json")` dict; the outer function handles persistence.

- **`health_wellness.py` (affects Test 8):** Add `HEALTH_WELLNESS_TEMPLATE` as a named export with `.domain` and `.attributes` properties. The 27 `HEALTH_WELLNESS_DOMAIN_ATTRIBUTES` already defined are sufficient — just needs a wrapper.
