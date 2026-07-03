import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import logging

logger = logging.getLogger(__name__)

class SAGEConv(nn.Module):
    """Custom GraphSAGE Convolution layer implemented in pure PyTorch."""
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.lin_self = nn.Linear(in_channels, out_channels)
        self.lin_neigh = nn.Linear(in_channels, out_channels)

    def forward(self, x: torch.Tensor, adj_norm: torch.Tensor) -> torch.Tensor:
        # x: [num_nodes, in_channels]
        # adj_norm: [num_nodes, num_nodes]
        out_self = self.lin_self(x)
        out_neigh = self.lin_neigh(torch.matmul(adj_norm, x))
        return F.relu(out_self + out_neigh)

class FraudGraphSAGE(nn.Module):
    """2-layer inductive GraphSAGE network for transaction fraud scoring."""
    def __init__(self, in_channels: int = 6, hidden_channels: int = 16):
        super().__init__()
        self.conv1 = SAGEConv(in_channels, hidden_channels)
        self.conv2 = SAGEConv(hidden_channels, hidden_channels)
        self.classifier = nn.Linear(hidden_channels, 1)

    def forward(self, x: torch.Tensor, adj_norm: torch.Tensor) -> torch.Tensor:
        h = self.conv1(x, adj_norm)
        h = self.conv2(h, adj_norm)
        logits = self.classifier(h)
        return torch.sigmoid(logits)

class GraphBuilder:
    """Helper class to construct node features and normalized adjacency matrix."""
    @staticmethod
    def build_features_and_adj(txs: list) -> tuple:
        num_nodes = len(txs)
        x = np.zeros((num_nodes, 6), dtype=np.float32)
        
        for i, tx in enumerate(txs):
            amt_val = tx.get("amount")
            amt = float(amt_val if amt_val is not None else tx.get("TransactionAmt", 0.0))
            
            v1_val = tx.get("velocity_1h")
            v1 = float(v1_val if v1_val is not None else 1.0)
            
            v6_val = tx.get("velocity_6h")
            v6 = float(v6_val if v6_val is not None else 1.0)
            
            v24_val = tx.get("velocity_24h")
            v24 = float(v24_val if v24_val is not None else 1.0)
            
            card1_val = tx.get("card1")
            card1 = float(card1_val if card1_val is not None else 1004.0)
            
            addr1_val = tx.get("addr1")
            addr1 = float(addr1_val if addr1_val is not None else 150.0)
            
            x[i, 0] = np.log1p(amt)
            x[i, 1] = v1
            x[i, 2] = v6
            x[i, 3] = v24
            x[i, 4] = card1 / 20000.0
            x[i, 5] = addr1 / 500.0
            
        # Vectorized Adjacency Matrix Construction
        cards = np.array([tx.get("card1") if tx.get("card1") is not None else 1004 for tx in txs])
        addrs = np.array([tx.get("addr1") if tx.get("addr1") is not None else 150.0 for tx in txs])
        devices = np.array([tx.get("DeviceType") if tx.get("DeviceType") is not None else "desktop" for tx in txs])
        
        # Avoid matching generic empty/unknown values
        for idx, d in enumerate(devices):
            if d in [None, "", "unknown"]:
                devices[idx] = f"__dummy_{idx}__"
        for idx, c in enumerate(cards):
            if c is None:
                cards[idx] = -999 - idx
        for idx, a in enumerate(addrs):
            if a is None:
                addrs[idx] = -999.0 - idx
                
        card_match = (cards[:, np.newaxis] == cards[np.newaxis, :])
        addr_match = (addrs[:, np.newaxis] == addrs[np.newaxis, :])
        device_match = (devices[:, np.newaxis] == devices[np.newaxis, :])
        
        A = (card_match | addr_match | device_match).astype(np.float32)
        
        # Self loops
        np.fill_diagonal(A, 1.0)
        
        row_sums = A.sum(axis=1)
        row_sums[row_sums == 0] = 1.0
        adj_norm = A / row_sums[:, np.newaxis]
        
        return torch.tensor(x, dtype=torch.float32), torch.tensor(adj_norm, dtype=torch.float32)

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "graph_fraud_model.pt")

class GraphFraudScorer:
    """Manages GraphSAGE model states and does collusion-ring inference."""
    def __init__(self):
        self.model = FraudGraphSAGE(in_channels=6, hidden_channels=16)
        self.model_loaded = False
        self.load_model()

    def load_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                self.model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
                self.model.eval()
                self.model_loaded = True
                logger.info(f"Loaded GraphSAGE model from {MODEL_PATH}")
            except Exception as e:
                logger.error(f"Failed to load GraphSAGE GNN model state dict: {e}")
        else:
            logger.warning(f"GraphSAGE model checkpoint not found at {MODEL_PATH}. GNN scoring will fallback to heuristic card-velocity risk.")

    def score_with_context(self, current_tx: dict, recent_txs: list) -> dict:
        """Scores transaction based on local collusion graph context."""
        all_txs = recent_txs + [current_tx]
        
        if not self.model_loaded:
            # Heuristic fallback if GNN model is not loaded yet
            card_txs = [t for t in recent_txs if t.get("card1") == current_tx.get("card1")]
            if len(card_txs) > 5:
                fallback_score = 0.45
            else:
                fallback_score = 0.05
            return {"graph_available": True, "gnn_score": fallback_score}

        try:
            x, adj_norm = GraphBuilder.build_features_and_adj(all_txs)
            with torch.no_grad():
                probs = self.model(x, adj_norm)
                target_prob = float(probs[-1].item())
            return {"graph_available": True, "gnn_score": target_prob}
        except Exception as e:
            logger.error(f"Error scoring with GraphSAGE GNN: {e}")
            return {"graph_available": False, "gnn_score": None}

graph_scorer = GraphFraudScorer()
