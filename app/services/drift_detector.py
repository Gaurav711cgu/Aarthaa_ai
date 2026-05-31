from collections import deque
import os
import json
import time
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

class DataDriftDetector:
    """Production-ready data drift monitor utilizing Evidently AI statistical drift preset.
    Maintains rolling-window observations, performs KS-test/Z-test data drift checks,
    and updates Prometheus gauges and streams Kafka alert events in real time.
    """
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.amount_window: deque = deque(maxlen=window_size)
        self.velocity_window: deque = deque(maxlen=window_size)
        self.last_report = None
        
        if os.path.exists(BASELINE_PATH):
            try:
                self.baseline_df = pd.read_csv(BASELINE_PATH)
                logger.info(f"Successfully loaded baseline transactions from {BASELINE_PATH} ({len(self.baseline_df)} rows).")
            except Exception as e:
                logger.error(f"Error loading baseline CSV dataset: {e}. Generating synthetic baseline.")
                self._generate_fallback_baseline()
        else:
            logger.warning(f"Baseline CSV dataset not found at {BASELINE_PATH}. Generating synthetic baseline.")
            self._generate_fallback_baseline()

    def _generate_fallback_baseline(self):
        """Generates a stable synthetic baseline dataset to ensure runtime durability."""
        np.random.seed(2026)
        self.baseline_df = pd.DataFrame({
            "amount": np.random.uniform(10.0, 10000.0, size=100),
            "velocity_1h": np.random.choice([1, 2, 3], size=100)
        })

    def check_drift(self, amount: float, velocity: int) -> dict:
        """Pushes fresh transactions into sliding windows, computes drift, and updates gauges."""
        self.amount_window.append(amount)
        self.velocity_window.append(velocity)
        
        drift_results = {"amount_drift": 0.0, "velocity_drift": 0.0, "dataset_drift": False}
        
        if len(self.amount_window) >= 10:
            try:
                current_df = pd.DataFrame({
                    "amount": list(self.amount_window),
                    "velocity_1h": list(self.velocity_window)
                })
                
                report = Report(metrics=[DataDriftPreset()])
                report.run(
                    reference_data=self.baseline_df[["amount", "velocity_1h"]],
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
                    
                    amount_p_val = res_cols["amount"].get("drift_score", 1.0)
                    velocity_p_val = res_cols["velocity_1h"].get("drift_score", 1.0)
                    
                    amount_drift_score = float(1.0 - amount_p_val)
                    velocity_drift_score = float(1.0 - velocity_p_val)
                    dataset_drift = bool(drift_table["result"].get("dataset_drift", False))
                    
                    DATA_DRIFT_SCORE.labels(feature_name="amount").set(amount_drift_score)
                    DATA_DRIFT_SCORE.labels(feature_name="velocity_1h").set(velocity_drift_score)
                    
                    drift_results["amount_drift"] = amount_drift_score
                    drift_results["velocity_drift"] = velocity_drift_score
                    drift_results["dataset_drift"] = dataset_drift
                    
                    if amount_drift_score > 0.6 or velocity_drift_score > 0.6:
                        logger.warning(
                            f"DATA DRIFT ALERT: Transaction distributions have shifted! "
                            f"Amount Drift Score: {amount_drift_score:.2f} | Velocity Drift Score: {velocity_drift_score:.2f}."
                        )
                        
                        try:
                            producer = get_kafka_producer()
                            drift_event = {
                                "event_type": "data_drift_alert",
                                "amount_drift_score": amount_drift_score,
                                "velocity_drift_score": velocity_drift_score,
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
                    "amount": list(self.amount_window) if self.amount_window else [0.0],
                    "velocity_1h": list(self.velocity_window) if self.velocity_window else [1]
                })
                report = Report(metrics=[DataDriftPreset()])
                report.run(
                    reference_data=self.baseline_df[["amount", "velocity_1h"]],
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
