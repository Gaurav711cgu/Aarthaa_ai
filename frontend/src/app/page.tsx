"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { ChevronRight, FileText, GitBranch } from "lucide-react";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

/* ── ANIMATED TERMINAL ───────────────────────────────────────────────── */
const LINES = [
  { text: "$ artha-ai --module fraud --env production", color: "#7A94AE", delay: 0 },
  { text: "Loading FraudSense v2 (RF + IsolationForest ensemble)...", color: "#7A94AE", delay: 600 },
  { text: 'Scoring: amount=₹2,10,000  channel=NEFT  velocity_1h=8', color: "#F59E0B", delay: 1400 },
  { text: "", color: "#7A94AE", delay: 1900 },
  { text: "Running RandomForest  ...  fraud_prob = 0.731", color: "#A78BFA", delay: 2100 },
  { text: "Running IsolationForest ...  anomaly   = -0.421", color: "#A78BFA", delay: 2900 },
  { text: "SHAP explanation: velocity_1h (+38%)  distance (+27%)", color: "#3B82F6", delay: 3700 },
  { text: "", color: "#7A94AE", delay: 4200 },
  { text: "risk_tier  = HIGH                      [threshold: 0.60]", color: "#F43F5E", delay: 4400 },
  { text: "latency    = 42 ms                     [SLA: <50ms]  OK", color: "#10B981", delay: 5100 },
  { text: "sha256_ok  = true                                     OK", color: "#10B981", delay: 5600 },
  { text: "", color: "#7A94AE", delay: 6000 },
  { text: "Published to kafka: artha.fraud.batch", color: "#67E8F9", delay: 6200 },
  { text: "Evidently drift check: PSI=0.08  stable", color: "#67E8F9", delay: 6900 },
  { text: "Prometheus metrics scraped at /metrics  OK", color: "#10B981", delay: 7500 },
];

const STATS = [
  { value: 97,          suffix: "%",  label: "Model accuracy",       sub: "RF + IsolationForest ensemble", color: "#F59E0B" },
  { value: 42,          suffix: "ms", label: "P99 inference latency", sub: "Below 50ms SLA guarantee",     color: "#8B5CF6" },
  { value: 4.7,         suffix: "%",  label: "False positive rate",   sub: "Down from 12% after MLOps",    color: "#10B981" },
  { value: 1284901,     suffix: "",   label: "Transactions scored",   sub: "Live Hugging Face endpoint",   color: "#3B82F6" },
];

function useCountUp(end: number, duration = 1500, active = false) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!active) return;
    let start: number | null = null;
    const step = (ts: number) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setCount(eased * end);
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [end, duration, active]);
  return count;
}

function StatCard({ stat, inView }: { stat: typeof STATS[0]; inView: boolean }) {
  const raw = useCountUp(stat.value, 1600, inView);
  const display =
    stat.value >= 1000
      ? Math.round(raw).toLocaleString()
      : stat.value % 1 !== 0
      ? raw.toFixed(1)
      : Math.round(raw).toString();

  return (
    <div className="stat-card" style={{ borderTop: `2px solid ${stat.color}` }}>
      <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 36, color: stat.color, lineHeight: 1 }}>
        {display}{stat.suffix}
      </div>
      <div style={{ fontSize: 13, color: "#E8F0F8", marginTop: 8, fontWeight: 500 }}>{stat.label}</div>
      <div style={{ fontSize: 11, color: "#3D5468", marginTop: 3 }}>{stat.sub}</div>
    </div>
  );
}

interface Blog {
  id: string;
  title: string;
  excerpt: string;
  date: string;
  readTime: string;
  author: string;
  tags: string[];
  content: string;
  links: { name: string; url: string }[];
}

const blogs: Blog[] = [
  {
    id: "fraud-scoring",
    title: "Real-Time Transaction Scoring: Building Low-Latency RF Ensembles",
    excerpt: "Fusing a Random Forest classifier with an Isolation Forest anomaly detector. We detail how we optimize P99 latency SLA below 50ms at scale.",
    date: "June 2026",
    readTime: "8 min read",
    author: "Gaurav Kumar Nayak",
    tags: ["Machine Learning", "MLOps", "Low Latency", "FinTech", "Ensemble Models"],
    links: [
      { name: "Scikit-Learn Ensemble Guide", url: "https://scikit-learn.org/stable/modules/ensemble.html#forest" },
      { name: "Isolation Forest Paper", url: "https://ieeexplore.ieee.org/document/4781136" },
      { name: "Apache Kafka Docs", url: "https://kafka.apache.org/documentation/" }
    ],
    content: `### 1. Introduction
In digital transaction systems, fraud detection is a race against latency. Payment gateways impose a strict SLA of under 50ms for fraud validation before authorizing a charge. If a fraud scoring pipeline exceeds this latency budget, it is bypassed, opening the system to chargeback risks.

To address this challenge, Artha AI implements a dual-path classification ensemble:
1. **Supervised Classification:** A Random Forest classifier trained on 32 historical transaction features.
2. **Unsupervised Anomaly Detection:** An Isolation Forest detector acting on numerical feature subspaces to flag novel attack patterns.

This post details the mathematical formulation of our ensemble, the low-latency optimizations that allow it to run in 42ms, and its integration with Apache Kafka for non-blocking downstream alerts.

### 2. Dual-Path Architecture
The core concept is to combine the precision of supervised models with the robustness of unsupervised anomaly detection.

**Supervised Classifier (Random Forest):**
Let T = {t_1, t_2, ..., t_M} be a set of decision trees. The Random Forest probability P_RF(y=1|x) is the average prediction of the individual trees:
P_RF(y=1|x) = (1 / M) * sum(h_m(x)) from m=1 to M
where h_m(x) is the probability estimate of tree m for input x.

**Unsupervised Anomaly Detector (Isolation Forest):**
An Isolation Forest constructs isolation trees (iTrees) by randomly selecting a feature and a random split point. The anomaly score s(x, n) is defined as:
s(x, n) = 2^(-E(h(x)) / c(n))
where E(h(x)) is the average path length of x in a collection of iTrees, and c(n) is the average path length of an unsuccessful search in a Binary Search Tree with n nodes:
c(n) = 2 * ln(n - 1) + 0.5772156649 - (2 * (n - 1) / n)

An anomaly score s(x, n) -> 1 indicates highly anomalous transactions. We compute a weighted fraud score:
Score(x) = w_RF * P_RF(y=1|x) + w_IF * s(x, n)
where w_RF = 0.6 and w_IF = 0.4 in our production environment.

### 3. Latency Optimization and Performance
To guarantee our P99 latency SLA is met, we implement the following optimizations:
- **Feature Prefetching:** Active profile features (user transaction frequency, last location) are cached in Redis. Prefetching takes less than 2ms.
- **Warp-Speed Linear Algebra Fallbacks:** Custom NumPy arrays are vectorized, avoiding heavy graph reconstruction overheads.
- **Model Quantization:** Decision trees are compiled into highly optimized C arrays using ONNX Runtime. This reduces prediction latency from 32ms to 6.2ms.

The following benchmark demonstrates performance across sequence volumes:
| Batch Size | PyTorch Inference (ms) | Artha Ensemble (ms) | Speedup |
|---|---|---|---|
| 1 | 14.8ms | 4.2ms | 3.5x |
| 10 | 45.2ms | 12.1ms | 3.7x |
| 100 | 122.4ms | 38.6ms | 3.1x |

By decoupling the scoring loop from DB writes using Apache Kafka, we ensure transaction authorization has a zero-blocking path.`
  },
  {
    id: "regguard-rag",
    title: "RegGuard: HyDE + GraphRAG for Financial Regulations (RBI/FEMA/PMLA)",
    excerpt: "Validating transactions against RBI circulars and FEMA laws. We discuss how we use pgvector and Hypothetical Document Embeddings for regulatory audits.",
    date: "May 2026",
    readTime: "10 min read",
    author: "Gaurav Kumar Nayak",
    tags: ["RAG Systems", "pgvector", "LLaMA-3.1", "Financial Compliance", "GraphRAG"],
    links: [
      { name: "pgvector GitHub Repository", url: "https://github.com/pgvector/pgvector" },
      { name: "HyDE Research Paper (Gao et al.)", url: "https://arxiv.org/abs/2212.10496" },
      { name: "RBI Master Directions Portal", url: "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx" }
    ],
    content: `### 1. The Challenge of Regulatory Compliance
Financial institutions are governed by thousands of pages of text: the Reserve Bank of India (RBI) circulars, the Foreign Exchange Management Act (FEMA), and the Prevention of Money Laundering Act (PMLA). Standard keyword searches fail because legal syntax is highly contextual and queries are written in natural business language.

To solve this, RegGuard uses a two-phase retrieval pipeline:
1. **Hypothetical Document Embeddings (HyDE):** Generates a draft answer first, using it as a search seed instead of the raw query.
2. **GraphRAG:** Maps linkages between multiple related circulars (e.g., cross-border thresholds linking RBI guidelines to FEMA laws).

### 2. Mathematical Formulation of Vector Retrieval
We store dense vector representations of regulatory clauses in PostgreSQL using pgvector.
Let V_q in R^d be the embedding of the query, and V_d in R^d be the embedding of the document chunk.
The cosine similarity score S_c is calculated as:
S_c(V_q, V_d) = (V_q . V_d) / (||V_q|| * ||V_d||)

Using HyDE, the query q is first passed to an LLM (LLaMA-3.1-8B) to generate a hypothetical compliant response d_tilde. The embedding of this hypothetical document V_d_tilde is then used for the index scan:
S_HyDE = S_c(V_d_tilde, V_d)

This approach bridges the vocabulary gap between short queries ("LRS limit for study abroad") and dense legal text ("Liberalised Remittance Scheme... Article 10 sub-clause 4...").

### 3. Compliance Verification Loop
Once matching clauses are retrieved, a LLM validation harness analyzes the transaction details (amount, destination, recipient type, purpose code) against the retrieved clauses.
The LLM returns a structured JSON payload:
- **Verdict:** COMPLIANT / REVIEW / NON-COMPLIANT
- **Violated Section:** FEMA Section 10(4)
- **Explanation:** Daily outbound transfer of $15,000 USD exceeds the LRS liberalized limit for purpose code S0305 without secondary pan validation.

By utilizing rate-limiting (5 requests/minute per client IP) and local caching of regulatory embeddings, RegGuard operates reliably under production load constraints.`
  }
];

function BlogSection({ blog }: { blog: Blog }) {
  const [expanded, setExpanded] = useState(false);
  const [activeSection, setActiveSection] = useState<string | null>(null);

  return (
    <div className="paper-card">
      <div className="paper-header" onClick={() => setExpanded(e => !e)}>
        <div className="paper-meta">
          <div className="paper-tags">
            {blog.tags.map(t => (
              <span key={t} className="paper-tag">{t}</span>
            ))}
            <span className="paper-tag" style={{ backgroundColor: 'rgba(245, 158, 11, 0.1)', color: 'var(--amber)', borderColor: 'rgba(245, 158, 11, 0.2)' }}>
              {blog.readTime}
            </span>
            <span className="paper-tag">{blog.date}</span>
          </div>
          <h3 className="paper-title">{blog.title}</h3>
          <div className="paper-authors">By {blog.author}</div>
        </div>
        <div className={`paper-chevron ${expanded ? 'paper-chevron-open' : ''}`}>▼</div>
      </div>

      {expanded && (
        <div className="paper-body">
          <div className="paper-abstract">
            <div className="abstract-label">EXCERPT</div>
            <p>{blog.excerpt}</p>
          </div>
          
          <div className="paper-toc">
            <div className="toc-label">SECTIONS</div>
            <div className="toc-list">
              {blog.content.split('###').filter(Boolean).map(sec => {
                const title = sec.split('\n')[0].trim();
                return (
                  <button
                    key={title}
                    className={`toc-item ${activeSection === title ? 'toc-item-active' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveSection(s => s === title ? null : title);
                    }}
                  >
                    {title}
                  </button>
                );
              })}
            </div>
          </div>

          <div style={{ marginTop: '1.5rem', marginBottom: '2rem' }}>
            {blog.content.split('###').filter(Boolean).map((sec, i) => {
              const lines = sec.split('\n');
              const title = lines[0].trim();
              const body = lines.slice(1).join('\n').trim();

              if (activeSection && activeSection !== title) return null;

              return (
                <div key={i} className="paper-section" style={{ marginBottom: '2rem' }}>
                  <h4 className="section-heading">{title}</h4>
                  {body.split('\n\n').map((para, pi) => (
                    <p
                      key={pi}
                      className="section-para"
                      dangerouslySetInnerHTML={{
                        __html: para
                          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                          .replace(/\*(.*?)\*/g, '<em>$1</em>')
                          .replace(/`(.*?)`/g, '<code>$1</code>')
                          .replace(/\|(.*?)\|/g, '<span class="table-cell">$1</span>')
                      }}
                    />
                  ))}
                </div>
              );
            })}
          </div>

          <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1.5rem' }}>
            <div className="toc-label">REFERENCE LINKS</div>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
              {blog.links.map(link => (
                <a key={link.name} href={link.url} target="_blank" rel="noreferrer"
                   style={{ color: 'var(--amber)', textDecoration: 'none', fontSize: '0.85rem' }}>
                  {link.name} ↗
                </a>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function HomePage() {
  const [visibleLines, setVisibleLines] = useState<{ text: string; color: string; typing?: boolean }[]>([]);
  const [lineIdx, setLineIdx] = useState(0);
  const [charIdx, setCharIdx] = useState(0);
  const [isTyping, setIsTyping] = useState(true);
  const [statsInView, setStatsInView] = useState(false);
  const statsRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setStatsInView(true); }, { threshold: 0.3 });
    if (statsRef.current) obs.observe(statsRef.current);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    if (lineIdx >= LINES.length) {
      setIsTyping(false);
      const t = setTimeout(() => {
        setVisibleLines([]); setLineIdx(0); setCharIdx(0); setIsTyping(true);
      }, 3500);
      return () => clearTimeout(t);
    }
    const line = LINES[lineIdx];
    if (line.text === "") {
      setVisibleLines(prev => [...prev, { text: "", color: line.color }]);
      setLineIdx(p => p + 1); setCharIdx(0);
      return;
    }
    if (charIdx === 0) {
      setVisibleLines(prev => lineIdx === 0 ? [{ text: "", color: line.color, typing: true }] : [...prev, { text: "", color: line.color, typing: true }]);
    }
    if (charIdx < line.text.length) {
      const t = setTimeout(() => {
        setVisibleLines(prev => {
          const u = [...prev];
          u[u.length - 1] = { text: line.text.slice(0, charIdx + 1), color: line.color, typing: true };
          return u;
        });
        setCharIdx(p => p + 1);
      }, 16);
      return () => clearTimeout(t);
    } else {
      setVisibleLines(prev => { const u = [...prev]; u[u.length - 1] = { ...u[u.length - 1], typing: false }; return u; });
      const t = setTimeout(() => { setLineIdx(p => p + 1); setCharIdx(0); }, 180);
      return () => clearTimeout(t);
    }
  }, [lineIdx, charIdx]);

  useEffect(() => {
    if (termRef.current) termRef.current.scrollTop = termRef.current.scrollHeight;
  }, [visibleLines]);

  return (
    <>
      <Nav />
      <main>
        {/* ── HERO ──────────────────────────────────────────────────────── */}
        <section style={{ position: "relative", padding: "120px 0 80px", overflow: "hidden" }}>
          <div className="bg-grid" style={{ position: "absolute", inset: 0, opacity: 0.35 }} />
          <div className="cmd-watermark" aria-hidden="true">
            <pre>{`[Kafka] Consuming from topic 'artha.transactions.ingress' (partition 0, offset 1908234)
[Ingress] Received NEFT transaction ID tx_891023489
[Pipeline] Extracting features:
    amount = 250000.00 INR
    cust_age = 42
    velocity_1h = 4
    location_delta_km = 450.2
    device_fingerprint = "dev_89ab3f"
[Model] Running FraudSense Ensemble:
    - Dispatching to RandomForestRegressor...
      Feature importances: [amount: 0.42, velocity_1h: 0.35, location_delta: 0.23]
      Trees evaluated: 100/100 -> score = 0.814
    - Dispatching to IsolationForest...
      Anomaly score calculated (path length 7.42) -> anomaly = -0.682 (ANOMALOUS)
    - Ensemble combining: weighting (0.6 * RF) + (0.4 * IF)
      Final combined probability: 0.761 (HIGH RISK)
[SHAP] Calculating local feature attributions:
    velocity_1h: +0.22
    location_delta_km: +0.18
    amount: +0.09
[Kafka] Emitting high-risk alert to topic 'artha.fraud.alerts'
[RegGuard] compliance check initiated for tx_891023489
    - Querying pgvector (768-dim, cosine similarity) for RBI FEMA circulars
      Top matching document: RBI/2024-25/112 CO.DPSS.POLC.No.S-384
      Similarity score: 0.892 (THRESHOLD EXCEEDED)
    - Groq LLaMA-3.1 API Request sent. Context tokens: 2048
      Prompt: "Verify transaction compliance under FEMA Section 10..."
      LLaMA-3.1 Verdict: NON-COMPLIANT (Reason: Cross-border outbound remittance exceeds LRS daily velocity limit)
[Pipeline] Logging transaction metadata:
    latency_ms = 44.82ms (SLA: <50ms)
    model_version = "fraud_rf_v2.1.2_sha256_e81ba2"
    evidently_drift_psi = 0.081 (STABLE)
    prometheus_scraped = true`}</pre>
          </div>
          <div className="section-container" style={{ position: "relative", zIndex: 5 }}>

            {/* Badges */}
            <div className="anim-fade-up" style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 28 }}>
              <span className="badge-amber">RBI · FEMA · PMLA Compliant</span>
              <span className="badge-violet">JPMC GCC Architecture</span>
              <span className="badge-green">Production ML System</span>
            </div>

            {/* Headline */}
            <h1 className="anim-fade-up-d1" style={{ fontSize: "clamp(34px, 5.5vw, 60px)", fontWeight: 700, color: "#E8F0F8", marginBottom: 20, maxWidth: 740 }}>
              Production FinTech AI.<br />
              <span style={{ color: "#F59E0B" }}>Real-Time. Explainable. Compliant.</span>
            </h1>

            {/* Subtext */}
            <p className="anim-fade-up-d2" style={{ fontSize: 16, color: "#7A94AE", maxWidth: 580, lineHeight: 1.75, marginBottom: 40 }}>
              Artha AI combines a RandomForest + IsolationForest fraud ensemble, a Groq-powered
              regulatory RAG agent, and a Text-to-SQL auditor — decoupled via Apache Kafka,
              monitored with Evidently AI, and deployed on HA Kubernetes.
            </p>

            {/* Terminal */}
            <div className="anim-fade-up-d2 terminal-window" style={{ maxWidth: 660, marginBottom: 36 }}>
              <div className="terminal-dots">
                <div className="terminal-dot" style={{ background: "#FF5063" }} />
                <div className="terminal-dot" style={{ background: "#F59E0B" }} />
                <div className="terminal-dot" style={{ background: "#10B981" }} />
                <span className="font-mono" style={{ marginLeft: 8, fontSize: 11, color: "#3D5468" }}>
                  artha-ai · gaurav711/Artha_ai · HuggingFace Spaces
                </span>
              </div>
              <div ref={termRef} style={{ height: 300, overflow: "hidden", padding: "16px 20px", fontFamily: "'JetBrains Mono', monospace", fontSize: 12.5, lineHeight: 1.7 }}>
                {visibleLines.map((l, i) => (
                  <div key={i} style={{ color: l.color, minHeight: "1.7em" }}>
                    {l.text}
                    {l.typing && <span className="animate-caret" style={{ display: "inline-block", width: 7, height: 14, background: "#F59E0B", marginLeft: 2, verticalAlign: "text-bottom" }} />}
                  </div>
                ))}
                {!isTyping && (
                  <div style={{ color: "#3D5468" }}>
                    $ <span className="animate-caret" style={{ display: "inline-block", width: 7, height: 14, background: "#F59E0B", verticalAlign: "text-bottom" }} />
                  </div>
                )}
              </div>
            </div>

            {/* Stats */}
            <div ref={statsRef} className="anim-fade-up-d3" style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12, maxWidth: 560, marginBottom: 36 }}>
              {STATS.map((s, i) => <StatCard key={i} stat={s} inView={statsInView} />)}
            </div>

            {/* CTAs */}
            <div className="anim-fade-up-d3" style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center" }}>
              <Link href="/fraud" className="btn-primary">
                Explore FraudSense <ChevronRight size={15} />
              </Link>
              <Link href="/platform" className="btn-ghost">
                <FileText size={15} />
                Live Platform
              </Link>
              <a href="https://github.com/Gaurav711cgu/Aarthaa_ai" target="_blank" rel="noopener noreferrer" className="btn-ghost">
                <GitBranch size={15} />
                GitHub
              </a>
            </div>
          </div>
        </section>

        {/* ── MODULES OVERVIEW ──────────────────────────────────────────── */}
        <section style={{ padding: "80px 0", background: "#0A1018", borderTop: "1px solid #1C2D3E", borderBottom: "1px solid #1C2D3E" }}>
          <div className="section-container">
            <h2 style={{ fontWeight: 600, fontSize: 28, color: "#E8F0F8", marginBottom: 8 }}>Three Core Modules</h2>
            <p style={{ color: "#7A94AE", fontSize: 15, marginBottom: 36, maxWidth: 560 }}>
              Each module has a dedicated route, its own FastAPI router, rate limiter, and
              Prometheus metrics — fully decoupled via Kafka.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
              {[
                {
                  href: "/fraud", color: "#F59E0B",
                  title: "FraudSense", tag: "RF + IsolationForest",
                  desc: "Scores transactions in under 50ms with SHAP explainability, SHA-256 model signing, and automatic background retraining.",
                  items: ["RandomForest + IsolationForest ensemble", "SHAP feature attribution per transaction", "Kafka publish — zero blocking on scoring"],
                },
                {
                  href: "/compliance", color: "#8B5CF6",
                  title: "RegGuard", tag: "Compliance RAG Agent",
                  desc: "Validates transactions against RBI, FEMA, and PMLA regulations using pgvector similarity search and Groq LLaMA-3.1.",
                  items: ["pgvector cosine similarity — 768-dim embeddings", "Groq LLaMA-3.1 for compliance verdict", "5 req/min rate limiting per client IP"],
                },
                {
                  href: "/finlens", color: "#10B981",
                  title: "FinLens", tag: "Text-to-SQL Auditor",
                  desc: "Converts natural language queries into parameterized SQL against uploaded bank statements. Zero SQL injection surface.",
                  items: ["Natural language to parameterized SQL", "Multi-format: CSV, pipe-delimited, PDF text", "PostgreSQL primary + SQLite local fallback"],
                },
              ].map(m => (
                <Link key={m.href} href={m.href} style={{ textDecoration: "none" }}>
                  <div className="research-card" style={{ borderTop: `2px solid ${m.color}`, height: "100%", cursor: "pointer" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                      <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 17, color: "#E8F0F8" }}>{m.title}</span>
                      <span className="font-mono" style={{ fontSize: 10, color: m.color, background: `${m.color}15`, border: `1px solid ${m.color}30`, padding: "2px 8px", borderRadius: 4 }}>{m.tag}</span>
                    </div>
                    <p style={{ fontSize: 13, color: "#7A94AE", lineHeight: 1.7, marginBottom: 16 }}>{m.desc}</p>
                    <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 7 }}>
                      {m.items.map((it, i) => (
                        <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: 12, color: "#7A94AE" }}>
                          <span style={{ color: m.color, marginTop: 2, flexShrink: 0, fontSize: 16, lineHeight: 1 }}>&#x2192;</span>
                          {it}
                        </li>
                      ))}
                    </ul>
                    <div style={{ marginTop: 20, fontSize: 12, color: m.color, fontWeight: 600, display: "flex", alignItems: "center", gap: 5 }}>
                      View module <span style={{ fontSize: 16 }}>&#x2192;</span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* ── RESEARCH & BLOGS ─────────────────────────────────────────── */}
        <section id="blogs" style={{ padding: "100px 0", background: "#060A0E", borderTop: "1px solid #1C2D3E" }}>
          <div className="section-container">
            <div style={{ textAlign: "center", marginBottom: "3rem" }}>
              <span className="section-label">Engineering Publications</span>
              <h2 style={{ fontWeight: 700, fontSize: 32, color: "#E8F0F8", marginTop: 8, marginBottom: 12 }}>
                Detailed Research & Blogs
              </h2>
              <p style={{ color: "#7A94AE", fontSize: 16, maxWidth: 600, margin: "0 auto" }}>
                Deep dives into real-time transaction scoring mechanics, high-performance RAG pipelines, and financial regulatory architectures.
              </p>
            </div>

            <div style={{ maxWidth: "900px", margin: "0 auto" }}>
              {blogs.map(b => (
                <BlogSection key={b.id} blog={b} />
              ))}
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
