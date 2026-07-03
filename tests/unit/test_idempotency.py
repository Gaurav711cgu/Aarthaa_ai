import uuid
import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_analyst_headers():
    response = client.post("/auth/token", json={
        "username": "analyst",
        "password": "analyst_password_2026"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_idempotent_scoring():
    """Verify that duplicate transaction scoring requests are cached and return duplicate results."""
    payload = {
        "amount": 120.0,
        "hour": 10,
        "velocity_1h": 1,
        "distance_from_home": 1.2,
        "merchant_risk": 0.01,
        "user_id": str(uuid.uuid4()),
        "card1": 9999,
        "timestamp": 1711111111
    }
    
    headers = get_analyst_headers()
    
    # Send transaction first time (runs model scoring)
    resp1 = client.post("/api/v1/fraud/score", json=payload, headers=headers)
    assert resp1.status_code == 200
    data1 = resp1.json()
    
    # Send duplicate transaction second time (returns cached result)
    resp2 = client.post("/api/v1/fraud/score", json=payload, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    
    assert data1["fraud_probability"] == data2["fraud_probability"]
    assert data1["risk_tier"] == data2["risk_tier"]
    assert data1["status"] == data2["status"]
    assert data1["explanation"] == data2["explanation"]
