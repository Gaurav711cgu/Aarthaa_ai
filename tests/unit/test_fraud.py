from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

def test_analyze_low_risk_transaction():
    """Verify that a standard legitimate transaction gets approved."""
    payload = {
        "amount": 250.0, # ₹250
        "hour": 14, # 2PM
        "velocity_1h": 1,
        "distance_from_home": 2.5,
        "merchant_risk": 0.02,
        "user_id": str(uuid.uuid4())
    }
    
    response = client.post("/api/v1/fraud/analyze", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["risk_tier"] == "LOW"
    assert data["status"] == "approved"
    assert "explanation" in data
    assert "shap_values" in data
    assert "amount" in data["shap_values"]
    assert data["model_source"] == "RandomForest+IsolationForest_Ensemble"

def test_analyze_high_risk_transaction():
    """Verify that a fraudulent transaction pattern gets flagged."""
    payload = {
        "amount": 850000.0, # ₹8.5L (high amount)
        "hour": 3, # 3AM (odd hours)
        "velocity_1h": 12, # high velocity
        "distance_from_home": 1500.0, # far away
        "merchant_risk": 0.85, # high merchant risk
        "user_id": str(uuid.uuid4())
    }
    
    response = client.post("/api/v1/fraud/analyze", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["risk_tier"] in ["HIGH", "CRITICAL"]
    assert data["status"] == "flagged_for_investigation"
    assert "explanation" in data
    # Explanation should contain indicators
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
    
    response = client.post("/api/v1/fraud/analyze", json=payload)
    assert response.status_code == 422 # Unprocessable Entity
