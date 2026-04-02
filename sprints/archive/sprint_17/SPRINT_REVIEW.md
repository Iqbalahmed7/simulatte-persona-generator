# Sprint 17 Review — Auto-Routing, Cognitive Loop Sarvam, Deployment

**Sprint:** 17
**Theme:** Complete Sarvam routing pipeline + Production deployment config
**Status:** COMPLETE ✅
**Date:** 2026-04-02
**Test Suite:** 327 passed, 10 skipped (up from 309)

---

## Deliverables

### Cursor — Auto-wire Router into identity_constructor
- `src/generation/identity_constructor.py`:
  - `ICPSpec.sarvam_enabled: bool = False` field added
  - After Step 1 (anchor resolved), calls `get_llm_client(self.llm, sarvam_enabled=icp_spec.sarvam_enabled, country=anchor.location.country)`
  - Passes `_llm_client` to `LifeStoryGenerator.generate()` and `NarrativeGenerator.generate()`
- `tests/test_identity_constructor_routing.py` — 3 tests
- **Result:** Routing is now fully transparent — callers set `icp_spec.sarvam_enabled=True`, everything routes automatically

### Codex — Cognitive Loop Sarvam Routing
- `src/cognition/perceive.py` — `llm_client: Any = None` param; uses `.complete()` when provided
- `src/cognition/reflect.py` — same
- `src/cognition/decide.py` — same (both LLM call sites)
- `src/cognition/loop.py` — `llm_client` threaded through `run_loop()` to all three callers
- `src/cli.py` (`_simulate_persona`) — calls `get_llm_client()` and passes `llm_client=_llm_client` to `run_loop()`
- `tests/test_cognitive_loop_routing.py` — 3 signature tests
- **Result:** Sarvam routing now covers the full persona lifecycle: generation → enrichment → simulation

### Goose — Deployment Config + Client Spec Examples
- `Dockerfile` — Python 3.11-slim, installs all deps, exposes 8000, starts uvicorn
- `docker-compose.yml` — passes `ANTHROPIC_API_KEY` + `SARVAM_API_KEY` from host env; named volume for cohort persistence
- `.env.example` — template with all required/optional env vars; safe to commit
- `examples/spec_littlejoys.json` — Urban Indian Mothers segment, metro/tier2, sarvam+simulation-ready
- `examples/spec_lo_foods.json` — two segments: Health-Conscious Professionals + Diabetic Adults
- `examples/README.md` — curl + docker-compose usage examples
- **Result:** Any team can clone, set API keys in `.env`, `docker-compose up`, and start generating

### Antigravity — Sprint 17 Gate Tests
- `tests/test_sprint17_gates.py` — 12 tests: identity constructor routing×3, cognitive loop×3, deployment config×3, client specs×3
- 12/12 passed
- **Result:** All Sprint 17 deliverables verified

---

## Complete Sarvam Routing Pipeline

With Sprint 17, Sarvam routing now covers every LLM call in the persona lifecycle:

```
icp_spec.sarvam_enabled=True + country="India"
        ↓
identity_constructor.build()
  → get_llm_client() → SarvamLLMClient
  → LifeStoryGenerator.generate(llm_client=sarvam)      ← Sprint 17
  → NarrativeGenerator.generate(llm_client=sarvam)      ← Sprint 17
  → SarvamEnricher.enrich() (detects BaseLLMClient)     ← Sprint 16
        ↓
run_loop() (simulate)
  → perceive(llm_client=sarvam)                         ← Sprint 17
  → reflect(llm_client=sarvam)                          ← Sprint 17
  → decide(llm_client=sarvam)                           ← Sprint 17
```

Without `SARVAM_API_KEY` set → falls back to Anthropic + warning. Zero crashes.

---

## How to Deploy

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env: add ANTHROPIC_API_KEY and optionally SARVAM_API_KEY

# 2. Start the microservice
docker-compose up

# 3. Generate Littlejoys Indian personas
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 5, "domain": "cpg", "sarvam_enabled": true, "mode": "simulation-ready"}'
# → returns cohort_id

# 4. Run a survey on the cohort
curl -X POST http://localhost:8000/survey \
  -H "Content-Type: application/json" \
  -d '{"cohort_id": "<id>", "questions": ["Which baby brand do you trust most?"]}'

# 5. Get a report
curl http://localhost:8000/report/<id>
```

---

## Sprint Summary: Sprints 1–17

| Sprint | Theme |
|--------|-------|
| 1–9 | Core schema, generation pipeline, memory, cognition |
| 10 | Sarvam post-generation enrichment layer |
| 11 | Health & Wellness domain template |
| 12 | CLI bug fixes, live E2E |
| 13 | Parallel generation, gate calibration |
| 14 | Simulation, retry wrapper, calibration state |
| 15 | 5:3:2 stratification, full retry coverage, Sarvam CR2/CR4 |
| 16 | FastAPI microservice, Sarvam LLM router abstraction, quality parity |
| 17 | Auto-routing in identity_constructor, cognitive loop Sarvam, deployment |

## Pending for Sprint 18 (optional enhancements)
- Load test: concurrent generate requests against the API
- `POST /cohorts` list endpoint (list all stored cohorts)
- Auth middleware (API key header for production deployment)
- Sarvam live validation test (with real SARVAM_API_KEY)
- Domain templates: Finance, EdTech
