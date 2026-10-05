/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        civic: {
          50: '#f0f7ff',
          100: '#e0effe',
          200: '#bae0fd',
          300: '#7cc8fb',
          400: '#36abf6',
          500: '#0c90e6',
          600: '#0273c5',
          700: '#035ca0',
          800: '#074e84',
          900: '#0c426e',
          950: '#082a49',
        },
      },
    },
  },
  plugins: [],
};
