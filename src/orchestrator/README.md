# Simulatte Persona Generator — Orchestration Layer

**Single-call API for persona generation from any external program, agent, or pipeline.**

---

## Overview

The orchestration layer wraps the full persona generation pipeline into one function:
`invoke_persona_generator(brief)`.

Pass a brief. Get back a result. Everything else — tier selection, cost estimation,
quality enforcement, optional simulation, and pipeline documentation — happens automatically.

```
PersonaGenerationBrief
        │
        ▼
┌───────────────────────────────────────────┐
│        invoke_persona_generator()         │
│                                           │
│  1. TierAdvisor   → recommend tier        │
│  2. CostEstimator → estimate + confirm    │
│  3. _run_generation() → build personas    │
│  4. Quality gates → persona/cohort gates   │
│  5. _run_simulation() → optional + G12     │
│  6. PipelineDocWriter → auto-doc          │
└───────────────────────────────────────────┘
        │
        ▼
PersonaGenerationResult
  ├── personas (list[PersonaRecord dict])
  ├── cohort_envelope (CohortEnvelope dict)
  ├── cost_actual (breakdown)
  ├── quality_report (generation/cohort gates; G12 only after simulation)
  ├── simulation_results (optional)
  ├── pipeline_doc_path (auto-generated .md)
  └── summary (one-line human-readable)
```

---

## Quick Start

### Python (async)

```python
import asyncio
from src.orchestrator import invoke_persona_generator
from src.orchestrator.brief import PersonaGenerationBrief, RunIntent, SimulationScenario

brief = PersonaGenerationBrief(
    client="LittleJoys",
    domain="cpg",
    business_problem="Why do Mumbai parents switch nutrition brands for under-5s?",
    count=30,
    run_intent=RunIntent.DELIVER,        # deep tier → full Sonnet reasoning
    sarvam_enabled=True,
    anchor_overrides={"location": "Mumbai", "life_stage": "parent"},
    simulation=SimulationScenario(
        stimuli=[
            "Pediatrician-endorsed nutrition supplement for children aged 2-10",
            "Product packaging: Vitamin D + Iron, Indian pediatric certification logo",
            "Testimonial: Delhi mother says her son has more energy",
            "Price: Rs 649/month on Flipkart and Amazon",
            "Limited offer: first month free on subscription",
        ],
        decision_scenario="Would you purchase a trial pack of this product today?",
    ),
    auto_confirm=False,    # shows cost estimate prompt before running
)

result = asyncio.run(invoke_persona_generator(brief))

print(result.summary)
print(f"Total cost: ${result.cost_actual.total:.2f}")
print(f"Per persona: ${result.cost_per_persona:.3f}")
print(f"Gates passed: {result.quality_report.gates_passed}")
result.save("./outputs/littlejoys-run.json")
```

### Python (sync)

```python
from src.orchestrator import invoke_persona_generator_sync
from src.orchestrator.brief import PersonaGenerationBrief, RunIntent

brief = PersonaGenerationBrief(
    client="Acme",
    domain="saas",
    business_problem="Why do SMB decision-makers churn in month 3?",
    count=20,
    run_intent=RunIntent.EXPLORE,
    auto_confirm=True,   # skip the prompt for automated pipelines
)

result = invoke_persona_generator_sync(brief)
print(result.summary)
```

### REST API

Start the server:
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Call the orchestrate endpoint:
```bash
curl -X POST http://localhost:8000/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "brief": {
      "client": "LittleJoys",
      "domain": "cpg",
      "business_problem": "Why do Mumbai parents switch nutrition brands?",
      "count": 10,
      "run_intent": "deliver",
      "auto_confirm": true
    }
  }'
```

---

## PersonaGenerationBrief — Full Reference

| Field | Type | Default | Description |
|---|---|---|---|
| `client` | str | **required** | Organisation / brand name |
| `domain` | str | **required** | `cpg`, `saas`, `ecommerce`, `healthcare`, … |
| `business_problem` | str | **required** | Research question this cohort answers |
| `count` | int | 10 | Number of personas (1–500) |
| `run_intent` | RunIntent | `explore` | Drives tier: `explore`/`calibrate`→SIGNAL, `deliver`→DEEP, `volume`→VOLUME |
| `tier_override` | str\|None | None | Force `deep`/`signal`/`volume` regardless of intent |
| `mode` | str | `deep` | Build depth: `quick`/`deep`/`simulation-ready`/`grounded` |
| `anchor_overrides` | dict | `{}` | Forced demographic values, e.g. `{"location": "Mumbai"}` |
| `persona_id_prefix` | str | `pg` | Prefix in persona_id strings |
| `sarvam_enabled` | bool | False | Enable Sarvam cultural enrichment (India personas) |
| `corpus_path` | path\|None | None | Path to JSON corpus for signal tagging + grounding |
| `domain_data` | list\[str\]\|None | None | Raw text strings passed directly |
| `simulation` | SimulationScenario\|None | None | Stimuli + decision_scenario to run after generation |
| `skip_gates` | bool | False | Skip cohort validation gates (dev/debug only) |
| `max_quarantine_pct` | float | 0.20 | Abort if >X% of personas fail quality checks |
| `output_dir` | path\|None | `COHORT_STORE_DIR` | Where to write cohort JSON + pipeline docs |
| `auto_confirm` | bool | False | Skip cost-estimate prompt (use `True` for automation) |
| `emit_pipeline_doc` | bool | True | Auto-generate pipeline documentation note |
| `registry_path` | path\|None | None | Persona registry for reuse + drift detection |

---

## RunIntent → Tier Mapping

| `run_intent` | Tier | Perceive | Reflect | Decide | ~Cost/persona (5 stim) |
|---|---|---|---|---|---|
| `explore` | SIGNAL | Haiku | Haiku | Sonnet | ~$0.051 |
| `calibrate` | SIGNAL | Haiku | Haiku | Sonnet | ~$0.051 |
| `deliver` | DEEP | Haiku | Sonnet | Sonnet | ~$0.096 |
| `volume` | VOLUME | Haiku | Haiku | Haiku | ~$0.024 |

Tier affects simulation phase only. Generation always uses Sonnet.

---

## Cost Estimate Output (example)

```
╔══════════════════════════════════════════════════════════╗
║  SIMULATTE PERSONA GENERATOR — COST ESTIMATE             ║
╠══════════════════════════════════════════════════════════╣
║  Brief:   LittleJoys / cpg                               ║
║  Count:   50 personas                                    ║
║  Intent:  → Tier: DEEP                                   ║
║           run_intent=deliver → final client output       ║
╠══════════════════════════════════════════════════════════╣
║  Signal tagging (~500 docs)               $0.30          ║
║  Persona generation (50 × Sonnet)         $5.80          ║
║  Simulation — DEEP (5 stimuli × 50)       $4.80          ║
║  ────────────────────────────────────────────────        ║
║  TOTAL ESTIMATE                          $10.90          ║
║  Per persona                              $0.218         ║
║  Estimated time                       25–40 min          ║
║  Alt: switch to SIGNAL to save ~$2.25                    ║
╚══════════════════════════════════════════════════════════╝

Proceed? [y/n] →
```

---

## PersonaGenerationResult — Key Fields

```python
result.run_id                    # "pg-littlejoys-2026-04-11-abc123"
result.cohort_id                 # CohortEnvelope cohort_id
result.tier_used                 # "deep" | "signal" | "volume"
result.count_delivered           # actual number of personas generated
result.summary                   # one-line human-readable summary
result.cost_actual.total         # float — actual $ spent
result.cost_actual.to_dict()     # {"pre_generation": 0.48, "generation": 5.72, ...}
result.quality_report.all_passed # bool
result.quality_report.to_dict()  # full gate results
result.personas                  # list[dict] — PersonaRecord dicts
result.cohort_envelope           # full CohortEnvelope dict
result.simulation_results        # simulation output dict (or None)
result.cohort_file_path          # path to saved cohort JSON
result.pipeline_doc_path         # path to auto-generated pipeline .md
result.save("./output/run.json") # write full result to disk
result.get_persona("pg-001")     # look up a single persona by ID
result.persona_ids()             # ["pg-001", "pg-002", ...]
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ Yes | — | Anthropic API key |
| `SARVAM_API_KEY` | If sarvam_enabled | — | Sarvam API key |
| `COHORT_STORE_DIR` | No | `/tmp/simulatte_cohorts` | Where cohorts are saved |
| `GENERATION_MODEL` | No | `claude-sonnet-4-6` | Override generation model |
| `ANTHROPIC_SONNET_PRICE_IN` | No | `3.00` | $/1M input tokens (Sonnet) |
| `ANTHROPIC_SONNET_PRICE_OUT` | No | `15.00` | $/1M output tokens (Sonnet) |
| `ANTHROPIC_HAIKU_PRICE_IN` | No | `0.80` | $/1M input tokens (Haiku) |
| `ANTHROPIC_HAIKU_PRICE_OUT` | No | `4.00` | $/1M output tokens (Haiku) |

---

## File Structure

```
src/orchestrator/
├── __init__.py            — public exports
├── brief.py               — PersonaGenerationBrief + RunIntent + SimulationScenario
├── cost_estimator.py      — CostEstimator + CostEstimate
├── tier_advisor.py        — TierAdvisor + TierAdvice
├── result.py              — PersonaGenerationResult + CostActual + QualityReport
├── pipeline_doc_writer.py — PipelineDocWriter (auto-generates .md docs)
├── invoke.py              — invoke_persona_generator() (main entry point)
└── README.md              — this file
```

---

## Using from a Claude Agent (via Agent SDK)

```python
# In your Claude agent's tool implementation
from src.orchestrator import invoke_persona_generator
from src.orchestrator.brief import PersonaGenerationBrief, RunIntent

async def run_persona_generation(
    client: str,
    domain: str,
    business_problem: str,
    count: int = 20,
    deliver: bool = False,
) -> dict:
    brief = PersonaGenerationBrief(
        client=client,
        domain=domain,
        business_problem=business_problem,
        count=count,
        run_intent=RunIntent.DELIVER if deliver else RunIntent.EXPLORE,
        auto_confirm=True,  # always True in agent context
    )
    result = await invoke_persona_generator(brief)
    return result.to_dict()
```
