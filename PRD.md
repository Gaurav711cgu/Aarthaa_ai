# ARTHA AI — Product Requirements Document
### Production-Grade FinTech AI Platform
**Powered by Groq LLaMA-3.1-70B · FastAPI · PostgreSQL · Redis · Kafka**
*   **Version:** 2.0.0 — Production Release
*   **Status:** APPROVED FOR DEVELOPMENT
*   **Author:** Gaurav Kumar Nayak
*   **Target:** JPMC GCC · Tier-1 AI Labs · FinTech Cos
*   **Date:** May 2026
*   **Classification:** INTERNAL — RESTRICTED

---

## 1. Executive Summary
Artha AI is a production-grade FinTech intelligence platform that unifies three AI-powered modules under a single high-throughput API gateway: **FraudSense** (real-time ML fraud detection with SHAP explainability), **RegGuard** (RAG-based regulatory compliance powered by Groq LLaMA-3.1-70B), and **FinLens** (an LLM-driven SQL agent for zero-hallucination financial statement analysis). This PRD defines the requirements, architecture changes, and implementation roadmap to transform the current prototype into a genuinely production-ready system that can withstand the technical scrutiny of JPMC GCC and Tier-1 AI lab engineering panels.

### 1.1 What This Document Covers
*   Honest gap analysis between current prototype capabilities and their claimed descriptions.
*   Concrete engineering changes required to make every claim technically accurate.
*   Full production architecture including auth, security, observability, and CI/CD.
*   Groq API integration specification (free tier: 30 req/min, 6,000 req/day on LLaMA-3.1-70B).
*   Phased implementation roadmap with effort estimates.
*   Acceptance criteria and definition of done for each module.

### 1.2 The Core Principle
Every feature this platform claims to have must actually work the way it claims to work. A senior engineer at any Tier-1 company will probe exactly three things: the SQL agent, the compliance RAG, and the drift detector. The current prototype has gaps in all three. This document closes them — entirely within a zero-cost infrastructure envelope using Groq's free API tier.

---

## 2. Current State Audit
A rigorous gap analysis of each claimed capability against the actual implementation.

### 2.1 Module-Level Gap Analysis

| Module | Claimed | Actual | Gap Severity |
|---|---|---|---|
| **FraudSense** | RF + IForest + SHAP ensemble | Correct — but only when `.pkl` exists | **MEDIUM** — model file must be pre-trained and committed or generated at startup |
| **RegGuard** | LLM-powered RAG agent | Template string with vector lookup — no LLM called | **CRITICAL** — the core differentiator does not use any LLM |
| **FinLens** | Zero-hallucination SQL Agent | if/elif keyword routing to hardcoded SQL templates | **CRITICAL** — keyword matching is not an agent; will fail on any novel query phrasing |
| **Drift Detector** | Evidently AI statistical drift | Simple mean deviation — Evidently is not imported | **HIGH** — class named `EvidentlyDataDriftDetector` but Evidently is not in `requirements.txt` |
| **Auth / Security** | Implied (`python-jose` in requirements) | No auth on any endpoint | **CRITICAL** — all endpoints are public; unacceptable for a fintech platform |
| **Secrets** | Environment-driven config | `SECRET_KEY` hardcoded in `config.py` and committed to Git | **CRITICAL** — active security vulnerability for a banking-targeted codebase |
| **Vector Store** | Secure local embeddings store | Pickle serialization — arbitrary code execution on load | **HIGH** — pickle is a known attack vector; use JSON or SQLite |

### 2.2 What Is Genuinely Good
*   FastAPI gateway structure with versioned routers — correct and scalable.
*   SHAP TreeExplainer integration — real, appropriate, and impressive in a demo.
*   Offline/online fallback chain (Postgres → SQLite, model → heuristic) — thoughtful resilience design.
*   Kafka publish hooks in the fraud pipeline — demonstrates event-streaming awareness.
*   Prometheus metrics endpoint with meaningful labels — correct observability pattern.
*   Indian regulatory corpus coverage (RBI/UPI/FEMA/PMLA) — strong domain differentiation.
*   Docker Compose + Hugging Face Spaces deployment — zero-friction demo setup.

---

## 3. Product Vision & Goals

### 3.1 Vision Statement
To be the reference-grade, open-source FinTech AI platform for the Indian market — demonstrating that production-quality fraud detection, regulatory compliance, and financial intelligence can be built entirely on zero-cost infrastructure while meeting the engineering standards of Tier-1 financial institutions.

### 3.2 Strategic Goals

| # | Goal | Success Criteria |
|---|---|---|
| **G1** | Technical Credibility | Every claimed feature demonstrably works end-to-end; no mock responses in production paths |
| **G2** | Zero Infrastructure Cost | Full production stack runs on Groq free tier + Hugging Face Spaces 2vCPU/16GB |
| **G3** | Security Baseline | JWT auth on all endpoints, no secrets in source, pickle replaced, input validation throughout |
| **G4** | Real AI Agents | RegGuard calls Groq LLaMA-3.1-70B; FinLens uses LangChain SQLAgent with Groq backend |
| **G5** | Genuine MLOps | Real Evidently AI drift reports, Prometheus scraping, Kafka event streaming all verified |
| **G6** | Demo-Ready UX | Gradio UI on Hugging Face Spaces; every module interactive without needing Postman |

### 3.3 Target Audience

| Persona | Role | What They Need | What Impresses Them |
|---|---|---|---|
| **Hiring Manager** | JPMC GCC / AI Lab | System design, security posture, production-readiness | Auth, real agents, observability |
| **Technical Screener** | Senior SWE / MLE | Code quality, honest claims, real implementations | SHAP explainability, Groq RAG working live |
| **Portfolio Viewer** | Recruiter / PM | A working demo they can actually use | Gradio UI, clear outputs, visual SHAP charts |
| **Open Source User** | FinTech Developer | Clean code they can fork and extend | Modularity, documented APIs, zero-cost stack |

---

## 4. Production Architecture

### 4.1 System Overview
The production architecture adds three layers that the prototype lacks: authentication, real LLM inference, and genuine observability. All additions remain within the zero-cost envelope.

```
CLIENT LAYER
Gradio UI  ·  Postman / curl  ·  External FinTech Apps
                        ▼
JWT AUTHENTICATION MIDDLEWARE  (python-jose + FastAPI Depends)
                        ▼
FASTAPI GATEWAY  ·  Rate Limiter  ·  GZip  ·  /health  ·  /metrics
        ┌─────────────────┬─────────────────┬─────────────────┐
        🧠 FraudSense         📋 RegGuard            🔍 FinLens
       RF+IForest+SHAP     Groq LLaMA-3.1-70B     LangChain SQLAgent
       Drift Detector       cosine RAG +             + Groq backend
       Kafka Publisher       JSON embeddings          + pgvector
        └─────────────────┴─────────────────┴─────────────────┘
                        ▼
DATA LAYER:  PostgreSQL+pgvector  ·  Redis Cache  ·  SQLite (offline)
EXTERNAL:  Groq API (free)  ·  Kafka  ·  Prometheus  ·  Evidently AI
```

### 4.2 Groq API Integration
Groq's free tier provides 30 requests/minute and 6,000 requests/day on LLaMA-3.1-70B — sufficient for demo, portfolio, and moderate production traffic. The integration pattern below applies to both RegGuard and FinLens.

| Parameter | RegGuard | FinLens |
|---|---|---|
| **Model** | `llama-3.1-70b-versatile` | `llama-3.1-70b-versatile` |
| **Max Tokens** | 512 (compliance answers are concise) | 1024 (SQL + explanation) |
| **Temperature** | 0.1 (factual, deterministic) | 0.0 (zero-temp for SQL generation) |
| **System Prompt** | Regulatory expert, cite sections | SQL-only output, no markdown fences |
| **Fallback** | Template string (offline mode) | if/elif routing (offline mode) |
| **Caching** | Redis TTL=3600s per query hash | No cache — SQL must be fresh per query |

---

## 5. Feature Requirements

### 5.1 Authentication & Security [CRITICAL — Build First]

#### 5.1.1 JWT Authentication
All API endpoints except `/health`, `/docs`, `/metrics`, and `/auth/token` must require a valid JWT Bearer token.
*   `POST /auth/token` — accepts username + password, returns `access_token` (JWT, 24h expiry) and `token_type`.
*   Dependency: `get_current_user = Depends(oauth2_scheme)` — injected into all protected routers.
*   Token payload: `{sub: username, exp: unix_timestamp, role: [admin|analyst|readonly]}`.
*   Roles enforced at endpoint level: fraud scoring requires analyst+, compliance queries require readonly+.
*   Return HTTP 401 with `WWW-Authenticate: Bearer` on missing/expired tokens.

#### 5.1.2 Secrets Management
*   Remove hardcoded `SECRET_KEY` from `config.py` — must raise `ValueError` on startup if `GROQ_API_KEY` or `SECRET_KEY` not in environment.
*   Add validation in Settings initialization: `assert len(SECRET_KEY) >= 32, 'SECRET_KEY too short'`.
*   Add secrets rotation endpoint: `PUT /auth/rotate-key` (admin only) — generates new JWT signing key and invalidates all existing tokens.
*   Update `.env.example` with all required keys — no default values for secrets.

#### 5.1.3 Input Validation
*   All Pydantic request models must have field validators — no bare float/int without range constraints.
*   `amount`: `confloat(ge=0.0, le=1_000_000_000)` — reject negative transactions.
*   `hour`: `conint(ge=0, le=23)` — enforce valid hour range.
*   SQL query strings sanitized via parameterized queries only — no string interpolation in SQL.
*   File upload endpoints (FinLens statement parser): validate MIME type, max 10MB, PDF/CSV only.

#### 5.1.4 Replace Pickle with JSON
*   Replace `pickle.dump/load` in `vector_store.py` with `json.dump/load`.
*   Vectors stored as lists of floats in JSON — compatible with `json` module without third-party dependencies.
*   Add CRC32 checksum field to embeddings file — validate on load, regenerate if corrupt.

---

### 5.2 RegGuard — Real LLM-Powered RAG [CRITICAL]

#### 5.2.1 Groq LLM Integration
Replace the template string response builder with an actual Groq API call. The RAG pipeline becomes: retrieve → augment → generate.
*   Install: `groq>=0.9.0` — add to `requirements.txt`.
*   GroqClient initialized once as module-level singleton with `GROQ_API_KEY` from settings.
*   System prompt: *'You are a senior Indian financial compliance officer. Answer only from the provided regulatory context. Always cite the specific section. Be precise with numbers — amounts, limits, deadlines. Never hallucinate. If unsure, say so.'*
*   User prompt template: `Context: {retrieved_chunks}\n\nQuestion: {user_query}\n\nProvide a cited, accurate compliance ruling.`
*   Parse `Groq response.choices[0].message.content` — return as `answer` field.
*   Offline fallback: if `GROQ_API_KEY` is None → use existing template string path (preserved for Hugging Face zero-config demo).

#### 5.2.2 RAG Pipeline Improvements
*   Increase `top_k` from 2 to 4 retrieved chunks — more context for complex multi-regulation queries.
*   Add chunk reranking: compute cosine similarity of each chunk to the Groq-generated answer (post-hoc citation verification).
*   Cache compliance query responses in Redis with key: `sha256(query_text)` — TTL 1 hour.
*   Expand regulations corpus: add SEBI KYC Master Circular, NPCI UPI 2.0 guidelines, RBI Digital Lending Framework 2022.
*   Section-aware chunking: preserve section headers in chunk metadata for precise citation rendering.

#### 5.2.3 Response Schema
The compliance query response must include:
*   `answer`: string — Groq-generated compliance ruling.
*   `citations`: list of `{document, section, relevance_score, chunk_text_preview}`.
*   `confidence`: float — mean cosine similarity of top chunks.
*   `model_used`: string — `'groq/llama-3.1-70b-versatile' | 'offline_template'`.
*   `processing_time_ms`: float — for observability.

---

### 5.3 FinLens — Real LangChain SQL Agent [CRITICAL]

#### 5.3.1 Replace Keyword Routing with LangChain SQLAgent
The if/elif chain must be replaced entirely with a LangChain `SQLDatabaseToolkit` backed by Groq. Natural language → LLM → SQL → execute → return.
*   Install: `langchain>=0.2.0`, `langchain-groq>=0.1.3`, `langchain-community>=0.2.0`.
*   `SQLDatabase.from_uri(database_url)` — LangChain connects to the same PostgreSQL/SQLite instance.
*   `ChatGroq(model='llama-3.1-70b-versatile', temperature=0.0, api_key=settings.GROQ_API_KEY)`.
*   `SQLDatabaseToolkit(db=db_connection, llm=llm)` — auto-discovers table schema.
*   `create_sql_agent(llm, toolkit, verbose=True, agent_type='openai-tools')`.
*   System prompt injection: *'Only query statement_transactions. statement_id must always be filtered. Return only the SQL result, not the query itself. Use INR currency formatting.'*
*   Agent output parsed: extract `numerical_value` via regex on result string.

#### 5.3.2 Offline Fallback
*   Keep the existing if/elif routing as the offline fallback path — activated when `GROQ_API_KEY` is None.
*   Log fallback activation clearly: `logger.warning('FinLens running in offline keyword-routing mode')`.
*   Expand keyword routing to cover 15+ additional patterns for better offline coverage.

#### 5.3.3 Statement Parser Improvements
*   Add support for CSV bank statement uploads (not just PDF) — use pandas for CSV parsing.
*   Add column normalisation: map 'Cr'/'Dr', 'Credit'/'Debit', '+'/'-' to canonical `CREDIT`/`DEBIT`.
*   Add statement summary endpoint: `GET /api/v1/finlens/statements/{id}/summary` — returns top 5 categories, monthly spend, income vs expense ratio.

---

### 5.4 FraudSense — Completing the ML Pipeline

#### 5.4.1 Auto-Train on Startup
*   If `fraud_model.pkl` does not exist at startup, automatically run `train_fraud_model.py` using synthetic Faker data — no manual step required.
*   Training runs in a background thread — API returns 503 with retry-after header during training.
*   Log model metrics (accuracy, precision, recall, AUC) to Prometheus counter on train completion.

#### 5.4.2 Batch Scoring Endpoint
*   `POST /api/v1/fraud/score/batch` — accepts list of up to 100 transactions.
*   Returns array of scores with per-transaction SHAP explanations.
*   Publishes batch summary event to Kafka topic: `artha.fraud.batch`.

#### 5.4.3 SHAP Visualization Data
*   Add `shap_chart_data` field to score response: `{labels: [...], values: [...]}` — ready for Gradio bar chart rendering.
*   Enables the Gradio UI to render SHAP waterfall chart without additional computation.

---

### 5.5 Drift Detector — Real Evidently AI
*   Add `evidently>=0.4.0` to `requirements.txt`.
*   Replace manual mean deviation with `Report([DataDriftPreset()])` on the sliding window.
*   Store baseline dataset as a proper CSV artifact — not hardcoded floats in Python.
*   Add endpoint: `GET /api/v1/monitoring/drift-report` — returns Evidently HTML report as base64.
*   Rename class to `DataDriftDetector` — remove the 'Evidently' prefix since it was misleading; now it actually uses Evidently.
*   Publish drift events to Kafka topic: `artha.monitoring.drift` when `drift_score > 0.6`.

---

## 6. API Specification

### 6.1 Authentication Endpoints

| Method | Path | Body | Response | Auth |
|---|---|---|---|---|
| **POST** | `/auth/token` | `username, password` | `{access_token, token_type}` | Public |
| **POST** | `/auth/refresh` | `refresh_token` | `{access_token}` | Public |
| **PUT** | `/auth/rotate-key` | — | `{message: 'Key rotated'}` | Admin JWT |

### 6.2 FraudSense Endpoints

| Method | Path | Request | Response | Rate Limit |
|---|---|---|---|---|
| **POST** | `/api/v1/fraud/score` | `TransactionRequest` | `FraudScoreResponse + SHAP + drift` | 60/min |
| **POST** | `/api/v1/fraud/score/batch` | `List[TransactionRequest]` | `List[FraudScoreResponse]` | 10/min |
| **GET** | `/api/v1/fraud/metrics` | — | `Model accuracy, AUC, training date` | 30/min |

### 6.3 RegGuard Endpoints

| Method | Path | Request | Response | Rate Limit |
|---|---|---|---|---|
| **POST** | `/api/v1/compliance/query` | `{query: string}` | `answer, citations, model_used` | 30/min |
| **POST** | `/api/v1/compliance/check` | `TransactionRequest` | `verdict, violations, citations` | 60/min |
| **GET** | `/api/v1/compliance/regulations` | — | `List of loaded regulation sources` | 30/min |
| **POST** | `/api/v1/compliance/ingest` | PDF/TXT upload | `chunks_added, source_name` | 5/min (admin) |

### 6.4 FinLens Endpoints

| Method | Path | Request | Response | Rate Limit |
|---|---|---|---|---|
| **POST** | `/api/v1/finlens/upload` | PDF/CSV file | `statement_id, rows_parsed` | 10/min |
| **POST** | `/api/v1/finlens/query` | `{statement_id, query}` | `answer, sql, numerical_value` | 30/min |
| **GET** | `/api/v1/finlens/statements/{id}` | — | `Statement metadata + row count` | 30/min |
| **GET** | `/api/v1/finlens/statements/{id}/summary` | — | `Category breakdown, income/expense` | 30/min |

---

## 7. Implementation Roadmap
Four phases. Each phase is independently deployable and testable. Do not skip Phase 1 — security issues block everything else.

### PHASE 1 · Security & Foundations
*   **1.1** Remove hardcoded `SECRET_KEY`; add startup validation for all env vars. (2h) [P0 — BLOCKER]
*   **1.2** Implement JWT auth: `/auth/token`, `get_current_user` dependency, 401 handling. (4h) [P0 — BLOCKER]
*   **1.3** Apply auth dependency to all protected routes; test with pytest. (2h) [P0 — BLOCKER]
*   **1.4** Replace pickle serialization in `vector_store.py` with JSON + CRC32. (2h) [P0]
*   **1.5** Add Pydantic field validators to all request models. (3h) [P0]
*   **1.6** Run Ruff + mypy; fix all type errors and linting violations. (2h) [P1]
*   **1.7** Update `.gitignore`: confirm `.env` is excluded; add pre-commit hook. (1h) [P1]
*   **1.8** Write unit tests for auth flows (token issue, expiry, 401 responses). (3h) [P1]

### PHASE 2 · Real AI Integration (Groq)
*   **2.1** Add `groq>=0.9.0`, `langchain-groq>=0.1.3`, `langchain-community>=0.2.0` to `requirements.txt`. (30m) [P0]
*   **2.2** RegGuard: Replace template string builder with Groq LLaMA call + offline fallback. (4h) [P0 — CRITICAL]
*   **2.3** RegGuard: Add Redis caching for compliance query responses (TTL 1h). (2h) [P1]
*   **2.4** RegGuard: Expand regulations corpus (SEBI, NPCI UPI 2.0, RBI Digital Lending). (3h) [P1]
*   **2.5** FinLens: Replace if/elif chain with LangChain SQLAgent + Groq backend. (6h) [P0 — CRITICAL]
*   **2.6** FinLens: Add offline fallback path with warning log; expand keyword coverage. (2h) [P1]
*   **2.7** FinLens: Add CSV upload support + column normalisation. (3h) [P1]
*   **2.8** FinLens: Add `/statements/{id}/summary` endpoint. (2h) [P2]
*   **2.9** Write integration tests for Groq paths (mock Groq responses in CI). (4h) [P1]

### PHASE 3 · MLOps & Observability
*   **3.1** Add `evidently>=0.4.0` to `requirements.txt`. (30m) [P0]
*   **3.2** Replace mean deviation drift with Evidently `Report([DataDriftPreset()])`. (4h) [P0]
*   **3.3** Store baseline dataset as CSV artifact; load at startup. (2h) [P0]
*   **3.4** Add `GET /api/v1/monitoring/drift-report` endpoint (Evidently HTML as base64). (2h) [P1]
*   **3.5** FraudSense: Auto-train on startup if `.pkl` missing (background thread + 503). (3h) [P0]
*   **3.6** FraudSense: Add `POST /fraud/score/batch` endpoint. (2h) [P1]
*   **3.7** FraudSense: Add `shap_chart_data` field to score response. (1h) [P1]
*   **3.8** Kafka: Verify event publishing works end-to-end; add `/monitoring/kafka-status` endpoint. (2h) [P1]

### PHASE 4 · Demo UI & CI/CD
*   **4.1** Build Gradio UI: FraudSense tab with SHAP bar chart, risk badge, explanation text. (4h) [P0]
*   **4.2** Build Gradio UI: RegGuard tab with query input, citation display, confidence score. (3h) [P0]
*   **4.3** Build Gradio UI: FinLens tab with CSV/PDF upload, NL query, SQL display, result. (3h) [P1]
*   **4.4** Build Gradio UI: Monitoring tab with drift score gauge, Prometheus metrics summary. (2h) [P1]
*   **4.5** GitHub Actions CI: lint (Ruff), type-check (mypy), unit tests, integration tests. (3h) [P1]
*   **4.6** GitHub Actions CD: auto-deploy to Hugging Face Spaces on main branch push. (2h) [P1]
*   **4.7** Update README: remove all overstated claims; replace with accurate technical descriptions. (2h) [P0]
*   **4.8** Add architecture diagram to README (Mermaid flowchart). (1h) [P2]

---

## 8. Non-Functional Requirements

| Category | Requirement | Measurement |
|---|---|---|
| **Performance** | Fraud scoring p99 latency | < 200ms (local model, no Groq) |
| **Performance** | RegGuard Groq query response | < 3s (Groq free tier typical: 800ms) |
| **Performance** | FinLens SQL agent end-to-end | < 5s (Groq + DB query) |
| **Availability** | Hugging Face Spaces uptime | > 99% (HF SLA) |
| **Availability** | Graceful degradation when Groq unavailable | Offline fallback activates within 500ms |
| **Security** | All endpoints require JWT | 401 returned on missing/invalid token |
| **Security** | No secrets in source code | Zero hardcoded credentials in any file |
| **Security** | Input validation | All fields validated; malformed inputs return 422 |
| **Observability** | Prometheus metrics endpoint | `/metrics` returns valid Prometheus exposition format |
| **Observability** | Structured logging | JSON logs with correlation IDs on all requests |
| **Scalability** | Stateless API design | No in-process session state; Redis for shared state |
| **Testing** | Unit test coverage | > 80% on `services/` and `api/` modules |
| **Testing** | Integration test suite | All 3 modules tested end-to-end with mocked Groq |

---

## 9. Success Metrics & Acceptance Criteria

### 9.1 Definition of Done Per Phase

#### Phase 1 — Done When:
*   `curl -X POST /api/v1/fraud/score` without Authorization header returns exactly HTTP 401.
*   `SECRET_KEY='' python -m uvicorn app.main:app` fails at startup with a clear error message.
*   `git log --all -p | grep 'SECRET_KEY'` shows no secret values in any commit.
*   All pytest unit tests pass with 0 failures.

#### Phase 2 — Done When:
*   `POST /api/v1/compliance/query` with 'What is the UPI daily limit?' returns an answer field containing text generated by Groq (not the template string), with a citations array of length >= 1.
*   `POST /api/v1/finlens/query` with `query='How much did I spend on food?'` returns `compiled_sql` field containing a valid SQL statement generated by the LLM, not a hardcoded template.
*   `GROQ_API_KEY=invalid` — both endpoints fall back gracefully to offline mode without raising HTTP 500.

#### Phase 3 — Done When:
*   `GET /api/v1/monitoring/drift-report` returns a base64 string that decodes to a valid Evidently HTML report.
*   Starting the app without `fraud_model.pkl` — model trains automatically, API returns 503 during training, 200 after.
*   Kafka topic `artha.fraud.score` receives a message within 2 seconds of a fraud scoring request.

#### Phase 4 — Done When:
*   Gradio UI loads on Hugging Face Spaces public URL without login.
*   All three modules are demoed end-to-end through the Gradio UI with no API calls to Postman.
*   GitHub Actions CI passes on every pull request to main.
*   README contains zero claims that are not backed by actual code implementation.

### 9.2 Portfolio Impact Metrics

| Signal | Current State | Post-PRD Target |
|---|---|---|
| **Technical accuracy of claims** | 3/7 features work as described | 7/7 features work as described |
| **Security posture** | 0 auth, 1 hardcoded secret | JWT auth, zero hardcoded secrets |
| **Demo-ability without Postman** | Not possible | Full Gradio UI on public URL |
| **Can withstand technical grilling** | Fails on SQL agent, RAG, drift | Passes all three probes |
| **CI/CD pipeline** | None | GitHub Actions + HF auto-deploy |
| **Test coverage** | 14 tests, some integration gaps | > 80% unit, full integration suite |
| **README accuracy** | Overstated on 4 major claims | 100% accurate, every claim verified |

---

## 10. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Groq free tier rate limit hit during demo** | Medium | High | Cache compliance responses in Redis (TTL 1h); implement exponential backoff; offline fallback activates automatically |
| **LangChain SQLAgent generates incorrect SQL** | Low | High | Temperature=0.0; system prompt restricts to SELECT only; parameterized execution; offline fallback for known patterns |
| **Evidently adds significant startup time** | Medium | Medium | Run drift detector initialization in background thread; return 202 Accepted on first drift check call |
| **HF Spaces 2vCPU insufficient for concurrent demos** | Medium | Medium | Fraud model pre-loaded at startup; Groq offloads LLM compute; SHAP only runs on request |
| **GROQ_API_KEY not set in HF Spaces secrets** | Medium | High | Startup validation logs clear error; offline mode activates; Gradio UI shows 'offline mode' banner |
| **Regulations corpus produces low-relevance chunks** | Low | Medium | Increase top_k to 4; add confidence threshold — if max score < 0.35, return 'insufficient regulatory context found' |

### 10.1 Groq Free Tier Limits — Reference

| Model | Requests/Min | Requests/Day |
|---|---|---|
| **`llama-3.1-70b-versatile`** | 30 req/min | 6,000 req/day |
| **`llama-3.1-8b-instant`** | 30 req/min | 14,400 req/day |
| **`mixtral-8x7b-32768`** | 30 req/min | 14,400 req/day |

*   **Strategy:** Use `llama-3.1-70b-versatile` for RegGuard compliance answers (quality-critical, low frequency). Use `llama-3.1-8b-instant` for FinLens SQL generation (speed-critical, higher frequency). Both are within free tier limits for demo and portfolio traffic.

---
*Artha AI — Product Requirements Document · CONFIDENTIAL*
