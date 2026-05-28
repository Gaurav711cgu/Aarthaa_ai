import os
import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score
from faker import Faker
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize Faker and seed for reproducibility
fake = Faker()
Faker.seed(2026)
np.random.seed(2026)

def generate_synthetic_data(num_records: int = 5000) -> pd.DataFrame:
    """Generates synthetic Indian transaction data with embedded fraud patterns."""
    logger.info(f"Generating {num_records} synthetic transaction records...")
    
    records = []
    for i in range(num_records):
        # Determine if this record will be fraudulent (approx 5% fraud rate)
        is_fraud = 1 if np.random.rand() < 0.05 else 0
        
        if is_fraud:
            # Fraud patterns
            fraud_type = np.random.choice(["high_amount", "velocity", "location_anomaly", "time_anomaly"])
            if fraud_type == "high_amount":
                amount = float(np.random.uniform(50000, 1000000)) # ₹50K to ₹10L
                hour = int(np.random.randint(0, 24))
                velocity_1h = int(np.random.randint(1, 4))
                distance_from_home = float(np.random.uniform(0, 50))
                merchant_risk = float(np.random.uniform(0.1, 0.4))
            elif fraud_type == "velocity":
                amount = float(np.random.uniform(100, 2000))
                hour = int(np.random.randint(0, 24))
                velocity_1h = int(np.random.randint(8, 25)) # high velocity
                distance_from_home = float(np.random.uniform(0, 10))
                merchant_risk = float(np.random.uniform(0.2, 0.7))
            elif fraud_type == "location_anomaly":
                amount = float(np.random.uniform(1000, 20000))
                hour = int(np.random.randint(0, 24))
                velocity_1h = int(np.random.randint(1, 3))
                distance_from_home = float(np.random.uniform(200, 5000)) # very far
                merchant_risk = float(np.random.uniform(0.3, 0.8))
            else: # time anomaly
                amount = float(np.random.uniform(5000, 50000))
                hour = int(np.random.choice([1, 2, 3, 4])) # 1AM - 4AM
                velocity_1h = int(np.random.randint(2, 5))
                distance_from_home = float(np.random.uniform(10, 150))
                merchant_risk = float(np.random.uniform(0.5, 0.9))
        else:
            # Legitimate transactions
            amount = float(np.random.uniform(10, 10000)) # ₹10 to ₹10K
            hour = int(np.random.choice([7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23])) # daylight/evening hours
            velocity_1h = int(np.random.choice([1, 2, 3])) # low velocity
            distance_from_home = float(np.random.uniform(0, 30)) # close to home coordinates
            merchant_risk = float(np.random.uniform(0.01, 0.15)) # standard merchants

        records.append({
            "amount": amount,
            "hour": hour,
            "velocity_1h": velocity_1h,
            "distance_from_home": distance_from_home,
            "merchant_risk": merchant_risk,
            "is_fraud": is_fraud
        })
        
    df = pd.DataFrame(records)
    logger.info("Dataset generated successfully.")
    return df

def train_and_save_ensemble():
    # 1. Generate Dataset
    df = generate_synthetic_data(10000)
    
    # 2. Features and Target split
    features = ["amount", "hour", "velocity_1h", "distance_from_home", "merchant_risk"]
    X = df[features]
    y = df["is_fraud"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=2026, stratify=y)
    
    # 3. Train RandomForest Classifier
    logger.info("Training RandomForest Classifier...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        random_state=2026,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    
    # 4. Train Isolation Forest Anomaly Detector
    logger.info("Training Isolation Forest Anomaly Detector...")
    # Contamination matches the ground truth fraud rate approx
    iforest = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=2026
    )
    iforest.fit(X_train)
    
    # 5. Evaluate RandomForest alone
    y_pred_rf = rf_model.predict(X_test)
    logger.info("Evaluation Metrics for RandomForest:")
    logger.info("\n" + classification_report(y_test, y_pred_rf))
    
    f1 = f1_score(y_test, y_pred_rf)
    precision = precision_score(y_test, y_pred_rf)
    recall = recall_score(y_test, y_pred_rf)
    
    # 6. Serializing models
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_dir = os.path.join(base_dir, "app", "models")
    os.makedirs(model_dir, exist_ok=True)
    
    model_path = os.path.join(model_dir, "fraud_model.pkl")
    logger.info(f"Saving models package to {model_path}...")
    
    # Save ensemble structure
    ensemble = {
        "rf": rf_model,
        "iforest": iforest,
        "features": features,
        "metrics": {
            "f1": float(f1),
            "precision": float(precision),
            "recall": float(recall)
        }
    }
    
    with open(model_path, "wb") as f:
        pickle.dump(ensemble, f)
        
    logger.info("Models saved successfully. Training completed successfully.")

if __name__ == "__main__":
    train_and_save_ensemble()
