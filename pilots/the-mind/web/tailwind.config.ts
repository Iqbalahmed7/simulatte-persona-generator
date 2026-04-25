import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#050505",
        parchment: "#E9E6DF",
        signal: "#A8FF3E",
        static: "#9A9997",
      },
      fontFamily: {
        condensed: ["Barlow Condensed", "Arial Narrow", "sans-serif"],
        sans: ["Barlow", "Calibri", "sans-serif"],
        mono: ["Martian Mono", "IBM Plex Mono", "monospace"],
      },
      borderRadius: { DEFAULT: "0px", sm: "0px", md: "0px", lg: "0px", xl: "0px", full: "9999px" },
    },
  },
  plugins: [],
};

export default config;
