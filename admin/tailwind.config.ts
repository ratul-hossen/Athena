import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        athina: {
          bg: "#000000",
          surface: "#161617",
          surface2: "#1D1D1F",
          surface3: "#2C2C2E",
          text: "#F5F5F7",
          muted: "#86868B",
          border: "rgba(255, 255, 255, 0.09)",
          accent: "#F59E0B",
          danger: "#FF6961",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
