#!/usr/bin/env bash
# Diagnostic startup wrapper. Echoes exit codes and keeps container alive
# briefly after exit so Railway logs flush before teardown.
set +e

echo "STARTUP_BEGIN"
echo "DB_URL_LEN=${#DATABASE_URL}"

alembic upgrade head 2>&1
ALEMBIC_RC=$?
echo "ALEMBIC_EXIT=${ALEMBIC_RC}"

if [ "${ALEMBIC_RC}" -ne 0 ]; then
  echo "ALEMBIC_FAILED — keeping container alive for log flush"
  sleep 300
  exit "${ALEMBIC_RC}"
fi

uvicorn src.api.main:app --host 0.0.0.0 --port "${PORT:-8000}" 2>&1
UVICORN_RC=$?
echo "UVICORN_EXIT=${UVICORN_RC}"
echo "PROCESS_DONE_KEEPALIVE"
sleep 300
exit "${UVICORN_RC}"
