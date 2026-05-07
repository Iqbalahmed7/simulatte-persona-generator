#!/usr/bin/env bash
# Production startup wrapper.
# Runs alembic migrations, then starts uvicorn (web) + calibration_worker
# in the same container. Forwards SIGTERM/SIGINT so Railway can stop both
# cleanly. If either exits, the container exits so Railway restarts it.
set -e

echo "STARTUP_BEGIN"
alembic upgrade head
echo "ALEMBIC_DONE"

# Start worker in background
python scripts/calibration_worker.py &
WORKER_PID=$!
echo "WORKER_STARTED pid=$WORKER_PID"

# Forward signals to children
term_handler() {
  echo "Caught signal — shutting down"
  kill -TERM "$WORKER_PID" 2>/dev/null || true
  kill -TERM "$UVICORN_PID" 2>/dev/null || true
  wait
  exit 0
}
trap term_handler SIGTERM SIGINT

# Start uvicorn in background so we can wait on either
uvicorn src.api.main:app --host 0.0.0.0 --port "${PORT:-8000}" &
UVICORN_PID=$!
echo "UVICORN_STARTED pid=$UVICORN_PID"

# Exit when either child exits (Railway restarts the container)
wait -n "$WORKER_PID" "$UVICORN_PID"
EXIT_CODE=$?
echo "child_exited code=$EXIT_CODE — bringing down both"
kill -TERM "$WORKER_PID" 2>/dev/null || true
kill -TERM "$UVICORN_PID" 2>/dev/null || true
wait
exit "$EXIT_CODE"
