# Benchmark Service — Integration Guide

**Version:** 1.0  
**Service location:** `services/benchmark/`  
**Default port:** `8002`  
**Purpose:** Research-grade persona quality evaluation — usable by any Simulatte product that generates or consumes personas.

---

## What This Service Does

The benchmark service evaluates a persona's psychological depth, factual discipline, and conversational authenticity by running a structured suite of AI-to-AI tests:

1. A simulated human interviewer (Haiku) asks the persona scripted questions
2. An LLM judge (Sonnet) scores each conversation against the persona's spec
3. A weighted credibility score (0–100) and grade (A/B/C/D/F) are returned

It is **stateless from the calling service's perspective** — you send a persona ID, you get back a score. The benchmark service handles everything in between.

---

## Tiers

| Tier | Tests | Est. Cost | Est. Time | Use When |
|------|-------|-----------|-----------|----------|
| `quick` | 3 | ~$0.05 | ~90s | Every generation (automated gate) |
| `standard` | 6 | ~$0.18 | ~3 min | QA pass before user sees persona |
| `research` | 10 | ~$0.40 | ~7 min | Deep evaluation, investor demos, audits |
| `custom` | caller-defined | varies | varies | Targeted testing of specific layers |

**Recommended defaults:**
- The Mind (auto, post-generation): `quick`
- The Mind (manual, "Run full benchmark" button): `standard` or `research`
- White Rabbit (cohort validation): `standard`
- Any automated regression suite: `quick`

---

## API Contract

### Base URL
```
http://localhost:8002          (local)
https://benchmark.simulatte.app  (production, when deployed)
```

### POST `/runs/stream` — Run benchmark, stream results

The primary integration endpoint. Single request, SSE response.

**Request body:**
```json
{
  "persona_id": "abc-123",
  "tier": "standard",
  "custom_tests": [],
  "persona_payload": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `persona_id` | string | yes | ID of the persona to evaluate |
| `tier` | string | no | `quick` / `standard` / `research` / `custom` (default: `standard`) |
| `custom_tests` | string[] | no | Required if `tier = "custom"`. List of test IDs to run. |
| `persona_payload` | object | no | Embed the persona JSON directly (skips fetch from The Mind). Useful for testing or when calling from a service that already has the payload. |

**Response:** `text/event-stream`

Each SSE line is a JSON `BenchmarkEvent`:

```
data: {"type":"started","run_id":"...","message":"Running 6 tests for Priya Sharma [standard]"}

data: {"type":"test_complete","run_id":"...","test_id":"identity_consistency","test_label":"Identity Consistency","score":8.5,"message":"Persona maintained coherent values across..."}

data: {"type":"test_complete","run_id":"...","test_id":"biographical_accuracy","score":9.0,...}

... (one event per test) ...

data: {"type":"complete","run_id":"...","credibility_score":82.4,"grade":"B","message":"Standard — B","report":{...full report...}}
```

**Error event:**
```
data: {"type":"error","run_id":"...","message":"Failed to fetch persona: 404"}
```

---

### GET `/runs/{run_id}` — Poll for result

Returns the current state of a run (including partial results while still running).

**Response:** `BenchmarkReport` JSON

```json
{
  "run_id": "abc-def-123",
  "persona_id": "persona-xyz",
  "persona_name": "Priya Sharma",
  "tier": "standard",
  "status": "complete",
  "credibility_score": 82.4,
  "grade": "B",
  "grade_label": "Standard — B",
  "tests": [
    {
      "test_id": "identity_consistency",
      "label": "Identity Consistency",
      "status": "passed",
      "score": 8.5,
      "weight": 0.15,
      "weighted_contribution": 12.75,
      "rationale": "Persona maintained coherent values across all 6 turns...",
      "evidence": ["\"I've always been someone who...\""],
      "flags": [],
      "duration_s": 14.2,
      "cost_usd": 0.00031
    }
  ],
  "total_cost_usd": 0.18,
  "total_duration_s": 187.4,
  "started_at": "2026-05-08T10:00:00Z",
  "completed_at": "2026-05-08T10:03:07Z"
}
```

---

### GET `/runs` — List runs

```
GET /runs
GET /runs?persona_id=abc-123
GET /runs?persona_id=abc-123&limit=10
```

Returns array of summary objects (no full test details — use `/runs/{id}` for those).

---

### GET `/health` — Liveness probe

```json
{"status": "ok", "service": "benchmark"}
```

---

## Available Tests

| test_id | Label | Weight | What it checks |
|---------|-------|--------|----------------|
| `identity_consistency` | Identity Consistency | 15% | Values, tone, and decision style hold across 6 different topic turns |
| `biographical_accuracy` | Biographical Accuracy | 15% | Age, location, occupation, household match locked spec |
| `gap_discipline` | Gap Discipline | 12% | Persona deflects rather than fabricates uncovered biographical facts |
| `decision_style_fidelity` | Decision Style Fidelity | 12% | Purchase scenario reveals correct decision style + objections |
| `contradiction_authenticity` | Contradiction Authenticity | 10% | Behavioural contradictions surface naturally without self-diagnosis |
| `emotional_register` | Emotional Register | 10% | Affect varies appropriately; no flat or mechanical responses |
| `symbolic_meaning_coherence` | Symbolic Meaning Coherence | 8% | Purchases framed through persona's symbolic register, not just utility |
| `attachment_expression` | Attachment Expression | 8% | Attachment style surfaces through relationship framing, not confession |
| `drift_resistance` | Drift Resistance | 5% | 10-turn conversation with reframing attempts — persona holds locked facts |
| `red_team_resilience` | Red-Team Resilience | 5% | Deflects "are you an AI?", jailbreaks, and prompt disclosure attempts |

---

## Grading

| Score | Grade | Meaning |
|-------|-------|---------|
| 90–100 | A | Exceptional — near-human psychological fidelity |
| 75–89 | B | Strong — minor gaps in depth or specificity |
| 60–74 | C | Adequate — passes basic checks, lacks texture |
| 45–59 | D | Weak — significant coherence or discipline issues |
| 0–44 | F | Failing — fabrication, character breaks, or flat identity |

The grade label includes the tier name: `"Research Grade — A"`, `"Standard — B"`, etc.

---

## Integration Patterns

### Pattern A — SSE passthrough (recommended)

The calling service opens the SSE stream from the benchmark service and passes it through to the frontend. The frontend renders progress in real time.

```
[Frontend] ←── SSE ──── [Your Service] ←── SSE ──── [Benchmark Service]
```

**When to use:** The Mind (post-generation flow), White Rabbit (on-demand evaluation)

**Caller implementation (Python/FastAPI):**
```python
import httpx
from fastapi.responses import StreamingResponse

BENCHMARK_URL = os.environ["BENCHMARK_API_URL"]  # e.g. http://localhost:8002

async def run_benchmark_stream(persona_id: str, tier: str = "standard"):
    async def _proxy():
        async with httpx.AsyncClient(timeout=600.0) as client:
            async with client.stream(
                "POST",
                f"{BENCHMARK_URL}/runs/stream",
                json={"persona_id": persona_id, "tier": tier},
            ) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk
    return StreamingResponse(
        _proxy(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

**Caller implementation (TypeScript/Next.js — client side):**
```typescript
async function runBenchmark(
  personaId: string,
  tier: "quick" | "standard" | "research",
  onEvent: (e: BenchmarkEvent) => void
) {
  const res = await fetch(`${YOUR_API}/personas/${personaId}/benchmark`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tier }),
  });
  const reader = res.body!.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try { onEvent(JSON.parse(line.slice(6))); } catch {}
      }
    }
  }
}
```

---

### Pattern B — Fire-and-forget + poll

Call `POST /runs/stream`, capture the `run_id` from the first `started` event, then poll `GET /runs/{run_id}` at intervals. Use when you don't want to keep an SSE connection open (e.g. background jobs, cron).

```python
async def start_benchmark_async(persona_id: str, tier: str = "quick") -> str:
    """Start benchmark, return run_id without waiting for completion."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        run_id = None
        async with client.stream(
            "POST",
            f"{BENCHMARK_URL}/runs/stream",
            json={"persona_id": persona_id, "tier": tier},
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    run_id = event.get("run_id")
                    break  # got run_id from first event, stop reading
    return run_id

# Later, poll:
async def poll_benchmark(run_id: str) -> BenchmarkReport:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BENCHMARK_URL}/runs/{run_id}")
        return resp.json()
```

---

### Pattern C — Inline (payload embed)

When your service already has the full persona JSON in memory (e.g. right after generation), skip the fetch round-trip by embedding it directly:

```python
async with httpx.AsyncClient(timeout=600.0) as client:
    async with client.stream(
        "POST",
        f"{BENCHMARK_URL}/runs/stream",
        json={
            "persona_id": persona_id,
            "tier": "quick",
            "persona_payload": persona_dict,  # full persona JSON
        },
    ) as resp:
        ...
```

---

## Environment Variables

Set these in each service that calls the benchmark:

| Variable | Description | Example |
|----------|-------------|---------|
| `BENCHMARK_API_URL` | URL of the running benchmark service | `http://localhost:8002` |

Set these **in the benchmark service itself**:

| Variable | Description | Example |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |
| `MIND_API_URL` | URL of The Mind API (for persona fetching) | `http://localhost:8001` |
| `BENCHMARK_BASE_URL` | Public URL of benchmark service | `http://localhost:8002` |
| `BENCHMARK_DB_PATH` | Path to SQLite database file | `benchmark.db` |
| `PORT` | Port to listen on | `8002` |

---

## Running the Service

**Local:**
```bash
cd services/benchmark
cp .env.example .env        # fill in ANTHROPIC_API_KEY
pip install -r requirements.txt
uvicorn main:app --port 8002 --reload
```

**Docker (when you add a Dockerfile):**
```bash
docker build -t simulatte-benchmark -f Dockerfile.benchmark .
docker run -p 8002:8002 --env-file services/benchmark/.env simulatte-benchmark
```

**Railway:**  
Add a new Railway service in the simulatte-persona-generator project, point it at `Dockerfile.benchmark`, set env vars via Railway dashboard. Costs ~$5/month idle (no always-on traffic).

---

## Service-Specific Wiring Guide

### 1. The Mind (`pilots/the-mind/api/`)

**What to add:**

**Backend — `main.py`:**
```python
# New endpoint: POST /generated/{persona_id}/benchmark
@app.post("/generated/{persona_id}/benchmark")
async def benchmark_persona(
    persona_id: str,
    tier: str = "standard",
    current_user = Depends(get_current_user),
):
    """Stream a benchmark run for a generated persona."""
    import httpx, os
    BENCHMARK_URL = os.environ.get("BENCHMARK_API_URL", "http://localhost:8002")

    async def _proxy():
        async with httpx.AsyncClient(timeout=600.0) as client:
            async with client.stream(
                "POST",
                f"{BENCHMARK_URL}/runs/stream",
                json={"persona_id": persona_id, "tier": tier},
            ) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk

    return StreamingResponse(
        _proxy(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

**Frontend — `web/lib/api.ts`:**
```typescript
export interface BenchmarkTestResult {
  test_id: string;
  label: string;
  status: "passed" | "failed" | "error" | "skipped";
  score: number;
  weight: number;
  weighted_contribution: number;
  rationale: string;
  evidence: string[];
  flags: string[];
  duration_s: number;
  cost_usd: number;
}

export interface BenchmarkReport {
  run_id: string;
  persona_id: string;
  persona_name: string;
  tier: string;
  status: "queued" | "running" | "complete" | "error";
  credibility_score: number;
  grade: string;
  grade_label: string;
  tests: BenchmarkTestResult[];
  total_cost_usd: number;
  total_duration_s: number;
  started_at?: string;
  completed_at?: string;
}

export interface BenchmarkEvent {
  type: "started" | "test_complete" | "complete" | "error";
  run_id: string;
  test_id?: string;
  test_label?: string;
  score?: number;
  credibility_score?: number;
  grade?: string;
  message?: string;
  report?: BenchmarkReport;
}

export async function runBenchmark(
  personaId: string,
  tier: "quick" | "standard" | "research",
  onEvent: (e: BenchmarkEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API}/generated/${personaId}/benchmark?tier=${tier}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await _authHeaders()) },
    signal,
  });
  if (!res.ok || !res.body) throw new Error("Benchmark request failed");
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try { onEvent(JSON.parse(line.slice(6))); } catch {}
      }
    }
  }
}
```

**UI placement:** Persona profile page (`/persona/[id]`) — "Run Benchmark" button in the header area. Shows a live progress list of tests, then renders the final grade badge + credibility score.

---

### 2. White Rabbit (future)

White Rabbit generates cohorts of agents, not individual personas. Two integration points:

**a) Per-agent evaluation** (same as The Mind pattern above — one benchmark per agent)

**b) Cohort-level evaluation** — run quick benchmarks on a random sample of agents and aggregate:
```python
import asyncio

async def benchmark_cohort_sample(agent_ids: list[str], sample_size: int = 5):
    """Run quick benchmarks on a random sample of agents in a cohort."""
    import random
    sample = random.sample(agent_ids, min(sample_size, len(agent_ids)))
    tasks = [
        start_benchmark_async(agent_id, tier="quick")
        for agent_id in sample
    ]
    run_ids = await asyncio.gather(*tasks)
    # Poll all results after a delay, aggregate scores
    ...
```

**Note:** White Rabbit agents may not have all the persona layers that The Mind generates (self_model, symbolic_meanings, etc.). The benchmark service handles missing layers gracefully — it skips tests that require fields not present in the payload, and scoring normalises to the subset of tests that ran.

---

### 3. Future Simulatte Products

Any product can integrate by following the same steps:

1. **Add `BENCHMARK_API_URL` to environment** (pointing at the running benchmark service)
2. **Add a proxy endpoint** in your backend using Pattern A above
3. **Add a TypeScript `runBenchmark()` function** in your API client using the contract above
4. **Choose a tier** — use `quick` for automated/background runs, `standard`/`research` for user-triggered runs
5. **Optionally embed persona payload** (Pattern C) to skip the fetch round-trip

The benchmark service does not care which Simulatte product calls it — it only needs the persona ID (to fetch from The Mind) or the full persona payload (for services that have it in memory).

---

## Testing the Service (No Integration Required)

You can call the benchmark directly against any persona already in The Mind database:

```bash
# Stream a standard benchmark for persona abc-123
curl -N -X POST http://localhost:8002/runs/stream \
  -H "Content-Type: application/json" \
  -d '{"persona_id": "abc-123", "tier": "standard"}'

# Quick benchmark
curl -N -X POST http://localhost:8002/runs/stream \
  -H "Content-Type: application/json" \
  -d '{"persona_id": "abc-123", "tier": "quick"}'

# Specific tests only
curl -N -X POST http://localhost:8002/runs/stream \
  -H "Content-Type: application/json" \
  -d '{"persona_id": "abc-123", "tier": "custom", "custom_tests": ["gap_discipline", "red_team_resilience"]}'

# Poll a completed run
curl http://localhost:8002/runs/{run_id}
```

---

## Cost Reference

| Tier | Haiku turns (est.) | Sonnet judge calls | Cost |
|------|-------------------|--------------------|------|
| Quick (3 tests) | ~18 turns | 3 calls | ~$0.05 |
| Standard (6 tests) | ~36 turns | 6 calls | ~$0.18 |
| Research (10 tests) | ~60 turns + 10 drift turns | 10 calls | ~$0.40 |

Running a quick benchmark on every generated persona adds ~$0.05/generation.  
At 100 personas/day that's $5/day, $150/month — a rounding error relative to generation costs.

---

## Roadmap

- [ ] **Wire to The Mind** — backend endpoint + frontend "Run Benchmark" button
- [ ] **Wire to White Rabbit** — cohort-level sampling
- [ ] **Benchmark history UI** — past runs visible on persona profile page
- [ ] **Automatic gate** — reject personas that score < 60 (C) on quick tier, regenerate automatically
- [ ] **Railway deployment** — `Dockerfile.benchmark` + Railway service config
- [ ] **PostgreSQL migration** — swap SQLite for Railway PostgreSQL when deploying
- [ ] **Webhook support** — POST to a caller-provided URL when a run completes (for async integrations)
- [ ] **Cohort aggregate report** — roll up N individual persona scores into a cohort credibility score
