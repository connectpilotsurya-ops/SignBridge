import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Executive Ultra-clean White & Iris studio theme
        bg: "#FAFBFD",
        surface: "#FFFFFF",
        "surface-raised": "#F4F5FF",
        border: "#E2E8F0",
        "border-strong": "#C7D2FE",
        ink: {
          900: "#0F172A",
          700: "#334155",
          500: "#64748B",
          400: "#94A3B8",
          300: "#CBD5E1",
        },
        primary: {
          DEFAULT: "#5D5FEF",
          hover: "#4B4ACF",
          soft: "rgba(93, 95, 239, 0.08)",
        },
        accent: {
          DEFAULT: "#6366F1",
          hover: "#4F46E5",
          soft: "rgba(99, 102, 241, 0.12)",
        },
        success: { DEFAULT: "#10B981", soft: "rgba(16, 185, 129, 0.12)" },
        warning: { DEFAULT: "#F59E0B", soft: "rgba(245, 158, 11, 0.12)" },
        danger: { DEFAULT: "#EF4444", soft: "rgba(239, 68, 68, 0.12)" },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        display: [
          "Manrope",
          "Inter",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      borderRadius: {
        xl: "14px",
        "2xl": "20px",
        "3xl": "28px",
      },
      boxShadow: {
        card: "0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)",
        pop: "0 12px 32px rgba(93, 95, 239, 0.15)",
        glass: "0 8px 32px 0 rgba(31, 38, 135, 0.07)",
        glow: "0 0 20px rgba(93, 95, 239, 0.25)",
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "glass-gradient": "linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(244,245,255,0.7) 100%)",
        "brand-gradient": "linear-gradient(135deg, #5D5FEF 0%, #6366F1 50%, #8B5CF6 100%)",
      },
    },
  },
  plugins: [],
};

export default config;

