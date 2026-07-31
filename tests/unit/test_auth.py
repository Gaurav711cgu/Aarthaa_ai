from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.auth import verify_token, blacklist_jti, is_jti_blacklisted

client = TestClient(app)

def test_login_dual_token_success():
    """Verify that valid credentials return both an access token and refresh token."""
    response = client.post("/auth/token", json={
        "username": "analyst",
        "password": "analyst_password_2026"
    })
    assert response.status_code == 200
    json_data = response.json()
    assert "access_token" in json_data
    assert "refresh_token" in json_data
    assert json_data["token_type"] == "bearer"
    assert json_data["expires_in"] == 1800
    assert json_data["refresh_expires_in"] == 604800

def test_login_invalid_credentials():
    """Verify that invalid credentials return HTTP 401 Unauthorized."""
    response = client.post("/auth/token", json={
        "username": "analyst",
        "password": "wrong_password"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password."

def test_refresh_token_rotation():
    """Verify that exchanging a refresh token returns new dual tokens and revokes the old refresh token JTI."""
    # 1. Login to get initial token pair
    login_res = client.post("/auth/token", json={
        "username": "analyst",
        "password": "analyst_password_2026"
    })
    tokens = login_res.json()
    refresh_token_1 = tokens["refresh_token"]

    # 2. Refresh tokens
    refresh_res = client.post("/auth/refresh", json={"refresh_token": refresh_token_1})
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens

    # 3. Attempt to reuse old refresh token -> Should fail with 401 (Revoked)
    replay_res = client.post("/auth/refresh", json={"refresh_token": refresh_token_1})
    assert replay_res.status_code == 401
    assert "revoked" in replay_res.json()["detail"].lower()

def test_logout_blacklists_access_and_refresh_tokens():
    """Verify that logging out revokes JTI in Redis and blocks subsequent requests."""
    # 1. Obtain token pair
    login_res = client.post("/auth/token", json={
        "username": "analyst",
        "password": "analyst_password_2026"
    })
    tokens = login_res.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Call logout with access token and refresh token
    logout_res = client.post("/auth/logout", json={"refresh_token": refresh_token}, headers=headers)
    assert logout_res.status_code == 200
    assert logout_res.json()["revoked_count"] >= 1

    # 3. Use revoked access token to access protected endpoint -> 401 Unauthorized
    protected_res = client.post("/api/v1/fraud/score", json={
        "amount": 45000.0,
        "hour": 23,
        "velocity_1h": 2,
        "distance_from_home": 345.5,
        "merchant_risk": 0.12,
        "user_id": "00000000-0000-0000-0000-000000000000",
        "channel": "UPI"
    }, headers=headers)
    assert protected_res.status_code == 401
    assert "revoked" in protected_res.json()["detail"].lower()

def test_admin_manual_jti_revocation():
    """Verify that admin can manually revoke a JTI via /auth/revoke."""
    # 1. Login as admin
    admin_res = client.post("/auth/token", json={
        "username": "admin",
        "password": "admin_password_2026"
    })
    admin_token = admin_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Revoke a dummy JTI
    revoke_res = client.post("/auth/revoke", json={"jti": "test-jti-uuid-12345"}, headers=admin_headers)
    assert revoke_res.status_code == 200
    assert revoke_res.json()["jti"] == "test-jti-uuid-12345"

    # Verify blacklisted in Redis helper
    assert is_jti_blacklisted("test-jti-uuid-12345") is True

def test_protected_routes_unauthorized():
    """Verify that accessing protected endpoints without an Auth header returns HTTP 401."""
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
