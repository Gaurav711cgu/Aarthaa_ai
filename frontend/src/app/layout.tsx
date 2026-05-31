import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Artha AI — Enterprise FinTech Intelligence Platform",
  description:
    "Real-time fraud detection, regulatory compliance RAG, and statement auditing. Production-grade ML system built for RBI/FEMA/PMLA compliance.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
