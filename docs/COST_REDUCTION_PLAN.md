# Simulatte Cost Reduction Plan — Multi-LLM Architecture

**Status:** Approved for implementation  
**Goal:** ~75–85% cost reduction on simulation runs with zero impact on Decide-stage quality  
**Constraint:** Sonnet 4.6 stays as the Decide model in all tiers, always. No exceptions.

---

## Current Cost Baseline (DEEP Tier, All Runs)

Per persona, 5-stimulus journey with 2 decision ticks:

| Stage   | Model      | Calls | Tokens In | Tokens Out | Cost/persona |
|---------|------------|-------|-----------|------------|--------------|
| Perceive | Haiku 4.5 | 5     | ~500      | ~256       | ~$0.007      |
| Reflect  | Sonnet 4.6 | ~4   | ~1,200    | ~512       | ~$0.045      |
| Decide   | Sonnet 4.6 | 2     | ~2,200    | ~1,024     | ~$0.044      |
| **Total** |           |       |           |            | **~$0.096**  |

At 100 personas: ~$9.60 per journey run.  
Reflect is the largest lever — it fires 80% of the time at Sonnet cost, but its output is intermediate working memory that Sonnet-Decide re-synthesises anyway.

---

## Core Principle

**Decide is the quality gate. Reflect is the working memory feed.**  
Haiku reflections are less literary but Sonnet-Decide reads full memory context and synthesises the final answer regardless. Downgrading Reflect does not degrade final output quality.

---

## Run Intent Framework — Replacing "Who Ordered It"

The ambiguity of "client run vs internal run" is resolved by classifying on **output lifecycle stage**, not on who requested it. Case study prep is internal research — it belongs in `explore`, not `deliver`.

| Intent | What it covers | Tier | Batch API |
|--------|---------------|------|-----------|
| `calibrate` | Sprint runs, benchmark sweeps, accuracy checks | SIGNAL | Yes |
| `explore` | Case study prep, scenario iteration, research runs | SIGNAL | Yes |
| `deliver` | Final client output, demo, published deck artifact | DEEP | No |

**The decision rule:** "Will this specific output file be shown to someone external, or used to make a strategic decision without re-running?" → If yes: `deliver`. If you're iterating or preparing: `explore`.

Case study prep runs are `explore` by default. When you run the version that goes into the deck, that one run is `deliver`.

### Automation in `run_case_studies.py`

The file currently hard-codes `"tier": "deep"` for all case studies. Change the default to `signal` and add a `--deliver` flag:

```bash
# Default: SIGNAL tier + eligible for batch (case study prep, iteration)
python3 run_case_studies.py --studies CS1 CS2

# Final run for deliverable: DEEP tier, real-time
python3 run_case_studies.py --studies CS1 CS2 --deliver
```

When `--deliver` is absent, tier stays SIGNAL. The intent is encoded in the flag, not in who ran it.

### Automation in sprint runners

Sprint calibration runs (`simulatte_batch_runner.py`) default to `signal` tier — this is already in the code. No change needed. Just ensure no sprint runner is overriding tier to `deep`.

---

## Phase 1 — Switch Reflect to Haiku for calibrate + explore Runs

**What:** Use SIGNAL tier (Haiku perceive + reflect, Sonnet decide) for all non-deliver runs.  
**What stays DEEP:** Only explicit `--deliver` runs.

SIGNAL tier is already implemented — it's just not being used for case studies.

**Savings:** ~47% reduction  
**Quality impact:** None on Decide outputs. Haiku reflections are less literary; Sonnet-Decide compensates.  
**Effort:** 1-line change per runner — set default tier to `signal`, add `--deliver` flag that switches to `deep`.  
**Validation:** Run 2 consecutive sprints on SIGNAL tier and confirm accuracy within ±1 pp of DEEP baseline.

---

## Phase 2 — Batch API for All Non-Real-Time Runs

**What:** Anthropic's Message Batches API gives 50% discount with a 24-hour result window.  
**Apply to:** `calibrate` and `explore` runs. Sprint calibrations already run overnight — free discount.  
**Do NOT apply to:** `deliver` runs (latency matters for demos, final exports).

**Savings:** Additional 50% on Phase 1 costs → **~74% combined reduction** for calibrate/explore.  
**Effort:** Medium — wrap Anthropic client calls in batch API format; results are file-based.  
**Dependency:** Phase 1 validated first.

---

## Phase 3 — Replace Perceive with GPT-4o Mini (Validated)

**What:** GPT-4o Mini is ~10× cheaper than Haiku for the perceive stage.  
**Why safe:** Perceive is pure pattern matching — "what from my memory is relevant to this stimulus?" It does not form opinions. Sonnet-Decide still resolves quality from the full memory context.

**Validation gate:** Run 1 sprint with Haiku-perceive vs GPT-4o Mini-perceive. If accuracy within ±1 pp, ship.  
**Savings:** ~7% additional (perceive is the smallest cost component).  
**Bonus:** Reduces single-vendor Anthropic dependency for the cheapest stage.  
**Effort:** Small — make perceive model configurable per tier.  
**Dependency:** Phase 1 + 2 stable first.

**Do NOT use Gemini for perceive or reflect.** India calibration study confirmed Gemini fails at 43–44% on cultural specificity — even as an intermediate stage it introduces cultural flattening into working memory.

---

## Phase 4 — Fine-Tuned Reflect Model (Long-Term Moat)

**What:** Distil a fine-tuned GPT-4o Mini on Sonnet-generated reflections to produce Sonnet-quality output at 10× lower cost.

**How:**
1. Collect 2,000–5,000 `(stimulus, memory_context, reflection)` triplets from existing sprint logs
2. Fine-tune GPT-4o Mini on these triplets
3. Benchmark quality: coherence, opinion specificity, persona attribute consistency
4. If validated, replace Sonnet reflect with fine-tuned model in DEEP tier

**Strategic value:** Every sprint run generates more training data. Calibration corpus (accuracy moat) becomes training corpus (cost moat). Compounding advantage.

**Savings:** ~47% on top of Phase 1 savings in DEEP tier → **~85% total reduction** at Phase 4.  
**Effort:** High — logging pipeline, fine-tuning workflow, quality evaluation.  
**Dependency:** Do not start before Sprint A-25+. More calibration data = better training signal.

---

## Cost Trajectory

| Configuration | Perceive | Reflect | Decide | Cost vs Today |
|---------------|----------|---------|--------|---------------|
| Today (all DEEP) | Haiku | Sonnet | Sonnet | 100% |
| Phase 1 (SIGNAL for explore/calibrate) | Haiku | Haiku | Sonnet | ~53% |
| Phase 1 + 2 (+ Batch API) | Haiku | Haiku | Sonnet (batch) | ~27% |
| Phase 1 + 2 + 3 (+ GPT-4o Mini perceive) | GPT-4o Mini | Haiku | Sonnet (batch) | ~25% |
| Phase 4 (fine-tuned reflect in DEEP) | GPT-4o Mini | Fine-tuned | Sonnet | ~15% |

`deliver` runs always stay DEEP and real-time (no batch). They are a small fraction of total run volume.

---

## What NOT to Do

- **Don't touch Decide.** Sonnet 4.6 stays for all tiers. This is a hard constraint.
- **Don't use Gemini** for any perceive/reflect stage. Cultural calibration failure confirmed.
- **Don't batch deliver runs.** Latency matters for demos and final exports.
- **Don't fine-tune before Sprint A-25+.** Need sufficient calibration data for training signal.
- **Don't make "who ordered it" the classification criterion.** Use output lifecycle stage instead.

---

## Implementation Checklist

### Phase 1 (Now)
- [ ] Add `--deliver` flag to `run_case_studies.py` (changes tier to `deep` when set; default `signal`)
- [ ] Verify sprint runners default to `signal` tier, not `deep`
- [ ] Run 2 sprints on SIGNAL tier; confirm accuracy within ±1 pp of DEEP baseline
- [ ] Document validation result in sprint log

### Phase 2 (After Phase 1 validated)
- [ ] Implement Anthropic Batch API wrapper for `calibrate` and `explore` runs
- [ ] Test batch result parsing and file-based output pipeline
- [ ] Integrate into sprint runner and case study runner

### Phase 3 (After Phase 2 stable)
- [ ] Make perceive model configurable per tier in loop.py / session.py
- [ ] Run 1-sprint A/B test: Haiku-perceive vs GPT-4o Mini-perceive
- [ ] If within ±1 pp, set GPT-4o Mini as perceive model for SIGNAL/explore

### Phase 4 (Sprint A-25+ data available)
- [ ] Build reflect logging pipeline: `(stimulus, memory_context, reflection)` triplets
- [ ] Collect 2,000+ triplets from sprint logs
- [ ] Fine-tune GPT-4o Mini on triplets
- [ ] Run quality benchmark vs Sonnet reflect baseline
- [ ] If validated, integrate fine-tuned model as reflect in DEEP tier
