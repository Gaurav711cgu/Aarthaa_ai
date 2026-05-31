"use client";

import { useState } from "react";
import { Server, Activity, Database, CheckCircle, RefreshCw, Cpu, Layers } from "lucide-react";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

const K8S_PODS = [
  { name: "artha-fraud-ensemble-pod-1", status: "RUNNING", cpu: "14%", mem: "142MB", age: "14d" },
  { name: "artha-fraud-ensemble-pod-2", status: "RUNNING", cpu: "11%", mem: "138MB", age: "14d" },
  { name: "artha-rag-compliance-pod-1", status: "RUNNING", cpu: "4%", mem: "310MB", age: "6d" },
  { name: "artha-text2sql-lens-pod-1", status: "RUNNING", cpu: "1%", mem: "420MB", age: "10d" }
];

const INFRA_STATS = [
  { label: "P99 Inference Latency", val: "42 ms", target: "SLA < 50ms", color: "#10B981" },
  { label: "Broker Queue Latency", val: "1.4 ms", target: "Kafka Decoupled", color: "#8B5CF6" },
  { label: "Vector Search Latency", val: "8.2 ms", target: "pgvector Index", color: "#3B82F6" },
  { label: "Active PG Connections", val: "18 / 100", target: "PgBouncer", color: "#F59E0B" }
];

export default function InfraPage() {
  const [refreshing, setRefreshing] = useState(false);
  const [metrics, setMetrics] = useState(INFRA_STATS);

  const triggerRefresh = () => {
    setRefreshing(true);
    setTimeout(() => {
      setMetrics(INFRA_STATS.map(s => {
        if (s.label.includes("Latency")) {
          const valNum = parseFloat(s.val) + (Math.random() * 2 - 1);
          return { ...s, val: `${valNum.toFixed(1)} ms` };
        }
        return s;
      }));
      setRefreshing(false);
    }, 800);
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
              <span className="badge-amber">HA Infrastructure</span>
              <span className="badge-violet">Kubernetes Orchestrated</span>
              <span className="badge-green">PgBouncer Pool</span>
            </div>
            <h1 style={{ fontSize: "clamp(30px, 4.5vw, 50px)", fontWeight: 700, color: "#E8F0F8", marginBottom: 16, maxWidth: 640 }}>
              System Architecture & Infrastructure
            </h1>
            <p style={{ fontSize: 15, color: "#7A94AE", maxWidth: 560, lineHeight: 1.75 }}>
              Tracks production serving hardware clusters, database pooling limits, and message
              broker backlogs. Showcases real-time telemetry from JPMC GCC Kubernetes pods, pgvector
              query speeds, and connection health metrics.
            </p>
          </div>
        </section>

        {/* Content Section */}
        <section style={{ padding: "0 0 80px" }}>
          <div className="section-container" style={{ display: "grid", gridTemplateColumns: "1.3fr 1.7fr", gap: 40 }}>
            {/* Left Panel: Infrastructure metrics */}
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              <div className="research-card" style={{ borderTop: "2px solid #F59E0B" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                  <h3 style={{ fontWeight: 600, fontSize: 16, color: "#E8F0F8", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                    <Activity size={16} style={{ color: "#F59E0B" }} />
                    Live System Telemetry
                  </h3>
                  <button
                    onClick={triggerRefresh}
                    disabled={refreshing}
                    style={{ background: "none", border: "none", color: "#F59E0B", cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}
                  >
                    <RefreshCw size={12} style={{ animation: refreshing ? "spin 0.8s linear infinite" : "none" }} />
                  </button>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {metrics.map(s => (
                    <div key={s.label} style={{ background: "#0A1018", border: "1px solid #1C2D3E", borderRadius: 8, padding: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <span style={{ fontSize: 12.5, color: "#7A94AE" }}>{s.label}</span>
                        <span style={{ display: "block", fontSize: 10, color: "#3D5468", marginTop: 2 }}>{s.target}</span>
                      </div>
                      <span className="font-mono" style={{ fontSize: 15, fontWeight: 700, color: s.color }}>{s.val}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Database Status */}
              <div className="research-card" style={{ borderTop: "2px solid #3B82F6" }}>
                <h3 style={{ fontWeight: 600, fontSize: 16, color: "#E8F0F8", marginBottom: 14, display: "flex", alignItems: "center", gap: 8 }}>
                  <Database size={16} style={{ color: "#3B82F6" }} />
                  DBMS Instances
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 12.5, color: "#7A94AE" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #1C2D3E", paddingBottom: 6 }}>
                    <span>PostgreSQL Primary</span>
                    <span className="font-mono" style={{ color: "#10B981" }}>ONLINE (PgBouncer)</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #1C2D3E", paddingBottom: 6 }}>
                    <span>pgvector Extension</span>
                    <span className="font-mono" style={{ color: "#10B981" }}>ACTIVE (768-dim index)</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>SQLite Local Database</span>
                    <span className="font-mono" style={{ color: "#8B5CF6" }}>STANDBY (Fallback ok)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Panel: K8s Pods status */}
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              <div>
                <span className="section-label" style={{ marginBottom: 12, display: "block" }}>Kubernetes Cluster Pods (Active)</span>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {K8S_PODS.map((pod, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "14px 16px",
                        background: "#0A1018",
                        border: "1px solid #1C2D3E",
                        borderRadius: 8,
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center"
                      }}
                    >
                      <div>
                        <span className="font-mono" style={{ fontSize: 12, fontWeight: 600, color: "#E8F0F8" }}>{pod.name}</span>
                        <div style={{ display: "flex", gap: 10, fontSize: 10.5, color: "#3D5468", marginTop: 4 }}>
                          <span>CPU: {pod.cpu}</span>
                          <span>MEM: {pod.mem}</span>
                          <span>Age: {pod.age}</span>
                        </div>
                      </div>
                      <span className="font-mono" style={{ fontSize: 10, color: "#10B981", background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)", padding: "2px 6px", borderRadius: 3 }}>
                        {pod.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* SLA & Monitoring Notice */}
              <div className="research-card" style={{ borderTop: "2px solid #8B5CF6" }}>
                <h3 style={{ fontWeight: 600, fontSize: 15, color: "#E8F0F8", marginBottom: 12 }}>Prometheus Telemetry Scraper</h3>
                <p style={{ fontSize: 12.5, color: "#7A94AE", lineHeight: 1.6, marginBlockEnd: 0 }}>
                  A custom Prometheus metrics daemon exposes scoring throughput (RPS), memory thresholds, and inference latency statistics on the secure <code>/metrics</code> API endpoint. Telemetry values are scraped every 15 seconds by the Grafana cluster dashboard.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Code block section */}
        <section style={{ padding: "0 0 80px" }}>
          <div className="section-container">
            <h2 style={{ fontWeight: 600, fontSize: 20, color: "#E8F0F8", marginBottom: 20 }}>Kubernetes Deployment Manifest (Sample)</h2>
            <div className="code-block">
              <span className="c-comment"># artha-fraud-ensemble deployment config</span>{"\n"}
              <span className="c-kw">apiVersion</span>: apps/v1{"\n"}
              <span className="c-kw">kind</span>: Deployment{"\n"}
              <span className="c-kw">metadata</span>:{"\n"}
              {"  "}<span className="c-kw">name</span>: artha-fraud-ensemble{"\n"}
              <span className="c-kw">spec</span>:{"\n"}
              {"  "}<span className="c-kw">replicas</span>: <span className="c-num">2</span>{"\n"}
              {"  "}<span className="c-kw">template</span>:{"\n"}
              {"    "}<span className="c-kw">spec</span>:{"\n"}
              {"      "}<span className="c-kw">containers</span>:{"\n"}
              {"      "}- <span className="c-kw">name</span>: scoring-engine{"\n"}
              {"        "}<span className="c-kw">image</span>: artha-ai/scoring:v2.4.1{"\n"}
              {"        "}<span className="c-kw">resources</span>:{"\n"}
              {"          "}<span className="c-kw">limits</span>:{"\n"}
              {"            "}<span className="c-kw">cpu</span>: <span className="c-str">"500m"</span>{"\n"}
              {"            "}<span className="c-kw">memory</span>: <span className="c-str">"512Mi"</span>
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
