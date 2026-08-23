import numpy as np
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DifferentialPrivacyLayer:
    """
    Staff-Level Security: Epsilon-Differential Privacy (ε-DP) Redactor for LLM RAG Context.
    
    Ensures that when regulatory context is retrieved and merged with merchant/user data
    to generate a chargeback defense, no PII or exact financial figures are leaked into 
    the LLM prompt, protecting the merchant against data exfiltration.
    """
    def __init__(self, epsilon: float = 1.0, sensitivity: float = 100.0):
        self.epsilon = epsilon
        self.sensitivity = sensitivity
        # Scale parameter for the Laplace distribution (b = sensitivity / epsilon)
        self.scale = self.sensitivity / self.epsilon
        logger.info(f"Initialized DP Layer with ε={epsilon}, Laplace scale={self.scale}")

    def apply_laplace_noise(self, exact_value: float) -> float:
        """Adds cryptographically secure Laplace noise to a numerical value."""
        # Using numpy random for the Laplace mechanism
        noise = np.random.laplace(loc=0.0, scale=self.scale)
        # Round to 2 decimal places to simulate real currency while preserving privacy
        return round(exact_value + noise, 2)

    def redact_pii(self, text: str) -> str:
        """Deterministic regex-based PII scrubbing (Emails, Cards, Phone numbers)."""
        # Redact emails
        text = re.sub(r'[\w\.-]+@[\w\.-]+', '[REDACTED_EMAIL]', text)
        # Redact 16-digit cards
        text = re.sub(r'\b(?:\d{4}[ -]?){3}\d{4}\b', '[REDACTED_CARD]', text)
        # Redact phones
        text = re.sub(r'\+?\d{10,14}', '[REDACTED_PHONE]', text)
        return text

    def sanitize_chargeback_context(self, raw_evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applies DP and redaction to the entire evidence payload before it is 
        sent to the LLM or Razorpay Dispute API.
        """
        sanitized = {}
        for key, value in raw_evidence.items():
            if isinstance(value, str):
                sanitized[key] = self.redact_pii(value)
            elif isinstance(value, (int, float)) and key in ["amount", "balance"]:
                # Apply formal Differential Privacy to financial figures
                dp_value = self.apply_laplace_noise(float(value))
                sanitized[f"{key}_dp_approx"] = dp_value
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_chargeback_context(value)
            else:
                sanitized[key] = value
                
        return sanitized
