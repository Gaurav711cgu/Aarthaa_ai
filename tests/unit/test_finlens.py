from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)

# Realistic sample bank statement representation
MOCK_STATEMENT_TEXT = """
BANK: HDFC Bank India
ACCOUNT: 50100234567891
PERIOD: March 2026

2026-03-01 | Opening Balance | CREDIT | 50000.00 | 50000.00
2026-03-05 | Swiggy Food Delivery Order | DEBIT | 450.00 | 49550.00
2026-03-10 | Salary Credit JPMC GCC | CREDIT | 125000.00 | 174550.00
2026-03-15 | Uber Cab Travel Bhubaneswar | DEBIT | 350.00 | 174200.00
2026-03-20 | House Rent Payment | DEBIT | 15000.00 | 159200.00
"""

def get_analyst_headers():
    response = client.post("/auth/token", json={
        "username": "analyst",
        "password": "analyst_password_2026"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_upload_and_parse_bank_statement():
    """Verify that uploading a text-based bank statement successfully parses transactions and saves them to SQL."""
    payload = {
        "raw_text": MOCK_STATEMENT_TEXT
    }
    
    headers = get_analyst_headers()
    response = client.post("/api/v1/finlens/upload", json=payload, headers=headers)
    assert response.status_code == 201
    
    data = response.json()
    assert data["status"] == "ingested_and_committed"
    assert data["bank_name"] == "HDFC Bank India"
    assert data["account_number"] == "50100234567891"
    assert data["total_deposits"] == 175000.0 # 50K opening + 125K salary
    assert data["total_withdrawals"] == 15800.0 # 450 swiggy + 350 uber + 15K rent
    assert data["ending_balance"] == 159200.0
    assert data["transaction_count"] == 5
    assert "statement_id" in data

def test_query_closing_balance():
    """Verify that querying closing balance generates a SQL query and returns the exact math-verified float value."""
    # First, ensure statement is uploaded
    headers = get_analyst_headers()
    upload_res = client.post("/api/v1/finlens/upload", json={"raw_text": MOCK_STATEMENT_TEXT}, headers=headers)
    statement_id = upload_res.json()["statement_id"]
    
    # Query closing balance
    payload = {
        "query": "Show me my final closing balance",
        "statement_id": statement_id
    }
    
    response = client.post("/api/v1/finlens/query", json=payload, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["numerical_value"] == 159200.0
    assert "Closing Balance" in data["answer"]
    assert "SELECT balance" in data["compiled_sql"]
    assert data["audit_status"] == "VERIFIED_VIA_SQL_DATABASE"

def test_query_food_expenses():
    """Verify that querying food spends successfully sums DEBIT food transactions in SQL."""
    headers = get_analyst_headers()
    upload_res = client.post("/api/v1/finlens/upload", json={"raw_text": MOCK_STATEMENT_TEXT}, headers=headers)
    statement_id = upload_res.json()["statement_id"]
    
    payload = {
        "query": "How much did I spend on food and restaurants?",
        "statement_id": statement_id
    }
    
    response = client.post("/api/v1/finlens/query", json=payload, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["numerical_value"] == 450.0 # Swiggy
    assert "Total Food Spend" in data["answer"]
    assert "SUM(amount)" in data["compiled_sql"]

def test_query_salary_credits():
    """Verify that querying salary earnings filters by CREDIT and description in SQL."""
    headers = get_analyst_headers()
    upload_res = client.post("/api/v1/finlens/upload", json={"raw_text": MOCK_STATEMENT_TEXT}, headers=headers)
    statement_id = upload_res.json()["statement_id"]
    
    payload = {
        "query": "What is my total salary deposit?",
        "statement_id": statement_id
    }
    
    response = client.post("/api/v1/finlens/query", json=payload, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["numerical_value"] == 125000.0 # Salary
    assert "Salary Earnings" in data["answer"]
    assert "LIKE" in data["compiled_sql"]

