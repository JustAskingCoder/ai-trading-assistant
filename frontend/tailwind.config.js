/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0b0e14',
          800: '#111722',
          700: '#1b2230',
          600: '#263042',
          500: '#344054'
        },
        trade: {
          green: '#10b981',
          greenBg: '#064e3b',
          red: '#ef4444',
          redBg: '#7f1d1d',
          yellow: '#f59e0b',
          blue: '#3b82f6'
        }
      },
      fontFamily: {
        sans: ['Nunito Sans', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
