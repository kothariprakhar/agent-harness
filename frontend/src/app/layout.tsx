import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentHarness — Deep Research Pipeline",
  description: "Multi-agent orchestration for research-to-article generation with hallucination evaluation",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
