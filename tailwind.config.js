/** @type {import('tailwindcss').Config} */
export default {
  // FIX: dark mode via class (set by App.jsx's darkMode state), not system preference
  darkMode: "class",

  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],

  theme: {
    extend: {
      // FIX: brand colours as CSS custom properties so they're easy to update
      colors: {
        brand: {
          50:  "#fff7ed",
          100: "#ffedd5",
          200: "#fed7aa",
          300: "#fdba74",
          400: "#fb923c",
          500: "#f97316",   // primary orange
          600: "#ea580c",
          700: "#c2410c",
          800: "#9a3412",
          900: "#7c2d12",
        },
      },

      fontFamily: {
        // FIX: Noto Sans Devanagari must come before system-ui so Hindi renders correctly
        sans: [
          "Noto Sans",
          "Noto Sans Devanagari",
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
      },

      // FIX: animation for the waveform bars in Recorder.jsx
      keyframes: {
        "wave-pulse": {
          "0%, 100%": { transform: "scaleY(1)" },
          "50%":      { transform: "scaleY(1.5)" },
        },
      },
      animation: {
        "wave-pulse": "wave-pulse 0.8s ease-in-out infinite",
      },

      // FIX: extra max-width for transcript panels on wide screens
      maxWidth: {
        "8xl": "88rem",
      },
    },
  },

  plugins: [],
};
