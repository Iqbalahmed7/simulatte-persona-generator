# Benchmark Service — Integration Guide

**Version:** 2.0  
**Service location:** `services/benchmark/`  
**Default port:** `8002`

---

## What This Service Is

An independent evaluation engine that scores any persona for psychological depth,
factual discipline, and conversational authenticity.

It has **no knowledge of The Mind, White Rabbit, or any other Simulatte product**.
It does not call any external API. It receives a persona JSON, runs a suite of
AI-to-AI tests, and returns a credibility score.

```
[Any product that generates personas]
        │
        │  POST /runs/stream
        │  { persona_payload: <full persona JSON>, tier: "standard" }
        ▼
[Benchmark Service — services/benchmark/]
        │
        │  Haiku simulates conversations
        │  Sonnet judges each conversation
        │
        ▼
  Credibility score 0–100 · Grade A–F · Per-test breakdown
```

**The calling service owns the persona fetch.** It passes the payload in.
The benchmark service never reaches out anywhere.

---

## The One Rule

> **Always send the full persona JSON in `persona_payload`.**
> The benchmark service will never fetch it for you.

---

## API

### `POST /runs/stream` — Run + stream results live

**Request:**
```json
{
  "persona_payload": { ...full persona JSON... },
  "tier": "standard",
  "persona_id": "abc-123",
  "custom_tests": []
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `persona_payload` | object | **yes** | The full persona JSON |
| `tier` | string | no | `quick` / `standard` / `research` / `custom` (default: `standard`) |
| `persona_id` | string | no | Tracking label only — your DB id, slug, or anything. Not used in evaluation. |
| `custom_tests` | string[] | no | Required only when `tier = "custom"` |

**Response:** `text/event-stream`

```
data: {"type":"started","run_id":"...","message":"Running 6 tests for Priya Sharma [standard]"}

data: {"type":"test_complete","run_id":"...","test_id":"identity_consistency","score":8.5,"message":"..."}

data: {"type":"test_complete","run_id":"...","test_id":"biographical_accuracy","score":9.0,...}

data: {"type":"complete","run_id":"...","credibility_score":82.4,"grade":"B","grade_label":"Standard — B","report":{...}}
```

---

### `POST /runs` — Fire-and-forget (returns run_id, no stream)

Same request body. Returns immediately with a `run_id`. Poll `GET /runs/{run_id}` for the result.
Use this when you don't want to hold an SSE connection open (background jobs, post-generation hooks).

**Response:**
```json
{
  "run_id": "abc-def-123",
  "status": "queued",
  "stream_url": "http://localhost:8002/runs/stream",
  "poll_url": "http://localhost:8002/runs/abc-def-123"
}
```

---

### `GET /runs/{run_id}` — Poll result

Returns the current `BenchmarkReport`. Check `status` field: `queued` → `running` → `complete` / `error`.

---

### `GET /runs?persona_id=...&limit=50` — List past runs

Returns summary objects (no full test detail). Filter by your `persona_id` tracking label.

---

### `GET /health`

```json
{"status": "ok", "service": "benchmark"}
```

---

## Tiers

| Tier | Tests run | Est. cost | Est. time | Recommended for |
|------|-----------|-----------|-----------|-----------------|
| `quick` | 3 | ~$0.05 | ~90s | Automated post-generation gate |
| `standard` | 6 | ~$0.18 | ~3 min | Manual QA, user-triggered |
| `research` | 10 | ~$0.40 | ~7 min | Deep audits, investor demos |
| `custom` | caller-defined | varies | varies | Targeted layer testing |

---

## Tests (all 10)

| test_id | Weight | What it checks |
|---------|--------|----------------|
| `identity_consistency` | 15% | Values and tone hold across 6 different topic turns |
| `biographical_accuracy` | 15% | Age, location, occupation, household match spec |
| `gap_discipline` | 12% | Persona deflects rather than fabricates uncovered facts |
| `decision_style_fidelity` | 12% | Purchase scenario reveals correct decision style and objections |
| `contradiction_authenticity` | 10% | Contradictions surface naturally, never diagnosed |
| `emotional_register` | 10% | Affect varies; no flat or mechanical responses |
| `symbolic_meaning_coherence` | 8% | Purchases framed through symbolic register, not just utility |
| `attachment_expression` | 8% | Attachment style in relationship framing, not confession |
| `drift_resistance` | 5% | 10-turn conversation with reframing attempts — facts hold |
| `red_team_resilience` | 5% | Deflects "are you an AI?", jailbreaks, prompt disclosure |

Scores are normalised to the subset of tests that ran, so a Quick run (3 tests) is
graded fairly against its own weight set.

---

## Grading

| Score | Grade |
|-------|-------|
| 90–100 | A |
| 75–89 | B |
| 60–74 | C |
| 45–59 | D |
| 0–44 | F |

The `grade_label` field includes the tier: `"Standard — B"`, `"Research Grade — A"`.

---

## Running the Service

```bash
cd services/benchmark
cp .env.example .env        # add ANTHROPIC_API_KEY
pip install -r requirements.txt
uvicorn main:app --port 8002 --reload
```

**Environment variables (benchmark service only):**

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | yes | Anthropic API key |
| `BENCHMARK_DB_PATH` | no | SQLite path (default: `benchmark.db`) |
| `BENCHMARK_BASE_URL` | no | Public URL, used in poll_url responses |
| `PORT` | no | Listen port (default: `8002`) |

No other service URLs required. The benchmark service makes no outbound HTTP calls.

---

## How to Integrate (any product)

Four steps. Takes under an hour.

### Step 1 — Add env var to your service

```bash
BENCHMARK_API_URL=http://localhost:8002   # or your deployed URL
```

### Step 2 — Fetch the persona in your service, then call benchmark

Your service already has the persona. Pass it straight through.

**Python:**
```python
import httpx
import os

BENCHMARK_URL = os.environ["BENCHMARK_API_URL"]

async def run_benchmark_stream(persona_payload: dict, tier: str = "standard"):
    """Proxy a live benchmark SSE stream to the caller."""
    from fastapi.responses import StreamingResponse

    async def _proxy():
        async with httpx.AsyncClient(timeout=600.0) as client:
            async with client.stream(
                "POST",
                f"{BENCHMARK_URL}/runs/stream",
                json={
                    "persona_payload": persona_payload,
                    "tier": tier,
                    "persona_id": persona_payload.get("persona_id"),  # optional
                },
            ) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk

    return StreamingResponse(
        _proxy(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

**TypeScript (client-side, reading the SSE your backend proxies):**
```typescript
export interface BenchmarkEvent {
  type: "started" | "test_complete" | "complete" | "error";
  run_id: string;
  test_id?: string;
  test_label?: string;
  score?: number;
  credibility_score?: number;
  grade?: string;
  grade_label?: string;
  message?: string;
  report?: BenchmarkReport;
}

async function runBenchmark(
  endpoint: string,          // your backend's proxy URL, e.g. /api/personas/abc/benchmark
  tier: "quick" | "standard" | "research",
  onEvent: (e: BenchmarkEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tier }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error("Benchmark failed");
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

### Step 3 — Decide what to show

Minimum viable UI: the final `credibility_score` and `grade_label` from the `complete` event.
Full UI: live test progress list during run, then per-test scores with rationale on completion.

### Step 4 — Choose a trigger

| Trigger | Tier | Notes |
|---------|------|-------|
| Auto, every generation | `quick` | Silent background job, no UI |
| User clicks "Run benchmark" | `standard` or `research` | Show live progress |
| Scheduled audit (cron) | `research` | Run on a sample, store results |

---

## Testing Without Any Integration

Point directly at the benchmark service with a persona JSON from anywhere:

```bash
# Grab a persona JSON from The Mind (or paste one manually)
PERSONA=$(curl -s http://localhost:8001/generated/abc-123)

# Run a quick benchmark against it
curl -N -X POST http://localhost:8002/runs/stream \
  -H "Content-Type: application/json" \
  -d "{\"persona_payload\": $PERSONA, \"tier\": \"quick\"}"
```

```bash
# Custom test — just gap discipline and red-team
curl -N -X POST http://localhost:8002/runs/stream \
  -H "Content-Type: application/json" \
  -d "{\"persona_payload\": $PERSONA, \"tier\": \"custom\", \"custom_tests\": [\"gap_discipline\", \"red_team_resilience\"]}"
```

---

## Roadmap

- [ ] Wire to The Mind — backend proxy endpoint + "Run Benchmark" button on persona profile
- [ ] Wire to White Rabbit — cohort-level sampling (quick benchmark on N random agents, aggregate score)
- [ ] Automatic quality gate — flag or regenerate personas that score below C on quick tier
- [ ] Railway deployment — `Dockerfile.benchmark` + Railway service config
- [ ] PostgreSQL migration — swap SQLite when deploying to Railway
- [ ] Webhook support — POST to caller URL on completion (for async integrations)
