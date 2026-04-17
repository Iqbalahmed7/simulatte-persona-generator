FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn[standard] httpx numpy

# Copy source
COPY src/ ./src/
COPY examples/ ./examples/

# Create cohort storage directory
RUN mkdir -p /tmp/simulatte_cohorts

EXPOSE 8000

# Use shell form so $PORT is expanded at runtime (required for Railway)
CMD uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
