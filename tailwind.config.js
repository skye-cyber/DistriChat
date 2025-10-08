/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./central_server/static/**/*.{js,jsx,ts,tsx}",
    "./central_server/templates/**/*.html",
  ],
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
        "cyber-blue": "#00d9ff",
        "cyber-purple": "#8a2be2",
        "cyber-dark": "#0a0a1f",
        "cyber-darker": "#050510",
      },
      animation: {
        "pulse-glow": "pulse-glow 2s infinite",
        "slide-in-float": "float-slide-in 6s ease-in-out infinite",
        float: "float 4s ease-in-out infinite",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": {
            boxShadow: "0 0 5px #00d9ff, 0 0 10px #00d9ff, 0 0 15px #00d9ff",
          },
          "50%": {
            boxShadow: "0 0 10px #00d9ff, 0 0 20px #00d9ff, 0 0 30px #00d9ff",
          },
        },
        "slide-in-float": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
        float: {
          "0%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
          "100%": { transform: "translateY(0)" },
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
