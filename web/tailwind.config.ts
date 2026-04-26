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
    },
  },
  plugins: [],
};

export default config;
