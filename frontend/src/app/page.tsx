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
        <section style={{ position: "relative", padding: "120px 0 80px" }}>
          <div className="bg-grid" style={{ position: "absolute", inset: 0, opacity: 0.35 }} />
          <div className="section-container" style={{ position: "relative" }}>

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
      </main>
      <Footer />
    </>
  );
}
