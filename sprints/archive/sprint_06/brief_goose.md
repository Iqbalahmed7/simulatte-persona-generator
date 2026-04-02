# SPRINT 6 BRIEF — GOOSE
**Role:** Survey End-to-End Test
**Sprint:** 6 — One-Time Survey Modality
**Spec check:** Validity Protocol BV4 (interview realism), BV5 (adjacent persona distinction)
**Previous rating:** 20/20

---

## Your Job This Sprint

One file: `tests/test_survey_e2e.py`. End-to-end integration test: 5 personas × 5 questions → report. Validates BV4 and BV5. Requires real LLM calls — mark with `@pytest.mark.integration`.

---

## File: `tests/test_survey_e2e.py`

### Setup

```python
import pytest
import asyncio
from src.modalities.survey import run_survey, SurveyQuestion
from src.modalities.survey_report import generate_report
from tests.fixtures.synthetic_persona import make_synthetic_persona

SURVEY_QUESTIONS = [
    SurveyQuestion(id="q1", text="How do you feel about trying a new brand for your household staples?", category="brand_perception"),
    SurveyQuestion(id="q2", text="Would you pay a premium for a product that claims to be healthier?", category="purchase_intent"),
    SurveyQuestion(id="q3", text="When you last made a big purchase, what was the most important factor?", category="decision_drivers"),
    SurveyQuestion(id="q4", text="How much do your friends and family influence what you buy?", category="social_influence"),
    SurveyQuestion(id="q5", text="If a trusted brand launched a new product, how quickly would you try it?", category="brand_loyalty"),
]
```

### Test 1: Full Pipeline

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_survey_pipeline_completes():
    """5 personas × 5 questions → 25 responses + 5-question report."""
    personas = [make_synthetic_persona() for _ in range(5)]
    result = await run_survey(SURVEY_QUESTIONS, personas)

    assert len(result.responses) == 25
    assert len(result.questions) == 5

    report = generate_report(result)
    assert len(report.question_summaries) == 5
    assert report.cohort_size == 5
```

### Test 2: BV4 — Responses Reference Persona Identity

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_bv4_responses_reference_persona_identity():
    """
    BV4: >= 3/5 responses should reference persona-specific signals.
    Check: reasoning_trace length >= 100 chars AND contains at least one
    identity word from Priya's profile.
    """
    persona = make_synthetic_persona()
    result = await run_survey(SURVEY_QUESTIONS, [persona])

    identity_signals = ['budget', 'family', 'quality', 'price', 'children',
                        'trust', 'peer', 'expensive', 'priya', 'mehta']
    persona_responses = [r for r in result.responses if r.persona_id == persona.persona_id]

    grounded = sum(
        1 for r in persona_responses
        if len(r.reasoning_trace) >= 100
        and any(w in r.reasoning_trace.lower() for w in identity_signals)
    )
    assert grounded >= 3, f"BV4 FAIL: {grounded}/5 responses grounded"
```

### Test 3: BV5 — Adjacent Personas Produce Distinct Responses

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_bv5_adjacent_personas_produce_distinct_responses():
    """
    BV5: Two similar personas produce < 50% shared language (Jaccard) on >= 3/5 questions.
    """
    persona_a = make_synthetic_persona()
    persona_b = _make_adjacent_persona()

    result = await run_survey(SURVEY_QUESTIONS, [persona_a, persona_b])

    resp_a = {r.question_id: r for r in result.responses if r.persona_id == persona_a.persona_id}
    resp_b = {r.question_id: r for r in result.responses if r.persona_id == persona_b.persona_id}

    distinct_count = 0
    for q in SURVEY_QUESTIONS:
        words_a = set(resp_a[q.id].reasoning_trace.lower().split())
        words_b = set(resp_b[q.id].reasoning_trace.lower().split())
        if words_a | words_b:
            jaccard = len(words_a & words_b) / len(words_a | words_b)
            if jaccard < 0.50:
                distinct_count += 1

    assert distinct_count >= 3, f"BV5 FAIL: only {distinct_count}/5 questions distinct"
```

### `_make_adjacent_persona()` Helper

Build Ritu Sharma directly in this file — same Social Validator type as Priya but different demographics:
- Name: Ritu Sharma, Age: 31, City: Delhi
- Occupation: Marketing professional, no children
- Similar social_proof_bias (0.72), peer trust anchor
- Different life stories and tensions

Reuse the same PersonaRecord construction pattern from `tests/fixtures/synthetic_persona.py`. Keep the G1–G3 rules satisfied (run `PersonaValidator().validate_all(persona)` to confirm).

---

## Constraints

- All three tests are `@pytest.mark.integration` — they make real LLM calls.
- They skip automatically without `--integration` flag (conftest.py handles this).
- Keep questions short and focused to minimise API cost.
- `_make_adjacent_persona()` must pass G1–G3 (use the PersonaValidator assertion).

---

## Outcome File

When done, write `sprints/outcome_goose.md` with:
1. File created (line count)
2. BV4 — grounding strategy (what counts as identity-grounded)
3. BV5 — Jaccard threshold + how Ritu differs from Priya
4. Known gaps / flakiness risks
