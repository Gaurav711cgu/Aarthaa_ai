import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class RazorpayTestClient:
    """
    Integration client for Razorpay AI Buildathon (Test Mode).
    Simulates fetching transaction details and generating chargeback evidence.
    """
    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.razorpay.com/v1"

    def fetch_payment_details(self, payment_id: str) -> Dict[str, Any]:
        """Fetch payment details from Razorpay API. (Mocked for buildathon)"""
        logger.info(f"[Razorpay] Fetching details for payment {payment_id}")
        
        # Simulate Razorpay payment object mapping to our feature schema
        return {
            "payment_id": payment_id,
            "amount": 25000.0,
            "currency": "INR",
            "method": "upi",
            "email": "fraud_test@gmail.com",
            "contact": "+919876543210",
            # Mapped to Aarthaa features
            "card1": 4123,
            "addr1": 300.0,
            "velocity_1h": 3,
            "velocity_6h": 5,
            "velocity_24h": 12
        }

    def generate_chargeback_evidence(self, payment_id: str, fraud_score: float, shap_explanation: str, regulatory_context: str) -> Dict[str, Any]:
        """
        Constructs a structured JSON payload that would be submitted to the 
        Razorpay Dispute API as evidence against a chargeback.
        """
        logger.info(f"[Razorpay] Generating chargeback evidence for {payment_id}")
        
        return {
            "dispute_id": f"disp_{payment_id[-10:]}",
            "evidence": {
                "billing_address": "Verified via AVS",
                "customer_email": "fraud_test@gmail.com",
                "customer_phone": "Verified via OTP",
                "explanation_letter": f"Transaction was verified with {1-fraud_score:.2%} confidence. "
                                      f"SHAP ML Risk Analysis: {shap_explanation}. "
                                      f"Regulatory basis: {regulatory_context}"
            }
        }
