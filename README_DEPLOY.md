# Persona Generator — Standalone Service Deployment

Deploys the Persona Generator (PG) as a self-contained Railway service with
Postgres-backed cohort persistence and an async-first `/v1/*` API.

## Architecture

- **web** — FastAPI app exposing legacy (`/generate`, `/orchestrate`,
  `/cohort/{id}`) and new (`/v1/calibrations`, `/v1/cohorts/...`,
  `/v1/cost/summary`) endpoints.
- **worker** — Long-running process (`scripts/calibration_worker.py`) that
  polls the `calibration_jobs` table and executes the orchestrator.
- **Postgres** — `cohorts`, `personas`, `calibration_jobs`, `cost_events`.
  Schema is managed by Alembic (`alembic upgrade head`).

## Step-by-step Railway deploy

1. **Create project**
   ```sh
   railway login
   railway init persona-generator
   ```
2. **Add Postgres plugin** in the Railway dashboard. Railway will inject
   `DATABASE_URL` into both services.
3. **Set env vars** for the web service (Settings → Variables):
   - `ANTHROPIC_API_KEY`
   - `INTERNAL_API_KEY` (generate with `openssl rand -hex 32`)
   - `LOG_LEVEL=INFO`
   - `COHORT_STORE_DIR=/tmp/simulatte_cohorts` (legacy fallback)
   - `SARVAM_API_KEY` (optional)
4. **Push** the branch:
   ```sh
   git push railway phase-c/standalone-async:main
   ```
   Railway builds from `Dockerfile`. The release command in `railway.toml`
   runs `alembic upgrade head` before starting uvicorn.
5. **Add the worker service** in the same Railway project:
   - "New Service" → use the same repo + Dockerfile.
   - Override the start command to `python scripts/calibration_worker.py`.
   - Inherit the same env vars (Railway → Service → Settings → Shared Variables).
6. **Verify**:
   ```sh
   curl https://<your-pg>.up.railway.app/health
   curl -H "Authorization: Bearer $INTERNAL_API_KEY" \
        https://<your-pg>.up.railway.app/v1/cost/summary
   ```

## Required env vars

| Var                   | Required | Notes                                            |
| --------------------- | -------- | ------------------------------------------------ |
| `ANTHROPIC_API_KEY`   | yes      | Anthropic API for the LLM cascade                |
| `DATABASE_URL`        | yes      | Auto-populated by Railway Postgres plugin        |
| `INTERNAL_API_KEY`    | yes (prod) | Bearer token required for `/v1/*` endpoints    |
| `SARVAM_API_KEY`      | no       | Enables Sarvam-powered Indian persona enrichment |
| `LOG_LEVEL`           | no       | Default `INFO`                                   |
| `COHORT_STORE_DIR`    | no       | Legacy filesystem cohort store fallback          |
| `WORKER_POLL_INTERVAL`| no       | Worker queue poll interval (seconds, default 5)  |

## Migrating legacy filesystem cohorts

Existing cohorts on disk can be backfilled into Postgres:
```sh
DATABASE_URL=... python scripts/migrate_filesystem_to_pg.py \
    --store-dir /tmp/simulatte_cohorts --tenant-id legacy
```

## Cost telemetry

```
GET /v1/cost/summary?from=2026-01-01&to=2026-12-31&tenant_id=acme
Authorization: Bearer $INTERNAL_API_KEY
```

Returns `{ total_usd, event_count, from_ts, to_ts, tenant_id }`.

## Compatibility with existing engine integration

The legacy endpoints (`/generate`, `/orchestrate`, `/cohort/{id}`) keep their
existing request/response shapes. `/orchestrate` additionally dual-writes the
generated cohort into Postgres when `DATABASE_URL` is set — engine callers
need no code change to benefit from the new persistence layer.
