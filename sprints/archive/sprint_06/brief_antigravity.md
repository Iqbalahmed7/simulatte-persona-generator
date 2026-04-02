# SPRINT 6 BRIEF — ANTIGRAVITY
**Role:** Survey Quality Gates (BV4, BV5 structural checks)
**Sprint:** 6 — One-Time Survey Modality
**Spec check:** Validity Protocol BV4, BV5; all G1–G9, G11 on generated cohort
**Previous rating:** 20/20

---

## Your Job This Sprint

One file: `tests/test_survey_gates.py`. Structural (non-LLM) tests that verify the survey pipeline's output shape and gate compliance before live runs.

---

## File: `tests/test_survey_gates.py`

### What to Test

No LLM calls. Use mock/stub `decide()` calls via `unittest.mock.AsyncMock`. Verify that the survey pipeline correctly:
1. Resets working memory before each persona's run
2. Calls `decide()` exactly N_questions × N_personas times
3. Produces the right output shape
4. Report generation computes correct decision distribution + divergence flag

---

### Test 1: Working Memory Is Reset

```python
from unittest.mock import AsyncMock, patch
import pytest

def test_survey_resets_working_memory():
    """
    Verify reset_working_memory is called once per persona before survey.
    Working memory is empty after reset.
    """
    from src.experiment.modality import reset_working_memory
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    persona = make_synthetic_persona()
    # Plant an observation in working memory
    from src.memory.working_memory import WorkingMemoryManager
    from tests.fixtures.synthetic_observation import make_synthetic_observation
    mgr = WorkingMemoryManager()
    obs = make_synthetic_observation(content="Pre-survey observation.", importance=7)
    dirty_working = mgr.write_observation(persona.memory.working, obs)
    from src.schema.persona import Memory
    dirty_persona = persona.model_copy(update={"memory": Memory(core=persona.memory.core, working=dirty_working)})

    # Reset
    clean_persona = reset_working_memory(dirty_persona)
    assert len(clean_persona.memory.working.observations) == 0
    assert clean_persona.memory.core.identity_statement == persona.memory.core.identity_statement
```

### Test 2: decide() Call Count

```python
@pytest.mark.asyncio
async def test_survey_calls_decide_correct_number_of_times():
    """
    5 personas × 3 questions = 15 decide() calls.
    """
    from src.modalities.survey import run_survey, SurveyQuestion
    from tests.fixtures.synthetic_persona import make_synthetic_persona

    questions = [SurveyQuestion(id=f"q{i}", text=f"Question {i}?") for i in range(3)]
    personas = [make_synthetic_persona() for _ in range(5)]

    mock_output = _make_mock_decision_output()

    with patch("src.modalities.survey.decide", new_callable=AsyncMock) as mock_decide:
        mock_decide.return_value = mock_output
        result = await run_survey(questions, personas)

    assert mock_decide.call_count == 15
    assert len(result.responses) == 15
```

### Test 3: Report Shape

```python
def test_report_shape():
    """
    generate_report produces correct structure.
    """
    from src.modalities.survey import SurveyResult, SurveyQuestion, PersonaResponse
    from src.modalities.survey_report import generate_report

    # Build a synthetic SurveyResult
    questions = [SurveyQuestion(id="q1", text="Test?"), SurveyQuestion(id="q2", text="Also?")]
    responses = [
        PersonaResponse(persona_id="p1", persona_name="Alice", question_id="q1",
                        decision="Yes I would", confidence=75, key_drivers=["price"], reasoning_trace="Because price", objections=[]),
        PersonaResponse(persona_id="p2", persona_name="Bob", question_id="q1",
                        decision="No I wouldn't", confidence=60, key_drivers=["brand"], reasoning_trace="Because brand", objections=["too expensive"]),
        PersonaResponse(persona_id="p1", persona_name="Alice", question_id="q2",
                        decision="Yes", confidence=80, key_drivers=["convenience"], reasoning_trace="Convenient", objections=[]),
        PersonaResponse(persona_id="p2", persona_name="Bob", question_id="q2",
                        decision="Yes", confidence=70, key_drivers=["convenience"], reasoning_trace="Also convenient", objections=[]),
    ]
    survey_result = SurveyResult(survey_id="test-001", questions=questions, responses=responses)

    report = generate_report(survey_result)

    assert report.cohort_size == 2
    assert len(report.question_summaries) == 2

    # q1 is divergent (yes vs no) — 50/50 split
    q1_summary = next(s for s in report.question_summaries if s.question_id == "q1")
    assert q1_summary.divergence_flag is True

    # q2 is not divergent (both yes)
    q2_summary = next(s for s in report.question_summaries if s.question_id == "q2")
    assert q2_summary.divergence_flag is False

    # q2 top shared drivers: "convenience" appears in both persona responses
    assert "convenience" in q2_summary.top_shared_drivers
```

### Test 4: Divergence Flag Threshold

```python
def test_divergence_flag_majority_threshold():
    """divergence_flag is False when >50% agree, True when no majority."""
    from src.modalities.survey import SurveyResult, SurveyQuestion, PersonaResponse
    from src.modalities.survey_report import generate_report

    questions = [SurveyQuestion(id="q1", text="Q?")]
    # 3 yes, 1 no → yes is 75% → no divergence
    responses = [
        PersonaResponse(persona_id=f"p{i}", persona_name=f"P{i}", question_id="q1",
                       decision="yes" if i < 3 else "no",
                       confidence=70, key_drivers=[], reasoning_trace="trace", objections=[])
        for i in range(4)
    ]
    result = SurveyResult(survey_id="t", questions=questions, responses=responses)
    report = generate_report(result)
    assert report.question_summaries[0].divergence_flag is False
```

### Helper

```python
def _make_mock_decision_output():
    from src.cognition.decide import DecisionOutput
    return DecisionOutput(
        decision="Yes, I would.",
        confidence=70,
        reasoning_trace="Given my values and budget...",
        gut_reaction="Positive",
        key_drivers=["price", "quality"],
        objections=[],
        what_would_change_mind="If price doubled.",
    )
```

---

## Constraints

- No LLM calls. All tests use `unittest.mock.AsyncMock` to stub `decide()`.
- The patch target for `decide` must be `"src.modalities.survey.decide"` (where it's imported), not `"src.cognition.decide.decide"`.
- All tests should pass with `pytest tests/test_survey_gates.py` without `--integration`.

---

## Outcome File

When done, write `sprints/outcome_antigravity.md` with:
1. File created (line count)
2. Test results (pass/fail counts)
3. Mock strategy — how decide() is stubbed
4. Known gaps
