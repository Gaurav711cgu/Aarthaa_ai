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

# Redirect Hugging Face Spaces home / cache to avoid permission errors
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Create a user with UID 1000 to match Hugging Face Spaces requirements
RUN useradd -m -u 1000 user

WORKDIR /app

# Install system dependencies needed for compiling binary packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    librdkafka-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install them, ensuring ownership by user 1000
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy all application directories and files with proper ownership
COPY --chown=user:user app /app/app
COPY --chown=user:user scripts /app/scripts
COPY --chown=user:user data /app/data

# Ensure write permissions on the /app directory so user 1000 can write local DB/models
RUN chown -R user:user /app && chmod -R 755 /app

# Pre-compile Python source files to bytecode to optimize startup latencies
RUN python -m compileall app/

# Switch to the non-root user (UID 1000)
USER user

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
