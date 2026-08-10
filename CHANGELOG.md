# Changelog

All notable changes to the Artha AI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-08-10

### Added
- Automated Data Drift Gate (`scripts/drift_check.py`) using Evidently AI to block CI merges when column drift exceeds 30%.
- Enhanced `/health` API endpoint delivering real-time model version (`1.2.0`), LightGBM + GraphSAGE ensemble metadata, validation AUC-ROC (`0.9138`), demographic parity gap (`0.0000`), and drift status.
- Automated GitHub Actions CI drift verification gate.

### Benchmarks
- Fraud Detection ROC-AUC: 0.9138 [measured]
- Demographic Subgroup AUC Parity Gap: 0.0000 [measured]
- Sub-15ms p95 Fraud Scoring Latency [measured]

## [1.0.0] - 2026-05-30
- Initial production release of FraudSense, RegGuard, and FinLens modules.
