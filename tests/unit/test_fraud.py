from fastapi.testclient import TestClient
from app.main import app as fastapi_app
from app.services.fraud_model import fraud_engine
import uuid
from unittest.mock import patch, MagicMock

client = TestClient(fastapi_app)

def get_analyst_headers():
    response = client.post("/auth/token", json={
        "username": "analyst",
        "password": "analyst_password_2026"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@patch("app.services.graph_fraud.graph_scorer.score_with_context")
def test_analyze_low_risk_transaction(mock_score):
    """Verify that a standard legitimate transaction gets approved."""
    mock_score.return_value = {"graph_available": False, "gnn_score": None}
    
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = [[0.99, 0.01]] # 1% fraud probability -> LOW risk
    
    with patch.object(fraud_engine, "rf_model", mock_model):
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
        assert any(k in data["shap_values"] for k in ["amount", "TransactionAmt"])
        assert data["model_source"] in ["RandomForest+IsolationForest_Ensemble", "hybrid_rf_gnn"]

@patch("app.services.graph_fraud.graph_scorer.score_with_context")
def test_analyze_high_risk_transaction(mock_score):
    """Verify that a fraudulent transaction pattern gets flagged."""
    mock_score.return_value = {"graph_available": False, "gnn_score": None}
    
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = [[0.05, 0.95]] # 95% fraud probability -> CRITICAL risk
    
    with patch.object(fraud_engine, "rf_model", mock_model):
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
    """Verify that negative amounts or invalid schema payloads get rejected with 422 Unprocessable Entity."""
    headers = get_analyst_headers()
    invalid_payload = {
        "amount": -50.0, # Invalid negative amount
        "hour": 12,
        "user_id": str(uuid.uuid4())
    }
    response = client.post("/api/v1/fraud/score", json=invalid_payload, headers=headers)
    assert response.status_code == 422
