"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, Shield } from "lucide-react";

const NAV_LINKS = [
  { href: "/fraud",      label: "FraudSense" },
  { href: "/compliance", label: "RegGuard" },
  { href: "/finlens",   label: "FinLens" },
  { href: "/mlops",     label: "MLOps" },
  { href: "/security",  label: "Security" },
  { href: "/infra",     label: "Infrastructure" },
  { href: "/#blogs",    label: "Research & Blogs" },
];

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 50,
        background: scrolled ? "rgba(6,10,14,0.92)" : "transparent",
        borderBottom: scrolled ? "1px solid #1C2D3E" : "1px solid transparent",
        backdropFilter: scrolled ? "blur(20px)" : "none",
        transition: "all 0.3s",
      }}
    >
      <div className="section-container" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", height: 64 }}>

        {/* Logo */}
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
          <svg width="26" height="26" viewBox="0 0 26 26" fill="none">
            <rect x="1" y="1" width="24" height="24" rx="5" stroke="#F59E0B" strokeWidth="1.5" />
            <line x1="13" y1="5" x2="13" y2="21" stroke="#F59E0B" strokeWidth="1.5" />
            <line x1="7"  y1="9"  x2="13" y2="9"  stroke="#8B5CF6" strokeWidth="1.5" />
            <line x1="7"  y1="13" x2="13" y2="13" stroke="#10B981" strokeWidth="1.5" />
            <line x1="7"  y1="17" x2="13" y2="17" stroke="#3B82F6" strokeWidth="1.5" />
            <circle cx="7"  cy="9"  r="1.8" fill="#8B5CF6" />
            <circle cx="7"  cy="13" r="1.8" fill="#10B981" />
            <circle cx="7"  cy="17" r="1.8" fill="#3B82F6" />
          </svg>
          <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 17, color: "#E8F0F8" }}>
            Artha AI
          </span>
          {/* live badge */}
          <div style={{ display: "flex", alignItems: "center", gap: 5, padding: "2px 9px", borderRadius: 99, background: "rgba(16,185,129,0.09)", border: "1px solid rgba(16,185,129,0.25)", fontSize: 10, fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, letterSpacing: "0.1em", color: "#10B981" }}>
            <span style={{ position: "relative", display: "inline-flex", width: 6, height: 6 }}>
              <span style={{ position: "absolute", inset: 0, borderRadius: "50%", background: "#10B981", animation: "ping 1.4s ease-in-out infinite", opacity: 0.6 }} />
              <span style={{ position: "relative", display: "block", width: 6, height: 6, borderRadius: "50%", background: "#10B981" }} />
            </span>
            API LIVE
          </div>
        </Link>

        {/* Desktop links */}
        <div className="hidden md:flex" style={{ gap: 28, alignItems: "center" }}>
          {NAV_LINKS.map(l => {
            const active = pathname === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                style={{
                  color: active ? "#F59E0B" : "#7A94AE",
                  fontWeight: 500, fontSize: 13,
                  textDecoration: "none",
                  transition: "color 0.15s",
                  borderBottom: active ? "1px solid #F59E0B" : "1px solid transparent",
                  paddingBottom: 2,
                }}
                onMouseEnter={e => { if (!active) (e.currentTarget as HTMLElement).style.color = "#E8F0F8"; }}
                onMouseLeave={e => { if (!active) (e.currentTarget as HTMLElement).style.color = "#7A94AE"; }}
              >
                {l.label}
              </Link>
            );
          })}
        </div>

        {/* CTA */}
        <div className="hidden md:flex" style={{ gap: 10 }}>
          <Link href="/platform" className="btn-ghost" style={{ padding: "8px 16px", fontSize: 13 }}>
            Live Platform
          </Link>
          <Link href="/fraud" className="btn-primary" style={{ padding: "8px 18px", fontSize: 13 }}>
            Explore Modules
          </Link>
        </div>

        {/* Mobile toggle */}
        <button
          className="md:hidden"
          onClick={() => setMobileOpen(!mobileOpen)}
          style={{ background: "none", border: "none", color: "#E8F0F8", cursor: "pointer", padding: 6 }}
        >
          {mobileOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div style={{ background: "#0A1018", borderTop: "1px solid #1C2D3E", padding: "12px 24px" }}>
          {NAV_LINKS.map(l => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setMobileOpen(false)}
              style={{ display: "block", padding: "12px 0", color: pathname === l.href ? "#F59E0B" : "#7A94AE", fontSize: 14, fontWeight: 500, textDecoration: "none", borderBottom: "1px solid #1C2D3E" }}
            >
              {l.label}
            </Link>
          ))}
        </div>
      )}

      <style>{`
        @keyframes ping {
          75%, 100% { transform: scale(2); opacity: 0; }
        }
      `}</style>
    </nav>
  );
}
