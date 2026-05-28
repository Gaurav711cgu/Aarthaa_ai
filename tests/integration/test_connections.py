from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    """Verify core API routing and module manifest outputs."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "Artha AI"
    assert "modules" in data

def test_health_check_endpoint():
    """Verify robust health checking infrastructure behavior.
    Expects 200 when local containers are active or 503 gracefully handled when inactive.
    """
    response = client.get("/health")
    assert response.status_code in [200, 503]
    
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "postgres" in data["services"]
    assert "redis" in data["services"]
    assert "kafka" in data["services"]

def test_metrics_endpoint():
    """Verify that Prometheus scrapable metrics are generated under /metrics."""
    response = client.get("/metrics")
    assert response.status_code == 200
    # Confirm presence of custom metrics inside body
    assert "artha_transactions_total" in response.text
