from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

import logging

logger = logging.getLogger(__name__)

# Single global metrics registry
registry = CollectorRegistry()

# 1. Counter tracking total transactions processed, labeled by channel and risk tier
TRANSACTIONS_PROCESSED = Counter(
    "artha_transactions_total",
    "Total transaction count evaluated for fraud",
    ["channel", "risk_tier"],
    registry=registry
)

# 2. Latency histogram tracking prediction pipelines in seconds
FRAUD_SCORING_LATENCY = Histogram(
    "artha_fraud_scoring_seconds",
    "Time consumed by ML scoring and SHAP explainability calculations",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
    registry=registry
)

# 3. Gauge tracking active in-flight compliance/agent audits
ACTIVE_INVESTIGATIONS = Gauge(
    "artha_active_investigations",
    "Total active stateful compliance investigations",
    registry=registry
)

# 4. Gauge tracking calculated feature distribution data drift scores (Evidently AI integration index)
DATA_DRIFT_SCORE = Gauge(
    "artha_data_drift_score",
    "Calculated statistical feature drift index (KS-statistic analogy)",
    ["feature_name"],
    registry=registry
)

def get_metrics_payload() -> tuple[bytes, str]:
    """Generates the latest Prometheus-compatible scrape format payload."""
    try:
        data = generate_latest(registry)
        return data, CONTENT_TYPE_LATEST
    except Exception as e:
        logger.error(f"Failed to generate Prometheus metrics scraping data: {e}")
        return b"", ""
