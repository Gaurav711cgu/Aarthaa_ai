from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any,  List
import uuid
import logging
import time
import json

from app.services.fraud_model import fraud_engine
from app.services.monitoring import TRANSACTIONS_PROCESSED, FRAUD_SCORING_LATENCY
from app.services.drift_detector import drift_detector
from app.kafka_client import get_kafka_producer
from app.api.v1.auth import RoleEnforcer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fraud", tags=["FraudSense"])

class TransactionRequest(BaseModel):
    amount: float = Field(..., description="Amount of the transaction in ₹ (INR)")
    hour: int = Field(..., description="Hour of the day (0-23)")
    velocity_1h: int = Field(..., ge=0, description="Number of transactions in the last hour")
    distance_from_home: float = Field(..., ge=0.0, description="Distance from cardholder's home address in km")
    merchant_risk: float = Field(0.05, ge=0.0, le=1.0, description="Calculated risk value of processing merchant (0.0 to 1.0)")
    user_id: uuid.UUID = Field(..., description="Cardholder's unique identification key")
    channel: str = Field("UPI", description="Transaction processing channel (e.g., UPI, CASH, CARD)")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v < 0.0 or v > 1000000000.0:
            raise ValueError("Amount must be between 0.0 and 1,000,000,000.0")
        return v

    @field_validator("hour")
    @classmethod
    def validate_hour(cls, v: int) -> int:
        if v < 0 or v > 23:
            raise ValueError("Hour must be between 0 and 23")
        return v

class ShapChartData(BaseModel):
    features: List[str]
    values: List[float]

class TransactionResponse(BaseModel):
    fraud_probability: float
    anomaly_score: float
    risk_tier: str
    explanation: str
    shap_values: Dict[str, float]
    shap_chart_data: ShapChartData
    status: str
    model_source: str

@router.post("/score", response_model=TransactionResponse, status_code=status.HTTP_200_OK)
async def score_transaction(
    payload: TransactionRequest, 
    current_user: Dict[str, Any] = Depends(RoleEnforcer("analyst"))
):
    """Parses transaction payloads, scores fraud, publishes to Kafka, and tracks drift/latency metrics."""
    if fraud_engine.is_training:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FraudSense engine is auto-training in the background. Please try again shortly.",
            headers={"Retry-After": "30"}
        )
        
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
            shap_chart_data=ShapChartData(**result["shap_chart_data"]),
            status=action_status,
            model_source=result["model_source"]
        )
    except Exception as e:
        logger.error(f"Failed to analyze transaction for user {payload.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Real-time transaction scoring execution failed: {str(e)}"
        )

@router.post("/score/batch", response_model=List[TransactionResponse], status_code=status.HTTP_200_OK)
async def score_batch_transactions(
    payload: List[TransactionRequest],
    current_user: Dict[str, Any] = Depends(RoleEnforcer("analyst"))
):
    """Processes a batch of transaction payloads, scores fraud, and publishes batch summary to Kafka."""
    if len(payload) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch transaction size cannot exceed 100 items."
        )
        
    if fraud_engine.is_training:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FraudSense engine is auto-training in the background. Please try again shortly.",
            headers={"Retry-After": "30"}
        )
        
    start_time = time.perf_counter()
    responses = []
    
    try:
        for tx in payload:
            tx_dict = tx.model_dump()
            tx_dict["user_id"] = str(tx_dict["user_id"])
            
            # 1. Update features distribution slide window to compute data drift (Evidently AI)
            drift_detector.check_drift(tx_dict["amount"], tx_dict["velocity_1h"])
            
            # 2. Invoke singleton fraud engine prediction
            result = fraud_engine.score_transaction(tx_dict)
            tier = result["risk_tier"]
            action_status = "flagged_for_investigation" if tier in ["HIGH", "CRITICAL"] else "approved"
            
            responses.append(
                TransactionResponse(
                    fraud_probability=result["fraud_probability"],
                    anomaly_score=result["anomaly_score"],
                    risk_tier=tier,
                    explanation=result["explanation"],
                    shap_values=result["shap_values"],
                    shap_chart_data=ShapChartData(**result["shap_chart_data"]),
                    status=action_status,
                    model_source=result["model_source"]
                )
            )
            
            # Update metrics per transaction
            TRANSACTIONS_PROCESSED.labels(channel=tx_dict["channel"], risk_tier=tier).inc()
            
        # 3. Publish batch summary event to Kafka
        try:
            producer = get_kafka_producer()
            batch_summary = {
                "event_type": "fraud_batch_summary",
                "batch_size": len(payload),
                "timestamp": time.time(),
                "critical_count": sum(1 for r in responses if r.risk_tier == "CRITICAL"),
                "high_count": sum(1 for r in responses if r.risk_tier == "HIGH"),
                "medium_count": sum(1 for r in responses if r.risk_tier == "MEDIUM"),
                "low_count": sum(1 for r in responses if r.risk_tier == "LOW")
            }
            producer.produce(
                topic="artha.fraud.batch",
                key="batch_summary",
                value=json.dumps(batch_summary)
            )
            producer.flush(timeout=0.05)
        except Exception as k_err:
            logger.error(f"Kafka batch event streaming summary failed: {k_err}")
            
        # 4. Record latency for the overall batch run
        latency = time.perf_counter() - start_time
        FRAUD_SCORING_LATENCY.observe(latency)
        
        return responses
    except Exception as e:
        logger.error(f"Failed to analyze batch of transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch transaction scoring execution failed: {str(e)}"
        )

@router.get("/metrics", status_code=status.HTTP_200_OK)
def get_model_metrics(current_user: Dict[str, Any] = Depends(RoleEnforcer("readonly"))):
    """Exposes accuracy and calibration statistics for active ensemble models."""
    if fraud_engine.is_training:
        return {
            "status": "training",
            "metrics": {}
        }
    return {
        "status": "ready",
        "model_source": "RandomForest+IsolationForest_Ensemble" if fraud_engine.is_compiled else "Heuristic_Rules",
        "metrics": fraud_engine.metrics
    }
