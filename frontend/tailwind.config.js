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
        slate: {
          950: '#060e20',
          900: '#0b1326',
          850: '#0F172A',
          800: '#171f33',
          750: '#1E293B',
          700: '#2d3449',
          600: '#334155',
          500: '#424754',
          400: '#8c909f',
          300: '#c2c6d6',
          200: '#dae2fd',
          100: '#e6e8ea',
          50: '#f8fafc',
        },
        brand: {
          blue: '#3b82f6',
          indigo: '#6366f1',
          emerald: '#10b981',
          amber: '#f59e0b',
          crimson: '#ef4444',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      }
    },
  },
  plugins: [],
}
