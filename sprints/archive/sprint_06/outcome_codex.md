# Sprint 6 Outcome — Codex

## 1. Files Created

| File | Lines |
|------|-------|
| `src/modalities/__init__.py` | 1 |
| `src/modalities/survey.py` | 136 |
| `src/modalities/survey_report.py` | 154 |

---

## 2. Concurrency Model

`run_survey` uses one `asyncio.gather()` call **per question**, not per persona.

```python
for question in questions:
    tasks = [_answer_question(q=question, persona=p) for p in reset_personas]
    question_responses = await asyncio.gather(*tasks)
```

All personas answer Q1 concurrently, then all answer Q2 concurrently, and so on.
Questions are sequenced; personas within each question run in parallel. This matches
the spec exactly and avoids unbounded concurrency across all questions at once.

---

## 3. Memory Handling

- `reset_working_memory(persona)` is called once per persona **before the survey loop**,
  producing `reset_personas` — a list of clean `PersonaRecord` copies.
- Core memory (`persona.memory.core`) is never touched; `reset_working_memory` only
  clears `persona.memory.working` (observations, reflections, plans, brand_memories,
  simulation_state). This satisfies §14A S18 (core memory immutability).
- `decide()` is called with `memories=[]` for every question — no prior working
  memory experiences are injected (BV4/BV5 one-time modality constraint).
- The reset personas are reused across all questions within the same survey run;
  no additional reset is needed between questions because working memory is never
  written to during a one-time survey.

---

## 4. Report Generation

### Decision Normalization

`_normalize_decision(text)` applied to `PersonaResponse.decision` before counting:

- Lowercased and stripped.
- Starts with `"yes"` → key `"yes"`.
- Starts with `"no"` → key `"no"`.
- Otherwise → first 40 characters of the lowercased string.

### Divergence Flag

```
divergence_flag = True  iff  max(decision_distribution.values()) / total_responses <= 0.5
```

A flag of `True` means no single decision label accounts for more than 50% of
responses — the cohort is genuinely split. A flag of `False` means there is a
majority-aligned decision.

### Top Shared Drivers

For each question, the code builds a `driver → set(persona_ids)` index from all
`PersonaResponse.key_drivers` across all responses. Drivers whose set has size ≥ 2
are included in `top_shared_drivers`. This guarantees that only cross-persona
signal (not one vocal persona repeating a driver) reaches the summary.

---

## 5. Known Gaps

- No retry logic in `_answer_question` beyond what `decide()` itself provides
  (decide retries once on JSON parse failure). A network-level retry wrapper could
  be added around `asyncio.gather` if needed.
- `run_survey` does not enforce a maximum cohort size; very large cohorts will
  issue all personas' `decide()` calls for a given question simultaneously. A
  semaphore-based concurrency cap could be added if rate limits become a concern.
- `generate_report` does not sort `top_shared_drivers` by frequency; order depends
  on dict iteration (insertion order). A frequency-sorted ranking would be a
  straightforward enhancement.
- No serialisation helpers (JSON/dict export) on `SurveyResult` or `SurveyReport`
  — downstream consumers must handle field extraction themselves.
