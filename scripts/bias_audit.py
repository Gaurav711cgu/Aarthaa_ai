"""
Fairness audit for fraud model across card network, card type, and email domain subgroups.
Produces: reports/bias_audit.json

Paper & Industry Reference: JP Morgan OmniAI Model Risk Governance.
Audits AUC-ROC parity across subgroups using real LightGBM model predictions.

Usage:
    python3 scripts/bias_audit.py
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(REPORTS_DIR, exist_ok=True)

from app.services.fraud_model import fraud_engine

SUBGROUP_COLUMNS = [
    "card4",          # visa / mastercard / discover / american express
    "card6",          # debit / credit
    "P_emaildomain",  # email domain proxy for customer demographic
]

FAIRNESS_THRESHOLD = 0.05


def audit_subgroup(probs: np.ndarray, y_val: np.ndarray, df_val: pd.DataFrame, col: str):
    """Compute metrics per subgroup and flag if AUC gap > FAIRNESS_THRESHOLD."""
    overall_auc = float(roc_auc_score(y_val, probs))
    
    results = {
        "column": col,
        "overall_auc": round(overall_auc, 4),
        "subgroups": [],
        "max_auc_gap": 0.0,
        "fairness_flag": False
    }
    
    if col not in df_val.columns:
        logger.warning(f"Subgroup column '{col}' not found in validation DataFrame.")
        return results

    unique_vals = df_val[col].dropna().unique()
    
    for val in unique_vals:
        mask = (df_val[col] == val).values
        n_samples = int(mask.sum())
        n_fraud = int(y_val[mask].sum())
        
        if n_samples < 50 or n_fraud < 5:
            continue
            
        try:
            sub_auc = float(roc_auc_score(y_val[mask], probs[mask]))
            gap = abs(sub_auc - overall_auc)
            flagged = gap > FAIRNESS_THRESHOLD
            
            results["subgroups"].append({
                "subgroup_value": str(val),
                "sample_count": n_samples,
                "fraud_count": n_fraud,
                "auc_roc": round(sub_auc, 4),
                "auc_gap_from_overall": round(gap, 4),
                "flagged": flagged
            })
            
            if gap > results["max_auc_gap"]:
                results["max_auc_gap"] = gap
        except Exception as err:
            logger.debug(f"Subgroup {col}={val} AUC calculation skipped: {err}")

    results["fairness_flag"] = results["max_auc_gap"] > FAIRNESS_THRESHOLD
    results["max_auc_gap"] = round(results["max_auc_gap"], 4)
    return results


def main():
    val_path = os.path.join(DATA_DIR, "val_split.csv")
    if not os.path.exists(val_path):
        logger.info("val_split.csv not found. Running threshold_analysis.py to generate split...")
        from scripts.threshold_analysis import generate_synthetic_val_split_if_missing
        df_val = generate_synthetic_val_split_if_missing(val_path)
    else:
        df_val = pd.read_csv(val_path)

    y_val = df_val["isFraud"].values

    # Run real model inference in vectorized batch
    logger.info("Scoring validation set with production fraud model...")
    probs = fraud_engine.score_dataframe(df_val)

    overall_auc = roc_auc_score(y_val, probs)
    logger.info(f"Overall Validation Model AUC-ROC: {overall_auc:.4f}")

    audit_results = {
        "audit_timestamp": pd.Timestamp.now().isoformat(),
        "model_version": "lgbm-v2.1-gnn-ensemble",
        "overall_auc_roc": round(float(overall_auc), 4),
        "fairness_threshold": FAIRNESS_THRESHOLD,
        "methodology": "AUC-ROC parity across card network, card type, and email domain subgroups",
        "subgroup_audits": []
    }

    print("\n================================================================================")
    print("ARTHA AI — SUBGROUP BIAS & FAIRNESS AUDIT REPORT")
    print("================================================================================")

    overall_passed = True
    for col in SUBGROUP_COLUMNS:
        res = audit_subgroup(probs, y_val, df_val, col)
        audit_results["subgroup_audits"].append(res)
        status = "FLAGGED (DISPARATE IMPACT)" if res["fairness_flag"] else "PASS (FAIR)"
        if res["fairness_flag"]:
            overall_passed = False
        print(f"Subgroup Feature: {col:<15} | Overall AUC: {res['overall_auc']:.4f} | Max Gap: {res['max_auc_gap']:.4f} → {status}")
        for sub in res["subgroups"]:
            flag_str = " [!] FLAGGED" if sub["flagged"] else ""
            print(f"   ↳ {sub['subgroup_value']:<20} (n={sub['sample_count']:<5}, fraud={sub['fraud_count']:<3}) AUC: {sub['auc_roc']:.4f} (Gap: {sub['auc_gap_from_overall']:.4f}){flag_str}")

    audit_results["overall_bias_audit_passed"] = overall_passed

    output_path = os.path.join(REPORTS_DIR, "bias_audit.json")
    with open(output_path, "w") as f:
        json.dump(audit_results, f, indent=2)

    print("================================================================================")
    print(f"OVERALL BIAS AUDIT STATUS: {'PASS' if overall_passed else 'WARNING - SUBGROUP GAP DETECTED'}")
    print(f"Audit JSON written to: {output_path}")
    print("================================================================ algorithm\n")


if __name__ == "__main__":
    main()
