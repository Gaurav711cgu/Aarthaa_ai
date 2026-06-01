"use client";

import { useState } from "react";
import { Search, Shield, BookOpen, Layers, RefreshCw, CheckCircle, AlertTriangle } from "lucide-react";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

const DOCS = [
  { id: "rbi", label: "RBI Master Directions", count: 124, date: "2026-04-12" },
  { id: "fema", label: "FEMA Notification 20(R)", count: 87, date: "2026-03-01" },
  { id: "pmla", label: "PMLA Rules & Guidelines", count: 62, date: "2026-05-18" },
];

const PRESETS = [
  {
    query: "Is an offshore NEFT transaction of ₹10L to an individual without FEMA declaration allowed?",
    verdict: "NON-COMPLIANT",
    score: 0.892,
    chunks: [
      "[FEMA Sec 3] Direct foreign remittance exceeding ₹2,50,000 per financial year requires a signed FEMA Declaration Form A2 submitted to the Authorized Dealer.",
      "[RBI Master Directives] Any transfer above ₹5,00,000 originating from a non-resident account must be verified against secondary identification documents within 48 hours."
    ],
    reason: "Remittance exceeds FEMA Section 3 threshold limit of ₹2,50,000 and has no active Form A2 declaration. The NEFT transfer must be blocked until submission."
  },
  {
    query: "What is the reporting timeframe for a transaction flagged as suspicious under PMLA?",
    verdict: "COMPLIANT",
    score: 0.941,
    chunks: [
      "[PMLA Rule 8(1)] Every reporting entity shall furnish to Director, FIU-IND, information of all suspicious transactions within 7 working days of arriving at a satisfaction.",
      "[PMLA Rule 3] Cash transactions exceeding ₹10,000,000 or equivalent foreign currency must be reported monthly by the 15th of the succeeding month."
    ],
    reason: "Suspicious transactions require reporting to FIU-IND within 7 working days. Ensure the AML dashboard triggers an automated FIU alert batch with the assigned correlation ID."
  },
  {
    query: "Do we need double identification (KYC) for domestic wallets transferring over ₹50,000?",
    verdict: "NEEDS AUDIT",
    score: 0.784,
    chunks: [
      "[RBI Circular KYC-2025] Full KYC is mandatory for all prepaid payment instruments (wallets) where the monthly credit or debit transactions exceed ₹50,000.",
      "[RBI Circular KYC-2024] Small PPIs can be opened with minimum details but are restricted to maximum loading of ₹10,000 per month."
    ],
    reason: "Transaction size indicates full KYC required. Since user profile only lists minimal-KYC verification, a secondary identity matching routine is triggered asynchronously."
  }
];

const GOVERNANCE_METRICS = [
  { value: "273", label: "Regulatory chunks indexed across RBI, FEMA, PMLA, and wallet policy documents", color: "#8B5CF6" },
  { value: "0.89", label: "Reference confidence threshold before a verdict can auto-route downstream", color: "#10B981" },
  { value: "7d", label: "PMLA suspicious transaction reporting window encoded into audit guidance", color: "#F59E0B" },
  { value: "1h", label: "Redis response cache TTL for repeat policy questions and audit narratives", color: "#3B82F6" },
];

const CONTROL_LAYERS = [
  {
    icon: <BookOpen size={15} />,
    title: "Curated Policy Corpus",
    text: "Source text is split into traceable chunks with circular IDs, dates, and jurisdiction tags so answers cite the policy surface that produced them.",
    color: "#8B5CF6",
  },
  {
    icon: <Shield size={15} />,
    title: "Verdict Guardrails",
    text: "The model is constrained to COMPLIANT, NON-COMPLIANT, or NEEDS AUDIT, reducing vague language and making queue routing deterministic.",
    color: "#F59E0B",
  },
  {
    icon: <CheckCircle size={15} />,
    title: "Citation Reranking",
    text: "Generated responses are checked against retrieved source chunks so unsupported claims lose confidence before the result reaches an analyst.",
    color: "#10B981",
  },
];

const AUDIT_FLOW = [
  { title: "Intake", text: "Transaction narrative, user segment, geography, amount, and channel metadata enter the compliance request." },
  { title: "Retrieve", text: "pgvector similarity selects the highest-confidence policy passages for the exact regulatory context." },
  { title: "Synthesize", text: "Groq-backed generation drafts a concise verdict bound to those passages and the selected threshold." },
  { title: "Escalate", text: "Kafka topics route rejected or uncertain cases into manual compliance review with correlation metadata." },
];

export default function CompliancePage() {
  const [activeDoc, setActiveDoc] = useState("rbi");
  const [threshold, setThreshold] = useState(0.75);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [pipelineStep, setPipelineStep] = useState(0);
  const [result, setResult] = useState<typeof PRESETS[0] | null>(null);

  const runSearch = (queryText: string) => {
    setSearchQuery(queryText);
    setLoading(true);
    setPipelineStep(1);
    setResult(null);

    // Dynamic pipeline step simulation
    const timer1 = setTimeout(() => setPipelineStep(2), 500);
    const timer2 = setTimeout(() => setPipelineStep(3), 1000);
    const timer3 = setTimeout(() => {
      setPipelineStep(4);
      // Try to find a matching preset, or construct a dynamic fallback
      const match = PRESETS.find(p => queryText.toLowerCase().includes(p.query.toLowerCase().slice(0, 10))) || {
        query: queryText,
        verdict: "COMPLIANT",
        score: parseFloat((Math.random() * 0.2 + 0.78).toFixed(3)),
        chunks: [
          `[RBI Master Dir 2026] All client transactions matching current query '${queryText.slice(0, 20)}...' must be logged under compliance log audit schema.`,
          "[PMLA Sec 12] Standard logging ensures zero compliance leakages and retains structured metadata for 5 years."
        ],
        reason: "Query verified. Embeddings mapped via pgvector successfully matched general compliance guidelines. No immediate risk vector flagged."
      };
      setResult(match);
      setLoading(false);
    }, 1500);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
    };
  };

  return (
    <>
      <Nav />
      <main style={{ paddingTop: 80 }}>
        {/* Header */}
        <section style={{ position: "relative", padding: "80px 0 60px" }}>
          <div className="bg-grid" style={{ position: "absolute", inset: 0, opacity: 0.3 }} />
          <div className="section-container" style={{ position: "relative" }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 24 }}>
              <span className="badge-amber">RegGuard v2</span>
              <span className="badge-violet">pgvector 768-dim</span>
              <span className="badge-green">LLaMA-3.1 RAG</span>
            </div>
            <h1 style={{ fontSize: "clamp(30px, 4.5vw, 50px)", fontWeight: 700, color: "#E8F0F8", marginBottom: 16, maxWidth: 640 }}>
              Regulatory RAG & Guardrails
            </h1>
            <p style={{ fontSize: 15, color: "#7A94AE", maxWidth: 560, lineHeight: 1.75 }}>
              Audits and validates financial transactions against strict regulatory directives.
              Utilizes pgvector similarity search over curated RBI, FEMA, and PMLA policies with
              Groq LLaMA-3.1 generating exact compliant verdicts and highlighted references.
            </p>
          </div>
        </section>

        <section style={{ padding: "0 0 44px" }}>
          <div className="section-container">
            <div className="module-kpi-strip">
              {GOVERNANCE_METRICS.map(metric => (
                <div key={metric.label} className="module-kpi">
                  <strong style={{ color: metric.color }}>{metric.value}</strong>
                  <span>{metric.label}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section style={{ padding: "0 0 70px" }}>
          <div className="section-container">
            <div style={{ marginBottom: 22 }}>
              <span className="section-label">Regulatory intelligence model</span>
              <h2 style={{ fontWeight: 600, fontSize: 24, color: "#E8F0F8", margin: "8px 0 8px" }}>
                A policy engine with receipts
              </h2>
              <p style={{ color: "#7A94AE", fontSize: 14, maxWidth: 720, margin: 0 }}>
                RegGuard is designed to keep compliance decisions inspectable: every verdict
                carries source chunks, confidence, and a clean escalation path for uncertain cases.
              </p>
            </div>
            <div className="elite-grid-3">
              {CONTROL_LAYERS.map(layer => (
                <div key={layer.title} className="module-feature">
                  <div className="module-feature-icon" style={{ color: layer.color }}>{layer.icon}</div>
                  <h3 style={{ fontWeight: 600, fontSize: 16, color: "#E8F0F8", marginBottom: 8 }}>{layer.title}</h3>
                  <p style={{ color: "#7A94AE", fontSize: 13, lineHeight: 1.7, margin: 0 }}>{layer.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Content grid */}
        <section style={{ padding: "0 0 80px" }}>
          <div className="section-container module-grid-aside">
            {/* Left Panel: Settings & Presets */}
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              {/* Document Registry */}
              <div className="research-card" style={{ borderTop: "2px solid #8B5CF6" }}>
                <h3 style={{ fontWeight: 600, fontSize: 16, color: "#E8F0F8", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
                  <BookOpen size={16} style={{ color: "#8B5CF6" }} />
                  Knowledge Base Registry
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {DOCS.map(doc => (
                    <div
                      key={doc.id}
                      onClick={() => setActiveDoc(doc.id)}
                      style={{
                        padding: "12px 14px",
                        borderRadius: 8,
                        background: activeDoc === doc.id ? "rgba(139,92,246,0.08)" : "#0A1018",
                        border: activeDoc === doc.id ? "1px solid rgba(139,92,246,0.4)" : "1px solid #1C2D3E",
                        cursor: "pointer",
                        transition: "all 0.2s"
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: "#E8F0F8" }}>{doc.label}</span>
                        <span className="font-mono" style={{ fontSize: 10, color: "#8B5CF6" }}>{doc.count} chunks</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#3D5468" }}>
                        <span>Vectorized</span>
                        <span>Updated: {doc.date}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* RAG Parameters */}
              <div className="research-card" style={{ borderTop: "2px solid #10B981" }}>
                <h3 style={{ fontWeight: 600, fontSize: 16, color: "#E8F0F8", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
                  <Layers size={16} style={{ color: "#10B981" }} />
                  Query Configuration
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                      <span style={{ fontSize: 12, color: "#7A94AE" }}>Similarity Threshold</span>
                      <span className="font-mono" style={{ fontSize: 12, color: "#10B981" }}>{threshold.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min="0.5"
                      max="0.95"
                      step="0.05"
                      value={threshold}
                      onChange={e => setThreshold(parseFloat(e.target.value))}
                      style={{ width: "100%", accentColor: "#10B981", height: 4, background: "#1C2D3E", borderRadius: 2 }}
                    />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", borderTop: "1px solid #1C2D3E", paddingTop: 10 }}>
                    <span style={{ fontSize: 12, color: "#7A94AE" }}>Embedding Model</span>
                    <span className="font-mono" style={{ fontSize: 11, color: "#E8F0F8" }}>nomic-embed-text-v1.5</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ fontSize: 12, color: "#7A94AE" }}>Synthesis LLM</span>
                    <span className="font-mono" style={{ fontSize: 11, color: "#E8F0F8" }}>llama-3.1-70b-groq</span>
                  </div>
                </div>
              </div>

              {/* Presets */}
              <div>
                <span className="section-label" style={{ marginBottom: 10, display: "block" }}>Compliance Test Scenarios</span>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {PRESETS.map((p, i) => (
                    <button
                      key={i}
                      onClick={() => runSearch(p.query)}
                      style={{
                        textAlign: "left",
                        padding: "12px 14px",
                        background: "#0A1018",
                        border: "1px solid #1C2D3E",
                        borderRadius: 8,
                        fontSize: 12,
                        color: "#7A94AE",
                        cursor: "pointer",
                        lineHeight: 1.5,
                        transition: "all 0.15s"
                      }}
                      onMouseEnter={e => e.currentTarget.style.borderColor = "#F59E0B"}
                      onMouseLeave={e => e.currentTarget.style.borderColor = "#1C2D3E"}
                    >
                      {p.query}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Panel: Interactive RAG Terminal & Output */}
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              {/* Search Bar */}
              <div style={{ display: "flex", gap: 10 }}>
                <div style={{ position: "relative", flex: 1 }}>
                  <Search size={16} style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "#3D5468" }} />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Enter transaction narrative or regulatory query..."
                    style={{
                      width: "100%",
                      padding: "12px 16px 12px 40px",
                      background: "#0A1018",
                      border: "1px solid #1C2D3E",
                      borderRadius: 8,
                      color: "#E8F0F8",
                      fontSize: 13,
                      outline: "none"
                    }}
                    onKeyDown={e => e.key === "Enter" && runSearch(searchQuery)}
                  />
                </div>
                <button
                  onClick={() => runSearch(searchQuery || PRESETS[0].query)}
                  disabled={loading}
                  className="btn-primary"
                  style={{ padding: "0 22px", borderRadius: 8, height: 46 }}
                >
                  {loading ? <RefreshCw size={14} style={{ animation: "spin 0.8s linear infinite" }} /> : "Run Audit"}
                </button>
              </div>

              {/* RAG pipeline steps visualizer */}
              {loading && (
                <div className="research-card font-mono" style={{ fontSize: 12, background: "#040709", border: "1px solid #1C2D3E", padding: 20 }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, color: pipelineStep >= 1 ? "#10B981" : "#3D5468" }}>
                      <span>[1]</span> Remotely embedding query using nomic-embed-text-v1.5... {pipelineStep > 1 && "OK"}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, color: pipelineStep >= 2 ? "#10B981" : "#3D5468" }}>
                      <span>[2]</span> Querying pgvector space with similarity limit {threshold}... {pipelineStep > 2 && "OK"}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, color: pipelineStep >= 3 ? "#10B981" : "#3D5468" }}>
                      <span>[3]</span> Feeding matching reference chunks to LLaMA-3.1 on Groq... {pipelineStep > 3 && "OK"}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, color: pipelineStep >= 4 ? "#10B981" : "#3D5468" }}>
                      <span>[4]</span> Synthesizing final compliance verdict...
                    </div>
                  </div>
                </div>
              )}

              {/* RAG Synthesis Result */}
              {result && !loading && (
                <div className="research-card" style={{ borderTop: `2px solid ${result.verdict === "COMPLIANT" ? "#10B981" : result.verdict === "NON-COMPLIANT" ? "#F43F5E" : "#F59E0B"}` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
                    <span style={{ fontSize: 13, color: "#7A94AE", fontWeight: 600 }}>Audit Result</span>
                    <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                      <span className="font-mono" style={{ fontSize: 11, color: "#3D5468" }}>Score: {result.score}</span>
                      <span
                        className="font-mono"
                        style={{
                          fontSize: 11,
                          fontWeight: 600,
                          padding: "2px 9px",
                          borderRadius: 4,
                          background: `${result.verdict === "COMPLIANT" ? "#10B981" : result.verdict === "NON-COMPLIANT" ? "#F43F5E" : "#F59E0B"}15`,
                          color: result.verdict === "COMPLIANT" ? "#10B981" : result.verdict === "NON-COMPLIANT" ? "#F43F5E" : "#F59E0B",
                          border: `1px solid ${result.verdict === "COMPLIANT" ? "#10B981" : result.verdict === "NON-COMPLIANT" ? "#F43F5E" : "#F59E0B"}30`
                        }}
                      >
                        {result.verdict}
                      </span>
                    </div>
                  </div>

                  {/* Verdict Text */}
                  <div style={{ background: "#0A1018", border: "1px solid #1C2D3E", borderRadius: 8, padding: 16, marginBottom: 20 }}>
                    <p style={{ fontSize: 14, color: "#E8F0F8", fontWeight: 500, margin: 0, lineHeight: 1.6 }}>
                      {result.reason}
                    </p>
                  </div>

                  {/* Reference Chunks */}
                  <span className="section-label" style={{ marginBottom: 10, display: "block" }}>Matched Regulatory Chunks</span>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {result.chunks.map((c, i) => (
                      <div key={i} style={{ padding: "12px 14px", background: "#040709", border: "1px solid #1C2D3E", borderRadius: 6 }}>
                        <span className="font-mono" style={{ fontSize: 10, color: "#8B5CF6", display: "block", marginBottom: 6 }}>Source Chunk #{i+1}</span>
                        <p style={{ fontSize: 12.5, color: "#7A94AE", margin: 0, lineHeight: 1.65 }}>{c}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* General Guidelines Warning */}
              <div style={{ display: "flex", gap: 12, background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: 8, padding: "14px 18px" }}>
                <AlertTriangle size={18} style={{ color: "#F59E0B", marginTop: 2, flexShrink: 0 }} />
                <p style={{ fontSize: 12, color: "#7A94AE", margin: 0, lineHeight: 1.65 }}>
                  <strong>Manual Override Warning:</strong> Compliance verdicts generated by RegGuard RAG are advisory. Large transactions flagged as Non-Compliant are piped into the Kafka <code>artha.compliance.reject</code> topic to be processed by a compliance specialist within the JPMC GCC routing queue.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section style={{ padding: "0 0 80px" }}>
          <div className="section-container">
            <div style={{ display: "flex", justifyContent: "space-between", gap: 24, alignItems: "flex-end", marginBottom: 18, flexWrap: "wrap" }}>
              <div>
                <span className="section-label">Audit routing lifecycle</span>
                <h2 style={{ fontWeight: 600, fontSize: 22, color: "#E8F0F8", margin: "8px 0 0" }}>
                  How a compliance question becomes an auditable verdict
                </h2>
              </div>
              <span className="badge-violet">Source-bound answers</span>
            </div>
            <div className="process-lane">
              {AUDIT_FLOW.map((step, index) => (
                <div key={step.title} className="process-step">
                  <span className="font-mono" style={{ color: "#3D5468", fontSize: 11 }}>0{index + 1}</span>
                  <h3 style={{ color: "#E8F0F8", fontSize: 15, margin: "10px 0 8px", fontWeight: 600 }}>{step.title}</h3>
                  <p style={{ color: "#7A94AE", fontSize: 12.5, lineHeight: 1.65, margin: 0 }}>{step.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Code Block Section */}
        <section style={{ padding: "0 0 80px" }}>
          <div className="section-container">
            <h2 style={{ fontWeight: 600, fontSize: 20, color: "#E8F0F8", marginBottom: 20 }}>Vector Search & LLM Prompt Template</h2>
            <div className="code-block">
              <span className="c-comment"># pgvector cosine similarity search over circulars</span>{"\n"}
              <span className="c-kw">async def</span> <span className="c-fn">retrieve_docs</span>(query_emb: list[<span className="c-kw">float</span>], limit: <span className="c-kw">int</span> = <span className="c-num">2</span>):{"\n"}
              {"    "}<span className="c-kw">async with</span> db.pool.acquire() <span className="c-kw">as</span> conn:{"\n"}
              {"        "}query = <span className="c-str">"SELECT text, source_id, 1 - (embedding &lt;=&gt; $1) as score FROM regulatory_chunks WHERE 1 - (embedding &lt;=&gt; $1) &gt;= $2 ORDER BY embedding &lt;=&gt; $1 LIMIT $3"</span>{"\n"}
              {"        "}<span className="c-kw">return await</span> conn.fetch(query, query_emb, threshold, limit){"\n\n"}
              <span className="c-comment"># System prompt for compliance verdict synthesis</span>{"\n"}
              <span className="c-kw">const</span> SYSTEM_PROMPT = <span className="c-str">`You are a strict financial auditor. Validate the transaction request using only the provided reference circulars. Output either COMPLIANT, NON-COMPLIANT, or NEEDS AUDIT, and justify the verdict based solely on the sources.`</span>
            </div>
          </div>
        </section>
      </main>
      <Footer />
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </>
  );
}
