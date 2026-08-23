from fastapi import APIRouter, Depends, HTTPException, Request
import logging
import uuid
from typing import Dict, Any

from app.services.fraud_detector import FraudDetector, get_fraud_detector
from app.services.vector_store import RAGService, get_rag_service
from app.integrations.razorpay_client import RazorpayTestClient

router = APIRouter(prefix="/razorpay", tags=["Razorpay AI Risk Manager"])
logger = logging.getLogger(__name__)

rzp_client = RazorpayTestClient()

@router.post("/webhook")
async def handle_razorpay_webhook(
    request: Request,
    fraud_detector: FraudDetector = Depends(get_fraud_detector),
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    Webhook endpoint to receive Razorpay events (e.g. payment.captured, payment.failed).
    Scores the transaction in real-time.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("event")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    payment_id = payment_entity.get("id", f"pay_{uuid.uuid4().hex[:14]}")
    
    logger.info(f"[Razorpay Webhook] Received {event_type} for {payment_id}")

    # 1. Map Razorpay entity to our model features
    features = rzp_client.fetch_payment_details(payment_id)
    model_input = [
        features["amount"], features["card1"], features["addr1"], 
        features["velocity_1h"], features["velocity_6h"], features["velocity_24h"]
    ]
    
    # 2. Run Fraud Ensemble
    fraud_result = fraud_detector.predict(model_input)
    is_fraud = fraud_result["is_fraud"]
    risk_score = fraud_result["fraud_probability"]
    
    # 3. If high risk, generate SHAP explanation and regulatory context for SAR
    if is_fraud:
        explanation = fraud_detector.explain(model_input)
        rag_context = rag_service.query_regulatory_context("Transaction exceeds velocity and amount limits for UPI.")
        
        evidence = rzp_client.generate_chargeback_evidence(
            payment_id, risk_score, 
            shap_explanation=explanation["summary"],
            regulatory_context=rag_context["summary"]
        )
        
        logger.warning(f"🚨 [Razorpay Risk Manager] FRAUD DETECTED on {payment_id}. Evidence generated.")
        return {"status": "fraud_blocked", "risk_score": risk_score, "evidence": evidence}

    return {"status": "approved", "risk_score": risk_score}
