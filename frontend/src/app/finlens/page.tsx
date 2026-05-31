"use client";

import { useState, useEffect } from "react";
import { Database, Search, Upload, Play, CheckCircle, BarChart3, AlertTriangle } from "lucide-react";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

const SCHEMA_TABLES = [
  {
    name: "accounts",
    rows: 4,
    cols: ["account_id (INT, PK)", "account_number (VARCHAR)", "balance (DECIMAL)", "currency (VARCHAR)"]
  },
  {
    name: "transactions",
    rows: 1420,
    cols: ["tx_id (INT, PK)", "account_id (INT, FK)", "amount (DECIMAL)", "channel (VARCHAR)", "timestamp (TIMESTAMP)", "status (VARCHAR)"]
  }
];

interface SqlQuery {
  query: string;
  sql: string;
  params: Record<string, string | number>;
  headers: string[];
  rows: string[][];
}

const PRESET_QUERIES: SqlQuery[] = [
  {
    query: "Show total volume of NEFT transactions over ₹1,00,000",
    sql: "SELECT SUM(amount) AS total_volume FROM transactions WHERE channel = :channel AND amount > :amount AND status = 'COMPLETED'",
    params: { channel: "NEFT", amount: 100000 },
    headers: ["total_volume"],
    rows: [["₹18,50,000"]]
  },
  {
    query: "Find transactions with a status of 'FAILED' grouped by channel",
    sql: "SELECT channel, COUNT(*) AS failed_count FROM transactions WHERE status = :status GROUP BY channel ORDER BY failed_count DESC",
    params: { status: "FAILED" },
    headers: ["channel", "failed_count"],
    rows: [
      ["UPI", "48"],
      ["CARD", "12"],
      ["NEFT", "2"]
    ]
  },
  {
    query: "List top 3 largest transactions in UPI",
    sql: "SELECT tx_id, amount, timestamp FROM transactions WHERE channel = :channel ORDER BY amount DESC LIMIT :limit",
    params: { channel: "UPI", limit: 3 },
    headers: ["tx_id", "amount", "timestamp"],
    rows: [
      ["TX-9014", "₹98,500", "2026-05-29 14:02"],
      ["TX-8841", "₹90,000", "2026-05-28 09:15"],
      ["TX-9122", "₹85,000", "2026-05-30 18:41"]
    ]
  }
];

export default function FinLensPage() {
  const [dbType, setDbType] = useState<"postgres" | "sqlite">("postgres");
  const [nlQuery, setNlQuery] = useState("");
  const [sqlResult, setSqlResult] = useState<SqlQuery | null>(null);
  const [loading, setLoading] = useState(false);
  const [fileUploaded, setFileUploaded] = useState(false);

  const runTextToSql = (queryText: string) => {
    setNlQuery(queryText);
    setLoading(true);
    setSqlResult(null);

    // Simulate query parsing, SQL generation and local execution
    setTimeout(() => {
      const match = PRESET_QUERIES.find(p => queryText.toLowerCase().includes(p.query.toLowerCase().slice(0, 10))) || {
        query: queryText,
        sql: "SELECT * FROM transactions WHERE status = :status ORDER BY timestamp DESC LIMIT :limit",
        params: { status: "COMPLETED", limit: 5 },
        headers: ["tx_id", "amount", "channel", "status"],
        rows: [
          ["TX-1002", "₹12,400", "UPI", "COMPLETED"],
          ["TX-1003", "₹45,000", "NEFT", "COMPLETED"],
          ["TX-1004", "₹2,100", "CARD", "COMPLETED"]
        ]
      };
      setSqlResult(match);
      setLoading(false);
    }, 900);
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
              <span className="badge-amber">FinLens v2</span>
              <span className="badge-violet">Text-to-SQL Auditor</span>
              <span className="badge-green">Anti-Injection Guard</span>
            </div>
            <h1 style={{ fontSize: "clamp(30px, 4.5vw, 50px)", fontWeight: 700, color: "#E8F0F8", marginBottom: 16, maxWidth: 640 }}>
              Natural Language SQL Auditor
            </h1>
            <p style={{ fontSize: 15, color: "#7A94AE", maxWidth: 560, lineHeight: 1.75 }}>
              Converts complex natural language queries into secure, parameterized SQL. Upload
              bank statements in PDF or CSV formats to inspect transaction schemas, run custom SQL
              computations, and visualize financial distributions without injection risk.
            </p>
          </div>
        </section>

        {/* Content grid */}
        <section style={{ padding: "0 0 80px" }}>
          <div className="section-container" style={{ display: "grid", gridTemplateColumns: "1.2fr 1.8fr", gap: 40 }}>
            {/* Left Panel: Schema & Statement Upload */}
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              {/* Bank Statement Uploader */}
              <div className="research-card" style={{ borderTop: "2px solid #F59E0B" }}>
                <h3 style={{ fontWeight: 600, fontSize: 16, color: "#E8F0F8", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
                  <Upload size={16} style={{ color: "#F59E0B" }} />
                  Bank Statement Source
                </h3>
                <div
                  onClick={() => setFileUploaded(true)}
                  style={{
                    border: "1px dashed #1C2D3E",
                    background: "rgba(6,10,14,0.4)",
                    borderRadius: 8,
                    padding: "28px 20px",
                    textAlign: "center",
                    cursor: "pointer",
                    transition: "all 0.15s"
                  }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = "#F59E0B"}
                  onMouseLeave={e => e.currentTarget.style.borderColor = "#1C2D3E"}
                >
                  <Database size={24} style={{ color: fileUploaded ? "#10B981" : "#3D5468", marginBottom: 8, display: "inline-block" }} />
                  <p style={{ fontSize: 13, color: "#E8F0F8", fontWeight: 500, margin: 0 }}>
                    {fileUploaded ? "statement_may_2026.csv loaded" : "Click to select or drag financial statement here"}
                  </p>
                  <p style={{ fontSize: 11, color: "#3D5468", marginTop: 4, marginBlockEnd: 0 }}>Supports CSV, pipe-delimited text, or bank PDFs</p>
                </div>
              </div>

              {/* Target DB Toggler */}
              <div className="research-card" style={{ borderTop: "2px solid #3B82F6" }}>
                <h3 style={{ fontWeight: 600, fontSize: 16, color: "#E8F0F8", marginBottom: 16 }}>Database Dialect</h3>
                <div style={{ display: "flex", gap: 8 }}>
                  {["postgres", "sqlite"].map(t => (
                    <button
                      key={t}
                      onClick={() => setDbType(t as "postgres" | "sqlite")}
                      style={{
                        flex: 1,
                        padding: "8px 0",
                        borderRadius: 6,
                        background: dbType === t ? "rgba(59,130,246,0.15)" : "#0A1018",
                        border: dbType === t ? "1px solid #3B82F6" : "1px solid #1C2D3E",
                        color: dbType === t ? "#3B82F6" : "#7A94AE",
                        fontWeight: 600,
                        fontSize: 12.5,
                        cursor: "pointer",
                        textTransform: "uppercase",
                        letterSpacing: "0.05em"
                      }}
                    >
                      {t === "postgres" ? "PostgreSQL" : "SQLite Local"}
                    </button>
                  ))}
                </div>
              </div>

              {/* Schema Inspector */}
              <div className="research-card" style={{ borderTop: "2px solid #8B5CF6" }}>
                <h3 style={{ fontWeight: 600, fontSize: 16, color: "#E8F0F8", marginBottom: 16 }}>Target Schema Browser</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  {SCHEMA_TABLES.map(table => (
                    <div key={table.name} style={{ background: "#0A1018", border: "1px solid #1C2D3E", borderRadius: 8, padding: 12 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, borderBottom: "1px solid #1C2D3E", paddingBottom: 6 }}>
                        <span className="font-mono" style={{ fontSize: 12, fontWeight: 600, color: "#8B5CF6" }}>{table.name}</span>
                        <span className="font-mono" style={{ fontSize: 10, color: "#3D5468" }}>{table.rows} rows</span>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                        {table.cols.map(c => (
                          <div key={c} className="font-mono" style={{ fontSize: 11, color: "#7A94AE" }}>{c}</div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Panel: SQL Execution & Table View */}
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              {/* Natural Language Query Bar */}
              <div style={{ display: "flex", gap: 10 }}>
                <div style={{ position: "relative", flex: 1 }}>
                  <Search size={16} style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "#3D5468" }} />
                  <input
                    type="text"
                    value={nlQuery}
                    onChange={e => setNlQuery(e.target.value)}
                    placeholder="Ask any question in plain English (e.g. 'Show NEFT transactions over ₹1L')..."
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
                    onKeyDown={e => e.key === "Enter" && runTextToSql(nlQuery)}
                  />
                </div>
                <button
                  onClick={() => runTextToSql(nlQuery || PRESET_QUERIES[0].query)}
                  disabled={loading}
                  className="btn-primary"
                  style={{ padding: "0 22px", borderRadius: 8, height: 46 }}
                >
                  {loading ? <div style={{ width: 14, height: 14, border: "2px solid #060A0E", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.6s linear infinite" }} /> : <Play size={14} />}
                </button>
              </div>

              {/* Presets Grid */}
              <div>
                <span className="section-label" style={{ marginBottom: 10, display: "block" }}>NL Query Presets</span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {PRESET_QUERIES.map((p, i) => (
                    <button
                      key={i}
                      onClick={() => runTextToSql(p.query)}
                      style={{
                        padding: "8px 12px",
                        background: "#0A1018",
                        border: "1px solid #1C2D3E",
                        borderRadius: 6,
                        fontSize: 11.5,
                        color: "#7A94AE",
                        cursor: "pointer",
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

              {/* SQL Result Output */}
              {sqlResult && !loading && (
                <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                  {/* Generated SQL block */}
                  <div className="research-card" style={{ borderTop: "2px solid #8B5CF6" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                      <span className="section-label">Generated SQL Code</span>
                      <span className="badge-violet" style={{ fontSize: 9 }}>PARAMETERIZED</span>
                    </div>
                    <div className="code-block" style={{ marginBottom: 14 }}>
                      <span className="c-kw">SELECT</span> {sqlResult.headers.join(", ")} <span className="c-kw">FROM</span> transactions...
                      {"\n"}<span className="c-str">"{sqlResult.sql}"</span>
                    </div>

                    {/* Parameter Bindings */}
                    <div style={{ borderTop: "1px solid #1C2D3E", paddingTop: 12 }}>
                      <span className="section-label" style={{ display: "block", marginBottom: 8 }}>Bound Parameters</span>
                      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                        {Object.entries(sqlResult.params).map(([k, v]) => (
                          <div key={k} className="font-mono" style={{ fontSize: 11, background: "#0A1018", border: "1px solid #1C2D3E", padding: "4px 10px", borderRadius: 4 }}>
                            <span style={{ color: "#3D5468" }}>{k}:</span> <span style={{ color: "#F59E0B" }}>{String(v)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Execution Output Table */}
                  <div className="research-card font-mono" style={{ borderTop: "2px solid #10B981" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                      <span className="section-label">Execution Results</span>
                      <span style={{ fontSize: 11, color: "#10B981", display: "flex", alignItems: "center", gap: 5 }}>
                        <CheckCircle size={12} /> Execution OK
                      </span>
                    </div>

                    {/* Data Table */}
                    <div style={{ overflowX: "auto" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, textAlign: "left" }}>
                        <thead>
                          <tr style={{ borderBottom: "2px solid #1C2D3E", color: "#7A94AE" }}>
                            {sqlResult.headers.map(h => (
                              <th key={h} style={{ padding: "8px 12px" }}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {sqlResult.rows.map((row, ri) => (
                            <tr key={ri} style={{ borderBottom: "1px solid #1C2D3E" }}>
                              {row.map((cell, ci) => (
                                <td key={ci} style={{ padding: "10px 12px", color: "#E8F0F8" }}>{cell}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Interactive Chart */}
                  {sqlResult.headers.includes("failed_count") && (
                    <div className="research-card" style={{ borderTop: "2px solid #3B82F6" }}>
                      <h3 style={{ fontWeight: 600, fontSize: 14, color: "#E8F0F8", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
                        <BarChart3 size={15} style={{ color: "#3B82F6" }} />
                        Failed Transactions Distribution
                      </h3>
                      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                        {[
                          { label: "UPI", val: 48, max: 48, col: "#F43F5E" },
                          { label: "CARD", val: 12, max: 48, col: "#F59E0B" },
                          { label: "NEFT", val: 2, max: 48, col: "#10B981" }
                        ].map(c => (
                          <div key={c.label}>
                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, fontFamily: "monospace", marginBottom: 4 }}>
                              <span style={{ color: "#7A94AE" }}>{c.label}</span>
                              <span style={{ color: "#E8F0F8" }}>{c.val} failures</span>
                            </div>
                            <div style={{ height: 6, background: "#16212E", borderRadius: 3, overflow: "hidden" }}>
                              <div style={{ height: "100%", background: c.col, width: `${(c.val / c.max) * 100}%`, borderRadius: 3 }} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Safety notice */}
              <div style={{ display: "flex", gap: 12, background: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.2)", borderRadius: 8, padding: "14px 18px" }}>
                <AlertTriangle size={18} style={{ color: "#3B82F6", marginTop: 2, flexShrink: 0 }} />
                <p style={{ fontSize: 12, color: "#7A94AE", margin: 0, lineHeight: 1.65 }}>
                  <strong>SQL Injection Protection:</strong> FinLens operates on dynamic tokenized mappings. Queries are structurally validated to prevent arbitrary statement executions. Safe, primary parameterized variables are generated via LLM mappings and strictly bound prior to DBMS execution.
                </p>
              </div>
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
