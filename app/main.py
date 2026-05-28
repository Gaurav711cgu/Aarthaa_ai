from fastapi import FastAPI, Depends, HTTPException, Request, Response, status
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from sqlalchemy import text
import time
import uuid
import logging
from typing import Dict, Any
import gradio as gr

logger = logging.getLogger(__name__)

from app.config import settings
from app.database import get_db
from app.redis_client import test_redis_connection
from app.kafka_client import test_kafka_connection
from app.services.monitoring import get_metrics_payload
from app.services.drift_detector import drift_detector
from app.api.v1.auth import router as auth_router, get_current_user
from app.api.v1.fraud import router as fraud_router
from app.api.v1.compliance import router as compliance_router
from app.api.v1.finlens import router as finlens_router
from app.ui.dashboard import build_dashboard

# Initialize API rate limiter per client IP address
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Artha AI — Elite FinTech AI Platform",
    description="Unified API gateway for FraudSense, RegGuard, and FinLens modules.",
    version="2.0.0"
)

# Attach rate limiting configs
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# GZip compression for high throughput JSON loads
app.add_middleware(GZipMiddleware, minimum_size=500)

# ── Correlation ID Middleware ─────────────────────────────────────────────────
# Injects a unique X-Correlation-ID header on every request+response.
# All downstream log lines should include this ID for distributed tracing.
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    # Bind to request state so route handlers can access it
    request.state.correlation_id = correlation_id
    # Inject into log context
    logger.debug("[%s] %s %s", correlation_id, request.method, request.url.path)
    response = await call_next(request)
    # Echo the correlation ID back in the response header
    response.headers["X-Correlation-ID"] = correlation_id
    return response

# Register Module API Routers
app.include_router(auth_router)
app.include_router(fraud_router, prefix="/api/v1")
app.include_router(compliance_router, prefix="/api/v1")
app.include_router(finlens_router, prefix="/api/v1")

@app.get("/api/v1/monitoring/drift-report")
def get_drift_report(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns the latest Evidently AI statistical data drift report as base64-encoded HTML."""
    report_base64 = drift_detector.get_drift_report_html_base64()
    if not report_base64:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Evidently drift report."
        )
    return {"report_base64": report_base64}

@app.get("/api/v1/monitoring/kafka-status")
def kafka_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns Kafka broker connectivity status and topic metadata."""
    from app.kafka_client import test_kafka_connection, get_kafka_producer
    is_alive = test_kafka_connection()
    topics = []
    if is_alive:
        try:
            producer = get_kafka_producer()
            metadata = producer.list_topics(timeout=3)
            topics = [
                t for t in metadata.topics.keys()
                if not t.startswith("__")  # exclude internal Kafka topics
            ]
        except Exception as e:
            logger.warning(f"Kafka topic listing failed: {e}")
    return {
        "kafka_status": "healthy" if is_alive else "unreachable",
        "broker": "localhost:9092",
        "artha_topics": topics,
        "expected_topics": [
            "transactions.raw",
            "artha.fraud.batch",
            "artha.monitoring.drift"
        ]
    }

@app.get("/health")
@limiter.limit("30/minute")
def health_check(request: Request, db: Session = Depends(get_db)):
    """Deep health check of backend infrastructure to prevent silent connection dropoffs."""
    # 1. Verify PostgreSQL connection
    pg_alive = False
    try:
        db.execute(text("SELECT 1"))
        pg_alive = True
    except Exception:
        pass
    
    # 2. Verify Redis cache connection
    redis_alive = test_redis_connection()
    
    # 3. Verify Kafka broker stream connection
    kafka_alive = test_kafka_connection()
    
    overall_status = "healthy" if (pg_alive and redis_alive and kafka_alive) else "degraded"
    
    health_status = {
        "status": overall_status,
        "timestamp": time.time(),
        "services": {
            "postgres": "healthy" if pg_alive else "unreachable",
            "redis": "healthy" if redis_alive else "unreachable",
            "kafka": "healthy" if kafka_alive else "unreachable"
        }
    }
    
    if overall_status == "degraded":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )
        
    return health_status

@app.get("/metrics")
def metrics():
    """Exposes Prometheus-scrapable latency, scoring, and data drift metrics."""
    data, content_type = get_metrics_payload()
    return Response(content=data, media_type=content_type)

# Mount the interactive Gradio dashboard UI directly on root (/) path
app = gr.mount_gradio_app(app, build_dashboard(), path="/")
