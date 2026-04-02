# SPRINT 6 BRIEF — CODEX
**Role:** Survey Runner + Report
**Sprint:** 6 — One-Time Survey Modality
**Spec check:** Master Spec §1 (one-time survey modality), §9 (cognitive loop — decide), Validity Protocol BV4, BV5
**Previous rating:** 20/20

---

## Your Job This Sprint

Two files: the survey runner and the survey report formatter. This is the first complete product modality end-to-end.

---

## File 1: `src/modalities/survey.py`

### What It Does

Presents a list of questions to a persona (or all personas in a cohort) and collects responses via `decide()`. One-time survey modality: core memory only, working memory empty at start, discarded after.

### Interface

```python
from dataclasses import dataclass, field
from src.schema.persona import PersonaRecord
from src.schema.cohort import CohortEnvelope
from src.cognition.decide import DecisionOutput

@dataclass
class SurveyQuestion:
    id: str
    text: str                              # the question as presented to the persona
    category: str = "general"             # e.g. "brand_perception", "purchase_intent"

@dataclass
class PersonaResponse:
    persona_id: str
    persona_name: str
    question_id: str
    decision: str                          # DecisionOutput.decision
    confidence: int                        # DecisionOutput.confidence
    key_drivers: list[str]                 # DecisionOutput.key_drivers
    reasoning_trace: str                   # DecisionOutput.reasoning_trace
    objections: list[str]                  # DecisionOutput.objections

@dataclass
class SurveyResult:
    survey_id: str
    questions: list[SurveyQuestion]
    responses: list[PersonaResponse]       # one per persona × question
    modality: str = "one_time_survey"

async def run_survey(
    questions: list[SurveyQuestion],
    personas: list[PersonaRecord],
    survey_id: str | None = None,
) -> SurveyResult:
    """
    Run a one-time survey across all personas.

    For each persona:
    1. Reset working memory (core only — one-time survey modality)
    2. For each question: call decide(question.text, [], persona)
       - Pass empty memories list (no prior working memory)
    3. Collect PersonaResponse for each question

    survey_id defaults to f"survey-{uuid4().hex[:8]}"
    All decide() calls are awaited. Run questions per persona sequentially.
    Run personas concurrently via asyncio.gather().
    """
    ...
```

### Memory Handling

One-time survey uses **core memory only**. Working memory is empty at start and discarded after:

```python
from src.experiment.modality import reset_working_memory

# For each persona before survey:
clean_persona = reset_working_memory(persona)
# Then call decide() with empty memories list
```

### LLM Concurrency

Run one `asyncio.gather()` per question across all personas. Each persona answers Q1 concurrently, then Q2 concurrently, etc.

```python
for question in questions:
    tasks = [_answer_question(q=question, persona=p) for p in reset_personas]
    question_responses = await asyncio.gather(*tasks)
```

### Create `src/modalities/__init__.py`

Empty package init.

---

## File 2: `src/modalities/survey_report.py`

### What It Does

Takes a `SurveyResult` and formats a structured report: per-persona responses and cohort-level summary.

### Interface

```python
from src.modalities.survey import SurveyResult, PersonaResponse

@dataclass
class QuestionSummary:
    question_id: str
    question_text: str
    decision_distribution: dict[str, int]   # normalised decision → count
    avg_confidence: float
    top_shared_drivers: list[str]           # drivers appearing in >=2 personas
    divergence_flag: bool                   # True if decisions are not majority-aligned

@dataclass
class SurveyReport:
    survey_id: str
    cohort_size: int
    question_summaries: list[QuestionSummary]
    per_persona_responses: dict[str, list[PersonaResponse]]  # persona_id → responses

def generate_report(result: SurveyResult) -> SurveyReport:
    """
    Produce a structured SurveyReport from a SurveyResult.
    All computation is deterministic — no LLM calls.
    """
    ...
```

### Decision Normalization for Summary

```python
def _normalize_decision(text: str) -> str:
    t = text.lower().strip()
    if t.startswith("yes"): return "yes"
    if t.startswith("no"): return "no"
    return t[:40]  # first 40 chars as key
```

### Divergence Flag

`divergence_flag = True` if no single normalized decision accounts for >50% of responses for that question.

### Top Shared Drivers

From all `PersonaResponse.key_drivers` for a question, collect drivers that appear in responses from ≥2 distinct personas.

---

## Integration Contract

- `from src.cognition.decide import decide, DecisionOutput`
- `from src.experiment.modality import reset_working_memory`
- `from src.schema.persona import PersonaRecord`
- Model: `claude-sonnet-4-6` via `decide()` — no direct model calls in survey.py

---

## Constraints

- Working memory must be reset before each persona's survey run (one-time modality rule).
- Pass empty `memories=[]` to `decide()` — the survey does not use prior experiences.
- No LLM calls in `survey_report.py` — pure computation.
- `run_survey` is async. All `decide()` calls are awaited.

---

## Outcome File

When done, write `sprints/outcome_codex.md` with:
1. Files created (line counts)
2. Concurrency model — how asyncio.gather is used
3. Memory handling — confirm core-only, empty working memory
4. Report generation — decision normalization + divergence flag logic
5. Known gaps
