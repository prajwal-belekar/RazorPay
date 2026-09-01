import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#0A0A0B",
          dark: "#050506",
        },
        surface: {
          DEFAULT: "#111113",
          elevated: "#17171A",
          hover: "#1C1C20",
        },
        border: {
          DEFAULT: "#26262B",
          subtle: "#1F1F24",
          highlight: "#3A3A42",
        },
        primaryText: "#F5F5F5",
        secondaryText: "#A1A1AA",
        mutedText: "#71717A",
        success: {
          DEFAULT: "#10B981",
          hover: "#059669",
          muted: "#064E3B",
          bg: "rgba(16, 185, 129, 0.08)",
          border: "rgba(16, 185, 129, 0.25)",
        },
        warning: {
          DEFAULT: "#F59E0B",
          hover: "#D97706",
          muted: "#78350F",
          bg: "rgba(245, 158, 11, 0.08)",
          border: "rgba(245, 158, 11, 0.25)",
        },
        danger: {
          DEFAULT: "#EF4444",
          hover: "#DC2626",
          muted: "#7F1D1D",
          bg: "rgba(239, 68, 68, 0.08)",
          border: "rgba(239, 68, 68, 0.25)",
        },
        ai: {
          DEFAULT: "#8B5CF6",
          hover: "#7C3AED",
          light: "#A78BFA",
          bg: "rgba(139, 92, 246, 0.1)",
          border: "rgba(139, 92, 246, 0.3)",
        },
        info: {
          DEFAULT: "#3B82F6",
          hover: "#2563EB",
          light: "#60A5FA",
          bg: "rgba(59, 130, 246, 0.08)",
          border: "rgba(59, 130, 246, 0.25)",
        },
      },
      borderRadius: {
        lg: "0.5rem",
        md: "0.375rem",
        sm: "0.25rem",
      },
      boxShadow: {
        subtle: "0 1px 2px 0 rgba(0, 0, 0, 0.3)",
        glow: "0 0 20px -5px rgba(139, 92, 246, 0.15)",
        card: "0 4px 12px rgba(0, 0, 0, 0.4)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Courier New", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
