# Artha AI: FinTech Audit & Observability Platform

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square&logo=vercel&logoColor=white)

Artha AI is an enterprise-grade FinTech audit, transaction validation, and regulatory compliance observability platform. It couples supervised machine learning fraud ensembles with real-time Tree SHAP attributions and an active regulatory RAG search engine for SEBI and NPCI circular compliance.

---

## Key Capabilities

### 1. Supervised Fraud Ensembles & Tree SHAP Explainability
Supervised models flagging financial transactions must provide auditing traces. Artha AI:
- Employs a voting ensemble (XGBoost + LightGBM + Random Forest) for transaction-level fraud auditing.
- Computes real-time Tree SHAP feature attributions for every flagged transaction.
- Breaks down exactly which transaction attributes (e.g. volume multipliers, velocity, recipient history) contributed to the risk score.

### 2. RegGuard RAG (SEBI & NPCI Circular Auditing)
Financial agents must act within strict regulatory frameworks. Artha AI integrates:
- Dense pgvector vector search indexing historical SEBI and NPCI circulars.
- BM25 sparse keyword retrievers aligned to document section indexes.
- Dynamic cross-encoder reranking using cosine similarity to map transaction records directly to compliance policy matches.

### 3. LangChain SQL Audit Agent & MLOps Monitoring
- Executes automated natural language auditing of relational transactions using a LangChain SQL database agent.
- Incorporates Evidently AI to monitor data drift and performance decay on transaction features.
- Employs Redis as a cache and transient rate-limiter to handle live banking audit APIs.

---

## System Architecture

(Add a ```mermaid tag around the block below to render the diagram)

    graph TD
        A[Banking Transaction Logs] -->|Stream API| B[FastAPI Gateway]
        B -->|Feature Engineering| C[ML Ensemble Classifier]
        C -->|Fraud Flag & SHAP Values| D[Tree SHAP Explainer]
        
        B -->|Compliance Vector Query| E[RegGuard RAG Engine]
        E -->|Neo4j circular mappings| F[SEBI / NPCI Circulars]
        
        B -->|SQL Schema Analysis| G[LangChain SQL Auditor]
        B -->|Evidently AI Logs| H[MLOps Drift Dashboard]

---

## Directory Structure

(Add a ```yaml tag around the block below)

    artha-ai/
      ├── models/
      │   ├── classifier.py     # Ensemble transaction voting classifier
      │   └── explainer.py      # Tree SHAP feature attribution generator
      ├── rag/
      │   ├── vector_search.py  # RegGuard pgvector database search logic
      │   └── loader.py         # NPCI/SEBI PDF parser and text chunker
      ├── auditor/
      │   └── sql_agent.py      # LangChain database agent logic
      ├── monitoring/
      │   └── drift.py          # Evidently AI feature drift analytics
      ├── api/
      │   └── main.py           # FastAPI transaction audit server
      └── requirements.txt      # Python dependencies

---

## Getting Started

### 1. Installation
Clone the repository and install dependencies:

    git clone https://github.com/Gaurav711cgu/Aarthaa_ai-main.git
    cd Aarthaa_ai-main
    pip install -r requirements.txt

### 2. Initialize Database & Vector Indexes
Configure environment database URLs, then run migrations and index compliance circular documents:

    python rag/loader.py --data_dir ./circulars

### 3. Run the Audit Platform
Launch the API gateway:

    uvicorn api.main:app --host 0.0.0.0 --port 8000

---

## Running Compliance Audits

To audit a batch of transaction records against current SEBI compliance circular vectors:

    python rag/vector_search.py --batch_file transactions.csv

### Example Output:

    [AUDIT ALERT] Transaction ID #9876 flagged for review.
    [ML ATTRIBUTION] SHAP values: transaction_velocity (+0.42), amount_multiplier (+0.35).
    [REGGUARD MATCH] 94% compliance match found: SEBI Circular 2026/04-A (Section 3: Velocity Limits).

---

## License
This project is licensed under the MIT License - see the LICENSE file for details.
