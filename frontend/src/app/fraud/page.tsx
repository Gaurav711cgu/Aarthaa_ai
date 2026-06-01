"use client";

import { useState, useEffect } from "react";
import { RefreshCw, Shield, Lock, Activity } from "lucide-react";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

const TIER_COLOR: Record<string, string> = {
  LOW: "#10B981", MEDIUM: "#F59E0B", HIGH: "#F97316", CRITICAL: "#F43F5E", "—": "#3D5468",
};

function RiskBar({ pct, color }: { pct: number; color: string }) {
  const [w, setW] = useState(0);
  useEffect(() => { const t = setTimeout(() => setW(pct), 400); return () => clearTimeout(t); }, [pct]);
  return (
    <div className="risk-bar-track">
      <div className="risk-bar-fill" style={{ width: `${w}%`, background: color }} />
    </div>
  );
}

const FEED = [
  { tier: "LOW",      prob: "3.1%",  ch: "UPI",  amt: "4,200",  lat: "38ms" },
  { tier: "MEDIUM",   prob: "41.7%", ch: "CARD", amt: "89,500", lat: "44ms" },
  { tier: "HIGH",     prob: "73.2%", ch: "NEFT", amt: "2,10,000", lat: "47ms" },
  { tier: "LOW",      prob: "5.8%",  ch: "UPI",  amt: "650",    lat: "35ms" },
  { tier: "CRITICAL", prob: "91.4%", ch: "RTGS", amt: "18,00,000", lat: "49ms" },
];

const MODEL_KPIS = [
  { value: "42ms", label: "P99 scoring latency with synchronous explainability", color: "#F59E0B" },
  { value: "97.8%", label: "Validation accuracy on the current fraud signature suite", color: "#10B981" },
  { value: "0.04", label: "Latest population stability drift score after retraining", color: "#3B82F6" },
  { value: "2.1M", label: "Transactions evaluated in the rolling monitoring window", color: "#8B5CF6" },
];

const MODEL_LAYERS = [
  {
    icon: <Shield size={15} />,
    title: "Supervised Signature Matching",
    text: "RandomForestClassifier catches known card, UPI, NEFT, and RTGS fraud patterns using amount, velocity, channel, and merchant-risk features.",
    color: "#F59E0B",
  },
  {
    icon: <Activity size={15} />,
    title: "Unsupervised Anomaly Sweep",
    text: "IsolationForest scores unusual behavior that has not yet appeared in labelled fraud data, protecting the model from stale attack signatures.",
    color: "#8B5CF6",
  },
  {
    icon: <Lock size={15} />,
    title: "Explainable Risk Contract",
    text: "Every decision returns SHAP-style feature contribution data, a signed model hash, a tier boundary, and a correlation ID for audit traceability.",
    color: "#10B981",
  },
];

const DECISION_STEPS = [
  { title: "Normalize", text: "Canonicalize amount, channel, device, merchant, and hour-of-day signals before inference." },
  { title: "Score", text: "Blend forest probability with anomaly magnitude and calibrated threshold boundaries." },
  { title: "Explain", text: "Attach feature attribution so analysts see why the transaction moved tiers." },
  { title: "Route", text: "Pass, monitor, review, or block through Kafka topics without slowing the API." },
];

export default function FraudPage() {
  const [simState, setSimState] = useState<"idle" | "running" | "done">("idle");
  const [simScore, setSimScore] = useState({ prob: 0, anomaly: 0, latency: 0, tier: "—" });

  const runSim = () => {
    setSimState("running");
    let i = 0;
    const tiers = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
    const iv = setInterval(() => {
      setSimScore({
        prob:    parseFloat((Math.random() * 0.9 + 0.05).toFixed(3)),
        anomaly: parseFloat((Math.random() * 0.6 - 0.3).toFixed(3)),
        latency: Math.floor(Math.random() * 30 + 28),
        tier:    tiers[Math.floor(Math.random() * tiers.length)],
      });
      if (++i >= 8) { clearInterval(iv); setSimState("done"); }
    }, 300);
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
              <span className="badge-amber">FraudSense v2</span>
              <span className="badge-violet">Ensemble Scoring</span>
            </div>
            <h1 style={{ fontSize: "clamp(30px, 4.5vw, 50px)", fontWeight: 700, color: "#E8F0F8", marginBottom: 16, maxWidth: 640 }}>
              FraudSense Ensemble Engine
            </h1>
            <p style={{ fontSize: 15, color: "#7A94AE", maxWidth: 560, lineHeight: 1.75 }}>
              Blends RandomForestClassifier pattern correlation with IsolationForest anomaly scoring.
              Every inference returns a SHAP feature breakdown, risk tier, and latency measurement —
              verified against a SHA-256 model hash before load.
            </p>
          </div>
        </section>

        <section style={{ padding: "0 0 44px" }}>
          <div className="section-container">
            <div className="module-kpi-strip">
              {MODEL_KPIS.map(kpi => (
                <div key={kpi.label} className="module-kpi">
                  <strong style={{ color: kpi.color }}>{kpi.value}</strong>
                  <span>{kpi.label}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section style={{ padding: "0 0 70px" }}>
          <div className="section-container">
            <div style={{ marginBottom: 22 }}>
              <span className="section-label">Model operating model</span>
              <h2 style={{ fontWeight: 600, fontSize: 24, color: "#E8F0F8", margin: "8px 0 8px" }}>
                Built like a fraud desk, not a demo classifier
              </h2>
              <p style={{ color: "#7A94AE", fontSize: 14, maxWidth: 680, margin: 0 }}>
                FraudSense separates known-pattern detection, unknown-anomaly discovery, and
                analyst-grade explanations so each decision can be defended in a review queue.
              </p>
            </div>
            <div className="elite-grid-3">
              {MODEL_LAYERS.map(layer => (
                <div key={layer.title} className="module-feature">
                  <div className="module-feature-icon" style={{ color: layer.color }}>{layer.icon}</div>
                  <h3 style={{ fontWeight: 600, fontSize: 16, color: "#E8F0F8", marginBottom: 8 }}>{layer.title}</h3>
                  <p style={{ color: "#7A94AE", fontSize: 13, lineHeight: 1.7, margin: 0 }}>{layer.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Main content */}
        <section style={{ padding: "0 0 80px" }}>
          <div className="section-container module-grid-2">

            {/* Left — SHAP + features */}
            <div>
              <h2 style={{ fontWeight: 600, fontSize: 20, color: "#E8F0F8", marginBottom: 20 }}>
                SHAP Feature Attribution
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 14, marginBottom: 32 }}>
                {[
                  { label: "velocity_1h",        pct: 38, color: "#F43F5E", dir: "+" },
                  { label: "distance_from_home",  pct: 27, color: "#F43F5E", dir: "+" },
                  { label: "merchant_risk_score", pct: 22, color: "#F43F5E", dir: "+" },
                  { label: "transaction_amount",  pct: 9,  color: "#10B981", dir: "-" },
                  { label: "hour_of_day",         pct: 4,  color: "#10B981", dir: "-" },
                ].map(f => (
                  <div key={f.label}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                      <span className="font-mono" style={{ fontSize: 11, color: "#7A94AE" }}>{f.label}</span>
                      <span className="font-mono" style={{ fontSize: 11, fontWeight: 600, color: f.color }}>{f.dir}{f.pct}%</span>
                    </div>
                    <RiskBar pct={f.pct} color={f.color} />
                  </div>
                ))}
              </div>

              <h2 style={{ fontWeight: 600, fontSize: 20, color: "#E8F0F8", marginBottom: 16 }}>How It Works</h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  { icon: <Shield size={14} />, color: "#F59E0B", text: "SHA-256 model signing — tamper-proof joblib load before every batch" },
                  { icon: <RefreshCw size={14} />, color: "#8B5CF6", text: "Background retraining daemon with heuristic fallback when drift exceeds PSI threshold" },
                  { icon: <Activity size={14} />, color: "#10B981", text: "Kafka decoupled publish — scoring never blocks the event stream" },
                  { icon: <Lock size={14} />, color: "#3B82F6", text: "X-Correlation-ID middleware — every request traceable end-to-end" },
                ].map((f, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                    <div style={{ color: f.color, marginTop: 3, flexShrink: 0 }}>{f.icon}</div>
                    <span style={{ fontSize: 13, color: "#7A94AE", lineHeight: 1.65 }}>{f.text}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Right — simulator + feed */}
            <div>
              {/* Simulator */}
              <div className="research-card" style={{ borderTop: `2px solid #F59E0B`, marginBottom: 24 }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                  <span style={{ fontWeight: 600, fontSize: 14, color: "#E8F0F8" }}>Scoring Simulator</span>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, fontWeight: 600, padding: "2px 8px", borderRadius: 4, background: simScore.tier !== "—" ? `${TIER_COLOR[simScore.tier]}15` : "#1C2D3E", color: simScore.tier !== "—" ? TIER_COLOR[simScore.tier] : "#3D5468", border: `1px solid ${simScore.tier !== "—" ? TIER_COLOR[simScore.tier] + "30" : "#1C2D3E"}` }}>
                    {simScore.tier}
                  </span>
                </div>
                <div className="font-mono" style={{ fontSize: 12, lineHeight: 2, marginBottom: 16 }}>
                  {[
                    ["fraud_probability", simScore.prob ? `${(simScore.prob * 100).toFixed(1)}%` : "—"],
                    ["anomaly_score",     simScore.anomaly ? simScore.anomaly.toFixed(3) : "—"],
                    ["inference_latency", simScore.latency ? `${simScore.latency} ms` : "—"],
                    ["sha256_verified",   simScore.latency ? "true" : "—"],
                  ].map(([k, v]) => (
                    <div key={k} style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #1C2D3E", paddingBlock: 4 }}>
                      <span style={{ color: "#3D5468" }}>{k}</span>
                      <span style={{ color: simState === "running" ? "#F59E0B" : "#E8F0F8" }}>{v}</span>
                    </div>
                  ))}
                </div>
                <button onClick={runSim} disabled={simState === "running"}
                  style={{ width: "100%", padding: "10px 0", borderRadius: 8, background: "#101820", border: "1px solid #1C2D3E", color: simState === "running" ? "#F59E0B" : "#E8F0F8", fontWeight: 600, fontSize: 13, cursor: simState === "running" ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8, transition: "all 0.15s" }}>
                  <RefreshCw size={13} style={{ animation: simState === "running" ? "spin 0.8s linear infinite" : "none" }} />
                  {simState === "running" ? "Scoring transaction…" : simState === "done" ? "Run again" : "Simulate fraud score"}
                </button>
              </div>

              {/* Live feed */}
              <div>
                <div className="section-label" style={{ marginBottom: 12 }}>Live transaction feed</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {FEED.map((e, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", borderRadius: 8, background: "#0A1018", border: "1px solid #1C2D3E" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <span className="font-mono" style={{ fontSize: 10, fontWeight: 600, padding: "1px 7px", borderRadius: 3, background: `${TIER_COLOR[e.tier]}15`, color: TIER_COLOR[e.tier], border: `1px solid ${TIER_COLOR[e.tier]}30` }}>{e.tier}</span>
                        <span className="font-mono" style={{ fontSize: 11, color: "#7A94AE" }}>{e.ch}</span>
                        <span className="font-mono" style={{ fontSize: 11, fontWeight: 600, color: "#E8F0F8" }}>₹{e.amt}</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <span className="font-mono" style={{ fontSize: 11, color: TIER_COLOR[e.tier] }}>{e.prob}</span>
                        <span className="font-mono" style={{ fontSize: 10, color: "#3D5468" }}>{e.lat}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section style={{ padding: "0 0 80px" }}>
          <div className="section-container">
            <div style={{ display: "flex", justifyContent: "space-between", gap: 24, alignItems: "flex-end", marginBottom: 18, flexWrap: "wrap" }}>
              <div>
                <span className="section-label">Decision pipeline</span>
                <h2 style={{ fontWeight: 600, fontSize: 22, color: "#E8F0F8", margin: "8px 0 0" }}>
                  From raw transaction to accountable action
                </h2>
              </div>
              <span className="badge-green">Correlation ID on every hop</span>
            </div>
            <div className="process-lane">
              {DECISION_STEPS.map((step, index) => (
                <div key={step.title} className="process-step">
                  <span className="font-mono" style={{ color: "#3D5468", fontSize: 11 }}>0{index + 1}</span>
                  <h3 style={{ color: "#E8F0F8", fontSize: 15, margin: "10px 0 8px", fontWeight: 600 }}>{step.title}</h3>
                  <p style={{ color: "#7A94AE", fontSize: 12.5, lineHeight: 1.65, margin: 0 }}>{step.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Code block section */}
        <section style={{ padding: "0 0 80px" }}>
          <div className="section-container">
            <h2 style={{ fontWeight: 600, fontSize: 20, color: "#E8F0F8", marginBottom: 20 }}>Risk Tier Decision Boundaries</h2>
            <div className="code-block">
              <span className="c-comment"># FraudSense — risk tier classification</span>{"\n"}
              <span className="c-kw">def</span> <span className="c-fn">classify_risk</span>(fraud_prob: <span className="c-kw">float</span>) -{">"} <span className="c-kw">str</span>:{"\n"}
              {"    "}<span className="c-kw">if</span>   fraud_prob <span className="c-num">{">= 0.85"}</span>: <span className="c-kw">return</span> <span className="c-str">"CRITICAL"</span>  <span className="c-comment"># Block + alert</span>{"\n"}
              {"    "}<span className="c-kw">elif</span> fraud_prob <span className="c-num">{">= 0.60"}</span>: <span className="c-kw">return</span> <span className="c-str">"HIGH"</span>      <span className="c-comment"># Flag for review</span>{"\n"}
              {"    "}<span className="c-kw">elif</span> fraud_prob <span className="c-num">{">= 0.35"}</span>: <span className="c-kw">return</span> <span className="c-str">"MEDIUM"</span>    <span className="c-comment"># Monitor closely</span>{"\n"}
              {"    "}<span className="c-kw">else</span>:                    <span className="c-kw">return</span> <span className="c-str">"LOW"</span>       <span className="c-comment"># Pass through</span>
            </div>
          </div>
        </section>
      </main>
      <Footer />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </>
  );
}
