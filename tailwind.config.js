/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./static/**/*.{js,jsx,ts,tsx}", "./templates/**/*.html"],
  theme: {
    screens: {
      sm: "640px",
      md: "768px",
      lg: "1024px",
      xl: "1280px",
      "2xl": "1536px",
    },
    fontFamily: {
      display: ["Source Serif Pro", "Georgia", "serif"],
      body: ["Synonym", "system-ui", "sans-serif"],
      mono: ["JetBrains Mono", "monospace"], // Adding JetBrains Mono for monospaced text
    },
    extend: {
      colors: {
        primary: {
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
        },
      },
      fontSize: {
        h1: "36", // Adjust as needed
        h2: "2rem", // Adjust as needed
        h3: "1.75rem", // Adjust as needed
        h4: "1.5rem", // Adjust as needed
        h5: "1.25rem", // Adjust as needed
        h6: "1rem", // Adjust as needed
      },
      fontWeight: {
        h1: "700", // Adjust as needed
        h2: "600", // Adjust as needed
        h3: "500", // Adjust as needed
        h4: "400", // Adjust as needed
        h5: "300", // Adjust as needed
        h6: "200", // Adjust as needed
      },
      zIndex: {
        41: "41",
        45: "45",
        51: "51",
        55: "55",
        60: "60",
        65: "65",
        70: "70",
        75: "75",
        80: "80",
        85: "85",
        90: "90",
        95: "95",
        100: "100",
      },
    },
  },
  plugins: [],
};
