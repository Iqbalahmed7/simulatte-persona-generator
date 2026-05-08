"""services/benchmark/main.py — FastAPI application for the benchmark service.

Endpoints:
    POST /runs                  — start a benchmark run (returns run_id + stream URL)
    GET  /runs/{run_id}         — poll for the current report
    GET  /runs/{run_id}/stream  — SSE stream of BenchmarkEvents
    GET  /runs                  — list recent runs (optional ?persona_id=...)
    GET  /health                — liveness probe
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import AsyncGenerator, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

load_dotenv()

from models import (
    BenchmarkEvent,
    BenchmarkReport,
    BenchmarkTier,
    RunResponse,
    RunRequest,
    RunStatus,
)
from runner import run_benchmark
from storage import get_run, init_db, list_runs

app = FastAPI(
    title="Simulatte Benchmark Service",
    description="Research-grade persona quality evaluation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    await init_db()


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "benchmark"}


# ── Start a run ───────────────────────────────────────────────────────────────

@app.post("/runs", response_model=RunResponse, status_code=202)
async def start_run(req: RunRequest):
    """
    Kick off a benchmark run.

    The run executes asynchronously. Poll /runs/{run_id} or stream
    /runs/{run_id}/stream for live progress.
    """
    import uuid
    run_id = str(uuid.uuid4())

    # Fire-and-forget: store result as it completes
    async def _execute():
        async for _ in run_benchmark(
            persona_id=req.persona_id,
            tier=req.tier,
            custom_tests=req.custom_tests,
            persona_payload=req.persona_payload,
        ):
            pass  # storage is handled inside run_benchmark

    asyncio.create_task(_execute())

    base = os.environ.get("BENCHMARK_BASE_URL", "http://localhost:8002")
    return RunResponse(
        run_id=run_id,
        status=RunStatus.QUEUED,
        stream_url=f"{base}/runs/{run_id}/stream",
        poll_url=f"{base}/runs/{run_id}",
    )


# ── SSE stream ────────────────────────────────────────────────────────────────

@app.get("/runs/{run_id}/stream")
async def stream_run(run_id: str, persona_id: str = Query(...), tier: BenchmarkTier = Query(BenchmarkTier.STANDARD)):
    """
    Server-Sent Events stream for a benchmark run.

    The client should connect immediately after POST /runs.
    This endpoint re-executes the run — designed for direct streaming use.
    For polling use GET /runs/{run_id}.
    """
    async def _generate() -> AsyncGenerator[bytes, None]:
        try:
            async for event in run_benchmark(
                persona_id=persona_id,
                tier=tier,
            ):
                yield f"data: {event.model_dump_json()}\n\n".encode()
        except Exception as exc:
            err_event = BenchmarkEvent(type="error", run_id=run_id, message=str(exc))
            yield f"data: {err_event.model_dump_json()}\n\n".encode()

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Direct stream (recommended for single-request use) ───────────────────────

@app.post("/runs/stream")
async def stream_run_direct(req: RunRequest):
    """
    One-shot SSE endpoint: POST request body contains the run config,
    response is an SSE stream. No polling needed.

    Recommended for wiring to The Mind API.
    """
    async def _generate() -> AsyncGenerator[bytes, None]:
        try:
            async for event in run_benchmark(
                persona_id=req.persona_id,
                tier=req.tier,
                custom_tests=req.custom_tests,
                persona_payload=req.persona_payload,
            ):
                yield f"data: {event.model_dump_json()}\n\n".encode()
        except Exception as exc:
            import uuid
            err = BenchmarkEvent(type="error", run_id=str(uuid.uuid4()), message=str(exc))
            yield f"data: {err.model_dump_json()}\n\n".encode()

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Poll ──────────────────────────────────────────────────────────────────────

@app.get("/runs/{run_id}", response_model=BenchmarkReport)
async def get_run_endpoint(run_id: str):
    report = await get_run(run_id)
    if not report:
        raise HTTPException(status_code=404, detail="Run not found")
    return report


# ── List ──────────────────────────────────────────────────────────────────────

@app.get("/runs")
async def list_runs_endpoint(
    persona_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    runs = await list_runs(persona_id=persona_id, limit=limit)
    from report import summary_dict
    return [summary_dict(r) for r in runs]


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8002))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
