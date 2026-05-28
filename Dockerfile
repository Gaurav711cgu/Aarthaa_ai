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

WORKDIR /app

# Install system dependencies needed for compiling binary packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies first to optimize Docker layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

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
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:7860/health || exit 1

# Start production uvicorn worker, defaulting to 7860 (Hugging Face standard)
# Run pipeline warmups on startup to bypass build network restrictions
CMD ["sh", "-c", "python scripts/train_fraud_model.py && python scripts/ingest_regulations.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
