# SPRINT 6 OUTCOME — ANTIGRAVITY
**Engineer:** Antigravity
**Role:** Survey Quality Gates (BV4, BV5 structural checks)
**Sprint:** 6 — One-Time Survey Modality
**Date:** 2026-04-02
**Status:** COMPLETE

---

## 1. Files Created

| File | Action | Lines |
|------|--------|-------|
| `tests/test_survey_gates.py` | Created | 157 |

No source files were created or modified — `src/modalities/survey.py` and `src/modalities/survey_report.py` were already present (authored by Codex in Sprint 6).

---

## 2. Test Results

```
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
asyncio: mode=strict
collected 4 items

tests/test_survey_gates.py::test_survey_resets_working_memory             PASSED
tests/test_survey_gates.py::test_survey_calls_decide_correct_number_of_times PASSED
tests/test_survey_gates.py::test_report_shape                             PASSED
tests/test_survey_gates.py::test_divergence_flag_majority_threshold       PASSED

============================== 4 passed in 0.49s ===============================
```

**Summary: 4 passed, 0 failed, 0 skipped**

---

## 3. Mock Strategy — How decide() Is Stubbed

All tests avoid live LLM calls. The `decide()` function is stubbed using `unittest.mock.AsyncMock`:

```python
with patch("src.modalities.survey.decide", new_callable=AsyncMock) as mock_decide:
    mock_decide.return_value = _make_mock_decision_output()
    result = await run_survey(questions, personas)
```

The patch target is `"src.modalities.survey.decide"` — the name as imported in `survey.py`, not the canonical module path `"src.cognition.decide.decide"`. This ensures the mock intercepts the actual reference used at call time.

`_make_mock_decision_output()` returns a valid `DecisionOutput` dataclass instance with realistic field values (`decision`, `confidence`, `reasoning_trace`, `gut_reaction`, `key_drivers`, `objections`, `what_would_change_mind`). Tests 3 and 4 bypass `run_survey()` entirely and build `SurveyResult` directly from `PersonaResponse` dataclass instances, so no mock is needed there.

---

## 4. Known Gaps

**Gap 1: Test 2 does not verify reset_working_memory call count.**
The test asserts `mock_decide.call_count == 15` and `len(result.responses) == 15`, but does not separately assert that `reset_working_memory` was called exactly 5 times (once per persona). The working memory reset is verified structurally by Test 1, but the integration of reset + survey in a single `run_survey()` call is not explicitly confirmed by call-count assertion.

**Gap 2: Tests use the same synthetic persona for all 5 slots in Test 2.**
`make_synthetic_persona()` always returns the same Priya Mehta record (same `persona_id`). The 5 personas in Test 2 are therefore identical objects. This is sufficient for call-count verification, but any test asserting per-persona identity uniqueness would fail. A `make_synthetic_persona(suffix=i)` variant would improve isolation.

**Gap 3: Divergence flag edge case at exactly 50% is not exhaustively tested for cohorts larger than 2.**
Tests 3 and 4 cover the 50/50 and 75/25 cases. The boundary at exactly 50% for a 4-persona cohort (2 yes, 2 no) is not covered. The implementation uses `<= 0.5` for divergence (True when tied), which matches the spec, but a dedicated test for 4-persona even split would add confidence.

**Gap 4: No test for empty personas or empty questions input.**
`run_survey([], personas)` or `run_survey(questions, [])` edge cases are not tested. The implementation would return an empty `SurveyResult`, but this is not gated.
