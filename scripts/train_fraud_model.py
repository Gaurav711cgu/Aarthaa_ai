"""
IEEE-CIS Fraud Detection: LightGBM ensemble with temporal train/val split.
Reads directly from data/raw/train_transaction.csv + data/raw/train_identity.csv.
Produces real AUC-ROC, precision, recall on a held-out temporal validation set.

Usage:
    kaggle competitions download -c ieee-fraud-detection -p data/raw/
    cd data/raw && unzip ieee-fraud-detection.zip && cd ../..
    python3 scripts/train_fraud_model.py
"""
import os
import json
import hashlib
import logging
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import LabelEncoder
import lightgbm as lgb

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR  = os.path.join(BASE_DIR, "data", "raw")
METRICS_DIR = os.path.join(BASE_DIR, "metrics")
os.makedirs(METRICS_DIR, exist_ok=True)


def load_and_merge() -> pd.DataFrame:
    logger.info("Loading train_transaction.csv (590k rows)...")
    trans = pd.read_csv(os.path.join(RAW_DIR, "train_transaction.csv"))
    id_path = os.path.join(RAW_DIR, "train_identity.csv")
    if os.path.exists(id_path):
        logger.info("Merging train_identity.csv...")
        identity = pd.read_csv(id_path)
        df = trans.merge(identity, on="TransactionID", how="left")
    else:
        df = trans
    logger.info(f"Merged dataset: {df.shape[0]:,} rows, {df.shape[1]} columns.")
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Per-card velocity windows (1h / 6h / 24h) + ratio + time features."""
    logger.info("Engineering velocity features...")
    df = df.sort_values(["card1", "TransactionDT"]).reset_index(drop=True)
    one_hour, six_hours, one_day = 3600, 21600, 86400
    v1h = np.ones(len(df), int)
    v6h = np.ones(len(df), int)
    v24h = np.ones(len(df), int)
    for _, grp in df.groupby("card1", sort=False):
        idx = grp.index.values
        ts  = grp["TransactionDT"].values
        for i in range(len(ts)):
            c1 = c6 = c24 = 0
            for j in range(i - 1, -1, -1):
                dt = ts[i] - ts[j]
                if dt > one_day: break
                if dt <= one_hour:  c1 += 1
                if dt <= six_hours: c6 += 1
                c24 += 1
            v1h[idx[i]]  = c1  + 1
            v6h[idx[i]]  = c6  + 1
            v24h[idx[i]] = c24 + 1

    new_cols = pd.DataFrame({
        "velocity_1h":       v1h,
        "velocity_6h":       v6h,
        "velocity_24h":      v24h,
        "amt_to_card_mean":  df["TransactionAmt"] / df.groupby("card1")["TransactionAmt"].transform("mean").replace(0, 1.0),
        "hour":              (df["TransactionDT"] // 3600) % 24,
        "dow":               (df["TransactionDT"] // 86400) % 7,
    }, index=df.index)
    df = pd.concat([df, new_cols], axis=1)
    return df


def prepare_features(df: pd.DataFrame):
    num_feats = [
        "TransactionAmt", "card1", "card2", "card3", "card5",
        "addr1", "addr2", "dist1", "dist2",
        "C1","C2","C3","C4","C5","C6","C7","C8","C9","C10","C11","C12","C13","C14",
        "D1","D2","D3","D4","D5","D10","D11","D15",
        "velocity_1h","velocity_6h","velocity_24h","amt_to_card_mean","hour","dow",
    ]
    v_cols = [
        "V95","V96","V97","V98","V99","V100",
        "V126","V127","V128","V129","V130",
        "V258","V263","V264","V266","V267","V271",
        "V283","V284","V285","V286","V287",
        "V303","V304","V306","V307","V308","V310",
    ]
    cat_feats = ["ProductCD", "card4", "card6", "P_emaildomain", "R_emaildomain", "M4"]
    all_feats = [c for c in num_feats + v_cols + cat_feats if c in df.columns]

    for col in cat_feats:
        if col in df.columns:
            df[col] = df[col].astype(str).fillna("unknown")
            df[col] = LabelEncoder().fit_transform(df[col])

    for col in all_feats:
        if df[col].dtype in [np.float64, np.float32, np.int64, np.int32]:
            df[col] = df[col].fillna(df[col].median())

    return df, all_feats


def temporal_split(df: pd.DataFrame):
    # Dataset spans days 1–182. Day ≤ 140 → train, > 140 → val.
    # Same boundary used by top public Kaggle kernels for this competition.
    df["day"] = df["TransactionDT"] // 86400
    train = df[df["day"] <= 140]
    val   = df[df["day"] >  140]
    logger.info(f"Temporal split: Train={len(train):,}, Val={len(val):,} (split at day 140)")
    return train, val


def train_and_save():
    df = load_and_merge()
    df = engineer_features(df)
    df, features = prepare_features(df)
    train, val   = temporal_split(df)

    X_train, y_train = train[features], train["isFraud"]
    X_val,   y_val   = val[features],   val["isFraud"]

    fraud_rate = y_train.mean()
    scale_pos  = (1 - fraud_rate) / fraud_rate
    logger.info(f"Fraud rate: {fraud_rate:.3%} → scale_pos_weight={scale_pos:.1f}")

    params = dict(
        objective="binary", metric="auc",
        num_leaves=256, learning_rate=0.05,
        feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1,
        min_child_samples=20, scale_pos_weight=scale_pos,
        n_jobs=-1, random_state=2026, verbose=-1,
    )
    logger.info("Training LightGBM (max 400 rounds, early-stopping on val AUC)...")
    model = lgb.train(
        params,
        lgb.Dataset(X_train, label=y_train),
        num_boost_round=400,
        valid_sets=[lgb.Dataset(X_val, label=y_val)],
        callbacks=[lgb.early_stopping(50, verbose=True), lgb.log_evaluation(50)],
    )

    y_prob = model.predict(X_val)
    y_pred = (y_prob >= 0.5).astype(int)
    metrics = {
        "auc_roc":      round(float(roc_auc_score(y_val, y_prob)), 4),
        "precision":    round(float(precision_score(y_val, y_pred, zero_division=0)), 4),
        "recall":       round(float(recall_score(y_val, y_pred, zero_division=0)), 4),
        "f1":           round(float(f1_score(y_val, y_pred, zero_division=0)), 4),
        "val_rows":     int(len(val)),
        "num_features": len(features),
        "model":        "LightGBM",
        "split":        "temporal (day > 140, ~118k val rows)",
        "dataset":      "IEEE-CIS Fraud Detection (590k transactions)",
    }

    logger.info("=" * 55)
    for k, v in metrics.items():
        logger.info(f"  {k}: {v}")
    logger.info("=" * 55)

    with open(os.path.join(METRICS_DIR, "fraud_metrics.json"), "w") as fp:
        json.dump(metrics, fp, indent=2)

    model_dir  = os.path.join(BASE_DIR, "app", "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "fraud_model.joblib")
    joblib.dump({"model": model, "features": features, "metrics": metrics}, model_path)

    sha = hashlib.sha256()
    with open(model_path, "rb") as fp:
        for chunk in iter(lambda: fp.read(4096), b""): sha.update(chunk)
    with open(model_path + ".sha256", "w") as fp:
        fp.write(sha.hexdigest())

    logger.info(f"Model → {model_path} (sha256={sha.hexdigest()[:16]}...)")
    return metrics


if __name__ == "__main__":
    m = train_and_save()
    print("\n📊 Final Metrics:")
    for k, v in m.items():
        print(f"   {k}: {v}")
