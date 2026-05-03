# Sprint Brief — Multi-Provider LLM Routing (Quality-Aware)

**Goal:** Add OpenAI as a fallback/cost-tier provider for the persona generator
without dipping persona quality.

**Non-goal:** Provider-agnostic everywhere. Some stages stay Anthropic-pinned
forever — that's the point.

---

## What's already landed (this PR)

- `src/utils/provider_locks.py` — per-stage routing rules (high / medium / low
  sensitivity) + capability locks (web_search → anthropic).
- `src/utils/openai_client.py` — `OpenAILLMClient` implementing `BaseLLMClient`.
  Default model `gpt-4o-mini`. Surfaces `InsufficientCreditError` on quota issues.
- `src/utils/llm_router.py` — extended with two new APIs:
  - `get_client_for_stage(stage, anthropic_client, run_provider, capabilities)`
  - `pick_run_provider(primary, capabilities_needed)` — call once at run start
- `src/utils/parity_gate.py` — calibration parity gate scaffolding (scorers stubbed).
- `tests/test_provider_locks.py` — 9 invariant tests including
  "no high-sensitivity stage may be flexible".
- Legacy `get_llm_client()` API preserved — existing callers untouched.

## What still needs doing (in order)

### Phase 1 — Wire the router (no quality risk)

1. **Add `OPENAI_API_KEY` to Railway** (the-mind-api service). Until then the
   router silently falls back to Anthropic.
2. **Add `openai>=1.40` to `pilots/the-mind/api/requirements.txt`** so the
   container has the SDK.
3. **Migrate low-sensitivity callers** to `get_client_for_stage()`:
   - `src/onboarding/signal_tagger.py` → stage="signal_tag"
   - `src/taxonomy/domain_extractor.py` → stage="domain_extract"
   - `src/memory/summarisation_engine.py` → stage="summarise"
   - `pilots/the-mind/api/the_operator/enrich_extract.py` → stage="enrich_extract"

   These are the safe wins — they get the cost savings immediately because
   `prefer_cheap=True` will route to gpt-4o-mini once OPENAI_API_KEY is set.

4. **Pin run-level provider** in the entry points:
   - `src/cli.py` and `src/orchestrator/result.py` — call
     `pick_run_provider()` at run start, thread the result through every
     `get_client_for_stage(run_provider=...)` call.

### Phase 2 — Build the parity gate scorers (one per medium-sensitivity stage)

`src/utils/parity_gate.py::_score_stage()` is currently a stub. Wire stage
scorers in `src/calibration/parity_scorers/`:

- `signal_tag.py` — Jaccard similarity over predicted tag sets.
- `domain_extract.py` — Jaccard over extracted entities + schema validity.
- `summarise.py` — semantic similarity (cheap embedding) + length-ratio guard.
- `reflect.py` — judge-model agreement on insight quality.
- `perceive.py` — judge-model framing-drift score.
- `frame_score.py` — bucket-match rate on reply_probability + score MAE.

Each scorer takes `baseline_outs`, `candidate_outs`, `eval_set` and returns a
metrics dict matching `PARITY_THRESHOLDS[stage]` keys.

### Phase 3 — Build per-stage eval sets

`calibration/parity/{stage}.jsonl` — list of `{system, messages, max_tokens}`.

Source: real production traffic. Sample 100 records per stage, anonymise,
check in. These become the canonical eval set — never edit them, only append.

### Phase 4 — Run the gate, update calibrated_for

Once a stage's scorer + eval set is ready:

```bash
python -m src.utils.parity_gate run --stage signal_tag --candidate openai
```

If passes → manually update `PROVIDER_LOCKS[stage]["calibrated_for"]` to add
the candidate. Commit with the parity report attached.

If fails → leave `calibrated_for` alone. Stage stays anthropic-only until a
prompt or model change closes the gap.

### Phase 5 — Quality SLO sampling (production)

Sample 5% of completions through a Haiku judge:
- self-consistency rate (≥0.85)
- schema adherence (=1.00)
- calibration score (≥0.80, where stage has a calibration target)

If SLO drops on a fallback provider → automatically demote that provider out
of `calibrated_for` and alert. Better to fail loud than ship drift.

---

## Quality contract

The contract this design enforces:

| Stage class | Behaviour |
|---|---|
| **High-sensitivity** (decide, synthesis, respond) | Anthropic-only forever. No failover. Retry, queue, hard-fail — but never silently swap. |
| **Medium-sensitivity** (reflect, perceive, frame_score) | Failover only among providers in `calibrated_for`. Each provider must pass the parity gate before being added to that list. |
| **Low-sensitivity** (signal_tag, domain_extract, summarise, enrich_extract) | Cheapest provider in `calibrated_for`. Same gate requirement. |
| **Unknown stages** | Default Anthropic-only. Fail closed. |

Cohort coherence:
- A run picks its provider via `pick_run_provider()` ONCE at start.
- All flexible stages in that run honour the pinned provider (if calibrated).
- Half-Anthropic / half-OpenAI cohorts are rejected by design.

Cost savings come from tier routing (Haiku/gpt-4o-mini for cheap stages),
NOT from swapping the expensive ones. Per memory: 75–85% reduction stays in
play; Sonnet stays as Decide.

---

## Failure modes this design rules out

- ❌ "Credits ran low so we silently switched Decide to GPT-4o" — prevented
  by `locked_provider` on high-sensitivity stages.
- ❌ "Cohort drifted because the run failed over mid-pipeline" — prevented
  by `pick_run_provider` + `run_provider` threading.
- ❌ "We added a new flexible stage and forgot to register it" — `get_stage_rule`
  defaults unknown stages to Anthropic-locked.
- ❌ "Parity passed once but the model regressed" — Phase 5 SLO sampling
  catches drift in production and auto-demotes.

## Failure modes this design DOES NOT rule out

- Anthropic outage longer than Decide-stage retry budget → run fails. By
  design — better to fail loud than ship drifted personas.
- Eval set quality bug (parity passes but production drifts) → mitigated by
  SLO sampling in Phase 5.
- Prompt rewrites invalidating prior parity results → process gate: any
  prompt change to a flexible stage requires re-running the parity check.

---

## Acceptance criteria

- [ ] `OPENAI_API_KEY` set on Railway
- [ ] `openai>=1.40` in requirements.txt and deployed
- [ ] At least one low-sensitivity stage migrated to `get_client_for_stage()`
- [ ] One full pipeline run completes with mixed-provider routing and passes
      existing calibration tests
- [ ] Parity gate scorer + eval set checked in for at least one stage
- [ ] SLO sampling stub running in production (can be a no-op alarm initially)

## Out of scope

- Sarvam parity gate (Sarvam is a separate codepath, kept on legacy router)
- Image generation (fal.ai stays for portraits)
- Anthropic web_search alternative (Tavily/Serper) — would be a separate sprint
