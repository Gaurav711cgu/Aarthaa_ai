# ==========================================
# Production-Grade Container Package for Artha AI
# ==========================================

FROM python:3.11-slim

LABEL maintainer="Gaurav Kumar Nayak"
LABEL description="Production-Grade FastAPI app container for Artha AI fintech platform"

# Configure Python execution variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
# Build-time placeholder — overridden at runtime by HF Spaces secrets injection.
# This allows warmup scripts (which import app.config) to run without crashing.
# The real SECRET_KEY must be set in HF Spaces → Settings → Secrets.
ENV SECRET_KEY="artha_docker_build_placeholder_secret_key"

WORKDIR /app

# Install system dependencies needed for compiling binary packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    librdkafka-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies first to optimize Docker layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy all application directories and files
COPY app /app/app
COPY scripts /app/scripts
COPY data /app/data

# Pre-compile Python source files to bytecode to optimize startup latencies
RUN python -m compileall app/

# Create a dedicated, unprivileged system user for runtime security
RUN groupadd -r artha && useradd -no-log-init -r -g artha artha && \
    chown -R artha:artha /app

# Switch to unprivileged runtime execution context
USER artha

# Expose standard HF Space port
EXPOSE 7860

# Set healthcheck to verify container health
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=3 \
  CMD curl -f http://localhost:7860/health || exit 1

# Start uvicorn immediately; run warmup scripts in background so a failure
# (e.g. missing DB, SECRET_KEY not yet injected) never blocks the web server.
CMD ["sh", "-c", "\
  (python scripts/train_fraud_model.py || echo '[WARN] train_fraud_model.py failed — heuristic fallback active') & \
  (python scripts/ingest_regulations.py || echo '[WARN] ingest_regulations.py failed — vector store may be empty') & \
  exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1 --log-level info \
"]
