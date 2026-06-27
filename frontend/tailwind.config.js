/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        dmpi: {
          red: '#CC0000',
          green: '#2D6A2D',
          gold: '#F5A623',
        },
      },
    },
  },
  plugins: [],
}
