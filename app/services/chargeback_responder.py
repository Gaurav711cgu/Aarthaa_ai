import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ChargebackResponder:
    """
    Auto-generates chargeback evidence using SHAP explanations and RAG context.
    Built for the Razorpay AI Risk Manager track.
    """
    def __init__(self, fraud_detector, rag_service, razorpay_client):
        self.fraud_detector = fraud_detector
        self.rag_service = rag_service
        self.rzp_client = razorpay_client

    def build_defense(self, payment_id: str, dispute_reason: str, user_features: list) -> Dict[str, Any]:
        """
        Builds a comprehensive defense against a chargeback.
        """
        logger.info(f"Building chargeback defense for {payment_id} due to {dispute_reason}")
        
        # Explain why we approved the transaction
        explanation = self.fraud_detector.explain(user_features)
        
        # Get regulatory backing for our decision
        query = f"Provide RBI guidelines or merchant terms supporting the validity of this transaction despite {dispute_reason}."
        rag_context = self.rag_service.query_regulatory_context(query)
        
        defense_payload = self.rzp_client.generate_chargeback_evidence(
            payment_id=payment_id,
            fraud_score=0.01,  # If it's a chargeback, it means we initially scored it low risk
            shap_explanation=explanation["summary"],
            regulatory_context=rag_context["summary"]
        )
        
        return defense_payload
