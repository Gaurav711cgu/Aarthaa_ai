from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    """Verify core API routing, headless JSON API output, browser redirects, and Gradio hidden endpoint."""
    # 1. Programmatic access (Default TestClient has no browser User-Agent)
    response = client.get("/")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    assert response.json()["gateway"] == "Artha AI Unified API Gateway"

    # 2. Browser access (Should trigger 307 Redirect)
    # We instantiate a temporary client with follow_redirects=False to catch the 307 status code
    no_redirect_client = TestClient(app, follow_redirects=False)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    response_redirect = no_redirect_client.get("/", headers=headers)
    assert response_redirect.status_code == 307

    # 3. Hidden dashboard access (Should return Gradio HTML)
    response_ui = client.get("/admin-dashboard-hidden")
    assert response_ui.status_code == 200
    assert "text/html" in response_ui.headers["content-type"]



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
