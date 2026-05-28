---
title: Artha AI
emoji: 🛡️
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Artha AI — Elite FinTech AI Platform

Artha AI is a highly sophisticated, production-grade FinTech intelligence platform engineered to showcase event-streaming architecture, advanced ML classification explainability, and real-time MLOps data drift auditing.

This project was built to establish a elite system-level engineering profile for JPMC GCC and Tier-1 Artificial Intelligence labs.

---

## 🏛 Susystem Architecture & Modules

The platform consists of three primary intelligent modules unified under a high-throughput **FastAPI Gateway**:

```
                              [ Unified API Gateway (FastAPI) ]
                                              │
                      ┌───────────────────────┼───────────────────────┐
                      ▼                       ▼                       ▼
              [ 🧠 FraudSense ]       [ 📋 RegGuard ]         [ 🔍 FinLens ]
             RandomForest+I-Forest     Section-Aware RAG       SQL-Agent Parser
             Tree SHAP Explainers    Local vector Indexing   Numerical Audits
```

### 1. 🧠 FraudSense (Prediction & Explainability)
*   **Ensemble ML Model**: Combines supervised learning (`RandomForestClassifier`) for fraud signature matching with unsupervised learning (`IsolationForest`) for structural anomaly detection.
*   **Local SHAP Rationale**: Calculates real-time **Tree SHAP feature attributions** (`shap.TreeExplainer`) to explain *exactly* why a transaction was flagged, transforming raw mathematical shapley weights into human-readable compliance logs.

### 2. 📋 RegGuard (Regulatory Auditing RAG)
*   **Indian Compliance Corpus**: Ingests custom RBI daily UPI caps, FEMA LRS outward remittance restrictions, KYC timeline deadlines, and PMLA triggers.
*   **Section-Aware Parser**: Chunks text on boundary headers to ensure citation precision.
*   **Local Vector Database Fallback**: Dynamically executes nearest-neighbor cosine similarity over a localized embedding registry using `sentence-transformers/all-MiniLM-L6-v2` (~90MB) for 100% offline query matching and compliance scores.

### 3. 🔍 FinLens (Statement Parser & Numerical SQL-Agent)
*   **Structured Parser**: Extracts ledger transaction tables from digital bank statements, committing them cleanly to database engines.
*   **Zero-Hallucination SQL-Agent**: Intercepts numerical balance audits and compiles natural language questions directly into executable SQL scripts, querying databases directly to guarantee 100% computational accuracy and preventing LLM math hallucinations.

---

## 🚀 Live Public Deployment (Hugging Face Spaces)

This repository is pre-configured to run as a **Hugging Face Docker Space** (2 vCPU · 16 GB RAM — 100% Free). 

### How to Run Locally

#### Option A: Docker Compose Orchestration (All Services)
Launch the entire network (FastAPI Gateway, PostgreSQL with pgvector, Redis Cache, Apache Kafka, Zookeeper) with one command:
```bash
docker compose up --build
```

#### Option B: Bare-Metal Interactive Launcher (`deploy_local.sh`)
```bash
chmod +x deploy_local.sh

# Run Dev Server (FastAPI locally with hot reload, DBs in Docker containers)
./deploy_local.sh --dev

# Run Offline Server (no Docker required; runs on SQLite + thread-safe in-memory mocks)
./deploy_local.sh --offline
```

---

## 👨‍💻 Author
**GAURAV KUMAR NAYAK**
*   **Email:** gauravnayak711@gmail.com
*   **GitHub:** [github.com/Gaurav711cgu](https://github.com/Gaurav711cgu)
*   **Portfolio:** [gaurav-portfolio-iycu.vercel.app](https://gaurav-portfolio-iycu.vercel.app/)
