from collections import deque
import numpy as np
from app.services.monitoring import DATA_DRIFT_SCORE
import logging

logger = logging.getLogger(__name__)

class EvidentlyDataDriftDetector:
    """Lightweight data drift monitor simulating Evidently AI feature drift sweeps.
    Maintains rolling-window observations and updates feature drift gauges in real time.
    """
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.amount_window = deque(maxlen=window_size)
        self.velocity_window = deque(maxlen=window_size)
        
        # Historical baseline references from baseline model training
        self.baseline_amount_mean = 5000.0
        self.baseline_amount_std = 15000.0
        self.baseline_velocity_mean = 2.0
        self.baseline_velocity_std = 1.5

    def check_drift(self, amount: float, velocity: int) -> dict:
        """Pushes fresh transactions into sliding windows, computes drift, and updates gauges."""
        self.amount_window.append(amount)
        self.velocity_window.append(velocity)
        
        drift_results = {}
        
        # Perform evaluations once rolling windows accumulate sufficient data points
        if len(self.amount_window) >= 10:
            # 1. Transaction Amount Drift Calculation (mean deviation metric)
            curr_amount_mean = np.mean(self.amount_window)
            amount_drift = float(abs(curr_amount_mean - self.baseline_amount_mean) / self.baseline_amount_std)
            amount_drift_score = min(max(amount_drift, 0.0), 1.0)
            
            # Update Prometheus Gauge
            DATA_DRIFT_SCORE.labels(feature_name="amount").set(amount_drift_score)
            drift_results["amount_drift"] = amount_drift_score
            
            # 2. Transaction Velocity Drift Calculation
            curr_velocity_mean = np.mean(self.velocity_window)
            velocity_drift = float(abs(curr_velocity_mean - self.baseline_velocity_mean) / self.baseline_velocity_std)
            velocity_drift_score = min(max(velocity_drift, 0.0), 1.0)
            
            # Update Prometheus Gauge
            DATA_DRIFT_SCORE.labels(feature_name="velocity_1h").set(velocity_drift_score)
            drift_results["velocity_drift"] = velocity_drift_score
            
            # Trigger warning notifications when drift scores exceed alerts threshold
            if amount_drift_score > 0.6 or velocity_drift_score > 0.6:
                logger.warning(
                    f"DATA DRIFT ALERT: Transaction distributions have shifted! "
                    f"Amount Drift: {amount_drift_score:.2f} | Velocity Drift: {velocity_drift_score:.2f}."
                )
        else:
            drift_results = {"amount_drift": 0.0, "velocity_drift": 0.0}
            
        return drift_results

# Global singleton drift detector
drift_detector = EvidentlyDataDriftDetector()
