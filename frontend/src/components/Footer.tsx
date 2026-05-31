import Link from "next/link";
import { GitBranch, ExternalLink } from "lucide-react";

export default function Footer() {
  return (
    <footer style={{ borderTop: "1px solid #1C2D3E", padding: "40px 0" }}>
      <div className="section-container" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
        <div>
          <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 15, color: "#E8F0F8", marginBottom: 4 }}>
            Artha AI
          </div>
          <div className="font-mono" style={{ fontSize: 11, color: "#3D5468" }}>
            Built under JPMC GCC technical evaluation standards
          </div>
        </div>
        <div style={{ display: "flex", gap: 24 }}>
          {[
            { href: "/fraud",      label: "FraudSense" },
            { href: "/compliance", label: "RegGuard" },
            { href: "/finlens",   label: "FinLens" },
            { href: "/mlops",     label: "MLOps" },
          ].map(l => (
            <Link key={l.href} href={l.href} style={{ fontSize: 13, color: "#7A94AE", textDecoration: "none", transition: "color 0.15s" }}
              onMouseEnter={e => (e.currentTarget.style.color = "#F59E0B")}
              onMouseLeave={e => (e.currentTarget.style.color = "#7A94AE")}>
              {l.label}
            </Link>
          ))}
        </div>
        <a href="https://github.com/Gaurav711cgu/Aarthaa_ai" target="_blank" rel="noopener noreferrer"
          style={{ display: "flex", alignItems: "center", gap: 7, color: "#7A94AE", textDecoration: "none", fontSize: 13, transition: "color 0.15s" }}
          onMouseEnter={e => (e.currentTarget.style.color = "#F59E0B")}
          onMouseLeave={e => (e.currentTarget.style.color = "#7A94AE")}>
          <GitBranch size={14} />
          Source Code
          <ExternalLink size={12} />
        </a>
      </div>
    </footer>
  );
}
