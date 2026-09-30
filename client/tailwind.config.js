/** @type {import('tailwindcss').Config} */
const scale = (n) => Object.fromEntries(['50','100','200','300','400','500','600','700','800','900','950'].map((k) => [k, `rgb(var(--${n}-${k}) / <alpha-value>)`]));
const tok = (n) => `rgb(var(--${n}) / <alpha-value>)`;
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        zinc: scale('z'),
        slate: scale('z'),
        neutral: scale('z'),
        background: tok('surf-0'),
        card: 'rgba(15, 23, 42, 0.75)',
        border: 'rgba(255, 255, 255, 0.08)',
        fg: tok('fg'),
        inv: tok('inv'),
        invtext: tok('invtext'),
        surf0: tok('surf-0'), surf1: tok('surf-1'), surf2: tok('surf-2'), surf3: tok('surf-3'),
        line1: tok('line-1'), line2: tok('line-2'),
        accent: {
          blue: '#3b82f6',
          purple: '#a855f7',
          cyan: '#06b6d4',
          emerald: '#10b981',
          rose: '#f43f5e'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['Fira Code', 'Consolas', 'monospace']
      }
    },
  },
  plugins: [],
}
