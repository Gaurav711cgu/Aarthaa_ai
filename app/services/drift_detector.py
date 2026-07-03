from collections import deque
import os
import json
import time
from typing import Dict, Any
import numpy as np
import pandas as pd
import logging
from evidently.legacy.report import Report
from evidently.legacy.metric_preset import DataDriftPreset
from app.services.monitoring import DATA_DRIFT_SCORE
from app.kafka_client import get_kafka_producer

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASELINE_PATH = os.path.join(BASE_DIR, "data", "baseline_transactions.csv")

DRIFT_FEATURES = [
    'TransactionAmt', 'card1', 'addr1', 
    'P_emaildomain', 'R_emaildomain', 'DeviceType', 
    'velocity_1h', 'velocity_6h', 'velocity_24h'
]

class DataDriftDetector:
    """Production-ready data drift monitor monitoring all 9 transaction features.
    Maintains rolling-window observations, performs KS-test/Z-test data drift checks,
    and updates Prometheus gauges and streams Kafka alert events in real time.
    """
    def __init__(self, window_size: int = 500):
        self.window_size = window_size
        self.features = DRIFT_FEATURES
        self.feature_windows: Dict[str, deque[Any]] = {feat: deque(maxlen=window_size) for feat in self.features}
        self.last_report = None
        
        if os.path.exists(BASELINE_PATH):
            try:
                self.baseline_df = pd.read_csv(BASELINE_PATH)
                # Ensure all 9 features exist in the loaded baseline
                missing = [f for f in self.features if f not in self.baseline_df.columns]
                if missing:
                    logger.warning(f"Loaded baseline is missing features {missing}. Reverting to fallback.")
                    self._generate_fallback_baseline()
                else:
                    logger.info(f"Successfully loaded baseline transactions from {BASELINE_PATH} ({len(self.baseline_df)} rows).")
            except Exception as e:
                logger.error(f"Error loading baseline CSV dataset: {e}. Generating synthetic baseline.")
                self._generate_fallback_baseline()
        else:
            logger.warning(f"Baseline CSV dataset not found at {BASELINE_PATH}. Generating synthetic baseline.")
            self._generate_fallback_baseline()

    def _generate_fallback_baseline(self):
        """Generates a stable synthetic baseline dataset of 5,000 rows to ensure runtime durability."""
        np.random.seed(2026)
        n_rows = 5000
        self.baseline_df = pd.DataFrame({
            "TransactionAmt": np.random.uniform(5.0, 5000.0, size=n_rows),
            "card1": np.random.randint(1000, 20000, size=n_rows),
            "addr1": np.random.choice([150.0, 200.0, 300.0, 450.0], size=n_rows),
            "P_emaildomain": np.random.choice(["gmail.com", "yahoo.com", "anonymous.com"], size=n_rows),
            "R_emaildomain": np.random.choice(["gmail.com", "yahoo.com", "anonymous.com"], size=n_rows),
            "DeviceType": np.random.choice(["desktop", "mobile"], size=n_rows),
            "velocity_1h": np.random.choice([1, 2, 3], size=n_rows),
            "velocity_6h": np.random.choice([2, 4, 6], size=n_rows),
            "velocity_24h": np.random.choice([5, 10, 15], size=n_rows)
        })

    def check_drift(self, tx_data: dict) -> dict:
        """Pushes fresh transactions into sliding windows, computes drift, and updates gauges."""
        # Align keys
        mapped_tx = {}
        for k, v in tx_data.items():
            if k == "amount":
                mapped_tx["TransactionAmt"] = float(v)
            elif k in ["card1", "velocity_1h", "velocity_6h", "velocity_24h"]:
                mapped_tx[k] = int(v) if v is not None else 0
            elif k == "addr1":
                mapped_tx[k] = float(v) if v is not None else 0.0
            else:
                mapped_tx[k] = v

        for feat in self.features:
            val: Any = mapped_tx.get(feat)
            if val is None:
                if feat in ["TransactionAmt", "addr1"]:
                    val = 0.0
                elif feat in ["card1", "velocity_1h", "velocity_6h", "velocity_24h"]:
                    val = 0
                else:
                    val = "unknown"
            self.feature_windows[feat].append(val)
        
        drift_results: Dict[str, Any] = {"dataset_drift": False}
        for feat in self.features:
            drift_results[f"{feat}_drift"] = 0.0
            
        if len(self.feature_windows["TransactionAmt"]) >= 10:
            try:
                current_df = pd.DataFrame({
                    feat: list(self.feature_windows[feat]) for feat in self.features
                })
                
                report = Report(metrics=[DataDriftPreset()])
                report.run(
                    reference_data=self.baseline_df[self.features],
                    current_data=current_df
                )
                self.last_report = report
                
                report_dict = report.as_dict()
                
                drift_table = None
                for metric_res in report_dict.get("metrics", []):
                    if metric_res.get("metric") == "DataDriftTable":
                        drift_table = metric_res
                        break
                
                if drift_table:
                    res_cols = drift_table["result"]["drift_by_columns"]
                    dataset_drift = bool(drift_table["result"].get("dataset_drift", False))
                    drift_results["dataset_drift"] = dataset_drift
                    
                    max_drift = 0.0
                    for feat in self.features:
                        p_val = res_cols[feat].get("drift_score", 1.0)
                        drift_score = float(1.0 - p_val) if p_val <= 1.0 else 0.0
                        drift_results[f"{feat}_drift"] = drift_score
                        DATA_DRIFT_SCORE.labels(feature_name=feat).set(drift_score)
                        if drift_score > max_drift:
                            max_drift = drift_score
                            
                    if max_drift > 0.6:
                        logger.warning(
                            f"DATA DRIFT ALERT: Transaction features have shifted! Max Drift Score: {max_drift:.2f}."
                        )
                        
                        try:
                            producer = get_kafka_producer()
                            drift_event = {
                                "event_type": "data_drift_alert",
                                "max_drift_score": max_drift,
                                "dataset_drift": dataset_drift,
                                "timestamp": time.time(),
                                "alert_threshold": 0.6
                            }
                            producer.produce(
                                topic="artha.monitoring.drift",
                                key="drift_alert",
                                value=json.dumps(drift_event)
                            )
                            producer.flush(timeout=0.05)
                        except Exception as k_err:
                            logger.error(f"Failed to publish drift event to Kafka: {k_err}")
            except Exception as e:
                logger.error(f"Error computing Evidently data drift: {e}")
        
        return drift_results

    def get_drift_report_html_base64(self) -> str:
        """Generates the latest Evidently HTML report and encodes it in base64."""
        if self.last_report is None:
            try:
                current_df = pd.DataFrame({
                    feat: list(self.feature_windows[feat]) if self.feature_windows[feat] else [self.baseline_df[feat].iloc[0]]
                    for feat in self.features
                })
                report = Report(metrics=[DataDriftPreset()])
                report.run(
                    reference_data=self.baseline_df[self.features],
                    current_data=current_df
                )
                self.last_report = report
            except Exception as e:
                logger.error(f"Error compiling fallback HTML report: {e}")
                return ""
                
        try:
            if self.last_report is None:
                return ""
            html_content = self.last_report.get_html()
            import base64
            return base64.b64encode(html_content.encode("utf-8")).decode("utf-8")
        except Exception as e:
            logger.error(f"Error encoding HTML report in base64: {e}")
            return ""

# Global singleton drift detector
drift_detector = DataDriftDetector()
