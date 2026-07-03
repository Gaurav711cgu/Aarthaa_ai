from fastapi.testclient import TestClient
from app.main import app
import uuid
from unittest.mock import patch

client = TestClient(app)

def get_analyst_headers():
    response = client.post("/auth/token", json={
        "username": "analyst",
        "password": "analyst_password_2026"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@patch("app.services.graph_fraud.graph_scorer.score_with_context")
@patch("app.services.fraud_model.fraud_engine.rf_model.predict_proba")
def test_analyze_low_risk_transaction(mock_predict, mock_score):
    """Verify that a standard legitimate transaction gets approved."""
    mock_score.return_value = {"graph_available": False, "gnn_score": None}
    mock_predict.return_value = [[0.99, 0.01]] # 1% fraud probability -> LOW risk
    
    payload = {
        "amount": 250.0, # ₹250
        "hour": 14, # 2PM
        "velocity_1h": 1,
        "distance_from_home": 2.5,
        "merchant_risk": 0.02,
        "user_id": str(uuid.uuid4())
    }
    
    headers = get_analyst_headers()
    response = client.post("/api/v1/fraud/score", json=payload, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["risk_tier"] == "LOW"
    assert data["status"] == "approved"
    assert "explanation" in data
    assert "shap_values" in data
    assert "amount" in data["shap_values"]
    assert data["model_source"] in ["RandomForest+IsolationForest_Ensemble", "hybrid_rf_gnn"]

@patch("app.services.graph_fraud.graph_scorer.score_with_context")
@patch("app.services.fraud_model.fraud_engine.rf_model.predict_proba")
def test_analyze_high_risk_transaction(mock_predict, mock_score):
    """Verify that a fraudulent transaction pattern gets flagged."""
    mock_score.return_value = {"graph_available": False, "gnn_score": None}
    mock_predict.return_value = [[0.05, 0.95]] # 95% fraud probability -> CRITICAL risk
    
    payload = {
        "amount": 850000.0, # ₹8.5L (high amount)
        "hour": 3, # 3AM (odd hours)
        "velocity_1h": 12, # high velocity
        "distance_from_home": 1500.0, # far away
        "merchant_risk": 0.85, # high merchant risk
        "user_id": str(uuid.uuid4())
    }
    
    headers = get_analyst_headers()
    response = client.post("/api/v1/fraud/score", json=payload, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["risk_tier"] in ["HIGH", "CRITICAL"]
    assert data["status"] == "flagged_for_investigation"
    assert "explanation" in data
    assert len(data["explanation"]) > 0

def test_analyze_invalid_payload():
    """Verify that invalid payloads are caught by Pydantic models."""
    payload = {
        "amount": -50.0, # invalid amount (must be >0)
        "hour": 25, # invalid hour (must be 0-23)
        "velocity_1h": -1, # invalid velocity (must be >=0)
        "distance_from_home": 12.0,
        "merchant_risk": 0.05,
        "user_id": "not-a-uuid" # invalid UUID
    }
    
    headers = get_analyst_headers()
    response = client.post("/api/v1/fraud/score", json=payload, headers=headers)
    assert response.status_code == 422 # Unprocessable Entity
