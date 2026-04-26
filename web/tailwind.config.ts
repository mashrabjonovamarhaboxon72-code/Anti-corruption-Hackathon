import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#06070a",
          900: "#0a0c12",
          800: "#11141d",
          700: "#1a1f2c",
          600: "#262b3a",
        },
        accent: {
          400: "#34d399",
          500: "#10b981",
          600: "#059669",
        },
        // Brand "Integrity Green" — used for active workflow steps and any
        // explicit emphasis on the system's integrity guarantees.
        integrity: "#00ff88",
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "Inter", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: {
        glass: "0 8px 32px 0 rgba(0, 0, 0, 0.45)",
      },
      backgroundImage: {
        "grid-fade":
          "radial-gradient(1200px 600px at 50% -10%, rgba(16,185,129,0.12), transparent 60%)",
      },
      keyframes: {
        // Vertical marquee for Broadcast Mode. Content is duplicated in the
        // DOM; -50% completes one full cycle, producing a seamless loop.
        "broadcast-marquee": {
          "0%": { transform: "translateY(0)" },
          "100%": { transform: "translateY(-50%)" },
        },
      },
      animation: {
        // Duration is set per-instance via the --marquee-duration CSS variable
        // so longer feeds scroll proportionally slower.
        "broadcast-marquee":
          "broadcast-marquee var(--marquee-duration, 60s) linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
