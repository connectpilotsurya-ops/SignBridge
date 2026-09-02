import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

// Deliberately NOT next/font/google here: that loader fetches the font
// CSS from Google at build time, which fails the whole build in any
// network-restricted environment (this sandbox included). The Tailwind
// font stack below falls back to the best-available system UI font
// instead — no external dependency, same visual family (Inter/Manrope
// are both geometric grotesques close to San Francisco/Segoe).

export const metadata: Metadata = {
  title: "SYNTHETIX HR — Proof Before Score",
  description:
    "Explainable candidate-analysis for recruiters. Don't score the claim. Score the evidence.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans bg-bg text-ink-900 antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
