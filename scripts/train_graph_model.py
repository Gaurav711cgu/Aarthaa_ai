import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score
from app.services.graph_fraud import FraudGraphSAGE, GraphBuilder, MODEL_PATH

# Ensure target directories exist
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

def train():
    print("Loading training and testing splits...")
    train_path = "data/train_split.csv"
    test_path = "data/test_split.csv"
    
    if not os.path.exists(train_path) or not os.path.exists(test_path):
        raise FileNotFoundError("Train/test splits not found. Please run scripts/setup_data.py first.")
        
    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)
    
    print("Building training graph features and adjacency matrix...")
    train_txs = train_df.to_dict(orient="records")
    x_train, adj_train = GraphBuilder.build_features_and_adj(train_txs)
    y_train = torch.tensor(train_df["isFraud"].values, dtype=torch.float32).unsqueeze(1)
    
    print("Building testing graph features and adjacency matrix...")
    test_txs = test_df.to_dict(orient="records")
    x_test, adj_test = GraphBuilder.build_features_and_adj(test_txs)
    y_test = torch.tensor(test_df["isFraud"].values, dtype=torch.float32).unsqueeze(1)
    
    model = FraudGraphSAGE(in_channels=6, hidden_channels=16)
    
    # Sample-weighted BCE loss to handle extreme fraud imbalance
    pos_count = y_train.sum().item()
    neg_count = len(y_train) - pos_count
    pos_weight = torch.tensor([neg_count / max(1.0, pos_count)], dtype=torch.float32)
    
    sample_weights = torch.ones_like(y_train)
    sample_weights[y_train == 1.0] = pos_weight
    
    optimizer = optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-4)
    
    print("Starting training...")
    model.train()
    for epoch in range(1, 101):
        optimizer.zero_grad()
        probs = model(x_train, adj_train)
        
        loss = F.binary_cross_entropy(probs, y_train, weight=sample_weights)
        loss.backward()
        optimizer.step()
        
        if epoch % 10 == 0:
            print(f"Epoch {epoch}/100 | Loss: {loss.item():.4f}")
            
    print("Training finished. Evaluating on test set...")
    model.eval()
    with torch.no_grad():
        test_probs = model(x_test, adj_test).numpy().flatten()
        y_test_np = y_test.numpy().flatten()
        
    auc_roc = roc_auc_score(y_test_np, test_probs)
    auc_pr = average_precision_score(y_test_np, test_probs)
    
    print(f"Test AUC-ROC: {auc_roc:.4f}")
    print(f"Test AUC-PR (Average Precision): {auc_pr:.4f}")
    
    # Save model state dict
    torch.save(model.state_dict(), MODEL_PATH)
    print(f"Saved trained GraphSAGE model state dict to {MODEL_PATH}")

if __name__ == "__main__":
    train()
