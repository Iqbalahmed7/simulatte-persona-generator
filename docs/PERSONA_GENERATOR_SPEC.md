# Simulatte Persona Generator — Interface Specification

**Version**: 1.0  
**Date**: 2026-04-11  
**Status**: Canonical — all invocation paths must conform to this spec

---

## The Rule

Every persona generation task — whether triggered by a research study, a client project, a migration script, or a manual CLI run — must submit a single JSON object: the **PersonaGenerationBrief**. No exceptions. No ad-hoc parameter passing. No "quick mode" that skips the brief.

---

## 1. Invocation Methods

There are exactly three ways to invoke the persona generator. All three accept the same brief format and return the same result format.

### A. Python (recommended for scripts and notebooks)

```python
from src.orchestrator import invoke_persona_generator
from src.orchestrator.brief import PersonaGenerationBrief, RunIntent, SimulationScenario
import asyncio

brief = PersonaGenerationBrief(**json.load(open("brief.json")))
result = asyncio.run(invoke_persona_generator(brief))
```

Or synchronous:
```python
from src.orchestrator import invoke_persona_generator_sync

result = invoke_persona_generator_sync(brief)
```

### B. HTTP API

```bash
POST http://localhost:8000/orchestrate
Content-Type: application/json

{
  "brief": { ... }   # Same JSON as the brief file
}
```

Start the server: `uvicorn src.api.main:main --host 0.0.0.0 --port 8000`

### C. CLI

```bash
python -m src.cli generate --brief brief.json
```

All three accept the same brief JSON. All three return the same result structure.

---

## 2. The Brief — Standard Input Format

Every brief must be a JSON object with the following fields. Copy this template, fill in the values, delete the comments.

### 2.1 Minimal Brief (3 required fields)

```json
{
  "client": "Acme Corp",
  "domain": "cpg",
  "business_problem": "Why do urban parents switch baby nutrition brands within 6 months of first purchase?"
}
```

This generates 10 personas at SIGNAL tier with no simulation. Defaults apply to everything else.

### 2.2 Full Brief (all fields)

```json
{
  // ── REQUIRED ─────────────────────────────────────────────
  "client": "Acme Corp",
  "domain": "cpg",
  "business_problem": "Why do urban parents switch baby nutrition brands within 6 months of first purchase?",

  // ── SCALE ────────────────────────────────────────────────
  "count": 7,

  // ── INTENT (determines tier + cost) ──────────────────────
  "run_intent": "deliver",

  // ── DEMOGRAPHIC CONSTRAINTS ──────────────────────────────
  "anchor_overrides": {
    "location": "Portland, OR",
    "life_stage": "parent",
    "age_min": 28,
    "age_max": 42
  },

  // ── GROUNDING CORPUS (optional, strongly recommended) ────
  "corpus_path": "./data/acme/corpus.json",

  // ── SIMULATION (optional) ────────────────────────────────
  "simulation": {
    "stimuli": [
      "New organic baby cereal, $8.99/box, 'Pediatrician recommended' badge",
      "Competitor ad: 'Same nutrition, half the price'",
      "Friend's Instagram post praising a third brand"
    ],
    "decision_scenario": "Would you switch to this product for your child's daily breakfast?",
    "rounds": 1
  },

  // ── CONTROLS ─────────────────────────────────────────────
  "auto_confirm": false,
  "output_dir": "./outputs/acme_study",
  "emit_pipeline_doc": true
}
```

### 2.3 Field Reference

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `client` | string | — | **Yes** | Organisation or brand name |
| `domain` | string | — | **Yes** | One of: `cpg`, `saas`, `ecommerce`, `financial_services`, `healthcare_wellness`, `education` |
| `business_problem` | string | — | **Yes** | The research question. Copy verbatim from the study brief. Do not rewrite. |
| `count` | int (1–500) | 10 | No | Number of personas to generate |
| `run_intent` | string | `"explore"` | No | `"explore"` / `"calibrate"` / `"deliver"` / `"volume"` — see Intent table below |
| `tier_override` | string / null | null | No | Force `"deep"` / `"signal"` / `"volume"`. Overrides intent logic. Use sparingly. |
| `anchor_overrides` | object | {} | No | Lock demographic attributes: `location`, `life_stage`, `age_min`, `age_max`, `gender`, `education`, `employment` |
| `corpus_path` | string / null | null | No | Path to JSON file: `["doc1 text...", "doc2 text...", ...]` |
| `domain_data` | string[] / null | null | No | Raw text strings passed directly (alternative to corpus_path) |
| `simulation` | object / null | null | No | See Simulation section below |
| `sarvam_enabled` | bool | false | No | Enable Sarvam cultural enrichment (India personas only) |
| `mode` | string | `"deep"` | No | `"quick"` / `"deep"` / `"simulation-ready"` / `"grounded"` |
| `auto_confirm` | bool | false | No | Skip cost confirmation prompt. Set true in automated pipelines. |
| `output_dir` | string / null | null | No | Where to write cohort JSON + pipeline doc |
| `emit_pipeline_doc` | bool | true | No | Auto-generate pipeline documentation |
| `skip_gates` | bool | false | No | Skip quality gates G6–G11. Dev/debug only. |
| `max_quarantine_pct` | float (0–1) | 0.20 | No | Abort if more than this % of personas fail quality gates |
| `max_retries_per_persona` | int (0–5) | 2 | No | Regeneration attempts per failed persona |
| `persona_id_prefix` | string | `"pg"` | No | Prefix for persona IDs (e.g., `"lj"` → `lj0001`) |
| `registry_path` | string / null | null | No | Path to persona registry for reuse/drift detection |

### 2.4 Simulation Object

```json
{
  "stimuli": ["stimulus 1", "stimulus 2", "stimulus 3"],
  "decision_scenario": "Would you buy this today?",
  "rounds": 1
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `stimuli` | string[] | — | Ordered sequence of stimuli the persona encounters |
| `decision_scenario` | string / null | null | The yes/no decision question. If null, no decision is generated. |
| `rounds` | int (1–10) | 1 | Number of stimulus rounds |

### 2.5 Intent → Tier Mapping

| Intent | Tier | Use When | Cost (7 personas) |
|--------|------|----------|-------------------|
| `"deliver"` | DEEP | Final client output, research report, case study | ~$1.50 |
| `"explore"` | SIGNAL | Internal hypothesis test, quick directional read | ~$0.65 |
| `"calibrate"` | SIGNAL | Prompt tuning, taxonomy testing, benchmark comparison | ~$0.65 |
| `"volume"` | VOLUME | 100+ personas, population modelling, segmentation | ~$0.17 |

**Rule of thumb**: If the output leaves the team → `deliver`. Everything else → `explore`.

### 2.6 Corpus Format

The corpus file is a JSON array of strings. Each string is one document (interview transcript, survey response, market report excerpt, etc.):

```json
[
  "Interview: 'I switched because the old brand changed their formula and my daughter refused to eat it...'",
  "Survey open-end: 'Price is important but not if it means compromising on ingredients...'",
  "Category report: 'The organic baby food market grew 23% YoY in the Portland metro area...'"
]
```

Even 20–30 real verbatims dramatically improves grounding fidelity.

---

## 3. Cost Confirmation

Before any generation begins, the system prints a cost estimate:

```
╔══════════════════════════════════════════════════════════════╗
║  SIMULATTE PERSONA GENERATOR — COST ESTIMATE                 ║
╠══════════════════════════════════════════════════════════════╣
║  Brief:   Acme Corp / cpg                                    ║
║  Count:   7 personas                                         ║
║  Intent:  → Tier: DEEP                                       ║
║           run_intent=deliver → final client output           ║
╠══════════════════════════════════════════════════════════════╣
║  Corpus signal tagging                          $0.15         ║
║  Persona generation (7 × Sonnet)                $0.81         ║
║  Simulation — DEEP (3 stimuli × 7)              $0.67         ║
║  ────────────────────────────────────────────────            ║
║  TOTAL ESTIMATE                                 $1.63         ║
║  Per persona                                    $0.233        ║
║  Estimated time                              7–12 min         ║
║  Alt: switch to SIGNAL to save ~47%                           ║
╚══════════════════════════════════════════════════════════════╝

Proceed? [y/n] →
```

Set `auto_confirm: true` to skip this prompt in automated pipelines.

### Cost Drivers

| Component | What Drives Cost |
|-----------|-----------------|
| Pre-generation | Corpus size (signal tagging uses Haiku) |
| Generation | `count` × tier (Sonnet for all tiers, but token budgets differ) |
| Simulation | `count` × `stimuli.length` × tier (Reflect step uses Sonnet in DEEP, Haiku in SIGNAL/VOLUME) |

### Model Routing by Tier

| Step | DEEP | SIGNAL | VOLUME |
|------|------|--------|--------|
| **Generate** | Sonnet | Sonnet | Sonnet |
| **Perceive** | Haiku | Haiku | Haiku |
| **Reflect** | Sonnet | Haiku | Haiku |
| **Decide** | Sonnet | Sonnet | Haiku |

---

## 4. Standard Output

Every invocation returns a `PersonaGenerationResult` with this structure:

### 4.1 Result Envelope

```json
{
  "run_id": "pg-acme-20260411-1505-abc123",
  "cohort_id": "cohort-cpg-abc123",
  "client": "Acme Corp",
  "domain": "cpg",
  "tier_used": "deep",
  "generated_at": "2026-04-11T15:05:00Z",

  "count_requested": 7,
  "count_delivered": 7,
  "wall_clock_seconds": 485.2,

  "cost_actual": {
    "pre_generation": 0.15,
    "generation": 0.81,
    "simulation": 0.67,
    "total": 1.63
  },

  "quality_report": {
    "gates_passed": ["G6-Diversity", "G7-Distinctiveness", "G11-CalibrationState"],
    "gates_failed": [],
    "all_passed": true,
    "personas_quarantined": 0,
    "personas_regenerated": 0,
    "distinctiveness_score": 0.72,
    "grounding_state": "anchored"
  },

  "summary": "7 DEEP personas for Acme Corp (cpg) + simulation. ✓ All gates passed. $1.63 (anchored)",
  "cohort_file_path": "./outputs/acme_study/cohort-cpg-abc123.json",
  "pipeline_doc_path": "./outputs/acme_study/pipeline_docs/cohort-cpg-abc123.md",

  "personas": [ /* array of PersonaRecord — see 4.2 */ ],
  "simulation_results": { /* see 4.3 */ },
  "cohort_envelope": { /* full CohortEnvelope — see 4.4 */ }
}
```

### 4.2 PersonaRecord (per persona)

```json
{
  "persona_id": "pg0001",
  "generated_at": "2026-04-11T15:05:00Z",
  "generator_version": "v0.2.0",
  "domain": "cpg",
  "mode": "deep",

  "demographic_anchor": {
    "name": "Sarah Mitchell",
    "age": 34,
    "gender": "female",
    "location": { "country": "USA", "region": "Oregon", "city": "Portland", "urban_tier": "metro" },
    "household": { "structure": "nuclear", "size": 4, "income_bracket": "75k-120k-usd", "dual_income": true },
    "life_stage": "parent",
    "education": "undergraduate",
    "employment": "full-time"
  },

  "life_stories": [
    {
      "title": "The pediatrician warning",
      "when": "2 years ago",
      "event": "Pediatrician flagged high sugar content in trusted cereal brand",
      "lasting_impact": "Now reads every ingredient label; trusts expert authority over brand marketing"
    },
    {
      "title": "The co-op discovery",
      "when": "18 months ago",
      "event": "Found a certified organic brand through parent co-op recommendation",
      "lasting_impact": "Peer + expert endorsement together became her gold standard for trust"
    }
  ],

  "attributes": {
    "financial": {
      "budget_consciousness": { "value": 0.72, "type": "continuous", "source": "inferred" }
    },
    "psychological": {
      "optimism_bias": { "value": 0.45, "type": "continuous", "source": "sampled" }
    }
  },

  "derived_insights": {
    "decision_style": "analytical",
    "decision_style_score": 0.82,
    "trust_anchor": "authority",
    "risk_appetite": "low",
    "primary_value_orientation": "quality",
    "consistency_score": 78,
    "consistency_band": "high",
    "key_tensions": [
      "Quality vs. cost in family nutrition",
      "Trust in brands vs. evidence-based scepticism"
    ]
  },

  "behavioural_tendencies": {
    "price_sensitivity": { "band": "medium", "description": "Pays premium for certified quality", "source": "grounded" },
    "trust_orientation": {
      "weights": { "expert": 0.85, "peer": 0.70, "brand": 0.40, "ad": 0.20, "community": 0.65, "influencer": 0.30 },
      "dominant": "expert"
    },
    "switching_propensity": { "band": "low", "description": "Loyal once trust is established", "source": "grounded" },
    "objection_profile": [
      { "objection_type": "trust_deficit", "likelihood": "high", "severity": "blocking" },
      { "objection_type": "price_vs_value", "likelihood": "medium", "severity": "friction" }
    ],
    "reasoning_prompt": "Sarah evaluates products by first checking expert certifications..."
  },

  "narrative": {
    "first_person": "I'm a working parent of two in Portland. My family's wellbeing comes before brand loyalty — but I need evidence, not marketing. Two years ago my pediatrician flagged the sugar content in a cereal I'd trusted for years. I spent three weekends researching alternatives, reading clinical studies, asking other parents in my co-op. I settled on a smaller brand with third-party nutritional certification. I check every quarter that nothing has changed.",
    "third_person": "Sarah Mitchell is a 34-year-old parent in Portland, OR. She works full-time and manages a household of four. After her pediatrician flagged high sugar content in her family's trusted cereal brand, she spent weeks researching alternatives. She now relies on expert certifications and peer endorsements to evaluate products, and reviews her choices quarterly.",
    "display_name": "Sarah Mitchell"
  },

  "decision_bullets": [
    "Trusts pediatrician and expert certifications over brand messaging",
    "Reads ingredient labels before every first purchase",
    "Price ceiling: $30/month per category before reconsidering",
    "Checks quarterly — loyalty is earned, not permanent"
  ],

  "memory": {
    "core": {
      "identity_statement": "I am a working parent who combines analytical thinking with protective care for my family.",
      "key_values": ["family health", "value for money", "scientific evidence"],
      "life_defining_events": [
        { "age_when": 32, "event": "Pediatrician flagged sugar in trusted brand", "lasting_impact": "Permanently shifted to evidence-based product selection" }
      ],
      "relationship_map": {
        "primary_decision_partner": "spouse",
        "key_influencers": ["pediatrician", "parent co-op"],
        "trust_network": ["healthcare providers", "parent community", "family"]
      },
      "immutable_constraints": {
        "budget_ceiling": "$30/month per category",
        "non_negotiables": ["expert-endorsed", "transparent ingredients", "third-party certified"],
        "absolute_avoidances": ["brands with reformulation history", "unverified health claims"]
      },
      "tendency_summary": "Analytical, evidence-driven decision maker with low risk tolerance for anything family-related"
    },
    "working": {
      "observations": [],
      "reflections": [],
      "plans": [],
      "brand_memories": {},
      "simulation_state": { "current_turn": 0, "importance_accumulator": 0.0, "reflection_count": 0 }
    }
  }
}
```

### 4.3 Simulation Results

```json
{
  "simulation_id": "sim-20260411-001",
  "cohort_id": "cohort-cpg-abc123",
  "rounds": 1,
  "decision_scenario": "Would you switch to this product for your child's daily breakfast?",
  "results": [
    {
      "persona_id": "pg0001",
      "persona_name": "Sarah Mitchell",
      "rounds": [
        {
          "round": 1,
          "stimulus": "New organic baby cereal, $8.99/box, 'Pediatrician recommended' badge",
          "observation_importance": 8,
          "reflected": true,
          "reflection": "This aligns with my trust framework — expert endorsement plus reasonable price...",
          "decided": true,
          "decision": "yes",
          "confidence": 0.78,
          "reasoning": "authority-trust → price-check → expert endorsement → YES"
        }
      ]
    }
  ]
}
```

### 4.4 Cohort Envelope (top-level aggregates)

```json
{
  "cohort_id": "cohort-cpg-abc123",
  "generated_at": "2026-04-11T15:05:00Z",
  "domain": "cpg",
  "client": "Acme Corp",
  "business_problem": "Why do urban parents switch baby nutrition brands?",
  "mode": "deep",

  "taxonomy_used": {
    "base_attributes": 100,
    "domain_extension_attributes": 33,
    "total_attributes": 133,
    "domain_data_used": true
  },

  "personas": [ /* PersonaRecord[] */ ],

  "cohort_summary": {
    "decision_style_distribution": { "analytical": 0.43, "emotional": 0.29, "habitual": 0.14, "social": 0.14 },
    "trust_anchor_distribution": { "authority": 0.43, "peer": 0.29, "family": 0.14, "self": 0.14 },
    "risk_appetite_distribution": { "low": 0.43, "medium": 0.43, "high": 0.14 },
    "consistency_scores": { "mean": 74, "min": 58, "max": 82 },
    "distinctiveness_score": 0.72,
    "coverage_assessment": "Good coverage across decision styles and risk profiles",
    "dominant_tensions": ["Quality vs. cost", "Brand trust vs. evidence-based scepticism"]
  },

  "grounding_summary": {
    "tendency_source_distribution": { "grounded": 0.65, "proxy": 0.25, "estimated": 0.10 },
    "domain_data_signals_extracted": 47,
    "clusters_derived": 8
  },

  "calibration_state": {
    "status": "uncalibrated",
    "method_applied": null,
    "last_calibrated": null,
    "benchmark_source": null,
    "notes": null
  }
}
```

---

## 5. Quick-Start Examples

### Research study with 7 personas (most common)

```json
{
  "client": "Acme Corp",
  "domain": "cpg",
  "business_problem": "Why do urban parents switch baby nutrition brands within 6 months of first purchase?",
  "count": 7,
  "run_intent": "deliver",
  "anchor_overrides": {
    "life_stage": "parent",
    "age_min": 25,
    "age_max": 40
  },
  "corpus_path": "./data/acme/interview_transcripts.json",
  "simulation": {
    "stimuli": [
      "New organic baby cereal, $8.99/box, 'Pediatrician recommended'",
      "Competitor ad: 'Same nutrition, half the price'",
      "Friend's Instagram post praising a third brand"
    ],
    "decision_scenario": "Would you switch to this product?"
  },
  "auto_confirm": false,
  "output_dir": "./outputs/acme_nutrition"
}
```

### Quick hypothesis test (internal)

```json
{
  "client": "Internal",
  "domain": "saas",
  "business_problem": "How do mid-market CTOs evaluate new DevOps tools?",
  "count": 5,
  "run_intent": "explore",
  "anchor_overrides": { "employment": "full-time" },
  "auto_confirm": true
}
```

### Large-scale segmentation

```json
{
  "client": "Acme Corp",
  "domain": "ecommerce",
  "business_problem": "What drives cart abandonment in the 18-35 demographic?",
  "count": 200,
  "run_intent": "volume",
  "anchor_overrides": { "age_min": 18, "age_max": 35 },
  "auto_confirm": true,
  "skip_gates": false
}
```

### Migration from handcrafted personas

```json
{
  "client": "LittleJoys",
  "domain": "cpg",
  "business_problem": "Why do Mumbai parents switch nutrition brands for under-5s?",
  "count": 7,
  "run_intent": "deliver",
  "sarvam_enabled": true,
  "anchor_overrides": { "location": "Mumbai", "life_stage": "parent" },
  "corpus_path": "./data/littlejoys/corpus.json",
  "simulation": {
    "stimuli": ["Ad copy A", "Product detail page", "Testimonial video"],
    "decision_scenario": "Would you buy this today?"
  },
  "auto_confirm": false,
  "output_dir": "./outputs/littlejoys_migration"
}
```

---

## 6. Post-Generation Operations

After a cohort is generated, these operations can be run against it:

### Survey

```bash
POST /survey
{
  "cohort_id": "cohort-cpg-abc123",
  "questions": [
    "On a scale of 1-10, how likely are you to recommend this product?",
    "What is the single biggest barrier to purchase?"
  ]
}
```

### Additional Simulation (new stimuli on existing cohort)

```bash
POST /simulate
{
  "cohort_id": "cohort-cpg-abc123",
  "scenario": {
    "stimuli": ["New pricing: $6.99 instead of $8.99"],
    "decision_scenario": "Would you switch now?"
  }
}
```

### Calibration (against market benchmarks)

```bash
python -m src.cli calibrate \
  --cohort-path ./outputs/acme/cohort.json \
  --benchmark-conversion 0.25 \
  --benchmark-wtp-median 2500
```

### Report Generation

```bash
GET /report/cohort-cpg-abc123
```

---

## 7. What NOT to Do

| Anti-Pattern | Why It Fails | Do This Instead |
|-------------|-------------|-----------------|
| Pass persona attributes directly | Bypasses taxonomy + conditional filling → uncorrelated personas | Use `anchor_overrides` for constraints, let the generator fill the rest |
| Rewrite the business_problem | Generator tunes domain attributes based on exact wording | Copy verbatim from the study brief |
| Use DEEP for internal tests | Costs 2.3× more with no audience benefit | Use `explore` for anything that doesn't leave the team |
| Skip the corpus | Personas are plausible but ungrounded — "Wikipedia people" | Even 20 verbatims from interviews dramatically improves fidelity |
| Set `auto_confirm: true` on large runs | No cost review before spending | Leave false, review the estimate, then confirm |
| Use `tier_override` instead of `run_intent` | Bypasses the advisor's safety checks (e.g., large cohort → volume) | Set intent, let the advisor pick the tier |
| Generate personas one at a time | No cohort-level diversity/distinctiveness checks | Generate the full count in one run |
