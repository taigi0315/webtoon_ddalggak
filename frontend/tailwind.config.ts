import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./stores/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#1c1f2a",
        slate: "#2a2f3e",
        mist: "#e6e9f0",
        pearl: "#f7f7fb",
        coral: "#ff7a6e",
        ocean: "#3b82f6",
        moss: "#3bb273"
      },
      boxShadow: {
        soft: "0 10px 30px rgba(17, 24, 39, 0.12)",
        lift: "0 15px 40px rgba(17, 24, 39, 0.18)"
      },
      borderRadius: {
        xl2: "1.25rem"
      }
    }
  },
  plugins: []
};

export default config;
