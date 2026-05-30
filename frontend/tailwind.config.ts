import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        tunnel: {
          bg: "#070814",
          panel: "#111423",
          focus: "#8b5cf6",
          mint: "#34d399"
        }
      },
      boxShadow: {
        glow: "0 0 80px rgba(139, 92, 246, 0.28)"
      }
    }
  },
  plugins: []
};

export default config;
