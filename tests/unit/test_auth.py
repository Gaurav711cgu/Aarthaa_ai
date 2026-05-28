import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_login_success():
    """Verify that valid credentials return a JWT token with bearer type."""
    response = client.post("/auth/token", json={
        "username": "analyst",
        "password": "analyst_password_2026"
    })
    assert response.status_code == 200
    json_data = response.json()
    assert "access_token" in json_data
    assert json_data["token_type"] == "bearer"

def test_login_invalid_credentials():
    """Verify that invalid credentials return HTTP 401 Unauthorized."""
    response = client.post("/auth/token", json={
        "username": "analyst",
        "password": "wrong_password"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password."

def test_protected_routes_unauthorized():
    """Verify that accessing protected endpoints without an Auth header returns HTTP 401."""
    # Fraudscoring endpoint should fail immediately without auth header
    response = client.post("/api/v1/fraud/score", json={
        "amount": 45000.0,
        "hour": 23,
        "velocity_1h": 2,
        "distance_from_home": 345.5,
        "merchant_risk": 0.12,
        "user_id": "00000000-0000-0000-0000-000000000000",
        "channel": "UPI"
    })
    assert response.status_code == 401
    assert "detail" in response.json()

def test_role_hierarchy_authorization():
    """Verify that users are restricted based on their role tiers."""
    # 1. Obtain token for readonly user
    response = client.post("/auth/token", json={
        "username": "readonly",
        "password": "readonly_password_2026"
    })
    assert response.status_code == 200
    readonly_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {readonly_token}"}
    
    # 2. Try to query compliance (requires readonly+) -> should succeed
    response = client.post("/api/v1/compliance/query", json={"query": "What is the UPI limit?"}, headers=headers)
    assert response.status_code == 200
    
    # 3. Try to score fraud (requires analyst+) -> should fail with 403 Forbidden
    response = client.post("/api/v1/fraud/score", json={
        "amount": 45000.0,
        "hour": 23,
        "velocity_1h": 2,
        "distance_from_home": 345.5,
        "merchant_risk": 0.12,
        "user_id": "00000000-0000-0000-0000-000000000000",
        "channel": "UPI"
    }, headers=headers)
    assert response.status_code == 403
    assert "requires role 'analyst' or higher" in response.json()["detail"]

def test_token_rotation_invalidates_old_tokens():
    """Verify that rotating the signing key invalidates all outstanding tokens."""
    # 1. Obtain token for analyst
    response = client.post("/auth/token", json={
        "username": "analyst",
        "password": "analyst_password_2026"
    })
    analyst_token = response.json()["access_token"]
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}
    
    # Verify the token works
    response = client.post("/api/v1/fraud/score", json={
        "amount": 45000.0,
        "hour": 23,
        "velocity_1h": 2,
        "distance_from_home": 345.5,
        "merchant_risk": 0.12,
        "user_id": "00000000-0000-0000-0000-000000000000",
        "channel": "UPI"
    }, headers=analyst_headers)
    assert response.status_code == 200
    
    # 2. Login as admin and trigger key rotation
    response = client.post("/auth/token", json={
        "username": "admin",
        "password": "admin_password_2026"
    })
    admin_token = response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    response = client.put("/auth/rotate-key", headers=admin_headers)
    assert response.status_code == 200
    
    # 3. Try to reuse the old analyst token -> should return 401 Unauthorized now!
    response = client.post("/api/v1/fraud/score", json={
        "amount": 45000.0,
        "hour": 23,
        "velocity_1h": 2,
        "distance_from_home": 345.5,
        "merchant_risk": 0.12,
        "user_id": "00000000-0000-0000-0000-000000000000",
        "channel": "UPI"
    }, headers=analyst_headers)
    assert response.status_code == 401
    assert "Could not validate credentials." in response.json()["detail"]
