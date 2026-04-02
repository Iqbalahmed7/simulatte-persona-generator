# Simulatte Persona Generator — Example Specs

This directory contains client ICP spec files and scenario/question examples for use with the Simulatte Persona Generator CLI and API.

## Spec Files

### spec_india_cpg.json
Generic India CPG spec. Use this as a baseline for any Indian consumer goods persona generation run. Sarvam-enabled. Suitable as a starting point before narrowing to a specific client ICP.

### spec_littlejoys.json
Littlejoys baby and child care ICP. Targets urban Indian mothers (ages 24-38) in metro and tier-2 cities. Covers nuclear and joint household types. Key attributes include safety consciousness, brand trust, and digital research behaviour. Sarvam-enabled for authentic Indian cultural context. Simulation-ready for multi-round product interaction studies.

### spec_lo_foods.json
Lo! Foods health snack ICP. Two segments: (1) health-conscious urban professionals following high-protein or keto diets, and (2) diabetic/pre-diabetic adults managing blood sugar through low-carb eating. Both segments are Sarvam-enabled and simulation-ready to test purchase decision scenarios around adoption barriers and health-benefit tradeoffs.

## Other Files

- **questions_cpg.json** — Survey question set for CPG domain personas
- **scenario_cpg.json** — Simulation scenario for CPG product decision-making
- **spec_saas.json** — Generic SaaS ICP spec (non-Indian, B2B)

## Usage

### CLI

```bash
# Generate 5 Littlejoys personas
python -m src.cli generate \
  --spec examples/spec_littlejoys.json \
  --count 5 \
  --domain cpg \
  --sarvam \
  --output cohort_littlejoys.json
```

### API

```bash
# Generate 5 Littlejoys personas
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 5, "domain": "cpg", "sarvam_enabled": true, "mode": "simulation-ready"}'
```

Start the API server with:

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Or with Docker Compose:

```bash
docker compose up
```
