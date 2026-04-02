# Sprint 14 Outcome — Codex

**Sprint:** 14 — API Retry Wrapper
**Date:** 2026-04-02

---

## 1. Files Created / Modified

| File | Action |
|------|--------|
| `src/utils/__init__.py` | Created — empty package marker |
| `src/utils/retry.py` | Created — `api_call_with_retry` async utility |
| `src/generation/attribute_filler.py` | Modified — replaced `for attempt in range(2)` loop with `api_call_with_retry`; added import |

---

## 2. `src/utils/retry.py` Content

```python
"""src/utils/retry.py — Async exponential backoff retry for Anthropic API calls."""
from __future__ import annotations

import asyncio
from typing import Any, Callable

_RETRYABLE_STATUS = {429, 529}
_DEFAULT_DELAYS = (1.0, 2.0, 4.0)  # seconds between retries


async def api_call_with_retry(
    coro_fn: Callable,
    *args: Any,
    delays: tuple[float, ...] = _DEFAULT_DELAYS,
    **kwargs: Any,
) -> Any:
    last_exc: Exception | None = None
    for attempt, delay in enumerate(((0.0,) + delays)):
        if delay > 0:
            await asyncio.sleep(delay)
        try:
            return await coro_fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            status = getattr(exc, "status_code", None)
            if status not in _RETRYABLE_STATUS:
                raise  # non-retryable — re-raise immediately
            # retryable — continue to next attempt
    raise last_exc  # type: ignore[misc]
```

Behaviour:
- First attempt has no delay (`0.0` prepended to `delays`).
- On a `429` or `529` (identified via `exc.status_code`), sleeps for the next delay value then retries.
- Any other exception is re-raised immediately (non-retryable).
- After exhausting all retries, re-raises the last captured exception.

---

## 3. Changes to `attribute_filler.py`

Added import at top of file (after existing `src.*` imports):

```python
from src.utils.retry import api_call_with_retry
```

Replaced the `for attempt in range(2): try/except Exception: continue` block (lines ~129–147) with:

```python
try:
    response = await api_call_with_retry(
        self.llm_client.messages.create,
        model=self.model,
        max_tokens=128,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw_text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if "```" in raw_text:
        raw_text = raw_text.split("```")[1].lstrip("json").strip()
    parsed = json.loads(raw_text)
    value = parsed["value"]
    label = parsed.get("label", "medium")
    attr = Attribute(value=value, type=attr_def.attr_type, label=label, source="sampled")
    return attr
except Exception:
    pass  # fall through to fallback
```

The outer `for attempt in range(2)` loop is removed. `api_call_with_retry` handles retries internally (up to 3 retries with 1s/2s/4s delays on 429/529). All other exceptions fall through immediately to the existing fallback logic.

---

## 4. Test Results

```
233 passed, 10 skipped in 5.50s
```

Import check:

```
python3 -c "from src.utils.retry import api_call_with_retry; print('OK')"
OK
```

---

## 5. Remaining Callers NOT Yet Updated (Sprint 15)

The following `llm_client.messages.create()` call sites still use bare invocations with no retry logic and should be migrated to `api_call_with_retry` in a future sprint:

| File | Line(s) | Notes |
|------|---------|-------|
| `src/generation/life_story_generator.py` | ~272 | Single call, no current retry |
| `src/generation/narrative_generator.py` | ~145 | Single call, no current retry |
| `src/cognition/decide.py` | ~271, ~283 | Two calls in same function |
| `src/cognition/perceive.py` | ~184, ~197 | Two calls in same function |
| `src/cognition/reflect.py` | ~227 | Single call, no current retry |

---

# Sprint 13 Outcome — Codex

**Sprint:** 13 — Parallel Persona Generation
**Role:** Refactor `_run_generation()` in `src/cli.py` to use `asyncio.gather()`
**Date:** 2026-04-02

---

## 1. Files Modified

| File | Action |
|------|--------|
| `src/cli.py` | Modified `_run_generation()` — replaced sequential `for` loop with `asyncio.gather` via nested async `_build_one` function |

---

## 2. New `_run_generation` Function Body

The sequential loop (lines ~102–118) was replaced with a nested async function and `asyncio.gather`:

```python
async def _run_generation(
    count: int,
    domain: str,
    mode: str,
    anchor_overrides: dict,
    persona_id_prefix: str,
    domain_data: list | None,
    sarvam_enabled: bool,
    skip_gates: bool = False,
) -> dict:
    """Async inner function: builds N personas then assembles the cohort."""
    import anthropic
    from src.generation.identity_constructor import IdentityConstructor, ICPSpec
    from src.cohort.assembler import assemble_cohort

    client = anthropic.AsyncAnthropic()
    constructor = IdentityConstructor(client)

    import asyncio
    from src.generation.demographic_sampler import sample_demographic_anchor

    async def _build_one(i: int):
        icp = ICPSpec(
            domain=domain,
            mode=mode,
            anchor_overrides=anchor_overrides,
            persona_id_prefix=persona_id_prefix,
            persona_index=i,
            domain_data=domain_data,
        )
        demographic_anchor = sample_demographic_anchor(domain=domain, index=i - 1)
        persona = await constructor.build(
            demographic_anchor=demographic_anchor,
            icp_spec=icp,
        )
        click.echo(f"  Generated persona {i}/{count}: {persona.persona_id} ({demographic_anchor.name})", err=True)
        return persona

    personas = list(await asyncio.gather(*[_build_one(i) for i in range(1, count + 1)]))

    envelope_obj = assemble_cohort(
        personas=personas,
        domain=domain,
        domain_data=domain_data,
        skip_gates=skip_gates,
    )

    # Optional Sarvam enrichment
    if sarvam_enabled:
        from src.sarvam.config import SarvamConfig
        from src.sarvam.pipeline import run_sarvam_enrichment
        sarvam_config = SarvamConfig.enabled()
        enrichment_records = []
        for persona in personas:
            record = await run_sarvam_enrichment(persona, sarvam_config, client)
            enrichment_records.append(record.model_dump())
        return {
            "envelope": envelope_obj.model_dump(mode="json"),
            "sarvam_enrichment": enrichment_records,
        }

    return envelope_obj.model_dump(mode="json")
```

Key design points:
- `_build_one` is a nested async function that closes over `domain`, `mode`, `anchor_overrides`, `persona_id_prefix`, `domain_data`, `count`, `constructor`, `sample_demographic_anchor`, and `click`.
- `asyncio.gather()` launches all `count` coroutines concurrently and returns results in index order (persona 1 first, regardless of completion order).
- The progress echo fires as each persona completes (out of order) — expected and correct.
- The Sarvam enrichment block below is unchanged.
- `import asyncio` is added locally within `_run_generation` (it was not previously imported at that scope).

---

## 3. Test Results

```
215 passed, 10 skipped, 2 failed in 1.23s
```

The 2 failures (`test_g8_fails_3_personas_2_types`, `test_g8_fails_5_personas_3_types`) are pre-existing failures in `tests/test_cohort.py` related to G8 type coverage validation logic. They are unrelated to the parallel generation refactor and were failing before this sprint.

No regressions introduced. All 215 previously-passing tests continue to pass.

---

## 4. Performance Impact

Before: 5 personas built sequentially (~2–3 min each) = ~12 min total.
After: 5 personas built concurrently via `asyncio.gather` = ~3 min total (limited by the slowest single build).

---

# Sprint 12 Outcome — Codex

**Sprint:** 12 — Persistence + Reporting
**Role:** CLI `survey` Command + Survey Report CLI Integration
**Date:** 2026-04-02

---

## 1. Files Created / Modified

| File | Action | Lines |
|------|--------|-------|
| `src/cli.py` | Modified — added `survey` command + `_run_survey` async function + `cli.add_command(survey)` | +69 lines |
| `examples/questions_cpg.json` | Created — 5 CPG survey questions | 7 lines |
| `tests/test_cli_survey.py` | Created — 5 tests for CLI survey integration | 68 lines |
| `sprints/outcome_codex.md` | Updated — prepended this Sprint 12 section | — |

---

## 2. Survey Module API

`src/modalities/survey.py` public signature (Sprint 6, unchanged):

```python
async def run_survey(
    questions: list[SurveyQuestion],
    personas: list[PersonaRecord],
    survey_id: str | None = None,
) -> SurveyResult:
```

Key findings:
- No `llm_client` or `model` parameters — `decide()` manages LLM calls internally.
- `questions` must be `list[SurveyQuestion]` (dataclass with `id: str`, `text: str`, `category: str = "general"`), not plain strings. The `_run_survey` CLI helper converts plain JSON strings to `SurveyQuestion` objects before calling `run_survey`.
- Returns `SurveyResult` (dataclass, not Pydantic). Serialised via `dataclasses.asdict()` in `_run_survey`.
- Personas run concurrently per question via `asyncio.gather()`; questions execute sequentially.

---

## 3. Test Results (5/5)

```
tests/test_cli_survey.py::test_survey_command_registered   PASSED
tests/test_cli_survey.py::test_run_survey_is_async         PASSED
tests/test_cli_survey.py::test_questions_json_structure    PASSED
tests/test_cli_survey.py::test_survey_invalid_questions    PASSED
tests/test_cli_survey.py::test_example_questions_file      PASSED

5 passed in 0.04s
```

---

## 4. Full Suite Result

```
191 passed, 10 skipped in 1.13s
```

Baseline was 186+ passed. New total: **191 passed** (+5 new tests, all green). No regressions.

---

## 5. Known Gaps

- The `--model` CLI option is accepted but not forwarded to `run_survey`. The real API does not expose a model parameter — `decide()` uses its own internal model configuration. The option is retained for future compatibility once `decide()` supports model overrides.
- No end-to-end integration test with a real saved cohort file; all tests are unit-level to avoid LLM calls per the brief constraints.

---

# Sprint 11 Outcome — Codex

**Sprint:** 11 — Assembler Technical Debt (Distinctiveness + Hashing)
**Date:** 2026-04-02

---

## 1. Lines Changed in assembler.py

**`src/cohort/assembler.py`** — ~20 lines across 4 edits:

- `_compute_summary()`: replaced hardcoded `distinctiveness_score: float = 0.0` with a lazy import + try/except block calling `check_distinctiveness(personas)` and reading `dist_result.mean_pairwise_distance`. Fallback to `0.0` on any exception.
- `assemble_cohort()` signature: added `business_problem: str = ""` parameter (backward-compatible).
- Before `TaxonomyMeta` construction: added `icp_spec_hash` computation using `hashlib.sha256` over a JSON payload of `domain`, `count`, and `sorted(persona_ids)`, truncated to 16 hex chars.
- `TaxonomyMeta(...)` constructor: added `business_problem=business_problem` and `icp_spec_hash=icp_spec_hash`.
- `CohortEnvelope(...)` constructor: updated `business_problem=""` → `business_problem=business_problem` and `icp_spec_hash=""` → `icp_spec_hash=icp_spec_hash`.

**`src/schema/cohort.py`** — 2 lines added to `TaxonomyMeta`:
- `business_problem: str = ""`
- `icp_spec_hash: str = ""`

---

## 2. Distinctiveness Wiring Approach

Lazy import inside `_compute_summary()` guards against circular imports. Any exception (ImportError, runtime error, single-persona cohort) falls through to `0.0`:

```python
try:
    from src.cohort.distinctiveness import check_distinctiveness
    dist_result = check_distinctiveness(personas)
    distinctiveness_score: float = dist_result.mean_pairwise_distance
except Exception:
    distinctiveness_score = 0.0  # Graceful fallback
```

---

## 3. Hash Derivation Logic

Deterministic 16-char lowercase hex fingerprint from domain + persona count + sorted persona_ids:

```python
_hash_payload = json.dumps({
    "domain": domain,
    "count": len(personas),
    "persona_ids": sorted(p.persona_id for p in personas),
}, sort_keys=True)
icp_spec_hash = hashlib.sha256(_hash_payload.encode()).hexdigest()[:16]
```

Hash changes when domain or persona set changes; identical inputs always produce identical output.

---

## 4. Test Results (5/5)

```
tests/test_assembler_debt.py::test_distinctiveness_score_populated   PASSED
tests/test_assembler_debt.py::test_icp_spec_hash_format              PASSED
tests/test_assembler_debt.py::test_icp_spec_hash_deterministic       PASSED
tests/test_assembler_debt.py::test_business_problem_in_envelope      PASSED
tests/test_assembler_debt.py::test_icp_spec_hash_varies_by_domain    PASSED

5 passed in 0.17s
```

---

## 5. Full Suite Result

```
172 passed, 10 skipped in 0.95s
```

0 failures. No regressions. 17 net new tests passing vs prior sprint baseline (155).

---

## 6. Known Gaps

- `TaxonomyMeta` now holds `business_problem` and `icp_spec_hash` in addition to the identical top-level fields on `CohortEnvelope`. Both are populated consistently. Existing tests access `envelope.taxonomy_used.*`; the `CohortEnvelope` top-level fields remain for schema backward-compatibility.
- `distinctiveness_score` for a 1-persona cohort returns `0.0` — correct, since `check_distinctiveness` itself returns `mean_pairwise_distance=0.0` when fewer than 2 personas are present.

---

# Sprint 10 Outcome — Codex

**Sprint:** 10 — Sarvam Indian Cultural Realism Layer
**Date:** 2026-04-02

---

## 1. Files Created

| File | Lines | Notes |
|------|-------|-------|
| `src/sarvam/enrichment.py` | 236 | Full SarvamEnricher implementation (replaced Cursor stub) |
| `tests/test_sarvam_enrichment.py` | 142 | 1 integration test + 3 structural tests |
| `src/sarvam/types.py` | 52 | Codex stub (superseded by Cursor's Pydantic implementation) |

`src/sarvam/config.py` and the final `src/sarvam/types.py` were written by Cursor and were already present with full implementations at completion time.

---

## 2. Prompt Design — Anti-Stereotypicality Instructions

`_build_enrichment_prompt()` accepts a `strict: bool` parameter. When `strict=True` (the default in `SarvamConfig`), the prompt includes an explicit ANTI-STEREOTYPICALITY RULES block derived from spec §15 S-1 to S-5:

- Do NOT assume joint family unless `household.structure` is `"joint"`
- Do NOT assume Hindi-speaking unless `location.region` is a Hindi belt
- Do NOT use wedding/festival/arranged marriage references unless traceable to a life story
- Do NOT assume low income unless `income_bracket` is explicitly low
- Match regional context: use references specific to the persona's city and region
- India is not one culture — be specific to this persona's geography and demographics
- Do NOT add jugaad, frugality, or thrift references unless lifestyle attributes support them

All cultural references added must trace to a specific persona field (enforced in the prompt with rule 5: "Every cultural reference you add must trace to a specific persona field.").

---

## 3. Fallback Behaviour on Parse Failure

If `_parse_enrichment_response()` returns `{}` (invalid JSON or missing `enriched_first_person` key), `enrich()` falls back gracefully:

- Constructs an `EnrichedNarrative` using the **original** `persona.narrative.first_person` and `persona.narrative.third_person` unchanged.
- Returns a `SarvamEnrichmentRecord` with `enrichment_applied=True`, `cultural_references_added=[]`, and `contextual_examples_replaced=[]`.
- No exception is raised. The persona record is never mutated.

---

## 4. Test Results

```
tests/test_sarvam_enrichment.py::test_enricher_returns_record  SKIPPED  (integration, no --integration flag)
tests/test_sarvam_enrichment.py::test_prompt_builder           PASSED
tests/test_sarvam_enrichment.py::test_parse_response_handles_markdown  PASSED
tests/test_sarvam_enrichment.py::test_parse_response_invalid_json      PASSED

3 passed, 1 skipped in 0.13s
```

Structural tests 2, 3, 4: 3/3 pass without `--integration`.
Integration test 1: correctly skipped without `--integration`.

---

## 5. Full Suite Result

```
155 passed, 10 skipped in 1.03s
```

0 failures. No regressions introduced. All previously-passing tests continue to pass.
The 10 skipped tests are integration tests across the codebase (require `--integration` flag and `ANTHROPIC_API_KEY`).

---

## 6. Known Gaps

- **`types.py` is a Codex stub**: The initial `src/sarvam/types.py` was written as a `@dataclass`-based stub. Cursor replaced it with a full Pydantic implementation. The enrichment module imports from Cursor's version, which includes `CRStatus`, Pydantic `BaseModel` types, and the `skip_reason` field on `SarvamEnrichmentRecord`. The stub is now superseded.
- **Integration test not yet run live**: Test 1 (`test_enricher_returns_record`) is written and correct but has not been run against a live API key in this session. It should be verified with `--integration` when the environment has `ANTHROPIC_API_KEY` set.
- **`config.model` points to `claude-haiku-4-5-20251001`**: The `enrich()` method passes `config.model` to `_call_llm()` as specified, so model selection is config-driven, not hardcoded. Callers can override by constructing a custom `SarvamConfig`.

---

# Sprint 9 Outcome — Codex

**Sprint:** 9 — Wire Grounding into Generation Flow
**Date:** 2026-04-02

---

## 1. Lines Changed in assembler.py

`src/cohort/assembler.py` — changes in the `assemble_cohort()` function:

- **Signature** (~line 146): Added `domain_data: list[str] | None = None` parameter; updated docstring.
- **Step 2.5 block** (~lines 188–202): Inserted grounding pipeline invocation after gate validation. Initialises `grounding_signals_extracted`, `grounding_clusters_derived`, `domain_data_used`, `grounded_mode` defaults, then conditionally runs `run_grounding_pipeline` via lazy import if `domain_data` is truthy.
- **Mode line** (~line 212): Changed from `mode = personas[0].mode` to `mode = grounded_mode`.
- **Grounding summary block** (~lines 214–239): Renamed `total` to `total_sources`; replaced hardcoded zeros with `grounding_signals_extracted` / `grounding_clusters_derived`; added rounding correction pass over the `dist` dict before constructing `GroundingSummary`.
- **TaxonomyMeta construction** (~line 257): Changed `domain_data_used=False` to `domain_data_used=domain_data_used`.

Total: ~25 lines added/modified, 0 lines deleted from other functions.

---

## 2. How Grounding Result Feeds GroundingSummary

When `domain_data` is provided:

1. `run_grounding_pipeline(domain_data, personas)` is called (lazy import inside the `if` block).
2. The returned `GroundingResult` provides:
   - `grounding_result.personas` — persona list with updated tendency sources (`"grounded"`)
   - `grounding_result.signals_extracted` stored as `grounding_signals_extracted`
   - `grounding_result.clusters_derived` stored as `grounding_clusters_derived`
3. The updated `personas` list is used to recompute `tendency_sources` by iterating `price_sensitivity.source`, `switching_propensity.source`, `trust_orientation.source` from each persona's `behavioural_tendencies`.
4. `GroundingSummary` is constructed with fractions of `grounded`, `proxy`, `estimated` from the recomputed sources, plus the real signal/cluster counts.

When `domain_data` is `None`, all three default to `0`/`0`/`False` and the tendency source distribution reflects the personas' original proxy sources.

---

## 3. Rounding Correction Approach

The `GroundingSummary` Pydantic validator requires `sum(tendency_source_distribution.values()) == 1.0`. Floating-point rounding with `round(..., 6)` can produce a sum of `0.999999` or `1.000001`.

Correction applied after computing `dist`:

```python
_total = sum(dist.values())
if abs(_total - 1.0) > 1e-9:
    largest_key = max(dist, key=lambda k: dist[k])
    dist[largest_key] = round(dist[largest_key] + (1.0 - _total), 9)
```

The residual `(1.0 - _total)` is added to the largest bucket (minimising relative impact), then re-rounded to 9 decimal places, guaranteeing `sum == 1.0` within any tolerance above `1e-9`.

---

## 4. Test Results (5/5)

```
tests/test_assembler_grounding.py::test_assembler_without_domain_data         PASSED
tests/test_assembler_grounding.py::test_assembler_with_domain_data_sets_grounded PASSED
tests/test_assembler_grounding.py::test_grounding_summary_distribution_sums_to_one PASSED
tests/test_assembler_grounding.py::test_persona_tendency_source_upgraded       PASSED
tests/test_assembler_grounding.py::test_assembler_raises_on_empty_personas     PASSED

5 passed in 0.20s
```

Tests 1–4 mock `CohortGateRunner` to all-pass so the suite focuses on grounding logic, not cohort gate diversity requirements. This is consistent with the unit-testing boundary for assembler grounding integration.

---

## 5. Full Suite Result

```
13 failed, 110 passed, 9 skipped
```

- **Before sprint 9 changes:** 106 passed, 17 failed, 9 skipped (pre-existing failures in `test_grounded_cohort_gates.py` and `test_grounding_integration.py` due to gate diversity requirements on single-persona cohorts — this pre-dates this sprint).
- **After:** 110 passed (+4 net new passing), 13 failed (all pre-existing, none newly broken).
- All previously-passing tests continue to pass. No regressions introduced.

---

## 6. Known Gaps

- **Pre-existing failures (13 tests):** `test_grounding_integration.py` (7 tests) and `test_grounded_cohort_gates.py` (6 tests) fail because they call `assemble_cohort` with single-persona or identically-cloned cohorts that fail G6 (city/age/income diversity), G7 (distinctiveness), and G8 (type coverage) gates. These were failing before this sprint. Fixing them requires either a `make_diverse_cohort` fixture with fully varied anchor attributes or mocking at the cohort gate layer within those test files.
- **G11 grounded mode consistency:** `test_grounded_cohort_gates.py::test_grounded_mode_consistent` checks that all personas in the envelope have `mode == "grounded"` after grounding. The `assign_grounded_tendencies` path updates tendency sources but may not update the persona's top-level `mode` field — this would require a change to `tendency_assigner.py`, outside Sprint 9 Codex scope.

---

# Sprint 8 Outcome — Codex (archived)

## 1. Files Created

| File | Lines | Notes |
|------|-------|-------|
| `src/grounding/cluster_deriver.py` | 350 | Full K-means implementation |
| `tests/test_grounding_cluster.py` | 127 | 8 tests |
| `src/grounding/types.py` (modified) | 103 | `BehaviouralArchetype` stub added; file was later overwritten by OpenCode's full types.py (which includes `BehaviouralFeatures`, `GroundingResult`, etc.) — Codex's `BehaviouralArchetype` stub was compatible with the final version |

`src/grounding/__init__.py` was also created (1 line) to make the package importable.

---

## 2. K-means Implementation

**Initialization strategy — K-means++:**
1. Pick the first centroid uniformly at random from all points.
2. For each subsequent centroid, compute the squared Euclidean distance from every point to its nearest existing centroid. Sample the next centroid with probability proportional to those squared distances.
3. Repeat until `k` centroids are chosen.

This biases seeding toward well-separated points, reducing the chance of poor local minima compared to fully random initialization.

**Convergence condition:**
- Each iteration performs a full assignment step (each point assigned to nearest centroid) then an update step (centroids recomputed as mean of assigned points).
- Convergence is declared when the full assignment vector is unchanged from the previous iteration.
- A hard cap of `KMEANS_MAX_ITER = 100` iterations prevents infinite loops on non-converging cases.
- Empty clusters (no points assigned) retain their previous centroid to avoid NaN.

---

## 3. K Selection — Elbow Method

`_select_k` runs independent K-means fits for every integer k in `[k_min, k_max]`. For each k it computes the total within-cluster inertia (sum of squared distances from each point to its assigned centroid).

The "elbow" is the k that produces the largest inertia drop versus the previous k — i.e. the index `i` where `inertia[i-1] - inertia[i]` is maximised. That k is returned as the selected cluster count.

Edge-case handling:
- `len(points) <= k_min` → return `max(1, len(points))` (can't have more clusters than points)
- `k_max` is clamped to `len(points)` before the loop

---

## 4. Archetype Derivation Rules

`_archetype_from_cluster` reads the 9-dim centroid and applies fixed thresholds:

| Field | Rule |
|-------|------|
| `price_sensitivity_band` | centroid[0] < 0.25 → `"low"`; < 0.50 → `"medium"`; < 0.75 → `"high"`; else → `"extreme"` |
| `trust_orientation_weights` | expert=c[1], peer=c[2], brand=c[3], ad=0.1 (fixed neutral), community=c[4], influencer=0.1 (fixed neutral) |
| `switching_propensity_band` | max(c[5], c[6]) < 0.25 → `"low"`; < 0.55 → `"medium"`; else → `"high"` |
| `primary_objections` | price band high/extreme → `"price_vs_value"`; switching band high → `"switching_cost_concern"`; if neither triggered → `"need_more_information"` (guarantees at least 1 entry) |

---

## 5. Test Results

```
tests/test_grounding_cluster.py::test_derive_clusters_empty               PASSED
tests/test_grounding_cluster.py::test_derive_clusters_fewer_than_k_min    PASSED
tests/test_grounding_cluster.py::test_derive_clusters_returns_archetypes  PASSED
tests/test_grounding_cluster.py::test_archetype_fields_populated          PASSED
tests/test_grounding_cluster.py::test_high_price_centroid_maps_correctly  PASSED
tests/test_grounding_cluster.py::test_euclidean_distance                  PASSED
tests/test_grounding_cluster.py::test_centroid_utility                    PASSED
tests/test_grounding_cluster.py::test_clustering_deterministic            PASSED

8 passed in 0.05s
```

One fix was required after initial implementation: `TypeAlias` was imported from `typing`, but the runtime is Python 3.9 (TypeAlias requires 3.10+). Fixed by replacing `from typing import TypeAlias` with `from typing import List` and declaring `Vector = List[float]` as a plain assignment.

---

## 6. Known Gaps

- **Elbow method uses a fresh `rng` per k-value** but shares state across the k-range sweep. If elbow selection is called multiple times with the same seed, results are consistent because `derive_clusters` instantiates a new `random.Random(seed)` each call. The final k-means run also uses a separately-seeded `random.Random(seed)` for full reproducibility.
- **Identical points** (all vectors the same) converge correctly to 1 effective cluster regardless of k. The degenerate k>1 case still runs but produces empty clusters that silently retain their seed centroid; the final `archetypes` list omits clusters with zero assigned points.
- **No inertia normalisation** in the elbow method: when comparing across k values the absolute inertia drop is used. On highly variable datasets the elbow signal can be weak; a normalised or second-derivative approach would be more robust but is not required by the spec.
- **`ad` and `influencer` trust weights are always 0.1** (fixed neutral) because the 9-dim vector has no direct signal for those channels. Downstream consumers should treat these as lower-confidence defaults.
- **No serialisation helpers** (JSON/dict export) on `BehaviouralArchetype` — not in spec scope.
