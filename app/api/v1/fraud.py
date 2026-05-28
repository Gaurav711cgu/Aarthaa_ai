from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import uuid
import logging
import time
import json

from app.services.fraud_model import fraud_engine
from app.services.monitoring import TRANSACTIONS_PROCESSED, FRAUD_SCORING_LATENCY
from app.services.drift_detector import drift_detector
from app.kafka_client import get_kafka_producer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fraud", tags=["FraudSense"])

class TransactionRequest(BaseModel):
    amount: float = Field(..., gt=0.0, description="Amount of the transaction in ₹ (INR)")
    hour: int = Field(..., ge=0, le=23, description="Hour of the day (0-23)")
    velocity_1h: int = Field(..., ge=0, description="Number of transactions in the last hour")
    distance_from_home: float = Field(..., ge=0.0, description="Distance from cardholder's home address in km")
    merchant_risk: float = Field(0.05, ge=0.0, le=1.0, description="Calculated risk value of processing merchant (0.0 to 1.0)")
    user_id: uuid.UUID = Field(..., description="Cardholder's unique identification key")
    channel: str = Field("UPI", description="Transaction processing channel (e.g., UPI, CASH, CARD)")

class TransactionResponse(BaseModel):
    fraud_probability: float
    anomaly_score: float
    risk_tier: str
    explanation: str
    shap_values: Dict[str, float]
    status: str
    model_source: str

@router.post("/analyze", response_model=TransactionResponse, status_code=status.HTTP_200_OK)
async def analyze_transaction(payload: TransactionRequest):
    """Parses transaction payloads, scores fraud, publishes to Kafka, and tracks drift/latency metrics."""
    start_time = time.perf_counter()
    try:
        tx_dict = payload.model_dump()
        tx_dict["user_id"] = str(tx_dict["user_id"])
        
        # 1. Update features distribution slide window to compute data drift (Evidently AI)
        drift_detector.check_drift(tx_dict["amount"], tx_dict["velocity_1h"])
        
        # 2. Invoke singleton fraud engine prediction
        result = fraud_engine.score_transaction(tx_dict)
        
        tier = result["risk_tier"]
        action_status = "flagged_for_investigation" if tier in ["HIGH", "CRITICAL"] else "approved"
        
        # 3. Decouple paths asynchronously by publishing event to Apache Kafka stream
        try:
            producer = get_kafka_producer()
            event_payload = {
                "transaction": tx_dict,
                "fraud_assessment": {
                    "probability": result["fraud_probability"],
                    "anomaly_score": result["anomaly_score"],
                    "risk_tier": tier,
                    "status": action_status
                }
            }
            producer.produce(
                topic="transactions.raw",
                key=tx_dict["user_id"],
                value=json.dumps(event_payload)
            )
            # Flush asynchronously with short local poll timeout to prevent gateway blockages
            producer.flush(timeout=0.05)
        except Exception as k_err:
            logger.error(f"Kafka event streaming ingestion failed: {k_err}")
            
        # 4. Update Prometheus dashboard gauges and metrics
        latency = time.perf_counter() - start_time
        FRAUD_SCORING_LATENCY.observe(latency)
        TRANSACTIONS_PROCESSED.labels(channel=tx_dict["channel"], risk_tier=tier).inc()
        
        return TransactionResponse(
            fraud_probability=result["fraud_probability"],
            anomaly_score=result["anomaly_score"],
            risk_tier=tier,
            explanation=result["explanation"],
            shap_values=result["shap_values"],
            status=action_status,
            model_source=result["model_source"]
        )
    except Exception as e:
        logger.error(f"Failed to analyze transaction for user {payload.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Real-time transaction scoring execution failed: {str(e)}"
        )
