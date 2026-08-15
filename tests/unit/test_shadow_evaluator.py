import pytest
from app.repositories.fraud_repository import FraudTransactionRepository
from app.services.shadow_evaluator import ShadowModelEvaluator

def test_fraud_repository_crud():
    repo = FraudTransactionRepository()
    tx = repo.add({"transaction_id": "tx_1001", "amount": 250.0, "user_id": "usr_99"})
    
    assert tx["transaction_id"] == "tx_1001"
    assert repo.get_by_id("tx_1001")["amount"] == 250.0
    assert len(repo.list_all()) == 1

    assert repo.remove("tx_1001") is True
    assert repo.get_by_id("tx_1001") is None

def test_shadow_evaluator_divergence_metrics():
    evaluator = ShadowModelEvaluator(divergence_threshold=0.04)
    res = evaluator.shadow_evaluate(primary_risk_score=0.10, payload={"amount": 1000.0})
    
    assert res["primary_score"] == 0.10
    assert res["shadow_score"] > 0.10
    assert res["is_divergent"] is True
    
    metrics = evaluator.get_metrics()
    assert metrics["evaluations_count"] == 1
    assert metrics["disagreements_count"] == 1
    assert metrics["disagreement_rate"] == 1.0
