# Model Card — FraudSense Ensemble Scoring Engine

## Model Details
* **Developed By**: Artha AI Engineering Team
* **Model Date**: May 2026
* **Model Type**: Supervised & Unsupervised Ensemble
  * **Supervised Classifier**: scikit-learn `RandomForestClassifier` (100 estimators, stratified splits)
  * **Unsupervised Anomaly Detector**: scikit-learn `IsolationForest` (100 estimators, 5% contamination target)
* **Explainability Engine**: TreeSHAP (`shap.TreeExplainer`)
* **Serialization Protocol**: Joblib serialization secured with SHA-256 integrity checksum signature checks on cold-start boot.

---

## Intended Use
### Primary Use Case
* **Real-time Fraud Scoring**: Evaluation of domestic Indian transaction payloads (UPI, Cards, LRS, PMLA cash structures) in INR.
* **Risk Categorization**: Instant scoring into LOW, MEDIUM, HIGH, and CRITICAL risk tiers.
* **Explainable AI (XAI)**: Generation of clear natural-language rationale narratives derived directly from mathematical feature Shapley values.

### Out of Scope & Limitations
* **Credit Decisioning**: This model is NOT validated for underwriting loans or calculating consumer credit scores.
* **Non-INR Currency**: The feature boundaries are heavily optimized for Indian banking behaviors (e.g., UPI limits, FEMA LRS limits) and will fail on USD/EUR/GBP profiles without retraining.
* **Synthetic Bias**: The baseline training data is synthetically generated using structural patterns. Before production deployment, the ensemble must be retrained on real historical banking logs.

---

## Model Validation & Performance Metrics
Validated using Stratified K-Fold splits on synthetic benchmark datasets.

| Metric | Target | Verified Score | Status |
|---|---|---|---|
| **ROC-AUC** | > 0.90 | 0.99 | Pass (Synthetic Baseline) |
| **F1-Score (Positive Class)** | > 0.80 | 1.00 | Pass (Synthetic Stratified) |
| **Precision** | > 0.85 | 1.00 | Pass |
| **Recall** | > 0.80 | 1.00 | Pass |
| **SHAP Latency (P99)** | < 10ms | 2.4ms | Pass |

---

## Explainability Story (TreeSHAP)
Instead of returning global feature importances, the engine integrates local feature attribution using **TreeSHAP**. Every transaction score is accompanied by exact Shapley contributions ($L_1$ norms), exposing:
* How much the **amount** pushed the transaction towards a high-risk tier.
* Whether a daylight execution **hour** offset anomalous high-volume scores.
* Dynamic local explanations translated directly into localized natural language sentences for internal compliance officers.

---

## Model Risk Management (MRM) Guidelines
Consistent with JPMC Model Governance standards:
1. **Anti-Tampering Enforcement**: The model refuses to load if its SHA-256 hash fails to match the committed signature file.
2. **Drift Monitoring**: rolling-window datasets are monitored for data drift via Kolmogorov-Smirnov (KS) tests inside the `EvidentlyDataDriftDetector`. Warnings and alert streams are triggered on Kafka topic `artha.monitoring.drift` if statistical drift scores exceed a threshold of `0.6`.
3. **Emergency Fallback**: In the event of model compilation corruption, the engine falls back to a transparent, static, rule-based Heuristic scoring logic (`RuleEngine_Fallback`), ensuring zero downtime for critical banking APIs.
