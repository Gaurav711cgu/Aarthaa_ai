from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

def get_readonly_headers():
    response = client.post("/auth/token", json={
        "username": "readonly",
        "password": "readonly_password_2026"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_compliant_retail_transaction():
    """Verify standard retail UPI transfer is marked as fully compliant."""
    payload = {
        "amount": 2500.0, # ₹2,500
        "channel": "UPI",
        "is_international": False,
        "user_id": str(uuid.uuid4())
    }
    
    headers = get_readonly_headers()
    response = client.post("/api/v1/compliance/check", json=payload, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["is_compliant"] is True
    assert data["verdict"] == "COMPLIANT"
    assert len(data["violations"]) == 0
    assert len(data["citations"]) == 0

def test_upi_limit_violation():
    """Verify UPI transfer exceeding ₹1,00,000 daily limit gets flagged with citations."""
    payload = {
        "amount": 150000.0, # ₹1.5 Lakhs
        "channel": "UPI",
        "is_international": False,
        "user_id": str(uuid.uuid4())
    }
    
    headers = get_readonly_headers()
    response = client.post("/api/v1/compliance/check", json=payload, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["is_compliant"] is False
    assert data["verdict"] == "NON_COMPLIANT"
    assert len(data["violations"]) == 1
    assert "exceeds the standard daily cap of ₹1,00,000.00" in data["violations"][0]
    
    assert len(data["citations"]) == 1
    assert data["citations"][0]["document"] == "RBI_UPI_LIMITS_2024"
    assert data["citations"][0]["section"] == "Para 2.1 - Daily UPI Transaction Thresholds"

def test_fema_lrs_limit_violation():
    """Verify cross-border remittance exceeding LRS annual threshold gets flagged."""
    payload = {
        "amount": 25000000.0, # ₹2.5 Crore (approx USD 297,000 > USD 250K)
        "channel": "LRS",
        "is_international": True,
        "user_id": str(uuid.uuid4())
    }
    
    headers = get_readonly_headers()
    response = client.post("/api/v1/compliance/check", json=payload, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["is_compliant"] is False
    assert data["verdict"] == "NON_COMPLIANT"
    assert any("exceeds the FEMA LRS annual cap" in v for v in data["violations"])
    
    assert any(c["document"] == "FEMA_LRS_2024" for c in data["citations"])

def test_compliance_rag_query():
    """Verify semantic search queries retrieve and synthesize the correct circular citations."""
    payload = {
        "query": "What is the daily transaction limit for standard UPI?"
    }
    
    headers = get_readonly_headers()
    response = client.post("/api/v1/compliance/query", json=payload, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "answer" in data
    assert len(data["citations"]) > 0
    # Correct circular should be cited first due to high cosine similarity
    assert data["citations"][0]["document"] == "RBI_UPI_LIMITS_2024"
    assert "Para 2.1" in data["citations"][0]["section"]

