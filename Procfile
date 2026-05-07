web: uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
worker: python scripts/calibration_worker.py
release: alembic upgrade head
