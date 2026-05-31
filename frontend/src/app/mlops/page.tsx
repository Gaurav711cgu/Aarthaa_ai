"use client";

import { useState, useEffect, useRef } from "react";
import { Activity, Play, RefreshCw, Cpu, Layers, BarChart3, Terminal } from "lucide-react";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

const MODELS = [
  { id: "ensemble_v2_prod", name: "FraudSense Ensemble", type: "RF + IsoForest", status: "ACTIVE", version: "v2.4.1", drift: "PSI=0.08 (Stable)" },
  { id: "rag_embedding_v1", name: "RegGuard Vector Map", type: "pgvector nomic", status: "ACTIVE", version: "v1.2.0", drift: "Stable" },
  { id: "text2sql_fine_tuned", name: "FinLens Parser", type: "Fine-Tuned LLaMA", status: "ACTIVE", version: "v3.1.2", drift: "Stable" },
];

const METRICS = [
  { label: "Predictive Drift (PSI)", val: "0.082", target: "< 0.15", status: "STABLE", col: "#10B981" },
  { label: "Data Quality Score", val: "99.8%", target: "> 98%", status: "OPTIMAL", col: "#10B981" },
  { label: "Cache Hit Rate", val: "84.3%", target: "Dynamic", status: "OPTIMAL", col: "#8B5CF6" },
  { label: "P99 Serving Latency", val: "42 ms", target: "< 50ms", status: "GUARANTEED", col: "#F59E0B" }
];

const MOCK_TRAINING_LOGS = [
  "Fetching training data from data lake...",
  "Loading baseline dataset (N=485,020 samples)...",
  "Validating data schema and consistency checks...",
  "Running Random Forest Classifier ensemble training...",
  "Training epoch 1/5 [Loss: 0.281, Accuracy: 0.941]",
  "Training epoch 2/5 [Loss: 0.194, Accuracy: 0.963]",
  "Training epoch 3/5 [Loss: 0.125, Accuracy: 0.971]",
  "Training epoch 4/5 [Loss: 0.092, Accuracy: 0.974]",
  "Training epoch 5/5 [Loss: 0.081, Accuracy: 0.978]",
  "Evaluating model against test partition...",
  "Comparing model accuracy metrics: Baseline (97.1%) vs Candidate (97.8%)...",
  "Accuracy improvement detected. Validating model drift on Evidently...",
  "Drift evaluation: PSI=0.04 (Stable). Data Quality checks passed.",
  "Calculating model SHA-256 signature...",
  "Generated signature: 8d92f741ae8c9a3b2b4e78f90c1284d76a91de...",
  "Serializing model binary structure [joblib format]...",
  "Syncing model package to model registry...",
  "Deploying candidate package to Kubernetes prod cluster...",
  "Active router toggled successfully. Ensemble v2.5.0 serving traffic.",
  "Prometheus scrape endpoint successfully verified."
];

export default function MLOpsPage() {
  const [activeTab, setActiveTab] = useState<"models" | "drift">("models");
  const [training, setTraining] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [logIdx, setLogIdx] = useState(0);
  const consoleRef = useRef<HTMLDivElement>(null);

  const startRetraining = () => {
    if (training) return;
    setTraining(true);
    setLogs([]);
    setLogIdx(0);
  };

  useEffect(() => {
    if (!training) return;
    if (logIdx >= MOCK_TRAINING_LOGS.length) {
      setTraining(false);
      return;
    }
    const t = setTimeout(() => {
      setLogs(prev => [...prev, MOCK_TRAINING_LOGS[logIdx]]);
      setLogIdx(p => p + 1);
    }, 350);
    return () => clearTimeout(t);
  }, [training, logIdx]);

  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <>
      <Nav />
      <main style={{ paddingTop: 80 }}>
        {/* Header */}
        <section style={{ position: "relative", padding: "80px 0 60px" }}>
          <div className="bg-grid" style={{ position: "absolute", inset: 0, opacity: 0.3 }} />
          <div className="section-container" style={{ position: "relative" }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 24 }}>
              <span className="badge-amber">MLOps Control</span>
              <span className="badge-violet">Evidently AI Drift</span>
              <span className="badge-green">SHA-256 Verified</span>
            </div>
            <h1 style={{ fontSize: "clamp(30px, 4.5vw, 50px)", fontWeight: 700, color: "#E8F0F8", marginBottom: 16, maxWidth: 640 }}>
              MLOps & Model Registry
            </h1>
            <p style={{ fontSize: 15, color: "#7A94AE", maxWidth: 560, lineHeight: 1.75 }}>
              Orchestrates training cycles, drift metrics, and continuous deployment workflows.
              Monitors and profiles operational drift using Evidently AI metrics, verifies model package
              hashes, and manages live rollouts securely across Kubernetes pods.
            </p>
          </div>
        </section>

        {/* Main Content Grid */}
        <section style={{ padding: "0 0 80px" }}>
          <div className="section-container" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 40 }}>
            {/* Left: Model Registry Table & Trigger Training */}
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              {/* Tab Selector */}
              <div style={{ display: "flex", borderBottom: "1px solid #1C2D3E", gap: 20, paddingBottom: 10 }}>
                {["models", "drift"].map(t => (
                  <button
                    key={t}
                    onClick={() => setActiveTab(t as "models" | "drift")}
                    style={{
                      background: "none",
                      border: "none",
                      color: activeTab === t ? "#F59E0B" : "#7A94AE",
                      fontSize: 14,
                      fontWeight: 600,
                      cursor: "pointer",
                      paddingBottom: 6,
                      borderBottom: activeTab === t ? "2px solid #F59E0B" : "2px solid transparent",
                      transition: "all 0.15s",
                      textTransform: "uppercase",
                      letterSpacing: "0.05em"
                    }}
                  >
                    {t === "models" ? "Active Models" : "Evidently Drift Metrics"}
                  </button>
                ))}
              </div>

              {activeTab === "models" ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  {MODELS.map(m => (
                    <div key={m.id} className="research-card" style={{ borderTop: "2px solid #8B5CF6" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                        <div>
                          <span style={{ fontSize: 14, fontWeight: 600, color: "#E8F0F8" }}>{m.name}</span>
                          <span className="font-mono" style={{ fontSize: 10.5, color: "#8B5CF6", display: "block", marginTop: 2 }}>{m.type}</span>
                        </div>
                        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                          <span className="font-mono" style={{ fontSize: 10, background: "rgba(16,185,129,0.08)", color: "#10B981", border: "1px solid rgba(16,185,129,0.2)", padding: "1px 6px", borderRadius: 3 }}>
                            {m.status}
                          </span>
                          <span className="font-mono" style={{ fontSize: 10, color: "#7A94AE" }}>{m.version}</span>
                        </div>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#3D5468", borderTop: "1px solid #1C2D3E", paddingTop: 8 }}>
                        <span>Real-time Monitoring</span>
                        <span className="font-mono" style={{ color: "#10B981" }}>{m.drift}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {METRICS.map(m => (
                    <div key={m.label} style={{ background: "#0A1018", border: "1px solid #1C2D3E", borderRadius: 8, padding: "14px 18px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <span style={{ fontSize: 13, color: "#E8F0F8", fontWeight: 500 }}>{m.label}</span>
                        <div style={{ display: "flex", gap: 10, fontSize: 11, color: "#3D5468", marginTop: 2 }}>
                          <span>Target: {m.target}</span>
                        </div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <span className="font-mono" style={{ fontSize: 16, fontWeight: 700, color: m.col }}>{m.val}</span>
                        <span className="font-mono" style={{ display: "block", fontSize: 9, color: m.col, letterSpacing: "0.08em", marginTop: 2 }}>{m.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Retraining Card */}
              <div className="research-card" style={{ borderTop: "2px solid #F59E0B", marginTop: 10 }}>
                <h3 style={{ fontWeight: 600, fontSize: 16, color: "#E8F0F8", marginBottom: 10, display: "flex", alignItems: "center", gap: 8 }}>
                  <Cpu size={16} style={{ color: "#F59E0B" }} />
                  Continuous Training Pipeline
                </h3>
                <p style={{ fontSize: 12.5, color: "#7A94AE", lineHeight: 1.6, marginBottom: 16 }}>
                  Trigger a dynamic retraining execution of the core FraudSense random forest ensemble classifier utilizing the latest drift window parameters.
                </p>
                <button
                  onClick={startRetraining}
                  disabled={training}
                  className="btn-primary"
                  style={{ width: "100%", height: 42, display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}
                >
                  <RefreshCw size={13} style={{ animation: training ? "spin 0.8s linear infinite" : "none" }} />
                  {training ? "Running Pipeline..." : "Trigger Model Retraining"}
                </button>
              </div>
            </div>

            {/* Right: Live Training Console / Logs */}
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                <span className="section-label" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <Terminal size={12} />
                  MLOps Pipeline Terminal
                </span>
                <span className="font-mono" style={{ fontSize: 10, color: training ? "#F59E0B" : "#3D5468" }}>
                  {training ? "RUNNING" : "STANDBY"}
                </span>
              </div>

              {/* Console window */}
              <div
                style={{
                  background: "#040709",
                  border: "1px solid #1C2D3E",
                  borderRadius: 10,
                  height: 380,
                  overflowY: "auto",
                  padding: "16px 20px",
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 12,
                  lineHeight: 1.8,
                  color: "#7A94AE"
                }}
                ref={consoleRef}
              >
                {logs.map((log, index) => (
                  <div key={index} style={{ color: log.includes("Error") ? "#F43F5E" : log.includes("Accuracy") || log.includes("passed") || log.includes("successfully") ? "#10B981" : "#7A94AE" }}>
                    <span style={{ color: "#3D5468", marginRight: 10 }}>[artha-ops]</span>
                    {log}
                  </div>
                ))}
                {training && (
                  <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#F59E0B", marginTop: 4 }}>
                    <span style={{ color: "#3D5468" }}>[artha-ops]</span>
                    <span>Processing training data sequence...</span>
                    <RefreshCw size={12} style={{ animation: "spin 0.8s linear infinite" }} />
                  </div>
                )}
                {logs.length === 0 && !training && (
                  <div style={{ color: "#3D5468", textAlign: "center", paddingTop: 150 }}>
                    Console idle. Click "Trigger Model Retraining" to launch continuous execution pipeline.
                  </div>
                )}
              </div>

              {/* Metric Card */}
              <div style={{ borderLeft: "2px solid #3B82F6", paddingLeft: 16 }}>
                <span className="section-label" style={{ display: "block", marginBottom: 6 }}>Pipeline Automation</span>
                <p style={{ fontSize: 12, color: "#7A94AE", margin: 0, lineHeight: 1.6 }}>
                  Our automated MLOps framework continuously tracks inference drift thresholds. When standard Population Stability Index (PSI) values scale beyond <code>0.15</code>, our Kubernetes daemon automatically triggers downstream container updates via Kafka event cues.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Code block section */}
        <section style={{ padding: "0 0 80px" }}>
          <div className="section-container">
            <h2 style={{ fontWeight: 600, fontSize: 20, color: "#E8F0F8", marginBottom: 20 }}>Evidently AI Monitor Script</h2>
            <div className="code-block">
              <span className="c-comment"># Evidently AI drift calculation logic</span>{"\n"}
              <span className="c-kw">from</span> evidently.metrics <span className="c-kw">import</span> ColumnDriftMetric{"\n"}
              <span className="c-kw">from</span> evidently.report <span className="c-kw">import</span> Report{"\n\n"}
              <span className="c-kw">def</span> <span className="c-fn">check_feature_drift</span>(reference_df, current_df, column: <span className="c-kw">str</span>) -{">"} <span className="c-kw">float</span>:{"\n"}
              {"    "}drift_report = Report(metrics=[ColumnDriftMetric(column_name=column)]){"\n"}
              {"    "}drift_report.run(reference_data=reference_df, current_data=current_df){"\n"}
              {"    "}result = drift_report.as_dict(){"\n"}
              {"    "}<span className="c-kw">return</span> result[<span className="c-str">"metrics"</span>][<span className="c-num">0</span>][<span className="c-str">"result"</span>][<span className="c-str">"drift_score"</span>]  <span className="c-comment"># Returns PSI/Wasserstein score</span>
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
