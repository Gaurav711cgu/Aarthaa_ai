import os
import pickle
import numpy as np
import pandas as pd
import shap
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Derive paths dynamically based on the file location for full ecosystem portability
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "app", "models", "fraud_model.pkl")

class FraudScoringEngine:
    """Production-grade transaction fraud scoring engine utilizing RandomForest + Isolation Forest."""
    def __init__(self):
        self.features = ["amount", "hour", "velocity_1h", "distance_from_home", "merchant_risk"]
        self.rf_model = None
        self.iforest = None
        self.explainer = None
        self.metrics = {}
        self.is_compiled = False
        
        self._load_model()
        
    def _load_model(self):
        """Loads serialized model files or defaults to heuristic scoring if files are missing."""
        if os.path.exists(MODEL_PATH):
            try:
                with open(MODEL_PATH, "rb") as f:
                    ensemble = pickle.load(f)
                self.rf_model = ensemble["rf"]
                self.iforest = ensemble["iforest"]
                self.features = ensemble["features"]
                self.metrics = ensemble.get("metrics", {})
                
                # Build real-time tree SHAP explainer for Random Forest
                self.explainer = shap.TreeExplainer(self.rf_model)
                self.is_compiled = True
                logger.info("Ensemble fraud scoring models and SHAP explainer loaded successfully.")
                return
            except Exception as e:
                logger.error(f"Error loading fraud models package: {e}")
                
        # Default fallback flag
        self.is_compiled = False
        logger.warning("Ensemble model package not found. Activating heuristic fallback scoring engine.")

    def score_transaction(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates fraud probabilities, anomaly thresholds, and natural language explanations."""
        # 1. Standardize features dictionary
        features_dict = {
            "amount": float(tx_data.get("amount", 0.0)),
            "hour": int(tx_data.get("hour", 12)),
            "velocity_1h": int(tx_data.get("velocity_1h", 1)),
            "distance_from_home": float(tx_data.get("distance_from_home", 0.0)),
            "merchant_risk": float(tx_data.get("merchant_risk", 0.05))
        }
        
        # Parse into DataFrame
        df_row = pd.DataFrame([features_dict], columns=self.features)
        
        if self.is_compiled and self.rf_model and self.iforest:
            try:
                # Class probabilities (positive class probability)
                prob = float(self.rf_model.predict_proba(df_row)[0][1])
                
                # Anomaly decision function score (lower values are more anomalous)
                anomaly_score = float(self.iforest.decision_function(df_row)[0])
                
                # Dynamic feature explainability via Tree SHAP values
                raw_shap_vals = self.explainer.shap_values(df_row)
                
                # Handle scikit-learn Random Forest output format for Tree SHAP:
                # Typically returns a list [shap_values_class0, shap_values_class1] or a 3D array
                if isinstance(raw_shap_vals, list):
                    # Select positive class contributions (class 1)
                    shap_vals = raw_shap_vals[1][0]
                elif isinstance(raw_shap_vals, np.ndarray):
                    if len(raw_shap_vals.shape) == 3:
                        # shape: (num_samples, num_features, num_classes)
                        shap_vals = raw_shap_vals[0, :, 1]
                    else:
                        shap_vals = raw_shap_vals[0]
                else:
                    shap_vals = np.zeros(len(self.features))
                
                # Align features to SHAP values
                shap_contributions = dict(zip(self.features, [float(v) for v in shap_vals]))
                
                # Generate explanation narrative
                explanation, risk_tier = self._compile_explanation_and_tier(prob, anomaly_score, shap_contributions, features_dict)
                
                return {
                    "fraud_probability": prob,
                    "anomaly_score": anomaly_score,
                    "risk_tier": risk_tier,
                    "explanation": explanation,
                    "shap_values": shap_contributions,
                    "model_source": "RandomForest+IsolationForest_Ensemble"
                }
            except Exception as e:
                logger.error(f"Inference pipeline execution error: {e}. Defaulting to heuristic fallback.")
                
        # 2. Heuristic Fallback logic
        return self._heuristic_fallback(features_dict)

    def _compile_explanation_and_tier(
        self, prob: float, anomaly_score: float, shap_vals: Dict[str, float], tx: Dict[str, Any]
    ) -> Tuple[str, str]:
        """Calculates risk categories and creates structural natural language rationales."""
        # Risk Tier assignment
        if prob >= 0.85:
            tier = "CRITICAL"
        elif prob >= 0.60:
            tier = "HIGH"
        elif prob >= 0.20:
            tier = "MEDIUM"
        else:
            tier = "LOW"
            
        # Select top indicators based on absolute SHAP weights
        sorted_shap = sorted(shap_vals.items(), key=lambda x: abs(x[1]), reverse=True)
        top_features = [f[0] for f in sorted_shap if f[1] > 0.01][:3]
        
        if not top_features:
            explanation = "Transaction shows standard operational parameters matching historical customer profiles."
            return explanation, tier
            
        narratives = []
        for feat in top_features:
            if feat == "amount":
                narratives.append(f"high transaction value (₹{tx['amount']:,.2f})")
            elif feat == "velocity_1h":
                narratives.append(f"unusual transaction frequency ({tx['velocity_1h']} requests in the last hour)")
            elif feat == "distance_from_home":
                narratives.append(f"large physical distance from registration coordinates ({tx['distance_from_home']:.1f} km)")
            elif feat == "hour":
                narratives.append(f"unconventional transaction execution hour ({tx['hour']}:00)")
            elif feat == "merchant_risk":
                narratives.append("elevated risk index of merchant processing gateway")
                
        explanation = f"Transaction flagged as {tier} risk primarily due to: " + ", combined with ".join(narratives) + "."
        
        if anomaly_score < -0.05:
            explanation += " Isolation Forest isolated this transaction pattern as a structural anomaly."
            
        return explanation, tier

    def _heuristic_fallback(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        """Static rule-based heuristic scoring fallback for local offline compilation safety."""
        # Simple weighted risk scoring
        risk_score = 0.0
        indicators = []
        
        if tx["amount"] > 100000:
            risk_score += 0.4
            indicators.append("high amount")
        if tx["velocity_1h"] > 5:
            risk_score += 0.3
            indicators.append("extreme velocity")
        if tx["distance_from_home"] > 250:
            risk_score += 0.3
            indicators.append("geographical mismatch")
        if tx["hour"] in [1, 2, 3, 4]:
            risk_score += 0.1
            indicators.append("odd transaction hours")
        if tx["merchant_risk"] > 0.5:
            risk_score += 0.2
            indicators.append("unverified merchant gateway")
            
        prob = min(risk_score, 1.0)
        
        if prob >= 0.85:
            tier = "CRITICAL"
        elif prob >= 0.60:
            tier = "HIGH"
        elif prob >= 0.20:
            tier = "MEDIUM"
        else:
            tier = "LOW"
            
        if indicators:
            explanation = f"Transaction scored via rule engine. Flagged as {tier} due to: " + ", ".join(indicators) + "."
        else:
            explanation = "Transaction shows standard operational parameters matching rules."
            
        return {
            "fraud_probability": prob,
            "anomaly_score": 0.0,
            "risk_tier": tier,
            "explanation": explanation,
            "shap_values": {k: 0.1 for k in self.features},
            "model_source": "RuleEngine_Fallback"
        }

# Global singleton scoring engine
fraud_engine = FraudScoringEngine()
