"use client";

import { useState, useEffect } from "react";
import { Activity, Shield, Layers, Database, Cpu, RefreshCw, CheckCircle, AlertTriangle } from "lucide-react";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

interface LogEntry {
  time: string;
  module: string;
  msg: string;
  color: string;
}

const INITIAL_LOGS: LogEntry[] = [
  { time: "02:40:02", module: "FraudSense", msg: "Scored transaction TX-9042 (Amount: ₹4,500) -> LOW Risk", color: "#10B981" },
  { time: "02:40:03", module: "RegGuard",   msg: "pgvector similarity check over RBI Circular complete -> COMPLIANT", color: "#8B5CF6" },
  { time: "02:40:05", module: "FinLens",    msg: "NL Query executed: 'Show daily balances' -> Parsed safe parameterized SQL", color: "#10B981" },
];

export default function PlatformPage() {
  const [activeTab, setActiveTab] = useState<"overview" | "telemetry">("overview");
  const [tps, setTps] = useState(14.5);
  const [isSimulating, setIsSimulating] = useState(true);
  const [logs, setLogs] = useState<LogEntry[]>(INITIAL_LOGS);
  const [systemAlert, setSystemAlert] = useState<string | null>(null);

  // Dynamic simulation of TPS and live logs
  useEffect(() => {
    if (!isSimulating) return;

    const interval = setInterval(() => {
      // Simulate TPS fluctuations
      setTps(prev => {
        const next = prev + (Math.random() * 2 - 1);
        return Math.max(8.0, Math.min(24.0, parseFloat(next.toFixed(1))));
      });

      // Periodic random log entries
      const modules = ["FraudSense", "RegGuard", "FinLens", "Infrastructure"];
      const mod = modules[Math.floor(Math.random() * modules.length)];
      const now = new Date();
      const timeStr = now.toTimeString().split(" ")[0];

      let msg = "";
      let color = "#7A94AE";

      if (mod === "FraudSense") {
        const amt = Math.floor(Math.random() * 200000 + 500);
        const randVal = Math.random();
        if (randVal > 0.85) {
          msg = `Scored transaction TX-${Math.floor(Math.random() * 9000 + 1000)} (Amount: ₹${amt.toLocaleString()}) -> CRITICAL Risk`;
          color = "#F43F5E";
          setSystemAlert(`High-Risk Transaction Flagged: TX-${Math.floor(Math.random() * 9000 + 1000)} requires manual RBI audit check.`);
        } else if (randVal > 0.6) {
          msg = `Scored transaction TX-${Math.floor(Math.random() * 9000 + 1000)} (Amount: ₹${amt.toLocaleString()}) -> HIGH Risk`;
          color = "#F59E0B";
        } else {
          msg = `Scored transaction TX-${Math.floor(Math.random() * 9000 + 1000)} (Amount: ₹${amt.toLocaleString()}) -> LOW Risk`;
          color = "#10B981";
        }
      } else if (mod === "RegGuard") {
        const codes = ["RBI Master Dir", "FEMA Section 3", "PMLA Rule 8"];
        msg = `pgvector similarity check over ${codes[Math.floor(Math.random() * codes.length)]} complete -> COMPLIANT`;
        color = "#8B5CF6";
      } else if (mod === "FinLens") {
        msg = "NL Query parsing completed. Parameter bindings mapped successfully.";
        color = "#3B82F6";
      } else {
        msg = "Kubernetes pods healthcheck response: OK. P99 Serving Latency: 42ms.";
        color = "#10B981";
      }

      setLogs(prev => [
        { time: timeStr, module: mod, msg, color },
        ...prev.slice(0, 14)
      ]);
    }, 2800);

    return () => clearInterval(interval);
  }, [isSimulating]);

  return (
    <>
      <Nav />
      <main style={{ paddingTop: 80 }}>
        {/* Header */}
        <section style={{ position: "relative", padding: "80px 0 60px" }}>
          <div className="bg-grid" style={{ position: "absolute", inset: 0, opacity: 0.3 }} />
          <div className="section-container" style={{ position: "relative" }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 24 }}>
              <span className="badge-amber">Operations Room</span>
              <span className="badge-violet">Decoupled Systems</span>
              <span className="badge-green">Telemetry Dashboard</span>
            </div>
            <h1 style={{ fontSize: "clamp(30px, 4.5vw, 50px)", fontWeight: 700, color: "#E8F0F8", marginBottom: 16, maxWidth: 640 }}>
              Enterprise Unified Platform
            </h1>
            <p style={{ fontSize: 15, color: "#7A94AE", maxWidth: 560, lineHeight: 1.75 }}>
              The central operational dashboard for Artha AI. Integrates real-time feeds from FraudSense
              scoring models, pgvector RegGuard search channels, FinLens Text-to-SQL databases,
              and live Kubernetes telemetry metrics.
            </p>
          </div>
        </section>

        {/* Alert Zone */}
        {systemAlert && (
          <section style={{ padding: "0 0 20px" }}>
            <div className="section-container">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(244,63,94,0.06)", border: "1px solid rgba(244,63,94,0.25)", borderRadius: 8, padding: "12px 18px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <AlertTriangle size={16} style={{ color: "#F43F5E" }} />
                  <span style={{ fontSize: 13, color: "#E8F0F8", fontWeight: 500 }}>{systemAlert}</span>
                </div>
                <button
                  onClick={() => setSystemAlert(null)}
                  style={{ background: "none", border: "none", color: "#F43F5E", cursor: "pointer", fontSize: 11, fontWeight: 600 }}
                >
                  DISMISS
                </button>
              </div>
            </div>
          </section>
        )}

        {/* Platform Grid */}
        <section style={{ padding: "0 0 80px" }}>
          <div className="section-container" style={{ display: "grid", gridTemplateColumns: "1.8fr 1.2fr", gap: 40 }}>
            {/* Left Panel: Unified Module Telemetry */}
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              {/* Telemetry Cards Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16 }}>
                <div className="research-card font-mono" style={{ borderTop: "2px solid #F59E0B" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <span className="section-label" style={{ fontSize: 9 }}>Ensemble Throughput</span>
                    <Cpu size={14} style={{ color: "#F59E0B" }} />
                  </div>
                  <div style={{ fontSize: 28, fontWeight: 700, color: "#F59E0B", lineHeight: 1 }}>
                    {tps} <span style={{ fontSize: 13, color: "#3D5468" }}>TPS</span>
                  </div>
                  <span style={{ display: "block", fontSize: 11, color: "#7A94AE", marginTop: 6 }}>Scoring transactions in real-time</span>
                </div>

                <div className="research-card font-mono" style={{ borderTop: "2px solid #8B5CF6" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <span className="section-label" style={{ fontSize: 9 }}>RAG Vector Index</span>
                    <Layers size={14} style={{ color: "#8B5CF6" }} />
                  </div>
                  <div style={{ fontSize: 28, fontWeight: 700, color: "#8B5CF6", lineHeight: 1 }}>
                    99.4% <span style={{ fontSize: 13, color: "#3D5468" }}>match</span>
                  </div>
                  <span style={{ display: "block", fontSize: 11, color: "#7A94AE", marginTop: 6 }}>Accurate semantic indexing score</span>
                </div>

                <div className="research-card font-mono" style={{ borderTop: "2px solid #10B981" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <span className="section-label" style={{ fontSize: 9 }}>SQL Guard Status</span>
                    <Database size={14} style={{ color: "#10B981" }} />
                  </div>
                  <div style={{ fontSize: 28, fontWeight: 700, color: "#10B981", lineHeight: 1 }}>
                    100% <span style={{ fontSize: 13, color: "#3D5468" }}>secure</span>
                  </div>
                  <span style={{ display: "block", fontSize: 11, color: "#7A94AE", marginTop: 6 }}>Zero SQL injection vectors reported</span>
                </div>

                <div className="research-card font-mono" style={{ borderTop: "2px solid #3B82F6" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <span className="section-label" style={{ fontSize: 9 }}>P99 serving Latency</span>
                    <Activity size={14} style={{ color: "#3B82F6" }} />
                  </div>
                  <div style={{ fontSize: 28, fontWeight: 700, color: "#3B82F6", lineHeight: 1 }}>
                    42 <span style={{ fontSize: 13, color: "#3D5468" }}>ms</span>
                  </div>
                  <span style={{ display: "block", fontSize: 11, color: "#7A94AE", marginTop: 6 }}>Well within SLA limit of 50ms</span>
                </div>
              </div>

              {/* Module Telemetry Summary */}
              <div className="research-card" style={{ borderTop: "2px solid #3B82F6" }}>
                <h3 style={{ fontWeight: 600, fontSize: 16, color: "#E8F0F8", marginBottom: 12 }}>Unified Operations Overview</h3>
                <p style={{ fontSize: 13, color: "#7A94AE", lineHeight: 1.65, marginBlockEnd: 0 }}>
                  This dashboard reflects the live decoupled structure of the Artha AI platform.
                  Transactions are logged sequentially to local Kafka partitions without halting client responses.
                  Downstream workers consume messages asynchronously, triggering pgvector compliance audits
                  and syncing records to our primary secure PostgreSQL database.
                </p>
              </div>
            </div>

            {/* Right Panel: Operations Logs */}
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span className="section-label" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <Activity size={12} style={{ color: "#F59E0B" }} />
                  Unified Platform Logs
                </span>
                <button
                  onClick={() => setIsSimulating(!isSimulating)}
                  style={{
                    background: "none",
                    border: "none",
                    color: isSimulating ? "#10B981" : "#3D5468",
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: "pointer",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em"
                  }}
                >
                  {isSimulating ? "Pause Simulation" : "Resume Simulation"}
                </button>
              </div>

              {/* Operations Console Window */}
              <div
                style={{
                  background: "#040709",
                  border: "1px solid #1C2D3E",
                  borderRadius: 10,
                  height: 380,
                  overflowY: "auto",
                  padding: "16px 18px",
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 11.5,
                  lineHeight: 1.75,
                  display: "flex",
                  flexDirection: "column",
                  gap: 10
                }}
              >
                {logs.map((log, index) => (
                  <div key={index} style={{ borderBottom: "1px solid #0A1018", paddingBottom: 6 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span className="font-mono" style={{ fontSize: 10, color: "#3D5468" }}>{log.time}</span>
                      <span className="font-mono" style={{ fontSize: 10, fontWeight: 600, color: log.color }}>
                        {log.module.toUpperCase()}
                      </span>
                    </div>
                    <span style={{ color: "#E8F0F8" }}>{log.msg}</span>
                  </div>
                ))}
              </div>

              {/* Status footer note */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11.5, color: "#7A94AE" }}>
                <CheckCircle size={13} style={{ color: "#10B981" }} />
                <span>All platform components fully synchronized.</span>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
