import pytest

try:
    import torch
    import numpy as np
    from app.services.graph_fraud import SAGEConv, FraudGraphSAGE, GraphBuilder, graph_scorer
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

pytestmark = pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch (torch) is not installed.")

def test_sage_conv():
    """Verify SAGEConv works correctly with standard PyTorch tensors."""
    conv = SAGEConv(in_channels=4, out_channels=8)
    x = torch.randn(5, 4)
    adj_norm = torch.eye(5)
    out = conv(x, adj_norm)
    assert out.shape == (5, 8)

def test_fraud_graph_sage():
    """Verify FraudGraphSAGE forward pass and output format."""
    model = FraudGraphSAGE(in_channels=6, hidden_channels=16)
    x = torch.randn(10, 6)
    adj_norm = torch.eye(10)
    out = model(x, adj_norm)
    assert out.shape == (10, 1)
    assert (out >= 0.0).all() and (out <= 1.0).all()

def test_graph_builder():
    """Verify GraphBuilder maps transaction features and builds collusion links."""
    txs = [
        {"amount": 100.0, "velocity_1h": 1, "velocity_6h": 2, "velocity_24h": 3, "card1": 1111, "addr1": 150.0, "DeviceType": "desktop"},
        {"amount": 200.0, "velocity_1h": 2, "velocity_6h": 4, "velocity_24h": 6, "card1": 1111, "addr1": 200.0, "DeviceType": "desktop"},
        {"amount": 300.0, "velocity_1h": 1, "velocity_6h": 1, "velocity_24h": 1, "card1": 2222, "addr1": 300.0, "DeviceType": "mobile"}
    ]
    
    x, adj_norm = GraphBuilder.build_features_and_adj(txs)
    
    assert x.shape == (3, 6)
    assert adj_norm.shape == (3, 3)
    
    # Node 0 and 1 share card1 = 1111 and DeviceType = desktop, so they must be connected
    assert adj_norm[0, 1] > 0.0
    assert adj_norm[1, 0] > 0.0
    
    # Node 2 shares nothing with node 0 and 1, so it shouldn't connect except self loop
    assert adj_norm[2, 0] == 0.0
    assert adj_norm[2, 2] > 0.0

def test_graph_scorer():
    """Verify graph_scorer scores with context fallback/gnn successfully."""
    current_tx = {"amount": 150.0, "velocity_1h": 1, "velocity_6h": 2, "velocity_24h": 3, "card1": 1111, "addr1": 150.0, "DeviceType": "desktop"}
    recent_txs = [
        {"amount": 100.0, "velocity_1h": 1, "velocity_6h": 2, "velocity_24h": 3, "card1": 1111, "addr1": 150.0, "DeviceType": "desktop"}
    ]
    
    res = graph_scorer.score_with_context(current_tx, recent_txs)
    assert res["graph_available"] is True
    assert "gnn_score" in res
    assert res["gnn_score"] is not None
