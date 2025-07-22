/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{html,tg}",
    "./components/**/*.{html,tg}",
    "./templates/**/*.html"
  ],
  theme: {
    extend: {
      colors: {
        'tagonpy': {
          50: '#f0f9ff',
          500: '#3b82f6',
          900: '#1e3a8a'
        }
      }
    },
  },
  plugins: [],
}