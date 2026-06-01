# ── Namespace Collision Resolution Shim ────────────────────────────────────────
import sys
try:
    import python_multipart.multipart as pm_multipart
    sys.modules["multipart.multipart"] = pm_multipart
except ImportError:
    pass
# ──────────────────────────────────────────────────────────────────────────────

import time
import uuid
import logging
from typing import Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Request, Response, status
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from sqlalchemy import text


from app.database import get_db
from app.redis_client import test_redis_connection, is_redis_active
from app.kafka_client import test_kafka_connection, is_kafka_active
from app.services.monitoring import get_metrics_payload
from app.services.drift_detector import drift_detector
from app.api.v1.auth import router as auth_router, get_current_user
from app.api.v1.fraud import router as fraud_router
from app.api.v1.compliance import router as compliance_router
from app.api.v1.finlens import router as finlens_router

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Artha AI — Elite FinTech AI Platform",
    description="Unified API gateway for FraudSense, RegGuard, and FinLens modules.",
    version="2.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://aarthaa-ai.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    logger.debug("[%s] %s %s", correlation_id, request.method, request.url.path)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response

app.include_router(auth_router)
app.include_router(fraud_router, prefix="/api/v1")
app.include_router(compliance_router, prefix="/api/v1")
app.include_router(finlens_router, prefix="/api/v1")

@app.get("/api/v1/monitoring/drift-report")
def get_drift_report(current_user: Dict[str, Any] = Depends(get_current_user)):
    report_base64 = drift_detector.get_drift_report_html_base64()
    if not report_base64:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Evidently drift report."
        )
    return {"report_base64": report_base64}

@app.get("/api/v1/monitoring/kafka-status")
def kafka_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    from app.kafka_client import test_kafka_connection, get_kafka_producer
    is_alive = test_kafka_connection()
    topics = []
    if is_alive:
        try:
            producer = get_kafka_producer()
            metadata = producer.list_topics(timeout=3)
            topics = [
                t for t in metadata.topics.keys()
                if not t.startswith("__")
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
    pg_alive = False
    try:
        db.execute(text("SELECT 1"))
        pg_alive = True
    except Exception:
        pass

    redis_alive = test_redis_connection()
    redis_status = "healthy" if redis_alive else ("mock_active" if not is_redis_active else "unreachable")

    kafka_alive = test_kafka_connection()
    kafka_status_str = "healthy" if kafka_alive else ("mock_active" if not is_kafka_active else "unreachable")

    overall_status = "healthy" if (pg_alive and redis_status == "healthy" and kafka_status_str == "healthy") else "degraded"

    return {
        "status": overall_status,
        "timestamp": time.time(),
        "services": {
            "postgres": "healthy" if pg_alive else "unreachable",
            "redis": redis_status,
            "kafka": kafka_status_str
        }
    }

@app.get("/metrics")
def metrics():
    data, content_type = get_metrics_payload()
    return Response(content=data, media_type=content_type)

@app.get("/")
def read_root():
    return {
        "gateway": "Artha AI Unified API Gateway",
        "status": "online",
        "version": "2.0.0",
        "documentation": "/docs",
        "frontend": "https://aarthaa-ai.vercel.app",
        "endpoints": {
            "fraud_scoring": "/api/v1/fraud/score",
            "compliance_audit": "/api/v1/compliance/check",
            "statement_parsing": "/api/v1/finlens/upload"
        }
    }
