/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        monsoon: { 50: "#eef6ff", 500: "#2563eb", 600: "#1d4ed8", 700: "#1e40af" },
      },
    },
  },
  plugins: [],
};
