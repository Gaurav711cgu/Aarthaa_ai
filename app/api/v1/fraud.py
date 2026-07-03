from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, List, Optional
import uuid
import logging
import time
import json
import hashlib

from app.services.fraud_model import fraud_engine
from app.services.monitoring import TRANSACTIONS_PROCESSED, FRAUD_SCORING_LATENCY
from app.services.drift_detector import drift_detector
from app.kafka_client import get_kafka_producer
from app.api.v1.auth import RoleEnforcer

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.redis_client import get_redis_client
from app.models.statement import ScoredTransaction

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
    card1: Optional[int] = Field(None, description="Card ID profile")
    timestamp: Optional[int] = Field(None, description="Transaction timestamp (epoch)")
    addr1: Optional[float] = Field(None, description="Billing address code")
    P_emaildomain: Optional[str] = Field(None, description="Purchaser email domain")
    R_emaildomain: Optional[str] = Field(None, description="Recipient email domain")
    DeviceType: Optional[str] = Field(None, description="Device type")

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

def _idempotency_key(tx_data: dict) -> str:
    """SHA-256 of canonical transaction fields."""
    card1 = tx_data.get("card1") or 1004
    amount = tx_data.get("amount") or 0.0
    timestamp = tx_data.get("timestamp") or int(time.time())
    canonical = f"{card1}:{amount}:{timestamp}"
    return f"idem:{hashlib.sha256(canonical.encode()).hexdigest()}"

@router.post("/score", response_model=TransactionResponse, status_code=status.HTTP_200_OK)
async def score_transaction(
    payload: TransactionRequest, 
    current_user: Dict[str, Any] = Depends(RoleEnforcer("analyst")),
    db: Session = Depends(get_db)
):
    """Parses transaction payloads, scores fraud with hybrid GNN+RF model, caches, and tracks drift."""
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
        
        # 1. Idempotency Check
        key = _idempotency_key(tx_dict)
        redis = get_redis_client()
        
        # SETNX atomic lock
        is_new = redis.set(key, "1", nx=True, ex=300)
        if not is_new:
            cached = redis.get(f"result:{key}")
            if cached:
                cached_data = json.loads(cached)
                return TransactionResponse(
                    fraud_probability=cached_data["fraud_probability"],
                    anomaly_score=cached_data["anomaly_score"],
                    risk_tier=cached_data["risk_tier"],
                    explanation=cached_data["explanation"],
                    shap_values=cached_data["shap_values"],
                    shap_chart_data=ShapChartData(**cached_data["shap_chart_data"]),
                    status=cached_data["status"],
                    model_source=cached_data["model_source"]
                )

        # 1.5. Query history upfront for real-time feature engineering & GNN neighborhood
        card1_raw = tx_dict.get("card1")
        card1 = int(card1_raw if card1_raw is not None else 1004)
        
        recent_txs_raw = db.execute(
            text("SELECT card1, amount, timestamp, addr1, P_emaildomain, R_emaildomain, DeviceType, velocity_1h, velocity_6h, velocity_24h FROM transactions WHERE card1 = :card1 ORDER BY timestamp DESC LIMIT 50"),
            {"card1": card1}
        ).fetchall()
        
        recent_txs = []
        for r in recent_txs_raw:
            recent_txs.append({
                "card1": r[0],
                "amount": r[1],
                "timestamp": r[2],
                "addr1": r[3],
                "P_emaildomain": r[4],
                "R_emaildomain": r[5],
                "DeviceType": r[6],
                "velocity_1h": r[7],
                "velocity_6h": r[8],
                "velocity_24h": r[9]
            })

        # Calculate dynamic amount to historical average ratio
        history_amounts = [r[1] for r in recent_txs_raw]
        if history_amounts:
            mean_amt = sum(history_amounts) / len(history_amounts)
        else:
            mean_amt = float(tx_dict.get("amount", 0.0))
            
        amount_to_mean_ratio = float(tx_dict.get("amount", 0.0)) / mean_amt if mean_amt > 0 else 1.0
        tx_dict["amount_to_mean_ratio"] = amount_to_mean_ratio

        # 2. Invoke ensemble fraud engine prediction
        result = fraud_engine.score_transaction(tx_dict)
        meta_dict = result.get("meta_dict", tx_dict)

        # 3. GNN score with card context
        from app.services.graph_fraud import graph_scorer
        gnn_result = graph_scorer.score_with_context(
            current_tx=meta_dict,
            recent_txs=recent_txs
        )
        
        # Hybrid score combination
        rf_prob = result["fraud_probability"]
        if gnn_result["graph_available"] and gnn_result["gnn_score"] is not None and len(recent_txs) > 0:
            hybrid_score = 0.6 * rf_prob + 0.4 * gnn_result["gnn_score"]
        else:
            hybrid_score = rf_prob
            
        # Determine final tier from hybrid score
        tier = "LOW"
        if hybrid_score >= 0.85:
            tier = "CRITICAL"
        elif hybrid_score >= 0.50:
            tier = "HIGH"
        elif hybrid_score >= 0.20:
            tier = "MEDIUM"
            
        action_status = "flagged_for_investigation" if tier in ["HIGH", "CRITICAL"] else "approved"
        
        # 4. Update data drift detector using full feature dict
        drift_detector.check_drift(meta_dict)
        
        # 5. Decouple paths asynchronously by publishing event to Apache Kafka stream
        try:
            producer = get_kafka_producer()
            event_payload = {
                "transaction": tx_dict,
                "fraud_assessment": {
                    "probability": round(hybrid_score, 4),
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
            
        # 6. Save current transaction to DB
        db_tx = ScoredTransaction(
            card1=int(meta_dict.get("card1") if meta_dict.get("card1") is not None else 1004),
            amount=float(meta_dict.get("amount") if meta_dict.get("amount") is not None else meta_dict.get("TransactionAmt", 0.0)),
            timestamp=int(meta_dict.get("timestamp") if meta_dict.get("timestamp") is not None else int(time.time())),
            addr1=float(meta_dict.get("addr1") if meta_dict.get("addr1") is not None else 150.0),
            P_emaildomain=str(meta_dict.get("P_emaildomain") if meta_dict.get("P_emaildomain") is not None else "gmail.com"),
            R_emaildomain=str(meta_dict.get("R_emaildomain") if meta_dict.get("R_emaildomain") is not None else "gmail.com"),
            DeviceType=str(meta_dict.get("DeviceType") if meta_dict.get("DeviceType") is not None else "desktop"),
            velocity_1h=int(meta_dict.get("velocity_1h") if meta_dict.get("velocity_1h") is not None else 1),
            velocity_6h=int(meta_dict.get("velocity_6h") if meta_dict.get("velocity_6h") is not None else 1),
            velocity_24h=int(meta_dict.get("velocity_24h") if meta_dict.get("velocity_24h") is not None else 1)
        )
        db.add(db_tx)
        db.commit()
        
        # 7. Update Prometheus dashboard gauges and metrics
        latency = time.perf_counter() - start_time
        FRAUD_SCORING_LATENCY.observe(latency)
        TRANSACTIONS_PROCESSED.labels(channel=tx_dict["channel"], risk_tier=tier).inc()
        
        res_data = {
            "fraud_probability": round(hybrid_score, 4),
            "anomaly_score": result["anomaly_score"],
            "risk_tier": tier,
            "explanation": result["explanation"],
            "shap_values": result["shap_values"],
            "shap_chart_data": result["shap_chart_data"],
            "status": action_status,
            "model_source": "hybrid_rf_gnn" if gnn_result["graph_available"] else "RandomForest+IsolationForest_Ensemble"
        }
        
        # Cache response
        redis.set(f"result:{key}", json.dumps(res_data), ex=300)
        
        return TransactionResponse(
            fraud_probability=res_data["fraud_probability"],
            anomaly_score=res_data["anomaly_score"],
            risk_tier=res_data["risk_tier"],
            explanation=res_data["explanation"],
            shap_values=res_data["shap_values"],
            shap_chart_data=ShapChartData(**res_data["shap_chart_data"]),
            status=res_data["status"],
            model_source=res_data["model_source"]
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
            drift_detector.check_drift(tx_dict)
            
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
