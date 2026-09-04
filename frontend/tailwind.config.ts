import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#dbe6fe",
          500: "#3b6fed",
          600: "#2c56d1",
          700: "#2444a8",
        },
      },
    },
  },
  plugins: [],
};

export default config;
