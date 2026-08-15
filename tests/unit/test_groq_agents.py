from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.compliance_agent import RegGuardComplianceAgent, _llm_limiter as reg_limiter
from app.services.finlens_engine import FinLensQueryEngine, _llm_limiter as finlens_limiter

client = TestClient(app)

def get_analyst_headers():
    response = client.post("/auth/token", json={
        "username": "analyst",
        "password": "analyst_password_2026"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@patch("app.services.compliance_agent.vector_store")
@patch("app.services.compliance_agent.Groq")
def test_regguard_groq_rag_execution(mock_groq_class, mock_vector_store):
    """Verify that RegGuard utilizes the Groq client for online RAG when initialized."""
    reg_limiter._buckets.clear()
    
    mock_vector_store.search.return_value = [{
        "text": "UPI per transaction limit is ₹1,00,000.",
        "source": "NPCI_UPI_CIRCULAR",
        "section": "Sec 1",
        "score": 0.95
    }]
    
    # 1. Setup mock Groq response
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    
    mock_chat = MagicMock()
    mock_client.chat = mock_chat
    
    mock_choice = MagicMock()
    mock_choice.message.content = "Groq LLaMA compliance ruling statement."
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_chat.completions.create.return_value = mock_completion
    
    # 2. Instantiate agent and trigger query
    with patch("app.services.compliance_agent.settings.GROQ_API_KEY", "mock_key_minimum_32_characters_long"):
        agent = RegGuardComplianceAgent()
        assert agent.groq_client is not None
        
        result = agent.query_regulations("Is a UPI transfer of ₹1,50,000 allowed?", username="test_regguard_user")
        
        # Verify Groq chat completions were indeed called
        mock_chat.completions.create.assert_called_once()
        assert result["answer"] == "Groq LLaMA compliance ruling statement."
        assert result["model_used"] == "groq/llama-3.1-70b-versatile"
        assert result["confidence"] > 0.0

@patch("app.services.compliance_agent.Groq")
@patch("app.services.compliance_agent.vector_store")
def test_regguard_groq_rag_graceful_fallback(mock_vector_store, mock_groq_class):
    """Verify that RegGuard falls back gracefully to offline template mode on API failures."""
    reg_limiter._buckets.clear()
    
    # 1. Force Groq API call failure
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = Exception("Groq Rate Limit Exceeded")
    
    # 2. Mock vector store to return a FEMA-specific chunk
    mock_vector_store.search.return_value = [{
        "text": "Content: FEMA LRS limit is USD 250,000.",
        "source": "FEMA_ACT",
        "section": "Sec 6",
        "score": 0.95
    }]
    
    with patch("app.services.compliance_agent.settings.GROQ_API_KEY", "mock_key_minimum_32_characters_long"):
        agent = RegGuardComplianceAgent()
        result = agent.query_regulations("What is the LRS limit under FEMA?", username="test_fallback_user")
        
        assert "fallback" in result["model_used"].lower() or "offline" in result["model_used"].lower()
        assert result["confidence"] > 0.0

def test_finlens_query_rate_limiter():
    """Verify that repeated queries to FinLens are rate-limited after exceedance limits."""
    from app.services.finlens_engine import finlens_engine
    original_executor = finlens_engine.agent_executor
    try:
        finlens_engine.agent_executor = None
        finlens_limiter._buckets.clear()
        engine = FinLensQueryEngine()
        mock_db = MagicMock()
        
        # We call it 5 times within 1 second, it should be fine
        for _ in range(5):
            result = engine.answer_numerical_query(mock_db, "Show me my closing balance", statement_id=1, username="test_rate_user")
            assert result["audit_status"] != "RATE_LIMITED"
            
        # The 6th call should trigger the rate-limiter
        limit_result = engine.answer_numerical_query(mock_db, "Show me my closing balance", statement_id=1, username="test_rate_user")
        assert limit_result["audit_status"] == "RATE_LIMITED"
        assert "Rate limit reached" in limit_result["answer"]
    finally:
        finlens_engine.agent_executor = original_executor
        finlens_limiter._buckets.clear()
