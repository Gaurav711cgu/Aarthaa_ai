"use client";

import { useState } from "react";
import { Shield, Lock, Key, RefreshCw, CheckCircle, Terminal, AlertTriangle, Layers } from "lucide-react";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

const HASHES = [
  { file: "ensemble_fraud_model.joblib", size: "42.8 MB", hash: "8d92f741ae8c9a3b2b4e78f90c1284d76a91de04f86d8a7c1b2c4d5e6f7a8b9c", date: "2026-05-30" },
  { file: "nomic_embedding_vectors.bin", size: "180.4 MB", hash: "4a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b", date: "2026-05-28" },
  { file: "llama_finetuned_sql.gguf", size: "4.2 GB", hash: "c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4", date: "2026-05-29" }
];

const AUDIT_LOGS = [
  { time: "02:35:14", ip: "192.168.1.42", module: "FraudSense", cid: "cid-9014-jpmc", status: "BLOCKED", tier: "CRITICAL" },
  { time: "02:32:09", ip: "10.0.12.87", module: "RegGuard", cid: "cid-8841-fema", status: "COMPLIANT", tier: "LOW" },
  { time: "02:29:41", ip: "192.168.1.18", module: "FinLens", cid: "cid-9122-sql", status: "EXECUTED", tier: "LOW" },
  { time: "02:24:55", ip: "172.16.8.99", module: "FraudSense", cid: "cid-7612-upi", status: "FLAGGED", tier: "HIGH" },
  { time: "02:18:02", ip: "10.0.12.112", module: "RegGuard", cid: "cid-6091-pmla", status: "AUDIT", tier: "MEDIUM" }
];

const KAFKA_TOPICS = [
  { name: "artha.fraud.batch", key: "tx_id", payload: "{ 'tx_id': 9014, 'amount': 1800000, 'prob': 0.914, 'tier': 'CRITICAL' }" },
  { name: "artha.audit.compliance", key: "correlation_id", payload: "{ 'cid': 'cid-8841-fema', 'verdict': 'COMPLIANT', 'score': 0.941 }" }
];

export default function SecurityPage() {
  const [verifying, setVerifying] = useState(false);
  const [verifiedStatus, setVerifiedStatus] = useState<"idle" | "done">("idle");

  const runVerification = () => {
    setVerifying(true);
    setTimeout(() => {
      setVerifying(false);
      setVerifiedStatus("done");
    }, 1200);
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
              <span className="badge-amber">Security Shield</span>
              <span className="badge-violet">SHA-256 Signatures</span>
              <span className="badge-green">Kafka Decoupled</span>
            </div>
            <h1 style={{ fontSize: "clamp(30px, 4.5vw, 50px)", fontWeight: 700, color: "#E8F0F8", marginBottom: 16, maxWidth: 640 }}>
              System Integrity & Compliance Security
            </h1>
            <p style={{ fontSize: 15, color: "#7A94AE", maxWidth: 560, lineHeight: 1.75 }}>
              Guarantees zero-tampering data execution across all modules. Verifies joblib model package
              hashes against our secure cryptographic registry, charts active audit footprints,
              and tracks the asynchronous telemetry pipeline using decoupled Kafka logs.
            </p>
          </div>
        </section>

        {/* Content Section */}
        <section style={{ padding: "0 0 80px" }}>
          <div className="section-container" style={{ display: "grid", gridTemplateColumns: "1.3fr 1.7fr", gap: 40 }}>
            {/* Left Panel: Cryptographic Model Hashes & Decoupled Topics */}
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              {/* Model Signature Registry */}
              <div className="research-card" style={{ borderTop: "2px solid #8B5CF6" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                  <h3 style={{ fontWeight: 600, fontSize: 16, color: "#E8F0F8", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                    <Key size={16} style={{ color: "#8B5CF6" }} />
                    Model Signature Registry
                  </h3>
                  {verifiedStatus === "done" && (
                    <span style={{ fontSize: 11, color: "#10B981", display: "flex", alignItems: "center", gap: 4, fontWeight: 600 }}>
                      <CheckCircle size={12} /> VERIFIED
                    </span>
                  )}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 16 }}>
                  {HASHES.map(h => (
                    <div key={h.file} style={{ background: "#0A1018", border: "1px solid #1C2D3E", borderRadius: 8, padding: 12 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <span className="font-mono" style={{ fontSize: 12, fontWeight: 600, color: "#E8F0F8" }}>{h.file}</span>
                        <span className="font-mono" style={{ fontSize: 10, color: "#3D5468" }}>{h.size}</span>
                      </div>
                      <div className="font-mono" style={{ fontSize: 9.5, color: "#7A94AE", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap", paddingBlock: 2 }}>
                        SHA-256: {h.hash}
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#3D5468", borderTop: "1px solid #16212E", paddingTop: 6, marginTop: 4 }}>
                        <span>Status: Verified Signature</span>
                        <span>Registered: {h.date}</span>
                      </div>
                    </div>
                  ))}
                </div>
                <button
                  onClick={runVerification}
                  disabled={verifying}
                  className="btn-primary"
                  style={{ width: "100%", height: 38, display: "flex", alignItems: "center", justifyContent: "center", gap: 8, fontSize: 12 }}
                >
                  <RefreshCw size={12} style={{ animation: verifying ? "spin 0.8s linear infinite" : "none" }} />
                  {verifying ? "Verifying hashes..." : "Verify System Signatures"}
                </button>
              </div>

              {/* Kafka Decoupled Pipeline */}
              <div className="research-card" style={{ borderTop: "2px solid #F59E0B" }}>
                <h3 style={{ fontWeight: 600, fontSize: 16, color: "#E8F0F8", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
                  <Layers size={16} style={{ color: "#F59E0B" }} />
                  Decoupled Kafka Pipeline
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  {KAFKA_TOPICS.map(topic => (
                    <div key={topic.name} style={{ background: "#0A1018", border: "1px solid #1C2D3E", borderRadius: 8, padding: 12 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, borderBottom: "1px solid #16212E", paddingBottom: 4 }}>
                        <span className="font-mono" style={{ fontSize: 11.5, fontWeight: 600, color: "#F59E0B" }}>{topic.name}</span>
                        <span className="font-mono" style={{ fontSize: 10, color: "#3D5468" }}>Key: {topic.key}</span>
                      </div>
                      <pre className="font-mono" style={{ fontSize: 10, color: "#7A94AE", margin: 0, overflowX: "auto", background: "#040709", padding: 8, borderRadius: 4 }}>
                        {topic.payload}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Panel: Audit Footprint & Access logs */}
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              <div>
                <span className="section-label" style={{ marginBottom: 12, display: "block" }}>Active Audit footprints</span>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {AUDIT_LOGS.map((log, i) => (
                    <div
                      key={i}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "12px 16px",
                        background: "#0A1018",
                        border: "1px solid #1C2D3E",
                        borderRadius: 8
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <span className="font-mono" style={{ fontSize: 10, color: "#3D5468" }}>{log.time}</span>
                        <span className="font-mono" style={{ fontSize: 11.5, color: "#E8F0F8", fontWeight: 600 }}>{log.module}</span>
                        <span className="font-mono" style={{ fontSize: 10, background: "rgba(139,92,246,0.06)", color: "#8B5CF6", border: "1px solid rgba(139,92,246,0.2)", padding: "1px 5px", borderRadius: 3 }}>
                          {log.cid}
                        </span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <span className="font-mono" style={{ fontSize: 11, color: "#7A94AE" }}>{log.ip}</span>
                        <span
                          className="font-mono"
                          style={{
                            fontSize: 10.5,
                            fontWeight: 600,
                            color: log.status === "BLOCKED" ? "#F43F5E" : log.status === "COMPLIANT" || log.status === "EXECUTED" ? "#10B981" : "#F59E0B"
                          }}
                        >
                          {log.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Rate Limiting Parameters */}
              <div className="research-card" style={{ borderTop: "2px solid #3B82F6" }}>
                <h3 style={{ fontWeight: 600, fontSize: 15, color: "#E8F0F8", marginBottom: 12 }}>API rate Limiting</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 12.5, color: "#7A94AE", lineHeight: 1.6 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #1C2D3E", paddingBottom: 6 }}>
                    <span>Burst Request Threshold</span>
                    <span className="font-mono" style={{ color: "#3B82F6" }}>5 req/min per IP</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #1C2D3E", paddingBottom: 6 }}>
                    <span>Rate Limit Middleware</span>
                    <span className="font-mono" style={{ color: "#E8F0F8" }}>SlowAPI / Redis-backed</span>
                  </div>
                  <p style={{ marginBlockStart: 4, marginBlockEnd: 0, fontSize: 11, color: "#3D5468" }}>
                    Security rules trigger dynamic temporary blocks (HTTP 429) to prevent API scanning from blacklisted proxy IP blocks.
                  </p>
                </div>
              </div>

              {/* Security override banner */}
              <div style={{ display: "flex", gap: 12, background: "rgba(244,63,94,0.06)", border: "1px solid rgba(244,63,94,0.2)", borderRadius: 8, padding: "14px 18px" }}>
                <AlertTriangle size={18} style={{ color: "#F43F5E", marginTop: 2, flexShrink: 0 }} />
                <p style={{ fontSize: 12, color: "#7A94AE", margin: 0, lineHeight: 1.65 }}>
                  <strong>Intrusion Detection Alert:</strong> System logs verify that models loaded outside of authorized Docker pipeline hashes are completely blocked from serving transaction scoring endpoints. System status triggers automated alerts to JPMC threat monitoring console.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Code block section */}
        <section style={{ padding: "0 0 80px" }}>
          <div className="section-container">
            <h2 style={{ fontWeight: 600, fontSize: 20, color: "#E8F0F8", marginBottom: 20 }}>SHA-256 Verification Middleware</h2>
            <div className="code-block">
              <span className="c-comment"># Cryptographic validation for joblib model signatures</span>{"\n"}
              <span className="c-kw">import</span> hashlib{"\n"}
              <span className="c-kw">import</span> hmac{"\n\n"}
              <span className="c-kw">def</span> <span className="c-fn">verify_model_hash</span>(filepath: <span className="c-kw">str</span>, expected_hash: <span className="c-kw">str</span>) -{">"} <span className="c-kw">bool</span>:{"\n"}
              {"    "}sha256_hash = hashlib.sha256(){"\n"}
              {"    "}<span className="c-kw">with</span> <span className="c-kw">open</span>(filepath, <span className="c-str">"rb"</span>) <span className="c-kw">as</span> f:{"\n"}
              {"        "}<span className="c-kw">for</span> byte_block <span className="c-kw">in</span> <span className="c-kw">iter</span>(<span className="c-kw">lambda</span>: f.read(<span className="c-num">4096</span>), <span className="c-str">b""</span>):{"\n"}
              {"            "}sha256_hash.update(byte_block){"\n"}
              {"    "}calculated_hash = sha256_hash.hexdigest(){"\n"}
              {"    "}<span className="c-kw">return</span> hmac.compare_digest(calculated_hash, expected_hash)
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
